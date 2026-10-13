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
