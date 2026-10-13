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
