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
    p.insert_textbox(pymupdf.Rect(72, 160, 523, 300), LOREM + " Der Umsatz entwickelte sich wie folgt.", fontsize=11)
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
