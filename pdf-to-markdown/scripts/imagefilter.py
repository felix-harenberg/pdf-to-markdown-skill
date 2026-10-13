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
    kind: str = "picture"  # layout class from pymupdf4llm, e.g. "picture" or "formula"


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
        elif image.kind == "formula":  # equations are thin and small, but never decoration
            reasons.append(None)
        elif long < MIN_SIDE_PT or area < MIN_AREA_SHARE * image.page_area_pt:
            reasons.append("small")
        elif short == 0 or long / short > MAX_ASPECT:
            reasons.append("banner")
        elif image.page_has_text and area >= BACKGROUND_SHARE * image.page_area_pt:
            reasons.append("background")
        else:
            reasons.append(None)
    return reasons
