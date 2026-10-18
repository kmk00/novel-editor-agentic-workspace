#!/usr/bin/env python3
"""
plain_text.py -- Convert a chapter25.txt-style story file (dialogue lines
`Name: [text]` / `???: [text]`, optionally with emotion tags <<...>>)
into clean, readable plain text.

Transformations:
  - `Name: [text]` / `???: [text]`  ->  `text` (dialogue becomes its own
    paragraph, speaker label and brackets removed; with --quotes it is
    wrapped in typographic quotes “...” instead).
  - Emotion/direction tags `<<...>>` are removed (e.g. `<<calm>>`), so
    emotion-tagged files (`-tagged.txt`) can be converted as well.
  - Narration paragraphs, ALL-CAPS headings and `<...>` system/transmission
    lines are kept exactly as they are.
  - Blank lines are normalized to exactly one between blocks.

Usage:
  python3 plain_text.py IN.txt [OUT.txt] [--quotes]

Default output: `<input-basename>-plain.txt` next to the input (the input
file is never overwritten).
"""
import argparse
import re
import sys
from pathlib import Path

DIALOGUE_RE = re.compile(r"^\s*([^:\n]+):\s*\[(.*)\]\s*$")
TAG_RE = re.compile(r"\s*<<[^<>]*>>")
DOUBLE_ANGLE_RE = re.compile(r"<<([^<>]*)>>")
SINGLE_ANGLE_RE = re.compile(r"<([^<>]*)>")


def clean_inner(text: str) -> str:
    """Strip emotion tags <<...>> and tidy the whitespace they leave behind."""
    text = TAG_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def to_parens(text: str) -> str:
    """Convert ANY angle brackets to parentheses — raw `<>` breaks TTS.

    `<<...>>` -> `(...)`, `<...>` -> `(...)`.
    """
    text = DOUBLE_ANGLE_RE.sub(r"(\1)", text)
    text = SINGLE_ANGLE_RE.sub(r"(\1)", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="chapter-style .txt file")
    ap.add_argument("output", nargs="?", help="output path (default: <name>-plain.txt)")
    ap.add_argument("--quotes", action="store_true",
                    help="wrap dialogue in typographic quotes (“...”) instead of leaving it bare")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        print(f"ERROR: input file not found: {src}", file=sys.stderr)
        return 1
    dst = Path(args.output) if args.output else src.with_name(src.stem + "-plain.txt")

    lines = src.read_text(encoding="utf-8").split("\n")

    out = []
    dialogue = narration = other = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        m = DIALOGUE_RE.match(line)
        if m and not stripped.startswith("<"):
            text = clean_inner(m.group(2))
            if text:
                out.append(f"“{text}”" if args.quotes else text)
                dialogue += 1
            else:
                out.append("")  # empty dialogue -> just a blank separator
            continue
        if "<<" in stripped and ">>" in stripped:
            line = clean_inner(line) or line
        out.append(line)
        if stripped.startswith("<"):
            other += 1
        elif stripped.isupper() or (stripped.isupper() is False and stripped.upper() == stripped and any(c.isalpha() for c in stripped)):
            other += 1  # ALL-CAPS heading
        else:
            narration += 1

    # normalize blank lines: exactly one between blocks, none at the edges
    result = []
    for l in out:
        if l == "" and (not result or result[-1] == ""):
            continue
        if l != "":
            l = to_parens(l)
        result.append(l)
    while result and result[-1] == "":
        result.pop()

    dst.write_text("\n".join(result) + "\n", encoding="utf-8")
    print(f"Wrote: {dst}")
    print(f"Dialogue lines: {dialogue} | narration paragraphs: {narration} | headings/system blocks: {other}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
