import re
import subprocess
import sys
import time
from pathlib import Path

import convert
import pymupdf
from pdfs import SCRIPTS, build_long_pdf, build_scanned_pdf, png


def test_only_chart_is_candidate(sample_result):
    code, md, manifest, _ = sample_result
    assert code == 0
    assert [e["id"] for e in manifest] == ["p2_1"]           # logo, icon, banner, background dropped
    assert re.findall(r"<!-- IMG:(\w+) -->", md) == ["p2_1"]
    assert "![" not in md


def test_chart_placeholder_position_and_context(sample_result):
    _, md, manifest, _ = sample_result
    entry = manifest[0]
    assert Path(entry["path"]).is_file()
    assert "Umsatz entwickelte" in entry["context_before"]
    assert "Analyse der Kosten" in entry["context_after"]
    assert md.index("Umsatz entwickelte") < md.index("<!-- IMG:p2_1 -->") < md.index("Analyse der Kosten")


def test_header_footer_removed(sample_result):
    _, md, _, _ = sample_result
    assert "ACME Quartalsbericht" not in md
    assert not re.search(r"Seite \d", md)


def test_structure_preserved(sample_result):
    _, md, _, _ = sample_result
    assert re.search(r"^#{1,3} .*Einleitung", md, re.M)
    assert "Datenbank" in md
    assert re.search(r"\|\s*Jahr\s*\|\s*Umsatz\s*\|", md)
    assert re.search(r"^\s*[-*]\s+.*Erstens", md, re.M)


def test_front_matter(sample_result):
    _, md, _, _ = sample_result
    assert md.startswith('---\ntitle: "ACME Testbericht"\nsource: "sample.pdf"\npages: 5\n---\n')


def test_scanned_pdf_exits_3(tmp_path):
    pdf = tmp_path / "scan.pdf"
    build_scanned_pdf(pdf)
    assert convert.main([str(pdf)]) == 3
    assert not (tmp_path / "scan.md").exists()


def test_missing_file_exits_1(tmp_path):
    assert convert.main([str(tmp_path / "nope.pdf")]) == 1


def test_missing_dependency_exits_2():
    script = SCRIPTS / "convert.py"
    code = ("import sys, runpy; sys.modules['pymupdf4llm'] = None; "
            f"sys.argv = ['convert.py', 'x.pdf']; runpy.run_path(r'{script}', run_name='__main__')")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 2
    assert "pip install" in result.stderr


def test_long_pdf(tmp_path):
    pdf = tmp_path / "long.pdf"
    build_long_pdf(pdf)
    start = time.monotonic()
    assert convert.main([str(pdf)]) == 0
    assert time.monotonic() - start < 60
    md = (tmp_path / "long.md").read_text(encoding="utf-8")
    assert "Abschnitt 1" in md and "Abschnitt 300" in md


def layout_chunk(tmp_path, image_px, box_class="picture", picture_text=None,
                 before="Davor kommt ein Absatz.", after="Danach kommt ein Absatz."):
    """A pymupdf4llm-style page chunk with one image ref inside a layout box of the given class."""
    image = tmp_path / "raw.png"
    image.write_bytes(png(*image_px, bars=True))
    text = f"{before}\n\n![]({image.as_posix()})\n\n"
    if picture_text is not None:
        text += f"<!-- Start of picture text -->\n{picture_text}<!-- End of picture text -->\n\n"
    start = text.index("![")
    chunk = {"text": text + after,
             "page_boxes": [{"class": box_class, "pos": (start, len(text))}]}
    doc = pymupdf.open()
    doc.new_page()
    workdir = tmp_path / "work"
    workdir.mkdir()
    images = list(convert.find_images([chunk], doc, tmp_path))
    return convert.place_images([chunk], images, workdir)


def test_formula_image_is_candidate(tmp_path):
    # pymupdf4llm renders display equations as thin images (287 x 26 pt at 150 dpi)
    pages, manifest, dropped = layout_chunk(tmp_path, (598, 54), box_class="formula")
    assert [e["id"] for e in manifest] == ["p1_1"]
    assert "<!-- IMG:p1_1 -->" in pages[0]
    assert not dropped


def test_picture_text_moves_into_manifest(tmp_path):
    pages, manifest, _ = layout_chunk(tmp_path, (800, 520), picture_text="Umsatz in Mio<br>2024<br>2025<br>")
    assert manifest[0]["picture_text"] == "Umsatz in Mio\n2024\n2025"
    assert "picture text" not in pages[0] and "Umsatz in Mio" not in pages[0]
    assert "<!-- IMG:p1_1 -->" in pages[0] and "Danach kommt" in pages[0]


def test_picture_text_of_dropped_image_kept_in_markdown(tmp_path):
    pages, manifest, dropped = layout_chunk(tmp_path, (40, 40), picture_text="Neu: 30 % Rabatt<br>")
    assert manifest == [] and dropped == {"small": 1}
    assert "Neu: 30 % Rabatt" in pages[0]
    assert "picture text" not in pages[0] and "![" not in pages[0]


def test_full_page_picture_holding_the_page_text_is_not_background(tmp_path):
    # a page whose only text sits inside one full-page picture (1240 x 1755 px = A4 at 150 dpi)
    text = "Unsere Ergebnisse 2025<br>Umsatz stieg um 12 Prozent<br>Kosten sanken um 3 Prozent<br>"
    pages, manifest, dropped = layout_chunk(tmp_path, (1240, 1755), picture_text=text,
                                           before="", after="")
    assert not dropped
    assert manifest[0]["picture_text"].startswith("Unsere Ergebnisse 2025\nUmsatz stieg")


def test_picture_text_of_missing_image_file_kept(tmp_path):
    chunk = {"text": "Text.\n\n![](gone.png)\n\n<!-- Start of picture text -->\nAchse 2024<br>"
                     "<!-- End of picture text -->\n\nMehr Text."}
    doc = pymupdf.open()
    doc.new_page()
    images = list(convert.find_images([chunk], doc, tmp_path))
    pages, manifest, _ = convert.place_images([chunk], images, tmp_path)
    assert images == [] and manifest == []
    assert "Achse 2024" in pages[0] and "gone.png" not in pages[0] and "picture text" not in pages[0]


def test_installed_layout_model_still_knows_formulas():
    # convert.layout_class relies on pymupdf4llm's layout class names; fail loudly if they change
    from pymupdf.layout.onnx.ImageFeatureExtractorV2 import _CLASS_NAMES
    assert {"picture", "formula"} <= set(_CLASS_NAMES)


def test_layout_class_tolerates_unknown_box_format():
    chunk = {"page_boxes": [{"kind": "formula", "range": (0, 10)}, {"class": "formula", "pos": (0, 10)}]}
    assert convert.layout_class(chunk, 5) == "formula"
    assert convert.layout_class({"page_boxes": [{"type": "x"}]}, 5) == "picture"


def test_picture_text_counts_as_page_text():
    # infographic pages may carry all their text inside pictures; they are not "scanned"
    page = "![](a.png)\n\n<!-- Start of picture text -->\n" + "Umsatz " * 10 + "<!-- End of picture text -->"
    assert convert.text_length(page) >= convert.MIN_TEXT_CHARS_PER_PAGE
