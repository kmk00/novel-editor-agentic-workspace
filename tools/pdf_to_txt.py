#!/usr/bin/env python3
"""
pdf_to_txt.py -- Extract a story text from a book PDF into the chapter25.txt style.

Output format:
  - Dialogue (paragraphs / lines that consist of a quoted string) -> one line:  ???: [text]
  - Narration -> plain paragraph, one paragraph per block, blank line between blocks.
  - ALL-CAPS headings are kept as their own block with blank lines around them.
  - Junk (URLs, ads, ISBN lines, page numbers, repeated running headers/footers,
    image-only pages) is removed automatically. Front/back matter (copyright page,
    TOC, afterword, ads) must be removed by the agent (use --first-page /
    --last-page or edit the output).

Usage:
  python3 pdf_to_txt.py BOOK.pdf [OUT.txt] [--first-page N] [--last-page N]

Requires: pdftotext (poppler-utils).
"""
import argparse
import re
import subprocess
from collections import Counter
from pathlib import Path

PAIRS = {"“": "”", "„": "”", "«": "»", "‘": "’", '"': '"'}
OPENERS = "".join(PAIRS.keys())
CLOSERS = ("”", "»", '"')  # NB: '’' (apostrophe closer) is handled by closer_index

# '’' as a closing quote: only if it ends the text, allowing trailing punctuation
APOST_CLOSER_RE = re.compile(r"’[””….!?,)\s]*$")

TERMINAL_PUNCT = tuple('.!?”"…:;)]')

URL_RE = re.compile(
    r"(https?://|www\.|\.com\b|\.net\b|\.org\b|\.io\b|pdf[-_ ]?room|t\.me/|"
    r"telegram|ISBN[-:\s]|e-?ISBN|LC record available|Created with|"
    r"scanned by|proofed by|watermark|visit us at)",
    re.IGNORECASE,
)

PAGE_NUM_RE = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,7})\s*$", re.IGNORECASE)
CAPS_RE = re.compile(r"^[^a-z]*$")


def is_caps_heading(line: str) -> bool:
    s = line.strip()
    if len(s) < 2 or not re.search(r"[A-ZÀ-Ž]", s):
        return False
    if not CAPS_RE.match(s):
        return False
    if s[0] in OPENERS:
        return False  # quoted screams like “AAAAH!!!” are not headings
    if re.search(r"(.)\1{9,}", s):
        return False  # scream letter-runs (IIIIIIIN!”) are not headings
    letters = sum(ch.isalpha() for ch in s)
    return letters >= max(3, len(s) * 0.5)


# ------------------------------------------------------------------ extraction

def extract_pages(pdf: Path, first: int | None, last: int | None,
                  layout: bool = False) -> list[list[str]]:
    args = ["pdftotext"]
    if layout:
        args.append("-layout")
    args += ["-enc", "UTF-8"]
    if first:
        args += ["-f", str(first)]
    if last:
        args += ["-l", str(last)]
    args += [str(pdf), "-"]
    raw = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    return [p.splitlines() for p in raw.split("\f")]


def clean_page(lines: list[str]) -> list[str]:
    out = []
    for ln in lines:
        if PAGE_NUM_RE.match(ln):
            continue
        if URL_RE.search(ln):
            continue
        out.append(ln.rstrip())
    return out


def drop_repeated_margins(pages: list[list[str]]) -> list[list[str]]:
    """Drop running headers/footers: first/last edge lines repeating on many pages."""
    real_pages = [p for p in pages if any(l.strip() for l in p)]
    if len(real_pages) < 8:
        return pages
    counts: Counter[str] = Counter()
    for p in real_pages:
        body = [l.strip() for l in p if l.strip()]
        for ln in body[:2] + body[-2:]:
            counts[ln] += 1
    thresh = max(5, int(len(real_pages) * 0.3))
    repeated = {ln for ln, c in counts.items() if c >= thresh and len(ln) > 1}
    if not repeated:
        return pages
    return [[l for l in p if l.strip() not in repeated] for p in pages]


# ------------------------------------------------------------------ segmentation

def _join_lines(lines: list[str]) -> str:
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not out:
            out = ln
            continue
        if out.endswith("-") and re.match(r"^[a-zà-ž]", ln):
            out = out[:-1] + ln  # dehyphenate soft line break
        elif out[-1:] in ("—", "―", "–") and not out.endswith("――"):
            out = out + ln  # em-dash line break: no space
        elif (
            re.search(r"(.)\1{9,}$", out)
            and ln[0:1].isalpha()
            and out[-1].lower() == ln[0].lower()
        ):
            out = out + ln  # scream letter-run wrapped mid-run: no space
        else:
            out = out + " " + ln
    return out


class Segment:
    def __init__(self, kind: str):
        self.kind = kind  # 'dialogue' | 'narration' | 'heading'
        self.lines: list[str] = []

    def text(self) -> str:
        return _join_lines(self.lines)


def quote_closed(line: str) -> bool:
    """True if the line appears to close an open quote."""
    return any(line.rfind(c) != -1 for c in CLOSERS)


def line_closed(line: str) -> bool:
    """True if the line closes with its own opener's closer."""
    op = line[0]
    if op in PAIRS:
        return closer_index(line, PAIRS[op]) != -1
    return quote_closed(line)


def closer_index(text: str, closer: str) -> int:
    """Position of the closing quote in the text; -1 if unclosed."""
    if closer == "’":
        m = APOST_CLOSER_RE.search(text)
        return m.start() if m else -1
    return text.rfind(closer)


def segment(pages: list[list[str]]) -> list[Segment]:
    segs: list[Segment] = []
    cur: Segment | None = None
    quote_open = False  # current dialogue segment left its quote unclosed

    def flush():
        nonlocal cur, quote_open
        if cur is not None and (cur.lines or cur.kind == "heading"):
            segs.append(cur)
        cur = None
        quote_open = False

    def new(kind: str) -> Segment:
        nonlocal cur
        flush()
        cur = Segment(kind)
        return cur

    for page in pages:
        for raw in page:
            s = raw.strip()
            if not s:
                continue
            if is_caps_heading(s):
                seg = segs[-1] if segs else None
                if seg is not None and seg.kind == "heading":
                    seg.lines.append(s)  # merge consecutive caps lines
                else:
                    flush()
                    h = Segment("heading")
                    h.lines.append(s)
                    segs.append(h)
                    cur = None  # headings are standalone; following text starts fresh
                continue
            starts_quote = s[0] in OPENERS
            if cur is None:
                cur = Segment("dialogue" if starts_quote else "narration")
                if starts_quote:
                    quote_open = not line_closed(s)
                cur.lines.append(s)
                continue
            if cur.kind == "heading":
                flush()
                cur = Segment("dialogue" if starts_quote else "narration")
                if starts_quote:
                    quote_open = not line_closed(s)
                cur.lines.append(s)
                continue
            if cur.kind == "dialogue":
                if starts_quote:
                    flush()
                    cur = Segment("dialogue")
                    quote_open = not line_closed(s)
                    cur.lines.append(s)
                elif quote_open:
                    cur.lines.append(s)
                    if quote_closed(s):
                        quote_open = False
                else:
                    # narration following a closed quote
                    flush()
                    cur = Segment("narration")
                    cur.lines.append(s)
            else:  # narration
                if starts_quote:
                    flush()
                    cur = Segment("dialogue")
                    quote_open = not line_closed(s)
                    cur.lines.append(s)
                else:
                    cur.lines.append(s)
    flush()
    return segs


# ------------------------------------------------------------------ dialogue conversion

def extractable(inner: str) -> bool:
    """True if the quoted content should become its own `???: [...]` line.
    Single-word, unpunctuated inline quotes (scare quotes like the “voice”
    of a young man) stay inline in narration."""
    if not re.search(r"[A-Za-z0-9]", inner):
        return False
    return len(inner.split()) >= 2 or inner[-1:] in ".!?…?!"


def process_text(text: str, out: list[str]) -> None:
    """Split text (a paragraph) into dialogue `???: [...]` lines and narration
    fragments. EVERY complete quote becomes its own `???: [...]` line, even
    when woven into the middle of a narration sentence; the narration around
    it is emitted as its own line. Scare-quote-style single-word inline quotes
    stay inline (see extractable)."""
    buf = ""  # narration buffer

    def flush_buf():
        nonlocal buf
        b = buf.strip()
        if b:
            out.append(b)
        buf = ""

    i = 0
    n = len(text)
    while i < n:
        if text[i] not in OPENERS:
            buf += text[i]
            i += 1
            continue
        op = text[i]
        k = i
        while k < n and text[k] == op:
            k += 1  # skip opener run (““““)
        cl = PAIRS[op]
        j = text.find(cl, k)
        if j == -1:
            # unclosed (multi-paragraph) quote: emit the rest as dialogue
            inner = text[k:].strip()
            if inner and re.search(r"[A-Za-z0-9]", inner):
                flush_buf()
                out.append(f"???: [{inner}]")
            else:
                buf += text[i:]
            return
        e = j
        while e < n and text[e] == cl:
            e += 1
        inner = text[k:j].strip()
        if extractable(inner):
            flush_buf()
            out.append(f"???: [{inner}]")
        else:
            buf += text[i:e]  # inline scare quote: keep in narration
        i = e
    flush_buf()


HEADING_RE = re.compile(
    r"^(PROLOGUE|EPILOGUE|INTERLUDE|INTERMISSION|CHAPTER|AFTERWORD|APPENDIX)\b"
    r"|^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)"
    r" LOSS\b",
    re.IGNORECASE,
)


def is_heading_para(text: str) -> bool:
    """Chapter/section heading: ALL-CAPS or a known section keyword, short, and
    without a terminal sentence period."""
    s = text.strip()
    if not s or len(s) > 80:
        return False
    if is_caps_heading(s):
        return True
    return bool(HEADING_RE.match(s))


def build_paragraphs(pages: list[list[str]]) -> list[list[str]]:
    """Group a page's lines into paragraphs using indentation (a line with
    leading whitespace begins a new paragraph; following unindented lines
    continue it). Blank lines and page tops also force a break.
    Requires pdftotext -layout output."""
    paras: list[list[str]] = []
    for page in pages:
        page_start = True
        for raw in page:
            line = raw.rstrip()
            if not line.strip():
                page_start = False
                continue
            indent = len(line) - len(line.lstrip(" \t"))
            if indent > 0 or page_start or (paras and not paras[-1]):
                page_start = False
                paras.append([line.strip()])
            else:
                if not paras:
                    continue
                paras[-1].append(line.strip())
        page_start = False
    return [p for p in paras if any(p)]


def build_output_layout(paras: list[list[str]]) -> list[str]:
    out: list[str] = []
    for para in paras:
        text = _join_lines(para)
        if is_heading_para(text):
            out += ["", _format_heading(text), ""]
        else:
            process_text(text, out)
    return _normalize(out)


def _format_heading(text: str) -> str:
    """Normalize a section heading: collapse spaces, uppercase, terminal dot."""
    s = " ".join(text.split())
    s = s.rstrip(". ")
    if not s.endswith(("!", "?", "…")):
        s += "."
    return s.upper()


def build_output(segs: list[Segment]) -> list[str]:
    out: list[str] = []
    for seg in segs:
        text = seg.text()
        if seg.kind == "heading":
            out += ["", text, ""]
        elif seg.kind == "dialogue":
            process_text(text, out)
        else:
            process_text(text, out)
    return _normalize(out)


def _normalize(out: list[str]) -> list[str]:
    # normalize: collapse 3+ blank lines
    lines: list[str] = []
    for l in out:
        if l == "" and (not lines or lines[-1] == ""):
            continue
        lines.append(l)
    # merge mid-sentence splits: a narration line starting with a lowercase
    # letter continues the previous narration line if it has no terminal punct
    terminal = tuple(".!?”…:;)]")
    merged: list[str] = []
    for l in lines:
        if (
            merged
            and l
            and not l.startswith("???: [")
            and l[0:1].islower()
            and merged[-1]
            and not merged[-1].startswith("???: [")
            and not is_caps_heading(merged[-1])
            and not merged[-1].endswith(terminal)
        ):
            merged[-1] = merged[-1] + " " + l
        else:
            merged.append(l)
    return merged


# ------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("--first-page", type=int, default=None)
    ap.add_argument("--last-page", type=int, default=None)
    ap.add_argument("--layout", action="store_true",
                    help="use pdftotext -layout and detect paragraphs by "
                         "indentation (needed for calibre-style PDFs where "
                         "paragraphs are not blank-line separated)")
    args = ap.parse_args()

    pages = extract_pages(args.pdf, args.first_page, args.last_page, args.layout)
    pages = [clean_page(p) for p in pages]
    pages = drop_repeated_margins(pages)
    pages = [p for p in pages if any(ch.isalpha() for l in p for ch in l)]

    if args.layout:
        lines = build_output_layout(build_paragraphs(pages))
    else:
        segs = segment(pages)
        lines = build_output(segs)
    text = "\n".join(lines).strip() + "\n"

    out = args.out if args.out else args.pdf.with_suffix(".txt")
    out.write_text(text, encoding="utf-8")

    dialogue = sum(1 for l in lines if l.startswith("???: ["))
    heading_pred = is_heading_para if args.layout else is_caps_heading
    narration = sum(
        1 for l in lines if l and not l.startswith("???: [") and not heading_pred(l)
    )
    headings = sum(1 for l in lines if l and heading_pred(l))
    print(f"Wrote: {out}")
    print(
        f"Dialogue lines: {dialogue} | narration paragraphs: {narration} "
        f"| headings: {headings} | total output lines: {len(lines)}"
    )
    print(
        "REVIEW NEEDED: remove front/back matter (copyright, TOC, ads, afterword) "
        "and check for mis-detected dialogue."
    )


if __name__ == "__main__":
    main()
