#!/usr/bin/env python3
"""
log_stats.py — append one run entry to the single per-series stats log.

Every `ln-*` skill calls this at the end of a run so that
`series/<slug>/stats.md` becomes the one place that records what was done,
for which file, how long it took, with what resources, and with what result.

Usage:
  python3 tools/log_stats.py <slug> --step <name> --file <path> \
      [--duration <seconds|text>] [--resources <text>] [--result <text>] \
      [--notes <text>]

Example:
  python3 tools/log_stats.py <slug> --step emotion-tagging \
      --file "series/<slug>/VOL02/<stem>-resolved-tagged.txt" --duration 3421 \
      --resources "ollama huihui_ai/gemma-4-abliterated:26b" \
      --result PASS --notes "1731 tagged, 0 fallbacks"
"""
from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path

HEADER = """# Stats — {slug}

One log for the whole series: every skill run, per file. Columns:

- **Timestamp** — when the run finished.
- **Step** — the skill / pipeline stage (e.g. `speaker-resolution`, `emotion-tagging`).
- **File** — the artifact produced (path relative to the repo root).
- **Duration** — wall-clock time (`12.3s`, `4m32s`, `1h02m`).
- **Resources** — model / tool / agent used.
- **Result** — `PASS`, `OK`, `DONE`, `FAIL`, …
- **Notes** — counts, decisions, caveats.

| Timestamp | Step | File | Duration | Resources | Result | Notes |
|---|---|---|---|---|---|---|
"""


def _cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--step", required=True)
    ap.add_argument("--file", default="")
    ap.add_argument("--duration", default="")
    ap.add_argument("--resources", default="")
    ap.add_argument("--result", default="DONE")
    ap.add_argument("--notes", default="")
    ap.add_argument("--series-root", default="series",
                    help="parent directory of the series folders (default: series)")
    args = ap.parse_args()

    path = Path(args.series_root) / args.slug / "stats.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(HEADER.format(slug=args.slug), encoding="utf-8")

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = "| {ts} | {step} | {file} | {dur} | {res} | {result} | {notes} |\n".format(
        ts=ts,
        step=_cell(args.step),
        file=_cell(args.file),
        dur=_cell(args.duration),
        res=_cell(args.resources),
        result=_cell(args.result),
        notes=_cell(args.notes),
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(row)
    print(f"Logged to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
