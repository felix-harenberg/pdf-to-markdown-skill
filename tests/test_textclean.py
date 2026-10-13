from textclean import clean_pages, collapse_blank_lines, dehyphenate, strip_page_furniture

TOPICS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]


def page(n):
    topic = TOPICS[n - 1]
    return (f"ACME Bericht 2026\n\n{topic} ist das Thema dieser Seite.\n\n"
            f"Mehr zu {topic}.\n\nSeite {n} von 5")


def test_repeating_header_and_footer_removed():
    cleaned = strip_page_furniture([page(n) for n in range(1, 6)])
    assert all("ACME" not in p and "von 5" not in p for p in cleaned)
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
