#!/usr/bin/env python3
"""
epub_to_txt.py -- Extract a story text from an EPUB into the canonical
chapter-format TXT (see docs/CONVENTIONS.md).

Unlike tools/pdf_to_txt.py (which anonymizes every speaker as ???), this script
KEEPS the speaker labels already present in the EPUB source:
paragraphs of the form `Label: “spoken text”` become `Label: [spoken text]`,
so the output is directly compatible with ln-speaker-resolution /
ln-emotion-tagging / ln-plain-copy / the translator.

Output format:
  - Dialogue paragraph  -> one line:  Label: [text]
    (labels already quoted or unquoted in the source; `???` is kept as-is)
  - Narration paragraph -> plain prose, one paragraph per line.
  - Headings (h1-h6)    -> standalone ALL-CAPS block ending with a dot,
    normalized to `CHAPTER 1. NAME.` / `PROLOGUE. NAME.` / `ACT ONE.`.
  - Exactly one blank line between blocks.
  - Blocks with no readable content (page/section numbers, `…`, `“…”`,
    `???: “…”` silence beats) are dropped, per docs/CONVENTIONS.md.

Front/back matter files (cover, TOC, foreword, afterword, insert image pages)
are dropped by default; override with --drop / --keep.

Usage:
  python3 tools/epub_to_txt.py BOOK.epub [OUT.txt] [--drop REGEX]... [--keep REGEX]...
  python3 tools/epub_to_txt.py BOOK.epub --report      # analysis only, no write

Requires: Python 3 stdlib only (zipfile + html.parser).
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

# --- quote characters -------------------------------------------------------
OPENERS = "“\"«„‘"
CLOSERS = "”\"»’"
QUOTE_ANY = OPENERS + CLOSERS

# --- speaker label pattern --------------------------------------------------
# A plausible speaker label: capitalized words (letters, spaces, . ' - &) or ???
LABEL = r"(?:[A-ZÀ-Þ][A-Za-zÀ-ÿ.'’&,\- ]{0,39}|\?\?\?+)"
LABEL_RE = re.compile(
    r"^(?:[" + re.escape(OPENERS) + r"])?(" + LABEL + r")(?:[" + re.escape(CLOSERS) + r"])?\s*:\s*(.+)$", re.S)
LABEL_NOCOLON_RE = re.compile(r"^(\?\?\?+)\s+(?=[" + re.escape(OPENERS) + r"])(.+)$", re.S)
# split a paragraph where a new label was concatenated right after a closing quote
SPLIT_RE = re.compile(
    r"(?<=[" + re.escape(CLOSERS) + r"])"
    r"(?=(?:" + LABEL + r")\s*:\s|(?:\?\?\?+)\s+(?=[" + re.escape(OPENERS) + r"]))"
)

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCK_TAGS = HEADING_TAGS | {"p"}

DEFAULT_DROP = [r"cover", r"^toc$", r"toc\.xhtml$", r"table_of_contents",
                r"afterword", r"foreword", r"insert\d*"]


class BlockParser(HTMLParser):
    """Collect <p> and <hN> blocks as ('tag', text) pairs, in order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._tag: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in BLOCK_TAGS:
            self._tag, self._buf = tag, []
        elif tag == "br" and self._tag:
            self._buf.append(" ")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag == "br" and self._tag:
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS and self._tag == tag:
            text = re.sub(r"[\s\u00a0]+", " ", "".join(self._buf)).strip()
            self.blocks.append((tag, text))
            self._tag = None

    def handle_data(self, data: str) -> None:
        if self._tag:
            self._buf.append(data)


def read_spine(zf: zipfile.ZipFile) -> list[str]:
    """Return the ordered list of content documents from the OPF spine."""
    container = zf.read("META-INF/container.xml").decode("utf-8")
    opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
    opf = zf.read(opf_path).decode("utf-8")
    base = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""

    manifest: dict[str, str] = {}
    for m in re.finditer(r"<item\b([^>]*)/?>", opf):
        attrs = m.group(1)
        mid = re.search(r'id="([^"]+)"', attrs)
        href = re.search(r'href="([^"]+)"', attrs)
        mt = re.search(r'media-type="([^"]+)"', attrs)
        if mid and href and mt and "xhtml" in mt.group(1):
            manifest[mid.group(1)] = href.group(1)

    order: list[str] = []
    for m in re.finditer(r"<itemref\b([^>]*)/?>", opf):
        idref = re.search(r'idref="([^"]+)"', m.group(1))
        if idref and idref.group(1) in manifest:
            href = manifest[idref.group(1)]
            order.append(f"{base}/{href}" if base else href)
    return order


def normalize_heading(text: str) -> str:
    """`Chapter 1:The Featherrun Sisters` -> `CHAPTER 1. THE FEATERRUN SISTERS.`"""
    s = re.sub(r"\s*:\s*", ":", text)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(Chapter|Act)\s+([0-9]+|[A-Za-z]+)\s*:?\s*(.*)$", s, re.I)
    if m:
        head = f"{m.group(1).upper()} {m.group(2).upper()}."
        name = m.group(3).strip()
        return f"{head} {name.upper()}." if name else head
    m = re.match(r"^(Prologue|Epilogue|Interlude|Foreword|Afterword|"
                 r"Curtain[’']s Close)\s*:?\s*(.*)$", s, re.I)
    if m:
        head = m.group(1).upper().replace("'S", "’S") + "."
        name = m.group(2).strip()
        return f"{head} {name.upper()}." if name else head
    s = s.upper()
    return s if s.endswith(".") else s + "."


def has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def _stable_punct(text: str) -> str:
    """Restore a missing sentence-final period (only when text ends in a word)."""
    return text + "." if text and text[-1].isalnum() else text


def parse_dialogue(label: str, rest: str) -> tuple[str, str]:
    """Split a label's payload into (dialogue_inner, trailing_narration)."""
    rest = rest.strip()
    if rest[:1] in OPENERS:
        body = rest[1:]
        # 1) trailing stray quote char (e.g. source typo closing with an opener)
        if body[-1:] in QUOTE_ANY:
            return _stable_punct(body[:-1].strip()), ""
        # 2) text after the closing quote -> dialogue + narration
        last = max((body.rfind(c) for c in CLOSERS), default=-1)
        if last != -1 and body[last + 1:].strip():
            return _stable_punct(body[:last].strip()), body[last + 1:].strip()
        return _stable_punct(body.strip()), ""
    return _stable_punct(rest), ""


def split_paragraph(text: str) -> list[tuple[str, str, str]]:
    """Split a paragraph into (kind, label, text) tuples (kind: dialogue|narration)."""
    out: list[tuple[str, str, str]] = []
    for seg in SPLIT_RE.split(text):
        seg = seg.strip()
        if not seg:
            continue
        m = LABEL_RE.match(seg) or LABEL_NOCOLON_RE.match(seg)
        if m:
            label, rest = m.group(1).strip(), m.group(2)
            inner, trailing = parse_dialogue(label, rest)
            if has_letters(inner):
                out.append(("dialogue", label, inner))
            if trailing.strip() and has_letters(trailing):
                out.append(("narration", "", _stable_punct(trailing.strip())))
        else:
            out.append(("narration", "", seg))
    return out


def collect_labels(docs: list[tuple[str, list[tuple[str, str]]]]) -> set[str]:
    """Whitelist = labels seen with a quote + labels seen >= 2x + ???."""
    quoted: set[str] = set()
    counts: Counter[str] = Counter()
    for _, blocks in docs:
        for tag, text in blocks:
            if tag != "p" or not text:
                continue
            for seg in SPLIT_RE.split(text):
                seg = seg.strip()
                m = LABEL_RE.match(seg) or LABEL_NOCOLON_RE.match(seg)
                if not m:
                    continue
                label, rest = m.group(1).strip(), m.group(2).strip()
                counts[label] += 1
                if rest[:1] in OPENERS:
                    quoted.add(label)
    return {l for l, c in counts.items() if l in quoted or c >= 2} | {"???"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("epub", type=Path)
    ap.add_argument("out", nargs="?", type=Path)
    ap.add_argument("--drop", action="append", default=[],
                    help="regex (on file basename) of docs to DROP; repeatable")
    ap.add_argument("--keep", action="append", default=[],
                    help="regex (on file basename) of docs to KEEP even if dropped")
    ap.add_argument("--report", action="store_true", help="analyze only, do not write")
    args = ap.parse_args()

    if not args.epub.is_file():
        print(f"ERROR: no such file: {args.epub}", file=sys.stderr)
        return 1
    out = args.out or args.epub.with_suffix(".txt")

    drop_res = [re.compile(p, re.I) for p in (DEFAULT_DROP + args.drop)]
    keep_res = [re.compile(p, re.I) for p in args.keep]

    with zipfile.ZipFile(args.epub) as zf:
        spine = read_spine(zf)
        dropped, kept = [], []
        docs: list[tuple[str, list[tuple[str, str]]]] = []
        for path in spine:
            name = path.rsplit("/", 1)[-1]
            if any(r.search(name) for r in drop_res) and not any(
                    r.search(name) for r in keep_res):
                dropped.append(name)
                continue
            if path not in zf.namelist():
                continue
            parser = BlockParser()
            parser.feed(zf.read(path).decode("utf-8"))
            if parser.blocks:
                kept.append(name)
                docs.append((name, parser.blocks))

        labels = collect_labels(docs)

        blocks_out: list[str] = []
        stats: Counter[str] = Counter()
        anomalies: list[tuple[str, str, str]] = []

        for name, blocks in docs:
            for tag, text in blocks:
                if not text:
                    continue
                if tag in HEADING_TAGS:
                    blocks_out.append(normalize_heading(text))
                    stats["headings"] += 1
                    continue
                for kind, label, payload in split_paragraph(text):
                    if kind == "dialogue":
                        if label not in labels:
                            # unsafe label guess -> keep the line as narration
                            blocks_out.append(_stable_punct(text))
                            stats["narration"] += 1
                            anomalies.append((name, "label-not-whitelisted", text[:110]))
                            break
                        blocks_out.append(f"{label}: [{payload}]")
                        stats["dialogue"] += 1
                        stats[f"speaker:{label}"] += 1
                    else:
                        if not has_letters(payload):
                            stats["dropped-empty"] += 1
                            continue
                        blocks_out.append(_stable_punct(payload))
                        stats["narration"] += 1
                # anomaly scan
                for line in blocks_out[-1:]:
                    if re.search(r"[" + re.escape(CLOSERS) + r"]\s*:|\?\?\?", line) \
                            and "???: [" not in line:
                        anomalies.append((name, "suspicious", line[:110]))

    print(f"EPUB     : {args.epub}")
    print(f"OUT      : {out}")
    print(f"spine    : {len(spine)} docs | kept {len(kept)} | dropped {len(dropped)}")
    print(f"dropped  : {', '.join(dropped) if dropped else '-'}")
    print(f"headings : {stats['headings']}")
    print(f"dialogue : {stats['dialogue']}  | narration: {stats['narration']}"
          f"  | empty blocks dropped: {stats['dropped-empty']}")
    speakers = sorted((k.split(":", 1)[1], v) for k, v in stats.items()
                      if k.startswith("speaker:"))
    print(f"speakers : {len(speakers)}")
    for label, n in speakers:
        print(f"           {n:5d}  {label}")
    if anomalies:
        print(f"\nANOMALIES ({len(anomalies)}):")
        for name, kind, line in anomalies[:60]:
            print(f"  [{kind}] {name}: {line}")
    else:
        print("\nANOMALIES: none")

    if args.report:
        return 0

    out.write_text("\n\n".join(blocks_out) + "\n", encoding="utf-8")
    print(f"\nwrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
