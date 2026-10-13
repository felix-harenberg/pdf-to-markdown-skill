# pdf-to-markdown Skill – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein auf GitHub veröffentlichter Claude-Skill, der PDFs in LLM-taugliches Markdown umwandelt. Deko-Bilder werden verworfen, informative Bilder durch Textbeschreibungen ersetzt.

**Architecture:** `convert.py` extrahiert per `pymupdf4llm` Markdown pro Seite und verwirft Bilder heuristisch (`imagefilter.py`). Übrige Bilder ersetzt es durch Platzhalter plus Manifest und bereinigt den Text (`textclean.py`). Claude bewertet die Kandidaten-Bilder und schreibt `decisions.json`. `finalize.py` setzt die Entscheidungen ein. Ohne Python/pymupdf liest Claude das PDF nativ (Fallback, nur in `SKILL.md`).

**Tech Stack:** Python ≥3.10, pymupdf4llm (bringt pymupdf mit), pytest, GitHub Actions, gh CLI.

**Spec:** `docs/superpowers/specs/2026-10-13-pdf-to-markdown-design.md`

## Global Constraints

- Python ≥3.10. Einzige Laufzeit-Abhängigkeit: `pymupdf4llm`.
- Eigener Code unter MIT. pymupdf (AGPL) wird **nicht** mitgeliefert, nur als Abhängigkeit genannt.
- **Niemals** das private, grafiklastige Marketing-PDF des Nutzers (lokal, evals/local/blueprint.pdf), daraus erzeugtes Markdown oder Fragen dazu committen (privates/fremdes Material). Lokale Eval-Dateien liegen in `evals/local/` (gitignored).
- Keine Test-PDFs im Repo. Tests erzeugen ihre PDFs selbst.
- README und SKILL.md auf Englisch (öffentliches Repo). Bildbeschreibungen im Output in der Sprache des Dokuments.
- Bildfilter-Schwellen (aus Spec): längste Seite < 100 pt **oder** Fläche < 2 % der Seite → `small`; gleiches Bild auf ≥3 Seiten → `repeated`; Seitenverhältnis > 8:1 → `banner`; ≥90 % der Seitenfläche **und** Seite hat Text → `background`.
- Header/Footer: normalisierte Randzeilen (oberste/unterste 3) auf ≥30 % und ≥3 Seiten.
- Platzhalter-Format: `<!-- IMG:p{seite}_{n} -->` (Seite und n 1-basiert).
- Exit-Codes `convert.py`: 0 ok, 1 Eingabefehler, 2 Abhängigkeit fehlt, 3 vermutlich Scan.
- Auf Windows: venv-Python ist `.venv/Scripts/python`.

## File Structure

```
pdf-to-markdown/                         (Repo-Root, C:\CodingProjects\pdf-to-markdown)
├── .gitignore
├── LICENSE                              MIT
├── README.md                            Installation, Nutzung, Qualitätszahlen
├── pyproject.toml                       nur pytest-Konfiguration
├── .github/workflows/test.yml           CI
├── pdf-to-markdown/                     ← Skill-Ordner
│   ├── SKILL.md
│   ├── requirements.txt
│   └── scripts/
│       ├── textclean.py                 reine Textfunktionen (Header/Footer, Seitenzahlen, Trennung)
│       ├── imagefilter.py               reine Heuristik: ImageInfo → Drop-Grund
│       ├── convert.py                   CLI: PDF → MD + manifest + Kandidaten-PNGs
│       └── finalize.py                  CLI: decisions.json → finales MD
├── tests/
│   ├── pdfs.py                          Builder für synthetische Test-PDFs
│   ├── conftest.py                      sys.path + Fixtures
│   ├── test_textclean.py
│   ├── test_imagefilter.py
│   ├── test_convert.py
│   └── test_finalize.py
└── evals/
    ├── README.md                        Ablauf des Q&A-Qualitätstests
    ├── attention.json                   Fragen zum arXiv-Paper 1706.03762
    └── local/                           (gitignored) private PDFs/Fragen
```

---

### Task 1: GitHub-Repo anlegen und Spec pushen

**Files:**
- Create: `.gitignore`, `LICENSE`, `README.md` (Platzhalter mit einem Satz, Ausbau in Task 8)

**Interfaces:**
- Produces: Remote `origin` → `https://github.com/<user>/pdf-to-markdown-skill`, Branch `main`

- [ ] **Step 1: gh-Login prüfen**

Run: `gh auth status`
Expected: „Logged in to github.com account <user>“. Falls `gh` fehlt oder nicht eingeloggt ist: den Nutzer bitten, `gh auth login` auszuführen, oder das GitHub-MCP-Tool `mcp__github__create_repository` verwenden (dann in Step 4 per `git remote add` verbinden).

- [ ] **Step 2: Basisdateien anlegen**

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
evals/local/
*_images/
```

`LICENSE`: Standard-MIT-Text, `Copyright (c) 2026 <Name>`. Den Namen aus `git config user.name` übernehmen.

`README.md`:
```markdown
# pdf-to-markdown

A Claude skill that turns PDFs into clean, LLM-ready Markdown. Work in progress.
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore LICENSE README.md
git commit -m "chore: add license, gitignore and readme stub"
```

- [ ] **Step 4: Öffentliches Repo erstellen und pushen** (vorher kurz beim Nutzer bestätigen: Name `pdf-to-markdown-skill`, öffentlich)

```bash
gh repo create pdf-to-markdown-skill --public --source . --remote origin --push \
  --description "Claude skill: convert PDFs into clean, LLM-ready Markdown - decorative images dropped, charts described as text"
```
Expected: URL des Repos wird ausgegeben. `git log origin/main --oneline` zeigt beide Commits.

---

### Task 2: Python-Umgebung und Abhängigkeiten

**Files:**
- Create: `pdf-to-markdown/requirements.txt`, `pyproject.toml`

**Interfaces:**
- Produces: `.venv/` mit pymupdf4llm + pytest. Bestätigtes `to_markdown`-Verhalten (Chunk-Format, Bildreferenzen), auf das Task 5 baut.

- [ ] **Step 1: venv anlegen und installieren**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install pymupdf4llm pytest
.venv/Scripts/python -m pip show pymupdf4llm pymupdf
```
Expected: beide Pakete mit Version. Die Version von pymupdf4llm als `X.Y.Z` notieren.

- [ ] **Step 2: requirements.txt und pyproject.toml schreiben**

`pdf-to-markdown/requirements.txt` (X.Y = installierte Major.Minor-Version):
```
pymupdf4llm>=X.Y
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: API-Smoke-Test** (bestätigt die Annahmen, auf denen convert.py aufbaut)

```bash
.venv/Scripts/python - <<'EOF'
import tempfile, pymupdf, pymupdf4llm
doc = pymupdf.open(); p = doc.new_page()
p.insert_text((72, 100), "Hallo Welt " * 20, fontsize=11)
pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 300), False); pix.set_rect(pix.irect, (200, 30, 30))
p.insert_image(pymupdf.Rect(72, 200, 372, 425), stream=pix.tobytes("png"))
with tempfile.TemporaryDirectory() as d:
    chunks = pymupdf4llm.to_markdown(doc, page_chunks=True, write_images=True, image_path=d,
                                     image_format="png", dpi=150, image_size_limit=0, show_progress=False)
    print(type(chunks), len(chunks), sorted(chunks[0].keys()))
    print(chunks[0]["text"])
EOF
```
Expected: eine Liste mit 1 Dict, Keys enthalten `text`. Der Text enthält „Hallo Welt“ und eine Referenz `![](...png)`.
**Falls Parameter abgelehnt werden oder das Format abweicht:** die Abweichung hier dokumentieren (als Kommentar im Plan) und den `to_markdown`-Aufruf bzw. `IMAGE_REF_RE` in Task 5 entsprechend anpassen. Die Tests in Task 5 prüfen das Verhalten, nicht den Aufruf.

- [ ] **Step 4: Commit**

```bash
git add pdf-to-markdown/requirements.txt pyproject.toml
git commit -m "chore: add dependencies and pytest config"
```

---

### Task 3: Text-Bereinigung (`textclean.py`)

**Files:**
- Create: `pdf-to-markdown/scripts/textclean.py`, `tests/conftest.py`, `tests/test_textclean.py`

**Interfaces:**
- Produces:
  - `strip_page_furniture(pages: list[str]) -> list[str]`
  - `dehyphenate(text: str) -> str`
  - `collapse_blank_lines(text: str) -> str` (Ergebnis endet mit genau einem `\n`)
  - `clean_pages(pages: list[str]) -> str`

- [ ] **Step 1: conftest anlegen**

`tests/conftest.py`:
```python
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "pdf-to-markdown" / "scripts"
sys.path.insert(0, str(SCRIPTS))
```

- [ ] **Step 2: Failing Tests schreiben**

`tests/test_textclean.py`:
```python
from textclean import clean_pages, collapse_blank_lines, dehyphenate, strip_page_furniture

TOPICS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]


def page(n):
    topic = TOPICS[n - 1]
    return (f"ACME Bericht 2026\n\n{topic} ist das Thema dieser Seite.\n\n"
            f"Mehr zu {topic}.\n\nSeite {n} von 5")


def test_repeating_header_and_footer_removed():
    cleaned = strip_page_furniture([page(n) for n in range(1, 6)])
    assert all("ACME" not in p and "Seite" not in p for p in cleaned)
    assert "Gamma ist das Thema dieser Seite." in cleaned[2]
    assert "Mehr zu Gamma." in cleaned[2]


def test_lone_page_number_removed_without_repetition():
    assert strip_page_furniture(["Text oben.\nMitte.\n- 7 -"]) == ["Text oben.\nMitte."]


def test_number_inside_body_kept():
    text = "a\nb\nc\n42\nd\ne\nf"
    assert strip_page_furniture([text]) == [text]


def test_placeholders_never_removed():
    pages = [f"<!-- IMG:p{n}_1 -->\n\n{TOPICS[n - 1]} Text." for n in range(1, 6)]
    assert strip_page_furniture(pages) == pages


def test_headings_never_removed():
    pages = [f"# Kapitel {n}\n\n{TOPICS[n - 1]} Text." for n in range(1, 6)]
    assert strip_page_furniture(pages) == pages


def test_dehyphenate():
    assert dehyphenate("Die Daten-\nbank") == "Die Datenbank"
    assert dehyphenate("Die Daten- bank") == "Die Datenbank"
    assert dehyphenate("Vor- und Nachteile") == "Vor- und Nachteile"
    assert dehyphenate("per E-\nMail") == "per E-\nMail"


def test_collapse_blank_lines():
    assert collapse_blank_lines("\na\n \n\n\nb\n\n") == "a\n\nb\n"


def test_clean_pages_joins_pages():
    assert clean_pages(["Erste Seite.", "Zweite Seite."]) == "Erste Seite.\n\nZweite Seite.\n"
```

- [ ] **Step 3: Tests laufen lassen, sie müssen fehlschlagen**

Run: `.venv/Scripts/python -m pytest tests/test_textclean.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'textclean'`

- [ ] **Step 4: Implementieren**

`pdf-to-markdown/scripts/textclean.py`:
```python
"""Cleanup for markdown that was extracted page by page from a PDF."""
import re
from collections import Counter

EDGE_LINES = 3          # non-empty lines at the top/bottom of a page that may be header/footer
REPEAT_SHARE = 0.3      # a header/footer appears on >= 30 % of pages ...
REPEAT_MIN_PAGES = 3    # ... and on at least 3 pages
PLACEHOLDER_PREFIX = "<!-- IMG:"

LOWER = "a-zß-öø-ÿ"
HYPHEN_RE = re.compile(rf"(\w)-(?:\n| )(?=[{LOWER}])(?!(?:und|oder|bis|sowie|and|or|to)\b)")
PAGE_NUMBER_RE = re.compile(
    r"^\W*(?:page|seite|s\.|p\.)?\s*\d{1,4}(?:\s*(?:/|of|von)\s*\d{1,4})?\W*$", re.IGNORECASE
)


def _edges(lines):
    filled = [i for i, line in enumerate(lines) if line.strip()]
    return set(filled[:EDGE_LINES] + filled[-EDGE_LINES:])


def _key(line):
    return re.sub(r"\d+", "#", line.strip().lower())


def strip_page_furniture(pages: list[str]) -> list[str]:
    """Remove headers, footers and page numbers from the top and bottom of each page."""
    split = [page.split("\n") for page in pages]
    counts = Counter()
    for lines in split:
        counts.update({_key(lines[i]) for i in _edges(lines)})
    threshold = max(REPEAT_MIN_PAGES, REPEAT_SHARE * len(pages))
    repeating = {k for k, n in counts.items() if n >= threshold and re.search(r"[^\W\d_]", k)}

    def furniture(line):
        if line.lstrip().startswith(("#", PLACEHOLDER_PREFIX)):  # headings like "# Kapitel 3" stay
            return False
        return _key(line) in repeating or bool(PAGE_NUMBER_RE.match(line.strip()))

    cleaned = []
    for lines in split:
        edges = _edges(lines)
        kept = [line for i, line in enumerate(lines) if not (i in edges and furniture(line))]
        cleaned.append("\n".join(kept).strip("\n"))
    return cleaned


def dehyphenate(text: str) -> str:
    """Join words split across lines ("Daten-\\nbank" -> "Datenbank")."""
    return HYPHEN_RE.sub(r"\1", text)


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"(?:[ \t]*\n){3,}", "\n\n", text).strip() + "\n"


def clean_pages(pages: list[str]) -> str:
    return collapse_blank_lines(dehyphenate("\n\n".join(strip_page_furniture(pages))))
```

- [ ] **Step 5: Tests laufen lassen**

Run: `.venv/Scripts/python -m pytest tests/test_textclean.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add pdf-to-markdown/scripts/textclean.py tests/conftest.py tests/test_textclean.py
git commit -m "feat: add text cleanup for headers, footers, page numbers and hyphenation"
```

---

### Task 4: Bild-Heuristik (`imagefilter.py`)

**Files:**
- Create: `pdf-to-markdown/scripts/imagefilter.py`, `tests/test_imagefilter.py`

**Interfaces:**
- Produces:
  - `@dataclass ImageInfo(page: int, width_pt: float, height_pt: float, page_area_pt: float, digest: str, page_has_text: bool)`
  - `drop_reasons(images: list[ImageInfo]) -> list[str | None]`, wobei der Grund einer von `"repeated"`, `"small"`, `"banner"`, `"background"` ist oder `None` (= behalten)

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_imagefilter.py`:
```python
from imagefilter import ImageInfo, drop_reasons

A4 = 595 * 842


def img(page=1, w=300, h=200, digest="a", text=True):
    return ImageInfo(page=page, width_pt=w, height_pt=h, page_area_pt=A4, digest=digest, page_has_text=text)


def test_regular_figure_kept():
    assert drop_reasons([img()]) == [None]


def test_icon_dropped():
    assert drop_reasons([img(w=16, h=16)]) == ["small"]


def test_tiny_area_dropped():
    assert drop_reasons([img(w=120, h=60)]) == ["small"]


def test_logo_on_three_pages_dropped():
    assert drop_reasons([img(page=p, digest="logo") for p in (1, 2, 3)]) == ["repeated"] * 3


def test_same_image_on_two_pages_kept():
    assert drop_reasons([img(page=p, digest="x") for p in (1, 2)]) == [None, None]


def test_banner_dropped():
    assert drop_reasons([img(w=500, h=40)]) == ["banner"]


def test_background_dropped_only_when_page_has_text():
    full_with_text = img(w=595, h=842, digest="a", text=True)
    full_without_text = img(w=595, h=842, digest="b", text=False)
    assert drop_reasons([full_with_text, full_without_text]) == ["background", None]
```

- [ ] **Step 2: Tests laufen lassen, sie müssen fehlschlagen**

Run: `.venv/Scripts/python -m pytest tests/test_imagefilter.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'imagefilter'`

- [ ] **Step 3: Implementieren**

`pdf-to-markdown/scripts/imagefilter.py`:
```python
"""Heuristics that decide which extracted images carry no information."""
from collections import defaultdict
from dataclasses import dataclass

MIN_SIDE_PT = 100        # images whose longest side is below 100 pt are icons/bullets
MIN_AREA_SHARE = 0.02    # ... as are images covering less than 2 % of the page
REPEAT_PAGES = 3         # the same image on >= 3 pages is a logo or decoration
MAX_ASPECT = 8           # thinner than 1:8 means rules and banners
BACKGROUND_SHARE = 0.9   # >= 90 % of a page that also has text means background


@dataclass
class ImageInfo:
    page: int
    width_pt: float
    height_pt: float
    page_area_pt: float
    digest: str
    page_has_text: bool


def drop_reasons(images: list[ImageInfo]) -> list[str | None]:
    """Return a drop reason per image, or None for images worth showing to Claude."""
    pages_per_digest = defaultdict(set)
    for image in images:
        pages_per_digest[image.digest].add(image.page)

    reasons = []
    for image in images:
        area = image.width_pt * image.height_pt
        short, long = sorted((image.width_pt, image.height_pt))
        if len(pages_per_digest[image.digest]) >= REPEAT_PAGES:
            reasons.append("repeated")
        elif long < MIN_SIDE_PT or area < MIN_AREA_SHARE * image.page_area_pt:
            reasons.append("small")
        elif short == 0 or long / short > MAX_ASPECT:
            reasons.append("banner")
        elif image.page_has_text and area >= BACKGROUND_SHARE * image.page_area_pt:
            reasons.append("background")
        else:
            reasons.append(None)
    return reasons
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv/Scripts/python -m pytest tests/test_imagefilter.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add pdf-to-markdown/scripts/imagefilter.py tests/test_imagefilter.py
git commit -m "feat: add heuristic image filter"
```

---

### Task 5: Konverter (`convert.py`)

**Files:**
- Create: `pdf-to-markdown/scripts/convert.py`, `tests/pdfs.py`, `tests/test_convert.py`
- Modify: `tests/conftest.py` (Fixtures ergänzen)

**Interfaces:**
- Consumes: `clean_pages` (Task 3), `ImageInfo`, `drop_reasons` (Task 4)
- Produces:
  - CLI `python convert.py <pdf> [--out <md>] [--workdir <dir>]` und `main(argv: list[str] | None) -> int`
  - Default `out` = `<pdf>.md`, Default `workdir` = `<out-stem>_images/` neben `out`
  - `<workdir>/manifest.json`: Liste von `{"id", "page", "path", "width_pt", "height_pt", "context_before", "context_after"}`
  - `<workdir>/<id>.png` (max. 1024 px Kante)
  - MD beginnt mit Front Matter `---\ntitle: "…"\nsource: "…"\npages: N\n---`

- [ ] **Step 1: PDF-Builder schreiben**

`tests/pdfs.py`:
```python
"""Builders for synthetic test PDFs with known content."""
from pathlib import Path

import pymupdf

SCRIPTS = Path(__file__).resolve().parents[1] / "pdf-to-markdown" / "scripts"

LOREM = ("Dies ist ein normaler Absatz mit genug Text, damit die Schriftgröße "
         "des Fließtexts eindeutig die häufigste im Dokument ist. ") * 4


def png(width, height, rgb=(200, 30, 30), bars=False):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    pix.set_rect(pix.irect, (255, 255, 255) if bars else rgb)
    if bars:
        step = (width - 80) // 4
        for i, share in enumerate((0.3, 0.5, 0.7, 0.9)):
            x0 = 40 + i * step
            pix.set_rect(pymupdf.IRect(x0, int(height * (1 - share)), x0 + step * 3 // 4, height - 10),
                         (30, 90 + 40 * i, 200))
    return pix.tobytes("png")


LOGO = png(240, 240, (10, 120, 60))


def add_chrome(page, number):
    """Header text, page number footer and a logo, identical on every page."""
    page.insert_text((72, 40), "ACME Quartalsbericht 2026", fontsize=9)
    page.insert_text((290, 815), f"Seite {number}", fontsize=9)
    page.insert_image(pymupdf.Rect(460, 20, 580, 140), stream=LOGO)


def build_sample_pdf(path):
    """5 pages: heading/list/hyphen/icon, chart, table, banner, background image."""
    doc = pymupdf.open()

    p = doc.new_page()
    add_chrome(p, 1)
    p.insert_text((72, 180), "Einleitung", fontsize=24)
    p.insert_textbox(pymupdf.Rect(72, 200, 523, 420), LOREM, fontsize=11)
    p.insert_text((72, 440), "Die Daten-", fontsize=11)
    p.insert_text((72, 454), "bank speichert alle Werte.", fontsize=11)
    p.insert_text((72, 480), "• Erstens", fontsize=11)
    p.insert_text((72, 494), "• Zweitens", fontsize=11)
    p.insert_image(pymupdf.Rect(72, 520, 88, 536), stream=png(32, 32, (0, 0, 0)))

    p = doc.new_page()
    add_chrome(p, 2)
    p.insert_textbox(pymupdf.Rect(72, 160, 523, 300), "Der Umsatz entwickelte sich wie folgt. " + LOREM, fontsize=11)
    p.insert_image(pymupdf.Rect(72, 320, 472, 580), stream=png(800, 520, bars=True))
    p.insert_textbox(pymupdf.Rect(72, 600, 523, 780), "Danach folgt die Analyse der Kosten. " + LOREM, fontsize=11)

    p = doc.new_page()
    add_chrome(p, 3)
    p.insert_textbox(pymupdf.Rect(72, 160, 523, 280), LOREM, fontsize=11)
    for r, row in enumerate([("Jahr", "Umsatz"), ("2024", "5 Mio"), ("2025", "8 Mio")]):
        for c, cell in enumerate(row):
            rect = pymupdf.Rect(72 + c * 150, 300 + r * 25, 222 + c * 150, 325 + r * 25)
            p.draw_rect(rect, color=(0, 0, 0), width=0.8)
            p.insert_text((rect.x0 + 5, rect.y1 - 8), cell, fontsize=11)

    p = doc.new_page()
    add_chrome(p, 4)
    p.insert_image(pymupdf.Rect(72, 160, 522, 180), stream=png(900, 40, (120, 120, 120)))
    p.insert_textbox(pymupdf.Rect(72, 200, 523, 400), LOREM, fontsize=11)

    p = doc.new_page()
    p.insert_image(p.rect, stream=png(595, 842, (235, 235, 245)))
    add_chrome(p, 5)
    p.insert_textbox(pymupdf.Rect(72, 200, 523, 400), LOREM, fontsize=11)

    doc.set_metadata({"title": "ACME Testbericht"})
    doc.save(path)


def build_scanned_pdf(path):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_image(p.rect, stream=png(595, 842, (240, 240, 240)))
    doc.save(path)


def build_long_pdf(path, pages=300):
    doc = pymupdf.open()
    for n in range(1, pages + 1):
        p = doc.new_page()
        p.insert_text((72, 80), f"Abschnitt {n}", fontsize=18)
        p.insert_textbox(pymupdf.Rect(72, 100, 523, 400), LOREM, fontsize=11)
    doc.save(path)
```

- [ ] **Step 2: Fixtures in conftest ergänzen**

`tests/conftest.py` komplett ersetzen:
```python
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "pdf-to-markdown" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pdfs import build_sample_pdf  # noqa: E402


@pytest.fixture(scope="session")
def sample_result(tmp_path_factory):
    """Run convert.main once on the sample PDF; return (exit code, markdown, manifest, workdir)."""
    import convert

    tmp = tmp_path_factory.mktemp("sample")
    pdf, out = tmp / "sample.pdf", tmp / "sample.md"
    build_sample_pdf(pdf)
    code = convert.main([str(pdf), "--out", str(out)])
    workdir = tmp / "sample_images"
    manifest = json.loads((workdir / "manifest.json").read_text(encoding="utf-8"))
    return code, out.read_text(encoding="utf-8"), manifest, workdir
```

- [ ] **Step 3: Failing Tests schreiben**

`tests/test_convert.py`:
```python
import re
import subprocess
import sys
import time
from pathlib import Path

import convert
from pdfs import SCRIPTS, build_long_pdf, build_scanned_pdf


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
```

- [ ] **Step 4: Tests laufen lassen, sie müssen fehlschlagen**

Run: `.venv/Scripts/python -m pytest tests/test_convert.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'convert'`

- [ ] **Step 5: Implementieren**

`pdf-to-markdown/scripts/convert.py`:
```python
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
IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def text_length(markdown):
    return len(IMAGE_REF_RE.sub("", markdown).strip())


def find_images(chunks, doc, image_dir):
    """Yield (page_index, ref, path, ImageInfo) for every image pymupdf4llm wrote and referenced."""
    for page_index, chunk in enumerate(chunks):
        rect = doc[page_index].rect
        has_text = text_length(chunk["text"]) >= MIN_TEXT_CHARS_PER_PAGE
        for match in IMAGE_REF_RE.finditer(chunk["text"]):
            path = Path(match.group(1))
            if not path.is_file():
                path = image_dir / path.name
            if not path.is_file():
                continue
            pix = pymupdf.Pixmap(str(path))
            yield page_index, match.group(0), path, ImageInfo(
                page=page_index + 1,
                width_pt=pix.width * 72 / DPI,
                height_pt=pix.height * 72 / DPI,
                page_area_pt=rect.width * rect.height,
                digest=hashlib.sha1(pix.samples).hexdigest(),
                page_has_text=has_text,
            )


def save_scaled(source, target):
    pix = pymupdf.Pixmap(str(source))
    while max(pix.width, pix.height) > MAX_EDGE_PX:
        pix.shrink(1)
    pix.save(str(target))


def place_images(chunks, images, workdir):
    """Swap kept image refs for placeholders and remove the rest. Returns pages, manifest, drop counts."""
    pages = [chunk["text"] for chunk in chunks]
    manifest, dropped, per_page = [], Counter(), Counter()
    for (page_index, ref, path, info), reason in zip(images, drop_reasons([i[3] for i in images])):
        if reason:
            dropped[reason] += 1
            pages[page_index] = pages[page_index].replace(ref, "", 1)
            continue
        per_page[page_index] += 1
        image_id = f"p{page_index + 1}_{per_page[page_index]}"
        target = workdir / f"{image_id}.png"
        save_scaled(path, target)
        pages[page_index] = pages[page_index].replace(ref, f"\n\n<!-- IMG:{image_id} -->\n\n", 1)
        manifest.append({"id": image_id, "page": page_index + 1, "path": str(target.resolve()),
                         "width_pt": round(info.width_pt), "height_pt": round(info.height_pt)})
    # refs whose file could not be found are removed as well
    return [IMAGE_REF_RE.sub("", page) for page in pages], manifest, dropped


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
```

- [ ] **Step 6: Tests laufen lassen**

Run: `.venv/Scripts/python -m pytest tests/test_convert.py -v`
Expected: 9 passed.
Falls einzelne Struktur-Tests (`test_structure_preserved`) an pymupdf4llm-Eigenheiten scheitern, etwa weil Überschrift oder Tabelle anders erkannt werden: das tatsächliche MD ausgeben (`print(md)`) und prüfen, ob das **Test-PDF** unrealistisch ist (dann den Builder anpassen) oder der **Code** etwas verliert (dann den Code fixen). Assertions nie einfach lockern, ohne den Grund im Commit zu nennen.

- [ ] **Step 7: Gesamte Suite und Commit**

Run: `.venv/Scripts/python -m pytest -v`
Expected: alle Tests grün (8 + 7 + 9)

```bash
git add pdf-to-markdown/scripts/convert.py tests/pdfs.py tests/conftest.py tests/test_convert.py
git commit -m "feat: add PDF to markdown converter with image candidates"
```

---

### Task 6: Finalisierung (`finalize.py`)

**Files:**
- Create: `pdf-to-markdown/scripts/finalize.py`, `tests/test_finalize.py`

**Interfaces:**
- Consumes: `collapse_blank_lines` (Task 3), Platzhalter-Format und Workdir aus Task 5
- Produces:
  - `apply_decisions(md: str, decisions: dict[str, str]) -> tuple[str, list[str]]` (neues MD, IDs ohne Entscheidung)
  - CLI `python finalize.py <md> <workdir>` / `main(argv) -> int`, liest `<workdir>/decisions.json`, löscht `<workdir>`

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_finalize.py`:
```python
import json

from finalize import apply_decisions, main

MD = "Text davor.\n\n<!-- IMG:p2_1 -->\n\nText danach.\n<!-- IMG:p3_1 -->\n"


def test_description_inserted_and_drop_removed():
    out, missing = apply_decisions(MD, {"p2_1": "> **[Abbildung: Chart]** Umsatz steigt.", "p3_1": "drop"})
    assert out == "Text davor.\n\n> **[Abbildung: Chart]** Umsatz steigt.\n\nText danach.\n"
    assert missing == []


def test_missing_decision_dropped_and_reported():
    out, missing = apply_decisions(MD, {"p2_1": "drop"})
    assert "IMG" not in out
    assert missing == ["p3_1"]


def test_main_writes_markdown_and_removes_workdir(tmp_path):
    md, work = tmp_path / "doc.md", tmp_path / "doc_images"
    md.write_text(MD, encoding="utf-8")
    work.mkdir()
    (work / "p2_1.png").write_bytes(b"png")
    (work / "decisions.json").write_text(json.dumps({"p2_1": "drop", "p3_1": "drop"}), encoding="utf-8")
    assert main([str(md), str(work)]) == 0
    assert md.read_text(encoding="utf-8") == "Text davor.\n\nText danach.\n"
    assert not work.exists()


def test_main_without_decisions_drops_everything(tmp_path, capsys):
    md, work = tmp_path / "doc.md", tmp_path / "doc_images"
    md.write_text(MD, encoding="utf-8")
    work.mkdir()
    assert main([str(md), str(work)]) == 0
    assert "IMG" not in md.read_text(encoding="utf-8")
    assert "p2_1, p3_1" in capsys.readouterr().out
```

- [ ] **Step 2: Tests laufen lassen, sie müssen fehlschlagen**

Run: `.venv/Scripts/python -m pytest tests/test_finalize.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'finalize'`

- [ ] **Step 3: Implementieren**

`pdf-to-markdown/scripts/finalize.py`:
```python
#!/usr/bin/env python3
"""Replace image placeholders with Claude's decisions and remove the work directory.

Usage: python finalize.py output.md workdir
Reads workdir/decisions.json: {"p2_1": "drop" | "<markdown description>"}.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from textclean import collapse_blank_lines  # noqa: E402

PLACEHOLDER_RE = re.compile(r"<!-- IMG:(p\d+_\d+) -->")


def apply_decisions(md, decisions):
    """Return the markdown with placeholders resolved, plus the ids that had no decision."""
    missing = []

    def replace(match):
        decision = decisions.get(match.group(1))
        if decision is None:
            missing.append(match.group(1))
            return ""
        if decision.strip().lower() == "drop":
            return ""
        return f"\n\n{decision.strip()}\n\n"

    return collapse_blank_lines(PLACEHOLDER_RE.sub(replace, md)), missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args(argv)

    decisions_file = args.workdir / "decisions.json"
    decisions = json.loads(decisions_file.read_text(encoding="utf-8")) if decisions_file.is_file() else {}
    md, missing = apply_decisions(args.markdown.read_text(encoding="utf-8"), decisions)
    args.markdown.write_text(md, encoding="utf-8")
    if missing:
        print(f"Warning: no decision for {', '.join(missing)} - dropped.")
    shutil.rmtree(args.workdir, ignore_errors=True)
    print(f"Wrote {args.markdown.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv/Scripts/python -m pytest -v`
Expected: alle grün (8 + 7 + 9 + 4)

- [ ] **Step 5: Commit**

```bash
git add pdf-to-markdown/scripts/finalize.py tests/test_finalize.py
git commit -m "feat: add finalize step that applies image decisions"
```

---

### Task 7: SKILL.md, README und CI

**Files:**
- Create: `pdf-to-markdown/SKILL.md`, `.github/workflows/test.yml`
- Modify: `README.md` (ersetzen)

**Interfaces:**
- Consumes: CLIs, Exit-Codes, Manifest- und Decisions-Format aus Task 5/6

- [ ] **Step 1: SKILL.md schreiben**

`pdf-to-markdown/SKILL.md`:
````markdown
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

   - Exit 0: continue. The output prints the markdown path and the `Workdir`.
   - Exit 2 (missing dependency): run `pip install -r "SKILL_DIR/requirements.txt"` once and retry. If it still fails, use the **Fallback**.
   - Exit 3 (probably scanned): tell the user OCR is not supported and ask whether to use the **Fallback** instead.

2. **Review image candidates.** Read `<Workdir>/manifest.json`. For each entry, view the image at `path` and read `context_before` / `context_after`. If there are more than 40 candidates, work in batches of 20 and save decisions after each batch.

3. **Write `<Workdir>/decisions.json`**, mapping every id to `"drop"` or to a markdown description:

   ```json
   {"p2_1": "> **[Figure: bar chart]** Revenue 2020-2024 rose from 2.1 to 8.4 M EUR; largest jump in 2022.", "p4_1": "drop"}
   ```

4. **Finalize**

   ```bash
   python "SKILL_DIR/scripts/finalize.py" "<output.md>" "<Workdir>"
   ```

5. **Quality check.** Do not read the whole file. Check the heading outline (`grep -n "^#"`), the beginning, the end and 2-3 random spots. Fix obvious problems (broken heading levels, shredded tables, leftover page furniture) with targeted edits.

6. **Report** the output path, page count, number of images described/dropped and the approximate token count (printed by convert.py).

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
- Do not repeat what `context_before` / `context_after` already say.
- Keep it short: usually 1-3 sentences.

## Fallback (no Python or pymupdf)

Read the PDF directly in blocks of about 20 pages and append the result to the output file block by block. Apply the same rules: markdown headings, lists and tables; no headers, footers or page numbers; images dropped or described as above. Start the file with the same front matter as convert.py (`title`, `source`, `pages`). For PDFs over 100 pages, tell the user first that this reads every page visually and is slower and more expensive.
````

- [ ] **Step 2: README schreiben**

`README.md` ersetzen durch:
````markdown
# pdf-to-markdown

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns PDFs into clean, LLM-ready Markdown, so you can drop them into context without wasting tokens.

- Text, headings, lists and tables preserved
- Headers, footers and page numbers removed, hyphenated words rejoined
- Decorative images (logos, icons, backgrounds, stock photos) dropped
- Informative images (charts, diagrams, tables as images) replaced by short text descriptions written by Claude
- Long PDFs are fine: text is extracted by a script, Claude only looks at the few images that matter

## Install

**Claude Code**

```bash
git clone https://github.com/<user>/pdf-to-markdown-skill
cp -r pdf-to-markdown-skill/pdf-to-markdown ~/.claude/skills/
pip install -r ~/.claude/skills/pdf-to-markdown/requirements.txt
```

**claude.ai / Claude Desktop**

Zip the `pdf-to-markdown/` folder and upload it under *Settings → Capabilities → Skills*. If the Python dependency is not available there, the skill falls back to reading the PDF directly.

## Usage

> Convert `report.pdf` to markdown.

Result: `report.md` next to the PDF.

## How it works

1. `scripts/convert.py` extracts markdown with [pymupdf4llm](https://github.com/pymupdf/RAG), filters images with simple heuristics and leaves placeholders for the rest.
2. Claude looks at each remaining image and either drops it or writes a description.
3. `scripts/finalize.py` puts the descriptions in place.

## Quality

See [evals/](evals/). Results are added after the first evaluation run.

## Development

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r pdf-to-markdown/requirements.txt pytest
.venv/Scripts/python -m pytest
```

## License

MIT for this repository. The dependency PyMuPDF is licensed under AGPL-3.0 (or commercially by Artifex). Check that this fits your use.
````
(`<user>` durch den GitHub-Namen aus Task 1 ersetzen.)

- [ ] **Step 3: CI-Workflow**

`.github/workflows/test.yml`:
```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r pdf-to-markdown/requirements.txt pytest
      - run: python -m pytest -v
```

- [ ] **Step 4: Skill-Frontmatter prüfen**

Run: `head -4 pdf-to-markdown/SKILL.md`
Expected: `name: pdf-to-markdown`. Die description ist eine Zeile unter 1024 Zeichen.

- [ ] **Step 5: Commit, Push, CI prüfen**

```bash
git add pdf-to-markdown/SKILL.md README.md .github/workflows/test.yml
git commit -m "docs: add SKILL.md, README and CI"
git push
gh run watch --exit-status
```
Expected: CI grün auf Ubuntu und Windows.

---

### Task 8: Manueller Skill-Test mit echten PDFs

**Files:**
- Create: nichts im Repo (Ergebnisse unter `evals/local/`, gitignored)

- [ ] **Step 1: Skill lokal installieren**

```bash
mkdir -p ~/.claude/skills
cp -r pdf-to-markdown ~/.claude/skills/
```

- [ ] **Step 2: Test-PDFs bereitstellen**

```bash
mkdir -p evals/local
cp "<Pfad zum privaten PDF>" evals/local/blueprint.pdf
curl -L -o evals/local/attention.pdf https://arxiv.org/pdf/1706.03762
```

- [ ] **Step 3: Konverter direkt laufen lassen und Ausgabe ansehen**

```bash
.venv/Scripts/python pdf-to-markdown/scripts/convert.py evals/local/blueprint.pdf
.venv/Scripts/python pdf-to-markdown/scripts/convert.py evals/local/attention.pdf
```
Notieren: Exit-Code, Seitenzahl, Kandidaten, verworfene Bilder nach Grund. Bei Exit 3 im Blueprint (Text nur als Bild): das ist ein Fund. Dem Nutzer berichten und mit ihm entscheiden, ob der Fallback reicht oder OCR doch nötig wird.
Kandidaten-Bilder stichprobenartig ansehen: Sind echte Deko-Bilder durchgerutscht? Wurden echte Diagramme verworfen? Bei systematischen Fehlern die Schwellen in `imagefilter.py` anpassen, mit einem neuen Unit-Test für den Fall, und committen.

- [ ] **Step 4: End-to-End über den Skill**

In einer **neuen** Claude-Code-Session: „Mach aus evals/local/attention.pdf eine Markdown-Datei.“
Prüfen:
- Löst der Skill aus?
- Folgt Claude dem Workflow?
- Ist `decisions.json` sinnvoll (Figure 1 und 2 beschrieben, nichts Dekoratives)?
- Ist das Workdir am Ende gelöscht?
- Ist der Bericht vollständig?

Danach dasselbe mit `blueprint.pdf`.

- [ ] **Step 5: Fallback testen**

```bash
python -m venv /tmp/nodeps && /tmp/nodeps/Scripts/python "pdf-to-markdown/scripts/convert.py" evals/local/attention.pdf; echo "exit $?"
```
Expected: `exit 2`. Danach in einer neuen Session den Skill mit dem Hinweis „pymupdf ist nicht installierbar, nutze den Fallback“ auf den ersten 10 Seiten von attention.pdf testen.

- [ ] **Step 6: Funde fixen, Tests grün, committen**

Jeder Fix bekommt einen Test (Task 3/4/5-Muster). `.venv/Scripts/python -m pytest -v` muss grün sein.
```bash
git add -A ':!evals/local'
git commit -m "fix: <konkreter Fund aus dem Praxistest>"
```

---

### Task 9: Q&A-Qualitätstest und Ergebnisse im README

**Files:**
- Create: `evals/README.md`, `evals/attention.json`
- Modify: `README.md` (Abschnitt „Quality“)

- [ ] **Step 1: Fragen-Datei für das öffentliche Paper**

`evals/attention.json`:
```json
{
  "pdf_url": "https://arxiv.org/pdf/1706.03762",
  "questions": [
    {"q": "How many identical layers does the encoder stack of the base model have?", "a": "6", "source": "text"},
    {"q": "What is d_model in the base model?", "a": "512", "source": "text"},
    {"q": "How many attention heads does the base model use?", "a": "8", "source": "text"},
    {"q": "What BLEU score does the big Transformer reach on WMT 2014 English-German?", "a": "28.4", "source": "table"},
    {"q": "On which hardware was the model trained?", "a": "8 NVIDIA P100 GPUs", "source": "text"},
    {"q": "How many warmup steps does the learning-rate schedule use?", "a": "4000", "source": "text"},
    {"q": "In the decoder layer diagram, which sub-layer sits between the masked multi-head attention and the feed-forward sub-layer?", "a": "Multi-head attention over the encoder output (encoder-decoder attention)", "source": "figure"},
    {"q": "List the operations of scaled dot-product attention in order as shown in the figure.", "a": "MatMul, Scale, Mask (optional), SoftMax, MatMul", "source": "figure"}
  ]
}
```

- [ ] **Step 2: Ablauf dokumentieren**

`evals/README.md`:
````markdown
# Quality evaluation

Question: can an LLM still answer questions about a PDF when it only gets the generated Markdown?

## Run

1. Download the PDF from `pdf_url` into `evals/local/` and convert it with the skill.
2. Start a fresh Claude session (or subagent) that gets **only** the generated `.md` file and the questions, not the answers or the PDF.
3. Grade each answer against `a` as correct / wrong.
4. Record:
   - accuracy, overall and for `source: figure`
   - Markdown tokens: `chars / 4` (printed by convert.py)
   - approx. PDF tokens when given to Claude directly: `pages × 1,500 + text tokens` (each page is sent as an image plus its text)

Private PDFs and their questions go into `evals/local/` (gitignored), never into the repo.

## Results

| PDF | Pages | Accuracy | Figure questions | MD tokens | PDF tokens (approx.) |
|---|---|---|---|---|---|
````

- [ ] **Step 3: Eval durchführen**

Für `attention.json` die Schritte 1–4 aus `evals/README.md` ausführen. Für die Antworten einen Subagent nutzen, der nur MD und Fragen bekommt. Für das Blueprint-PDF mit dem Nutzer 5–10 Fragen in `evals/local/blueprint.json` festlegen und genauso auswerten. Dieses Ergebnis nur als anonyme Zeile („grafiklastiger Marketing-Guide, N Seiten“) in die Tabelle übernehmen, und nur, wenn der Nutzer zustimmt.
Ziel aus der Spec: ≥90 % richtig. Liegt es darunter: die falschen Antworten analysieren (fehlende Bildbeschreibung? kaputte Tabelle?), in Task-8-Manier fixen und neu messen.

- [ ] **Step 4: Ergebnisse eintragen, README-Abschnitt „Quality“ ersetzen**

Ergebniszeilen in `evals/README.md` eintragen. In `README.md` den Satz unter „Quality“ ersetzen durch eine Zeile pro PDF, z.B. „Attention Is All You Need (15 pages): 8/8 questions answered correctly from the Markdown, ~X tokens instead of ~Y.“

- [ ] **Step 5: Commit und Push**

```bash
git add evals/README.md evals/attention.json README.md
git commit -m "docs: add Q&A evaluation and results"
git push
```

- [ ] **Step 6: Abschlusscheck**

- CI grün (`gh run list --limit 1`)
- `git status` sauber
- `git ls-files | grep -i -E "blueprint|\.pdf$"` liefert **nichts**
