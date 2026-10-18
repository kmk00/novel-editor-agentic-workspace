#!/usr/bin/env python3
"""
apply_speaker_map.py — apply an agent-authored line->speaker map.

.. deprecated::
    Moved to ``tools/legacy/``. Prefer resolving speakers directly in the
    chapter file (see ``ln-speaker-resolution``); this helper is kept only for
    migrating old workflows.

The agent resolves `???` speakers by reading the chapter, then records the
decisions in a plain text map file (one entry per line):

    123 Yanami        # comment allowed after #
    456 Tamaki

This tool rewrites only those `???:` speaker labels; every other byte is kept,
so the result passes `tools/resolve_names.py --check`.

Usage:
  python3 tools/legacy/apply_speaker_map.py <original.txt> <map.txt> <out.txt>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DIALOGUE_RE = re.compile(r"^(\s*)([^:\[\]]+?)(\s*):\s*\[(.*)\](\s*)$")


def load_map(path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").split("\n"):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        out[int(parts[0])] = parts[1].strip()
    return out


def main() -> int:
    orig, map_path, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    mapping = load_map(map_path)
    lines = orig.read_text(encoding="utf-8").split("\n")
    applied = 0
    for n, name in mapping.items():
        if n < 1 or n > len(lines):
            print(f"WARN: line {n} out of range", file=sys.stderr)
            continue
        m = DIALOGUE_RE.match(lines[n - 1])
        if not m or m.group(2).strip() != "???":
            print(f"WARN: line {n} is not a '???:' line", file=sys.stderr)
            continue
        lines[n - 1] = f"{m.group(1)}{name}{m.group(3)}: [{m.group(4)}]{m.group(5)}"
        applied += 1
    dst.write_text("\n".join(lines), encoding="utf-8")
    print(f"Applied {applied} resolutions -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
