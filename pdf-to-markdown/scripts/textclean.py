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
    """Join words split across lines ("Daten-\nbank" -> "Datenbank")."""
    return HYPHEN_RE.sub(r"\1", text)


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"(?:[ \t]*\n){3,}", "\n\n", text).strip() + "\n"


def clean_pages(pages: list[str]) -> str:
    return collapse_blank_lines(dehyphenate("\n\n".join(strip_page_furniture(pages))))
