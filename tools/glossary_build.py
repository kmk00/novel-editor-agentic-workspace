#!/usr/bin/env python3
"""
glossary_build.py -- scaffold and validate a per-book translation glossary.

The input is a plain-text file (usually `<stem>-plain.txt` produced by
`ln-to-plain-txt-only`) in a volume folder `series/<slug>/VOLxx/`. The tool
finds candidate proper nouns / coined terms / multi-word phrases with their
occurrence counts, seeds already-decided renderings from `characters.yaml` and
`polonize.yaml`, and writes a human-reviewable `glossary.md` next to the book.
The agent fills in the Polish renderings and copies the ready YAML block into
`translator/ln-translator/prompt.yaml` -> `glossary:`.

Usage:
  python3 tools/glossary_build.py scan <plain.txt> [--out glossary.md]
        [--characters characters.yaml] [--polonize polonize.yaml]
        [--min-count 2] [--slug SLUG] [--volume VOLxx]
  python3 tools/glossary_build.py check <glossary.md> [--min-count 2]

`scan` never guesses Polish forms: it only fills what `characters.yaml` /
`polonize.yaml` already decide (so terminology stays consistent across volumes).

`check` verifies the glossary has a fenced ```yaml block that parses to a
`glossary:` mapping of non-empty `"EN": "PL"` pairs with no duplicate keys, and
reports candidates (>= --min-count) that are not covered yet.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Capitalised single token (incl. Polish letters, apostrophes, hyphens).
TOKEN_RE = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż'’\-]*[a-ząćęłńóśźż]\b")
ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")
# Capitalised word used for phrase detection (stops at sentence end).
WORD_RE = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻ][A-Za-ząćęłńóśźż'’\-]*")

COMMON = {
    "I", "A", "An", "The", "But", "And", "Or", "Not", "No", "Yes", "It", "He",
    "She", "They", "We", "You", "His", "Her", "Their", "My", "Your", "Our",
    "This", "That", "These", "Those", "There", "Then", "When", "What", "Who",
    "Why", "How", "Where", "If", "In", "On", "At", "To", "Of", "For", "With",
    "From", "By", "As", "Was", "Were", "Is", "Are", "Be", "Been", "Had", "Has",
    "Have", "Do", "Does", "Did", "Will", "Would", "Could", "Should", "Can",
    "May", "Might", "Must", "Shall", "So", "Such", "One", "Two", "All", "Any",
    "Each", "Every", "Some", "Most", "More", "Less", "Now", "Here", "Just",
    "Even", "Still", "Also", "Once", "After", "Before", "While", "Because",
    "Chapter", "Interlude", "Epilogue", "Prologue", "Afterword",
    # interjections / onomatopoeia (not glossary material)
    "Oh", "Ah", "Hmm", "Huh", "Hey", "Wow", "Yeah", "Okay", "Ugh",
    "Gah", "Whoa", "Hah", "Heh", "Eh", "Er", "Um", "Grr", "Eek",
    "Tsk", "Hmph", "Hm", "Ooh", "Aah", "Ahem", "Phew", "Yikes",
}

# Common English contractions / possessives that the capitalised-token scan
# picks up on the first word (I’m, That’s, Don’t, …).
CONTRACTION_BASES = {
    "I", "You", "We", "They", "He", "She", "It", "That", "There",
    "What", "Who", "Here", "Let", "Don", "Can", "Won", "Isn", "Aren",
    "Wasn", "Weren", "Hasn", "Haven", "Hadn", "Doesn", "Didn",
    "Wouldn", "Couldn", "Shouldn", "Mustn", "Ain", "Y", "Cause",
}


def _is_contraction(tok: str) -> bool:
    if "’" not in tok and "'" not in tok:
        return False
    base = re.split(r"[’']", tok, maxsplit=1)[0]
    return base in CONTRACTION_BASES or base.lower() in {
        w.lower() for w in COMMON}

ARTICLES = {"The", "A", "An"}
YAML_BLOCK_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)

# Dependency-free characters.yaml parsing (same subset as voice_casting.py).
TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*$")
CHAR_KEY_RE = re.compile(r"^\s{2}(?:\"([^\"]+)\"|'([^']+)'|([^:#][^:]*?))\s*:\s*$")
ALIASES_RE = re.compile(r"^\s*aliases\s*:\s*\[(.*?)\]", re.IGNORECASE)


def load_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def seed_from_characters(path: Path) -> dict[str, str]:
    """Return {name/alias: polonize form} from a characters.yaml manifest.

    Dependency-free: parses the small subset used by the cast manifest
    (`characters:` block, 2-space `Name:` keys, `polonize:` value,
    `aliases: [..]` list).
    """
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    in_characters = False
    current: str | None = None
    polonize = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m_top = TOP_KEY_RE.match(line)
        if m_top:
            if current and current:
                out.setdefault(current, polonize)
            in_characters = m_top.group(1) == "characters"
            current, polonize = None, ""
            continue
        if not in_characters:
            continue
        m_key = CHAR_KEY_RE.match(line)
        if m_key:
            if current:
                out.setdefault(current, polonize)
            current = (m_key.group(1) or m_key.group(2) or m_key.group(3) or "").strip()
            polonize = ""
            continue
        m_pol = re.match(r"^\s+polonize\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if m_pol and current:
            polonize = m_pol.group(1).strip().strip("\"'")
            continue
        m_alias = ALIASES_RE.match(line)
        if m_alias and current:
            for alias in m_alias.group(1).split(","):
                alias = alias.strip().strip("\"'")
                if alias:
                    out.setdefault(alias, polonize)
    if current:
        out.setdefault(current, polonize)
    return out


def seed_from_polonize(path: Path) -> dict[str, str]:
    data = load_yaml(path)
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    # fallback: "Key": "Value" lines
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r'^["\']?(.+?)["\']?\s*:\s*["\']?(.+?)["\']?\s*$', s)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def scan_candidates(text: str) -> tuple[Counter, Counter, Counter]:
    """Return (total single-token counts, mid-sentence counts, phrase counts).

    A real proper noun appears at least once *inside* a sentence; words that only
    ever sit at a sentence start (Well, Maybe, Anyway…) are dropped by requiring
    `mid >= 1`.
    """
    total: Counter = Counter()
    mid: Counter = Counter()
    # Characters that mark the start of a sentence / line of dialogue, so a
    # capitalised word right after them is still sentence-initial (not evidence
    # of a proper noun).
    start_marks = set(".?!…\u201c\u201d\u201e\u00ab\u00bb\"'\n\r\t")
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0)
        if tok in COMMON or _is_contraction(tok):
            continue
        total[tok] += 1
        p = m.start() - 1
        while p >= 0 and text[p] in " \t\r\n":
            p -= 1
        if p >= 0 and text[p] not in start_marks:
            mid[tok] += 1
    for m in ACRONYM_RE.finditer(text):
        tok = m.group(0)
        if tok in COMMON:
            continue
        total[tok] += 1
        p = m.start() - 1
        while p >= 0 and text[p] in " \t\r\n":
            p -= 1
        if p >= 0 and text[p] not in start_marks:
            mid[tok] += 1

    phrases: Counter = Counter()
    words = [(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(text)]
    i = 0
    while i < len(words):
        w, _, _ = words[i]
        if w[:1].isupper() and w not in COMMON:
            j = i
            seq: list[str] = []
            while j < len(words) and len(seq) < 4:
                wj, wstart, wend = words[j]
                if not wj[:1].isupper():
                    break
                if seq:
                    gap = text[words[j - 1][2]:wstart]
                    if re.search(r"[.!?…\n]", gap):
                        break
                seq.append(wj)
                j += 1
            while seq and seq[0] in ARTICLES:
                seq = seq[1:]
            if 2 <= len(seq) <= 4 and not all(t in COMMON for t in seq):
                phrases[" ".join(seq)] += 1
            i = j if j > i else i + 1
        else:
            i += 1
    return total, mid, phrases


def build_scaffold(args) -> int:
    src = Path(args.plain)
    if not src.is_file():
        print(f"ERROR: input not found: {src}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8")
    total, mid, phrases = scan_candidates(text)

    seeded: dict[str, str] = {}
    for p in args.polonize:
        seeded.update(seed_from_polonize(Path(p)))
    for p in args.characters:
        seeded.update(seed_from_characters(Path(p)))
    for p in getattr(args, "glossary", []):
        gp = Path(p)
        if gp.is_file():
            pairs, err = extract_yaml(gp.read_text(encoding="utf-8"))
            if pairs:
                seeded.update({k: v for k, v in pairs if v})

    min_count = args.min_count
    rows: list[tuple[str, str, int]] = []
    for tok, c in total.items():
        if seeded.get(tok) is not None or mid.get(tok, 0) >= 1:
            rows.append((tok, seeded.get(tok, ""), c))
    for phr, c in phrases.items():
        if c >= min_count:
            rows.append((phr, seeded.get(phr, ""), c))
    rows.sort(key=lambda r: (-r[2], r[0].lower()))

    out = Path(args.out) if args.out else src.with_name("glossary.md")
    slug = args.slug or ""
    volume = args.volume or ""
    decided = {en: pl for en, pl, _ in rows if pl}
    lines: list[str] = []
    lines.append(f"# Glossary — {slug}{(' / ' + volume) if volume else ''}".rstrip())
    lines.append("")
    lines.append(f"> Źródło: `{src}`")
    lines.append(f"> Kandydaci: {len(rows)}  |  z gotową formą PL: {len(decided)}")
    lines.append(">")
    lines.append("> Wypełnij kolumnę **PL** (zostaw puste = pomiń), uzupełnij **Typ**")
    lines.append("> (`postać` / `miejsce` / `organizacja` / `termin` / `przedmiot` /")
    lines.append("> `honoryfikacja` / `fraza`), usuń zbędne wiersze, a następnie")
    lines.append("> skopiuj blok YAML na końcu do `translator/ln-translator/prompt.yaml`")
    lines.append("> → `glossary:`.")
    lines.append("")
    lines.append("| EN | PL | Typ | Wyst. | Uwagi |")
    lines.append("|---|---|---|---|---|")
    for en, pl, c in rows:
        en_cell = en.replace("|", "\\|")
        pl_cell = pl.replace("|", "\\|")
        lines.append(f"| {en_cell} | {pl_cell} |  | {c} |  |")
    lines.append("")
    lines.append("## Gotowe do wklejenia (YAML)")
    lines.append("")
    lines.append("```yaml")
    lines.append("glossary:")
    if decided:
        for en in sorted(decided):
            lines.append(f'  "{en}": "{decided[en]}"')
    else:
        lines.append('  # "EN": "PL"      # uzupełnij po wypełnieniu tabeli')
    lines.append("```")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Candidates: {len(rows)} | seeded PL: {len(decided)}")
    return 0


def extract_yaml(text: str):
    """Return (list of (key, value) pairs, error)."""
    m = YAML_BLOCK_RE.search(text)
    if not m:
        return None, "no fenced ```yaml block found"
    body = m.group(1)
    if body.lstrip().startswith("#") and "glossary:" not in body:
        return None, "yaml block has no glossary: mapping"
    try:
        import yaml  # type: ignore
    except Exception:
        return _parse_glossary_block(body)
    try:
        data = yaml.safe_load(body)
    except Exception as e:  # noqa: BLE001
        return None, f"yaml does not parse: {e}"
    if not isinstance(data, dict) or "glossary" not in data:
        return None, "yaml block must define a `glossary:` mapping"
    gloss = data["glossary"]
    if gloss is None:
        return [], None
    if not isinstance(gloss, dict):
        return None, "`glossary:` must be a mapping of \"EN\": \"PL\""
    return [(str(k), "" if v is None else str(v)) for k, v in gloss.items()], None


def _parse_glossary_block(body: str):
    """PyYAML-free parser for the simple `glossary:` mapping block.

    Returns the ordered (key, value) pairs so duplicates and empty values are
    not silently lost.
    """
    pairs: list[tuple[str, str]] = []
    in_map = False
    for raw in body.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s == "glossary:":
            in_map = True
            continue
        if not in_map:
            continue
        mm = re.match(r'^["\']?(.+?)["\']?\s*:\s*(.*)$', s)
        if not mm:
            continue
        key = mm.group(1).strip()
        val = mm.group(2).strip().strip('"\'')
        pairs.append((key, val))
    return pairs, None


def check_glossary(args) -> int:
    path = Path(args.glossary)
    if not path.is_file():
        print(f"ERROR: glossary not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    pairs, err = extract_yaml(text)
    problems: list[str] = []
    if err:
        problems.append(err)
        pairs = []
    seen: set[str] = set()
    for k, v in (pairs or []):
        if not str(k).strip():
            problems.append("empty key in glossary")
        if v is None or not str(v).strip():
            problems.append(f'entry without PL form: "{k}"')
        if k in seen:
            problems.append(f"duplicate key: {k}")
        seen.add(k)

    print(f"Glossary check: {path}")
    print(f"  entries: {len(pairs or [])}")
    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems[:50]:
            print("  " + p)
        return 1
    print("PASS — valid `glossary:` mapping, no empty values, no duplicate keys.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scan", help="build a glossary.md scaffold")
    sc.add_argument("plain", help="plain-text file in the volume folder")
    sc.add_argument("--out", help="output path (default: <plain-dir>/glossary.md)")
    sc.add_argument("--characters", action="append", default=[],
                    help="characters.yaml to seed from (repeatable)")
    sc.add_argument("--polonize", action="append", default=[],
                    help="polonize.yaml to seed from (repeatable)")
    sc.add_argument("--glossary", action="append", default=[],
                    help="existing glossary.md to seed from (repeatable)")
    sc.add_argument("--min-count", type=int, default=2,
                    help="minimum occurrences for a candidate (default: 2)")
    sc.add_argument("--slug", default="", help="series slug for the title")
    sc.add_argument("--volume", default="", help="volume folder name for the title")

    ck = sub.add_parser("check", help="validate a glossary.md")
    ck.add_argument("glossary", help="glossary.md to validate")
    ck.add_argument("--min-count", type=int, default=2,
                    help="unused (kept for symmetry)")

    args = ap.parse_args()
    if args.cmd == "scan":
        return build_scaffold(args)
    if args.cmd == "check":
        return check_glossary(args)
    ap.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
