#!/usr/bin/env python3
"""
plain_sentences.py -- canonical chapter-format file -> plain reading text.

Turns a chapter file (`Name: [text]` / `???: [text]`, optionally with
`<<emotion>>` tags) into clean plain text for reading / TTS:

  - speaker labels and `[ ]` brackets are removed,
  - every spoken line (`Name: [...]` / `???: [...]`) is kept **in double
    quotation marks** (`“...”`) so dialogue is always distinguishable from the
    narration (`--no-quotes` opts out),
  - emotion/direction tags `<<...>>` are removed,
  - ANY angle brackets `<...>` / `<<...>>` are converted to parentheses `(...)`
    (raw `<>` breaks TTS),
  - EVERY sentence and EVERY dialogue line goes on its own line, separated
    from the next by a blank line (line-blank-line-blank; the default),
  - EVERY line ends with terminal punctuation (`.`, `?`, `!`, `…`);
    a missing mark gets `…` appended,
  - ALL-CAPS headings are kept, standalone, ending with `.`,
  - `<...>` system/transmission lines are kept, converted to `(...)`,
  - unreadable lines (no letters/digits) are dropped,
  - exactly one blank line between blocks, none at the edges.

Usage:
  python3 tools/plain_sentences.py IN.txt [OUT.txt] [--no-quotes] [--compact]
  python3 tools/plain_sentences.py --check OUT.txt

Default output puts a blank line after every line AND wraps every spoken line in
`“...”`. Use `--compact` to keep same-paragraph sentences adjacent instead, and
`--no-quotes` to emit dialogue as bare prose.

Default output: `<input-basename>-plain.txt` next to the input
(the input file is never overwritten).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DIALOGUE_RE = re.compile(r"^\s*([^:\n]+):\s*\[(.*)\]\s*$")
LEAD_TAG_RE = re.compile(r"^\s*<<[^<>]*>>\s*")
DOUBLE_ANGLE_RE = re.compile(r"<<([^<>]*)>>")
SINGLE_ANGLE_RE = re.compile(r"<([^<>]*)>")
TERMINAL = ".!?…"
TERMINAL_END_RE = re.compile(r"[.!?…][\"'”’)\]>]*$")
READABLE_RE = re.compile(r"[0-9A-Za-z\u00C0-\u024F]")

# Abbreviations that must NOT end a sentence when followed by more text.
ABBR = {
    "mr", "mrs", "ms", "dr", "prof", "st", "no", "vs", "etc", "jr", "sr",
    "lt", "gen", "col", "capt", "sgt", "rev", "hon", "pres", "gov", "sen",
    "rep", "maj", "cmdr", "adm", "brig", "fig", "vol", "ch", "approx",
    "dept", "est", "inc", "ltd", "co", "corp", "a.m", "p.m", "e.g", "i.e",
}
ABBR_END_RE = re.compile(r"\b([A-Za-z]{1,5}\.)$")
INITIAL_END_RE = re.compile(r"(?<![A-Za-z0-9-])[A-Z]\.$")
NUMBER_DOT_END_RE = re.compile(r"\d\.$")


def strip_emotion_tags(text: str) -> str:
    """Remove leading `<<emotion>>` direction tag(s) from a dialogue body."""
    prev = None
    while prev != text:
        prev = text
        text = LEAD_TAG_RE.sub("", text)
    return text


def to_parens(text: str) -> str:
    """Convert ANY angle brackets to parentheses — raw `<>` breaks TTS.

    `<<...>>` -> `(...)`, `<...>` -> `(...)`.
    """
    text = DOUBLE_ANGLE_RE.sub(r"(\1)", text)
    text = SINGLE_ANGLE_RE.sub(r"(\1)", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def clean_dialogue(text: str) -> str:
    """Strip leading emotion tags, then convert leftover angle brackets."""
    return to_parens(strip_emotion_tags(text))


def strip_redundant_quotes(text: str) -> str:
    """Drop leaked outer double quotes from a dialogue body before we wrap it
    in our own ``“...”``.

    Source files often keep the book's closing quote inside the `[...]`
    wrapper (`???: [..., right?”]`) or leak a stray `”` mid-line
    (`???: [here”, and then ...]`). Those would produce `“...”“”`-style
    nesting once wrapped, so remove them first.
    """
    s = text.strip()
    # leaked closing quote right before punctuation: `here”, and ...`
    s = re.sub(r"[\u201d\"][ \t]*(?=[,.;:!?\u2026])", "", s)
    s = s.strip()
    # redundant wrapping curly quotes around the whole body
    while s[:1] == "\u201c":
        s = s[1:].lstrip()
    while s[-1:] == "\u201d":
        s = s[:-1].rstrip()
    # straight quotes: only if the whole body is wrapped in them
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    return s


def clean_narration(text: str) -> str:
    """Convert any angle brackets in narration/system text to parentheses."""
    return to_parens(text)


def ensure_terminal(sentence: str) -> str:
    """Guarantee the line ends with terminal punctuation (append `…`).

    Also strips a leading dialogue dash (`—`, `–`, `―`) and trailing dashes.
    """
    s = sentence.strip()
    s = re.sub(r"^[—–―]+\s*", "", s)  # leading dialogue dash -> dropped
    s = re.sub(r"[—–\-]+$", "", s).rstrip()  # trailing dashes -> dropped
    if not s:
        return s
    if TERMINAL_END_RE.search(s):
        return s
    return s + "…"


def split_sentences(text: str) -> list[str]:
    """Split text into sentences on terminal punctuation + whitespace.

    Abbreviations, initials (`J.`) and decimals (`7.5`) do not end a sentence.
    """
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?…])\s+", text)
    merged: list[str] = []
    for part in parts:
        if not part:
            continue
        if merged:
            prev = merged[-1]
            word = prev.rsplit(" ", 1)[-1].lower()
            if (
                ABBR_END_RE.search(prev) and word in ABBR
                or INITIAL_END_RE.search(prev)
                or NUMBER_DOT_END_RE.search(prev)
            ):
                merged[-1] = prev + " " + part
                continue
        merged.append(part)
    return [m.strip() for m in merged if m.strip()]


def is_heading(line: str) -> bool:
    s = line.strip()
    if len(s) < 2 or not re.search(r"[A-ZÀ-Ž]", s):
        return False
    letters = sum(ch.isalpha() for ch in s)
    if letters < max(3, len(s) * 0.5):
        return False
    return s.upper() == s and not re.search(r"(.)\1{9,}", s)


def check_plain(path: Path) -> int:
    """Verify a plain-sentences output: no labels/brackets/tags/???, every line
    terminal-punctuated, no unreadable lines."""
    lines = path.read_text(encoding="utf-8").split("\n")
    problems: list[str] = []
    n = 0
    for i, l in enumerate(lines, 1):
        if not l.strip():
            continue
        n += 1
        if DIALOGUE_RE.match(l):
            problems.append(f"line {i}: speaker label / brackets left: {l[:80]!r}")
        if "???" in l:
            problems.append(f"line {i}: '???' left: {l[:80]!r}")
        if "<<" in l or ">>" in l or "<" in l or ">" in l:
            problems.append(f"line {i}: raw angle bracket left (breaks TTS): {l[:80]!r}")
        if not READABLE_RE.search(l):
            problems.append(f"line {i}: unreadable (no letters/digits): {l[:80]!r}")
        if not TERMINAL_END_RE.search(l):
            problems.append(f"line {i}: no terminal punctuation: {l[:80]!r}")
    print(f"Plain check: {path}")
    print(f"  non-blank lines: {n}")
    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems[:50]:
            print("  " + p)
        return 1
    print("PASS — no labels/???/tags, every line terminal-punctuated.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="chapter-style .txt file")
    ap.add_argument("output", nargs="?", help="output path (default: <name>-plain.txt)")
    ap.add_argument("--quotes", dest="quotes", action="store_true", default=True,
                    help="wrap dialogue sentences in typographic quotes (“...”); "
                         "this is the DEFAULT")
    ap.add_argument("--no-quotes", dest="quotes", action="store_false",
                    help="do NOT wrap dialogue in quotes (dialogue stays bare prose)")
    ap.add_argument("--spaced", action="store_true", default=True,
                    help="put a blank line after EVERY sentence/line "
                         "(line-blank-line-blank); this is the DEFAULT")
    ap.add_argument("--compact", dest="spaced", action="store_false",
                    help="keep same-paragraph sentences adjacent (no blank "
                         "line between every line); opt-out of the default")
    ap.add_argument("--check", metavar="PLAIN.txt",
                    help="verify an existing plain output and exit (no writing)")
    args = ap.parse_args()

    spaced = args.spaced

    if args.check:
        return check_plain(Path(args.check))
    if not args.input:
        ap.error("input file is required (or use --check PLAIN.txt)")

    src = Path(args.input)
    if not src.is_file():
        print(f"ERROR: input file not found: {src}", file=sys.stderr)
        return 1
    dst = Path(args.output) if args.output else src.with_name(src.stem + "-plain.txt")

    lines = src.read_text(encoding="utf-8").split("\n")

    out: list[str] = []
    n_sent = n_dial = n_head = n_sys = n_drop = 0

    def emit_block(block: list[str]) -> None:
        """Append a block of lines followed by a blank separator.

        With `spaced`, every line is separated by a blank line instead of
        keeping same-paragraph sentences adjacent.
        """
        if not block:
            return
        if spaced:
            for b in block:
                out.append(b)
                out.append("")
        else:
            out.extend(block)
            out.append("")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 1) dialogue line -> prose sentences
        m = DIALOGUE_RE.match(line)
        if m and not stripped.startswith("<"):
            text = clean_dialogue(m.group(2))
            if args.quotes:
                text = strip_redundant_quotes(text)
            if not text or not READABLE_RE.search(text):
                n_drop += 1
                continue
            sents = split_sentences(text)
            block = []
            for s in sents:
                s = ensure_terminal(s)
                if not s or not READABLE_RE.search(s):
                    continue
                block.append(f"“{s}”" if args.quotes else s)
                n_sent += 1
            if block:
                n_dial += 1
                emit_block(block)
            continue

        # 2) system / transmission line -> keep as one block, brackets -> ()
        if stripped.startswith("<"):
            text = ensure_terminal(clean_narration(stripped))
            if not READABLE_RE.search(text):
                n_drop += 1
                continue
            n_sys += 1
            emit_block([text])
            continue

        # 3) ALL-CAPS heading -> standalone, dotted
        if is_heading(stripped):
            head = stripped
            if not TERMINAL_END_RE.search(head):
                head += "."
            n_head += 1
            emit_block([head])
            continue

        # 4) narration paragraph -> one sentence per line
        text = clean_narration(stripped)
        if not text or not READABLE_RE.search(text):
            n_drop += 1
            continue
        block = [ensure_terminal(s) for s in split_sentences(text)]
        block = [b for b in block if b and READABLE_RE.search(b)]
        if block:
            n_sent += len(block)
            emit_block(block)

    # collapse repeated blank lines, drop edges
    result: list[str] = []
    for l in out:
        if l == "" and (not result or result[-1] == ""):
            continue
        result.append(l)
    while result and result[-1] == "":
        result.pop()

    dst.write_text("\n".join(result) + "\n", encoding="utf-8")
    print(f"Wrote: {dst}")
    print(
        f"Sentences: {n_sent} | dialogue turns: {n_dial} | headings: {n_head} "
        f"| system lines: {n_sys} | unreadable dropped: {n_drop}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
