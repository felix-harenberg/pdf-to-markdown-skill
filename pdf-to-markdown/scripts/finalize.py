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
    try:
        decisions = json.loads(decisions_file.read_text(encoding="utf-8")) if decisions_file.is_file() else {}
    except json.JSONDecodeError as error:
        print(f"{decisions_file} is not valid JSON ({error}). Nothing was changed; fix the file "
              "and run again (a backslash must be written as \\\\).", file=sys.stderr)
        return 1
    md, missing = apply_decisions(args.markdown.read_text(encoding="utf-8"), decisions)
    args.markdown.write_text(md, encoding="utf-8")
    if missing:
        print(f"Warning: no decision for {', '.join(missing)} - dropped.")
    shutil.rmtree(args.workdir, ignore_errors=True)
    print(f"Wrote {args.markdown.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
