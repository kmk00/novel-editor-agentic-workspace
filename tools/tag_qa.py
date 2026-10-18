#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA for an emotion-tagged chapter file (`-tagged.txt`, canonical `<<...>>` format).

Checks everything the `ln-emotion-tagging` / `ln-generate-full` skills require
beyond the mandatory coverage gate, and exits non-zero when something is wrong.

Usage:
    python3 tools/tag_qa.py <tagged.txt> [--quiet]

Exit codes: 0 = clean, 1 = problems found, 2 = usage/file error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_coverage import is_banned  # noqa: E402

DIALOGUE_RE = re.compile(r"^\s*([^:\[\]]+?)\s*:\s*\[")
TAGGED_RE = re.compile(r"^\s*([^:\[\]]+?)\s*:\s*\[<<([^<>]*)>>\s+(\S.*)\]\s*$")
TAG_RE = re.compile(r"<<[^<>]*>>")
TERMINAL_RE = re.compile(r"[.!?…][\"'”’]?$")
PL_RE = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tagged", type=Path)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.tagged.is_file():
        print(f"ERROR: no such file: {args.tagged}", file=sys.stderr)
        return 2

    lines = args.tagged.read_text(encoding="utf-8").split("\n")
    dialogue = [l for l in lines if DIALOGUE_RE.match(l)]
    tagged = [l for l in dialogue if "<<" in l]
    untagged = [l for l in dialogue if "<<" not in l]

    problems: list[str] = []
    tags: list[str] = []
    for i, line in enumerate(lines, 1):
        stripped = TAG_RE.sub("", line)
        if "<<" in stripped or ">>" in stripped:
            problems.append(f"line {i}: raw << or >> outside a tag")
        m = TAGGED_RE.match(line)
        if not m:
            continue
        tag, spoken = m.group(2), m.group(3)
        tags.append(tag)
        if tag.count(",") > 1:
            problems.append(f"line {i}: tag has >1 comma: <<{tag}>>")
        if not tag[:1].isupper():
            problems.append(f"line {i}: tag does not start uppercase: <<{tag}>>")
        if PL_RE.search(tag):
            problems.append(f"line {i}: tag is not English: <<{tag}>>")
        bad = is_banned(tag)
        if bad:
            problems.append(f"line {i}: banned sound-effect word {bad!r}: <<{tag}>>")
        words = re.findall(r"[A-Za-z']+", tag)
        if len(words) < 4:
            problems.append(f"line {i}: tag too short ({len(words)} words): <<{tag}>>")
        if len(words) > 24:
            problems.append(f"line {i}: tag too long ({len(words)} words): <<{tag}>>")
        if not TERMINAL_RE.search(spoken):
            problems.append(f"line {i}: spoken text without terminal punctuation: {spoken[-40:]!r}")

    for line in dialogue:
        if "<<" in line and not TAGGED_RE.match(line):
            problems.append(f"malformed tagged line: {line[:80]!r}")

    if not args.quiet:
        print(f"File        : {args.tagged}")
        print(f"Lines       : {len(lines)}")
        print(f"Dialogue    : {len(dialogue)}  (tagged {len(tagged)}, untagged {len(untagged)})")
        if tags:
            wc = [len(re.findall(r"[A-Za-z']+", t)) for t in tags]
            print(f"Tags        : min {min(wc)} / avg {sum(wc)/len(wc):.1f} / max {max(wc)} words")
        if problems:
            print(f"\nPROBLEMS ({len(problems)}):")
            for p in problems[:80]:
                print(f"  - {p}")
            if len(problems) > 80:
                print(f"  … and {len(problems) - 80} more")
            print("\nFAIL")
            return 1
        print("\nPASS — all tagging rules satisfied")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
