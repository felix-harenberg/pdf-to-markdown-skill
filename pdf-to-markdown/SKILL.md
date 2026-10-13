---
name: pdf-to-markdown
description: Convert PDF files into clean, LLM-ready Markdown for use as context. Drops decorative images (logos, icons, backgrounds, stock photos) and replaces informative ones (charts, diagrams, tables shown as images) with concise text descriptions. Use when the user wants to turn a PDF into Markdown or text, make a PDF usable as context for an LLM, or extract a PDF's content without images - e.g. "convert this PDF to markdown", "mach aus dem PDF eine md-Datei".
---

# PDF to Markdown

Produces a single `.md` file next to the PDF: text, headings, lists and tables preserved, headers/footers removed, images either dropped or replaced by short text descriptions. No image files remain.

`SKILL_DIR` below means the directory containing this file.

## Workflow

1. **Convert**

   ```bash
   python "SKILL_DIR/scripts/convert.py" "<input.pdf>" [--out "<output.md>"]
   ```

   - Exit 0: continue. The output prints the markdown path, the `Workdir`, the image counts and an approximate token count.
   - Exit 1: the input path is wrong. Check it with the user.
   - Exit 2 (missing dependency): run `python -m pip install -r "SKILL_DIR/requirements.txt"` once (same `python` as above) and retry. If pip refuses (e.g. "externally managed environment"), create a venv and use its python. If it still fails, use the **Fallback**.
   - Exit 3 (probably scanned): tell the user OCR is not supported and ask whether to use the **Fallback** instead.

2. **Review image candidates.** Read `<Workdir>/manifest.json`. For each entry, view the image at `path` and read `context_before` / `context_after`; `picture_text`, if present, is raw text found inside the image (labels, axis ticks) - use it to read values. It is not in the markdown, so "drop" discards it too: if that text carries content, describe the image instead. If there are more than 40 candidates, work in batches of 20 and save decisions after each batch.

3. **Write `<Workdir>/decisions.json`**, mapping every id to `"drop"` or to a markdown description:

   ```json
   {"p2_1": "> **[Figure: bar chart]** Revenue 2020-2024 rose from 2.1 to 8.4 M EUR; largest jump in 2022.",
    "p3_1": "$$E = mc^2 \\qquad (1)$$",
    "p4_1": "drop"}
   ```

   It must be valid JSON: escape `"` as `\"` and every backslash as `\\` (LaTeX `\frac` is written `\\frac`; an unescaped `\f`, `\t`, `\n` or `\b` silently becomes a control character). With many formulas, build the dict in Python and write it with `json.dump` instead.

4. **Finalize**

   ```bash
   python "SKILL_DIR/scripts/finalize.py" "<output.md>" "<Workdir>"
   ```

   It deletes the workdir. If it exits 1 (invalid `decisions.json`), nothing was changed: fix the file and run it again.

5. **Quality check.** Do not read the whole file. Check the heading outline (`grep -n "^#"`), the beginning, the end, the tables and 2-3 random spots. Fix obvious problems with targeted edits:
   - shredded tables (header split over several rows, words cut across cells): rebuild it from the cell contents
   - headings split over two heading lines: merge them; section labels that duplicate the next heading: remove
   - leftover page furniture, e.g. running section titles repeated at the top of pages

   Designed documents (brochures, e-books) often have a chaotic outline with most headings at one level. Fix splits and duplicates, but do not re-level every heading.

6. **Report** the output path, page count, number of image candidates described/dropped (plus the images convert.py dropped automatically) and the approximate token count (printed by convert.py; descriptions change it only slightly).

## Image decisions

Drop:
- stock photos, decorative illustrations, portraits, mood images
- images whose content the surrounding text already states completely
- anything you would not miss when answering questions about the document

Describe (charts, diagrams, flowcharts, screenshots with relevant content, tables or formulas rendered as images):
- Format: `> **[Figure: <type>]** <content>`, using the document's language for the label (e.g. `Abbildung` in German documents).
- Information, not looks: no colours, styles or layout unless they carry meaning.
- Give concrete numbers, labels, trends, and the order of steps.
- A table shown as an image becomes a markdown table instead of a quote.
- A formula becomes a LaTeX display block `$$...$$`, keeping its equation number, e.g. `\qquad (2)`.
- Do not repeat what `context_before` / `context_after` already say.
- Keep it short: usually 1-3 sentences.

## Fallback (no Python or pymupdf)

Read the PDF directly in blocks of about 20 pages and append the result to the output file block by block. Reading page ranges needs poppler (`pdftoppm`); if the Read tool reports it missing, a small PDF can be read in one go without a page range - otherwise ask the user to install `pymupdf4llm` or poppler. Apply the same rules: markdown headings, lists and tables; no headers, footers or page numbers; images dropped or described as above. Start the file with the same front matter as convert.py (`title`, `source`, `pages`). For PDFs over 100 pages, tell the user first that this reads every page visually and is slower and more expensive.
