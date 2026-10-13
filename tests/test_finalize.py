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


def test_main_with_invalid_json_keeps_everything(tmp_path, capsys):
    # e.g. LaTeX written into decisions.json with unescaped backslashes
    md, work = tmp_path / "doc.md", tmp_path / "doc_images"
    md.write_text(MD, encoding="utf-8")
    work.mkdir()
    (work / "decisions.json").write_text(r'{"p2_1": "$$\mathrm{x}$$"}', encoding="utf-8")
    assert main([str(md), str(work)]) == 1
    assert md.read_text(encoding="utf-8") == MD
    assert work.exists()
    assert "decisions.json" in capsys.readouterr().err
