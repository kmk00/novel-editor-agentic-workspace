#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Voice casting checker for the NOVEL EDITOR pipeline.

Scans a chapter file in the canonical format (`Name: [ ... ]` / `???: [ ... ]`)
and checks every speaker against a per-series `characters.yaml` cast manifest.

Dependency-free (no PyYAML): reads the small subset of YAML used by the manifest
(`narrator:` block, `characters:` block, `Name:` keys, `aliases: [..]` lists).

Usage:
    python3 tools/voice_casting.py <chapter.txt> [characters.yaml] [--allow-missing]

Exit codes:
    0  every speaker is cast (or only `???` / deliberately missing allowed)
    1  at least one speaker has no cast entry
    2  usage / file error
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

DIALOGUE_RE = re.compile(r"^\s*([^:\[\]]+?)\s*:\s*\[")
# keys inside the `characters:` block: 2-space indent, "Name:" (quoted or bare)
CHAR_KEY_RE = re.compile(r"^\s{2}(?:\"([^\"]+)\"|'([^']+)'|([^:#][^:]*?))\s*:\s*$")
ALIASES_RE = re.compile(r"^\s*aliases\s*:\s*\[(.*?)\]", re.IGNORECASE)
TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*$")


def parse_cast(path: Path) -> tuple[set[str], dict[str, str]]:
    """Return (known_names_lowercased -> canonical, alias->canonical)."""
    if not path.exists():
        return set(), {}
    text = path.read_text(encoding="utf-8")
    in_characters = False
    current: str | None = None
    known: dict[str, str] = {}      # lowercase name/alias -> canonical
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m_top = TOP_KEY_RE.match(line)
        if m_top:
            in_characters = m_top.group(1) == "characters"
            current = None
            continue
        if not in_characters:
            continue
        m_key = CHAR_KEY_RE.match(line)
        if m_key:
            current = (m_key.group(1) or m_key.group(2) or m_key.group(3) or "").strip()
            if current:
                known.setdefault(current.lower(), current)
            continue
        m_alias = ALIASES_RE.match(line)
        if m_alias and current:
            for alias in m_alias.group(1).split(","):
                alias = alias.strip().strip("\"'")
                if alias:
                    known.setdefault(alias.lower(), current)
    return known, known


def scan_speakers(path: Path) -> Counter:
    speakers: Counter = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DIALOGUE_RE.match(line)
        if m:
            speakers[m.group(1).strip()] += 1
    return speakers


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapter", type=Path)
    ap.add_argument("characters", type=Path, nargs="?",
                    help="default: <series-dir>/characters.yaml (two levels up from chapter)")
    ap.add_argument("--allow-missing", action="store_true",
                    help="report missing cast but exit 0")
    args = ap.parse_args()

    if not args.chapter.exists():
        print(f"ERROR: chapter not found: {args.chapter}", file=sys.stderr)
        return 2

    cast_path = args.characters
    if cast_path is None:
        cast_path = args.chapter.parent.parent / "characters.yaml"
    if not cast_path.exists():
        print(f"ERROR: cast manifest not found: {cast_path}", file=sys.stderr)
        print("Create one (see docs/VOICES.md, docs/characters.template.yaml).", file=sys.stderr)
        return 2

    known, _ = parse_cast(cast_path)
    speakers = scan_speakers(args.chapter)

    cast, unknown, anon = {}, [], []
    for name, count in speakers.most_common():
        if name == "???":
            anon.append((name, count))
        elif name.lower() in known:
            cast[name] = count
        else:
            unknown.append((name, count))

    print(f"Chapter : {args.chapter}")
    print(f"Cast    : {cast_path}")
    print(f"Speakers: {len(speakers)} distinct, {sum(speakers.values())} dialogue lines\n")

    if cast:
        print("CAST:")
        for name, count in sorted(cast.items(), key=lambda kv: -kv[1]):
            print(f"  {name:<28} {count:>4} lines")
    if anon:
        print("\nUNRESOLVED (`???` — keep unless 100% certain):")
        for name, count in anon:
            print(f"  {name:<28} {count:>4} lines")
    if unknown:
        print("\nMISSING FROM CAST (add to characters.yaml):")
        for name, count in unknown:
            print(f"  {name:<28} {count:>4} lines")

    if unknown and not args.allow_missing:
        print("\nFAIL: uncast speakers found.", file=sys.stderr)
        return 1
    print("\nPASS: every named speaker is cast.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
