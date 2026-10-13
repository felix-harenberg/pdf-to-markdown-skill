# pdf-to-markdown

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns PDFs into clean, LLM-ready Markdown, so you can drop them into context without wasting tokens.

- Text, headings, lists and tables preserved
- Headers, footers and page numbers removed, hyphenated words rejoined
- Decorative images (logos, icons, backgrounds, stock photos) dropped
- Informative images (charts, diagrams, tables as images) replaced by short text descriptions written by Claude
- Long PDFs are fine: text is extracted by a script, Claude only looks at the few images that matter

## Install

**Claude Code** (requires Python 3.10+)

```bash
git clone https://github.com/felix-harenberg/pdf-to-markdown-skill
mkdir -p ~/.claude/skills
cp -r pdf-to-markdown-skill/pdf-to-markdown ~/.claude/skills/
python3 -m pip install -r ~/.claude/skills/pdf-to-markdown/requirements.txt
```

On Windows use `python` instead of `python3`.

**claude.ai / Claude Desktop**

Zip the `pdf-to-markdown/` folder and upload it under *Settings → Capabilities → Skills*. Code execution and file creation must be enabled for the skill to run its scripts. If the Python dependency is not available there, the skill falls back to reading the PDF directly.

## Usage

> Convert `report.pdf` to markdown.

Result: `report.md` next to the PDF.

## How it works

1. `scripts/convert.py` extracts markdown with [pymupdf4llm](https://github.com/pymupdf/RAG), filters images with simple heuristics and leaves placeholders for the rest.
2. Claude looks at each remaining image and either drops it or writes a description.
3. `scripts/finalize.py` puts the descriptions in place.

## Quality

Attention Is All You Need (15 pages): 8/8 questions answered correctly from the Markdown, ~10,400 tokens instead of ~32,400. See [evals/](evals/).

## Development

```bash
# Linux / macOS
python3 -m venv .venv && .venv/bin/python -m pip install -r pdf-to-markdown/requirements.txt pytest
.venv/bin/python -m pytest

# Windows (Git Bash)
python -m venv .venv && .venv/Scripts/python -m pip install -r pdf-to-markdown/requirements.txt pytest
.venv/Scripts/python -m pytest
```

## License

MIT for this repository. The dependency PyMuPDF is licensed under AGPL-3.0 (or commercially by Artifex). Check that this fits your use.
