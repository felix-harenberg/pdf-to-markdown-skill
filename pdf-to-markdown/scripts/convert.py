#!/usr/bin/env python3
"""Convert a PDF into LLM-friendly markdown with placeholders for informative images.

Usage: python convert.py input.pdf [--out output.md] [--workdir dir]
Exit codes: 0 ok, 1 bad input, 2 missing dependency, 3 probably a scanned PDF.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

try:
    import pymupdf
    import pymupdf4llm
except ImportError:
    print("Missing dependency. Install with: pip install pymupdf4llm", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).parent))
from imagefilter import ImageInfo, drop_reasons  # noqa: E402
from textclean import clean_pages  # noqa: E402

DPI = 150
MAX_EDGE_PX = 1024
CONTEXT_CHARS = 300
MIN_TEXT_CHARS_PER_PAGE = 50
IMAGE_LINK = r"!\[[^\]]*\]\(([^)]+)\)"
# an image ref, optionally followed by the text pymupdf4llm found inside the picture
IMAGE_REF_RE = re.compile(
    IMAGE_LINK + r"(?:\s*<!-- Start of picture text -->(.*?)<!-- End of picture text -->)?", re.S)


def text_length(markdown):
    """Length of the page text without image links; text inside pictures counts."""
    return len(re.sub(IMAGE_LINK, "", markdown).strip())


def picture_text(match):
    """Text pymupdf4llm found inside the picture of an IMAGE_REF_RE match, one line per <br>."""
    return (match.group(2) or "").replace("<br>", "\n").strip()


def without_link(match):
    """Replacement for a dropped or missing image: the link goes, the text found in it stays."""
    text = picture_text(match)
    return f"\n\n{text}\n\n" if text else ""


def layout_class(chunk, offset):
    """Class of the pymupdf4llm layout box ("picture", "formula", ...) covering a text offset."""
    for box in chunk.get("page_boxes") or []:
        start, end = box.get("pos") or (0, 0)
        if start <= offset < end:
            return box.get("class") or "picture"
    return "picture"


def find_images(chunks, doc, image_dir):
    """Yield (page_index, IMAGE_REF_RE match, path, ImageInfo) for every image pymupdf4llm wrote."""
    for page_index, chunk in enumerate(chunks):
        rect = doc[page_index].rect
        text = chunk["text"]
        for match in IMAGE_REF_RE.finditer(text):
            # the image's own picture text does not make it a background behind other text
            others = text[:match.start()] + text[match.end():]
            path = Path(match.group(1))
            if not path.is_file():
                path = image_dir / path.name
            if not path.is_file():
                continue
            pix = pymupdf.Pixmap(str(path))
            yield page_index, match, path, ImageInfo(
                page=page_index + 1,
                width_pt=pix.width * 72 / DPI,
                height_pt=pix.height * 72 / DPI,
                page_area_pt=rect.width * rect.height,
                digest=hashlib.sha1(pix.samples).hexdigest(),
                page_has_text=text_length(others) >= MIN_TEXT_CHARS_PER_PAGE,
                kind=layout_class(chunk, match.start()),
            )


def save_scaled(source, target):
    pix = pymupdf.Pixmap(str(source))
    while max(pix.width, pix.height) > MAX_EDGE_PX:
        pix.shrink(1)
    pix.save(str(target))


def place_images(chunks, images, workdir):
    """Swap kept image refs for placeholders and remove the rest. Returns pages, manifest, drop counts.

    Text pymupdf4llm found inside a kept picture moves into the manifest; for dropped
    pictures it stays in the markdown as plain text.
    """
    pages = [chunk["text"] for chunk in chunks]
    manifest, dropped, per_page = [], Counter(), Counter()
    for (page_index, match, path, info), reason in zip(images, drop_reasons([i[3] for i in images])):
        ref = match.group(0)
        if reason:
            dropped[reason] += 1
            pages[page_index] = pages[page_index].replace(ref, without_link(match), 1)
            continue
        per_page[page_index] += 1
        image_id = f"p{page_index + 1}_{per_page[page_index]}"
        target = workdir / f"{image_id}.png"
        save_scaled(path, target)
        pages[page_index] = pages[page_index].replace(ref, f"\n\n<!-- IMG:{image_id} -->\n\n", 1)
        entry = {"id": image_id, "page": page_index + 1, "path": str(target.resolve()),
                 "width_pt": round(info.width_pt), "height_pt": round(info.height_pt)}
        if picture_text(match):
            entry["picture_text"] = picture_text(match)
        manifest.append(entry)
    # refs whose file could not be found are removed as well
    return [IMAGE_REF_RE.sub(without_link, page) for page in pages], manifest, dropped


def add_context(manifest, md):
    for entry in manifest:
        marker = f"<!-- IMG:{entry['id']} -->"
        start = md.index(marker)
        end = start + len(marker)
        entry["context_before"] = md[max(0, start - CONTEXT_CHARS):start].strip()
        entry["context_after"] = md[end:end + CONTEXT_CHARS].strip()


def front_matter(doc, pdf):
    title = (doc.metadata or {}).get("title") or pdf.stem
    return (f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\n"
            f"source: {json.dumps(pdf.name, ensure_ascii=False)}\npages: {doc.page_count}\n---\n\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args(argv)
    if not args.pdf.is_file():
        print(f"Not a file: {args.pdf}", file=sys.stderr)
        return 1
    out = args.out or args.pdf.with_suffix(".md")
    workdir = args.workdir or out.with_name(f"{out.stem}_images")

    doc = pymupdf.open(args.pdf)
    with tempfile.TemporaryDirectory() as raw_dir:
        chunks = pymupdf4llm.to_markdown(
            doc, page_chunks=True, write_images=True, image_path=raw_dir,
            image_format="png", dpi=DPI, image_size_limit=0, show_progress=False,
        )
        if sum(text_length(c["text"]) for c in chunks) < MIN_TEXT_CHARS_PER_PAGE * doc.page_count:
            print("Almost no extractable text: this PDF is probably scanned. OCR is not supported.",
                  file=sys.stderr)
            return 3
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True)
        images = list(find_images(chunks, doc, Path(raw_dir)))
        pages, manifest, dropped = place_images(chunks, images, workdir)

    md = front_matter(doc, args.pdf) + clean_pages(pages)
    add_context(manifest, md)
    out.write_text(md, encoding="utf-8")
    (workdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pages: {doc.page_count}, characters: {len(md)}, approx. tokens: {len(md) // 4}")
    print(f"Image candidates: {len(manifest)}, dropped: {dict(dropped) or 0}")
    print(f"Markdown: {out.resolve()}")
    print(f"Workdir: {workdir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
