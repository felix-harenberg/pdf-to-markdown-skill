# pdf-to-markdown Skill – Design

**Datum:** 2026-10-13
**Status:** Entwurf, wartet auf Review

## Ziel

Ein Claude-Skill (veröffentlicht auf GitHub), der PDFs in hochwertige Markdown-Dateien umwandelt, die sich gut als Kontext für LLMs eignen. Bilder ohne Informationswert werden verworfen. Bilder mit Informationswert (Diagramme, Charts, Tabellen als Bild) werden durch knappe Textbeschreibungen ersetzt. Das Ergebnis ist eine einzelne `.md`-Datei ohne Bilddateien.

## Rahmenbedingungen

- **Umgebungen:** Claude Code **und** claude.ai/Desktop (dasselbe `SKILL.md`)
- **Haupt-PDF-Typen:** digital erzeugte Text-PDFs, auch sehr lange (100+ Seiten). Gescannte PDFs (OCR) und tabellenlastige Spezialfälle sind keine Ziele für v1.
- **Kosten:** Claude soll bei langen PDFs **nicht** jede Seite visuell lesen.

## Ansatz

Hybrid: Ein Python-Skript erledigt die deterministische Arbeit (Textextraktion, Heuristik-Bildfilter). Claude kommt nur dort zum Einsatz, wo Urteilsvermögen nötig ist (relevante Bilder bewerten und beschreiben). Wenn Python oder pymupdf fehlt, liest Claude das PDF nativ (Fallback).

Verworfene Alternativen: rein natives Lesen (zu teuer bei langen PDFs), marker/docling (PyTorch-Abhängigkeit, ungeeignet für claude.ai), pypdf/pdfplumber (schlechtere Erkennung von Struktur und Überschriften).

## Repo-Struktur

```
pdf-to-markdown/
├── README.md               Installation (Claude Code + claude.ai), Beispiel, Qualitätszahlen
├── LICENSE                 MIT (eigener Code; pymupdf ist AGPL und nur Abhängigkeit, nicht mitgeliefert)
├── .github/workflows/test.yml   pytest in CI
├── tests/                  pytest; Test-PDFs werden im Test generiert
├── evals/                  Q&A-Qualitätstest (Fragen pro PDF, Auswertungsanleitung)
└── pdf-to-markdown/        der Skill-Ordner (zippbar für claude.ai)
    ├── SKILL.md
    ├── requirements.txt    pymupdf4llm
    └── scripts/
        ├── convert.py
        └── finalize.py
```

## Komponenten

### `convert.py <input.pdf> [--out <path.md>] [--workdir <dir>]`

- Nutzt `pymupdf4llm` für das Markdown: Überschriften, Listen, Tabellen, fett/kursiv.
- **Text-Bereinigung:**
  - Entfernt Kopf- und Fußzeilen: Zeilen, die auf ≥30 % der Seiten an gleicher Position mit (fast) gleichem Text vorkommen, wobei Ziffern normalisiert werden.
  - Entfernt reine Seitenzahlen.
  - Fügt getrennte Wörter wieder zusammen („Daten-\nbank“ → „Datenbank“).
  - Reduziert überflüssige Leerzeilen.
- **Heuristischer Bildfilter.** Ein Bild wird verworfen, wenn eine dieser Regeln zutrifft:
  - Darstellungsgröße < 100×100 pt **oder** Fläche < 2 % der Seite (Icons, Bullets)
  - Gleicher Bild-Hash (xref/Inhalt) auf ≥3 Seiten (Logos, wiederkehrende Deko)
  - Deckt ≥90 % der Seite ab **und** auf der Seite liegt extrahierbarer Text darüber (Hintergrund)
  - Extremes Seitenverhältnis > 8:1 (Trennlinien, Banner)
- **Vektorgrafiken:** pymupdf4llm rendert Bereiche mit Vektorgrafiken (Charts aus Linien) selbst als Bild (`write_images=True`); sie durchlaufen denselben Filter.
- Jedes verbleibende Bild wird als PNG in `<workdir>/` gespeichert, auf max. 1024 px Kantenlänge skaliert, und im MD durch einen Platzhalter `<!-- IMG:p{seite}_{n} -->` an seiner Leseposition ersetzt.
- Schreibt `<workdir>/manifest.json`: pro Kandidat `id`, `page`, `path`, `width_pt`, `height_pt`, `context_before`, `context_after` (je ~300 Zeichen).
- `<workdir>` ist standardmäßig `<output-stem>_images/` neben der MD-Datei.
- Gibt auf stdout eine kurze Zusammenfassung aus: Seiten, Zeichen, Kandidaten, verworfene Bilder nach Grund.
- **Exit-Codes:** 0 = ok, 2 = Abhängigkeit fehlt (→ Fallback), 3 = PDF hat kaum extrahierbaren Text (vermutlich ein Scan; der Hinweis geht an den Nutzer).

### Bild-Entscheidung durch Claude (in `SKILL.md` beschrieben)

- Claude sieht sich jedes Kandidaten-Bild zusammen mit seinem Kontext an und schreibt `<workdir>/decisions.json`: `{ "p12_3": "drop" | "<beschreibung>" }`.
- **Regeln für die Beschreibung:**
  - Nur Information, keine Optik („blaues Balkendiagramm mit Schatten“ ist falsch).
  - Konkrete Zahlen, Trends und Beschriftungen.
  - Bei Tabellen als Bild: als Markdown-Tabelle.
  - Nichts wiederholen, was schon im umgebenden Text steht.
- **Format:** `> **[Abbildung: <Typ>]** <Inhalt>`
- **Verwerfen:** Stockfotos, dekorative Illustrationen, Porträts ohne Informationswert und Bilder, deren Inhalt der Text vollständig wiedergibt.
- Bei >40 Kandidaten werden sie in Batches verarbeitet, um den Kontext zu schonen.

### `finalize.py <md> <workdir>`

- Ersetzt die Platzhalter anhand von `decisions.json`.
- Ein fehlender Eintrag gilt als `drop`, mit Warnung auf stdout.
- Löscht `<workdir>`.

### Qualitätscheck durch Claude

- Claude liest Überschriften-Gliederung, Anfang, Ende und 2–3 Stichproben, aber nicht das ganze Dokument.
- Offensichtliche Fehler (falsche Überschriften-Hierarchie, zerbrochene Tabellen) korrigiert Claude gezielt per Edit.

### Fallback (kein Python/pymupdf, Exit-Code 2 oder Import-Fehler)

- Zuerst wird `pip install pymupdf4llm` versucht.
- Schlägt das fehl, liest Claude das PDF nativ in Blöcken à ~20 Seiten, wendet dieselben Bild- und Formatregeln an und hängt das Ergebnis Block für Block an die MD-Datei an.
- Bei sehr langen PDFs weist Claude vorher auf die Kosten hin.

## Output

`<pdfname>.md` neben dem PDF (bzw. `--out`). Am Dateianfang steht ein kurzer Kopf mit Titel, Quelle und Seitenzahl.

## Tests

1. **pytest (CI):** Die Test-PDFs werden im Test mit pymupdf generiert. Abgedeckt werden:
   - Logo auf jeder Seite → verworfen
   - Icon → verworfen
   - großes Diagramm → Kandidat mit korrekter Platzhalter-Position
   - Kopf-/Fußzeile und Seitenzahlen → entfernt
   - Überschriften, Tabelle und Liste → korrekt formatiert
   - Silbentrennung → zusammengeführt
   - `finalize.py` → ersetzt und entfernt Platzhalter korrekt, räumt auf
   - 300-Seiten-PDF → vollständig und in < 60 s
2. **Skill-Test (manuell):**
   - Test-PDFs: `C:\FromPhone\TD Social Media Blueprint.pdf` (grafiklastig, 50 MB) und ein frei verfügbares arXiv-Paper mit Diagrammen.
   - Prüfen: Löst der Skill aus? Sind die Bild-Entscheidungen sinnvoll? Funktioniert der Fallback ohne pymupdf?
3. **Q&A-Qualitätstest (`evals/`):**
   - Pro Test-PDF gibt es 5–10 Fragen, ein Teil davon nur über Abbildungen beantwortbar.
   - Ein frischer Claude beantwortet sie nur anhand der MD-Datei.
   - Ziel: ≥90 % richtig, deutlich weniger Tokens als das rohe PDF. Die Ergebnisse kommen ins README.

## Nicht im Umfang (v1)

OCR für Scans, Formeln als LaTeX, mehrspaltige Spezial-Layouts jenseits dessen, was pymupdf4llm leistet, Aufteilung in mehrere Dateien pro Kapitel, Bild-Extraktion als Dateien.
