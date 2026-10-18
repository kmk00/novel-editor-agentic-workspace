#!/usr/bin/env python3
"""
Speaker-resolution helper (NOVEL EDITOR).

Modes:
  --scan   <file>                 : print every `???:` dialogue line with surrounding
                                    context (for fast analysis without reading the file).
  --check  <original> <resolved>  : verify that the ONLY change between the two files is
                                    `???:` speaker prefixes replaced with character names.
                                    Exit 0 = PASS, 1 = FAIL.
"""
import sys
import re
from pathlib import Path

DIALOGUE_RE = re.compile(r"^\s*([^:\[\]]+)\s*:\s*\[")
# A plausible character name: letters (incl. accented), spaces, dots, hyphens,
# apostrophes; no brackets, colons, tags or ??? leftovers.
NAME_RE = re.compile(r"^[A-ZÀ-Ž][\w .'\-à-ÿ]*$")
FORBIDDEN_IN_NAME = ("[", "]", ":", "<<", ">>", "?", "!", ",", '"')


def is_dialogue(line: str) -> bool:
    return bool(DIALOGUE_RE.match(line))


def speaker_of(line: str) -> str | None:
    m = DIALOGUE_RE.match(line)
    return m.group(1).strip() if m else None


def known_names(text: str) -> set[str]:
    """Names that appear as speaker labels anywhere in the text (exact spelling)."""
    names = set()
    for line in text.splitlines():
        if is_dialogue(line):
            sp = speaker_of(line)
            if sp and sp != "???":
                names.add(sp)
                names.update(sp.split())  # also accept single parts e.g. "Tiga Rauleon" -> "Tiga"
    return names


def name_in_text(name: str, text: str) -> bool:
    """True if the name (or any of its words) appears in the file at all
    (speaker label OR narration), using the chapter's own spelling."""
    if name in text:
        return True
    words = [w for w in name.split() if len(w) > 1]
    return bool(words) and all(w in text for w in words)


def cmd_scan(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [i for i, ln in enumerate(lines) if speaker_of(ln) == "???"]
    if not hits:
        print(f"OK: no '???:' dialogue lines found in {path.name}")
        return 0
    print(f"Found {len(hits)} '???:' dialogue line(s) in {path.name}\n")
    for i in hits:
        lo, hi = max(0, i - 4), min(len(lines), i + 5)
        print(f"=== line {i + 1} ===")
        for j in range(lo, hi):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {j + 1:5d} | {lines[j]}")
        print()
    return 0


def cmd_check(orig_path: Path, res_path: Path) -> int:
    orig = orig_path.read_text(encoding="utf-8")
    res = res_path.read_text(encoding="utf-8")
    orig_lines, res_lines = orig.splitlines(), res.splitlines()
    errors: list[str] = []

    if len(orig_lines) != len(res_lines):
        print(f"FAIL: line count differs: original {len(orig_lines)} vs resolved {len(res_lines)}")
        return 1

    replacements: list[tuple[int, str, str]] = []
    for idx, (o, r) in enumerate(zip(orig_lines, res_lines), start=1):
        if o == r:
            continue
        so, sr = speaker_of(o), speaker_of(r)
        # Allowed: only the speaker label changed, dialogue body byte-identical.
        o_body = o[o.index("["):] if so is not None else None
        r_body = r[r.index("["):] if sr is not None else None
        if so == "???" and so is not None and o_body == r_body and sr is not None:
            name = sr
            problems = []
            if name in ("???",) or "???" in name:
                problems.append("speaker still contains ???")
            if not NAME_RE.match(name):
                problems.append(f"'{name}' is not a plausible character name")
            if any(ch in name for ch in FORBIDDEN_IN_NAME):
                problems.append(f"'{name}' contains forbidden characters")
            elif not name_in_text(name, orig + "\n" + res):
                problems.append(f"'{name}' does not appear as a speaker/narrated name anywhere in the file")
            if problems:
                errors.append(f"line {idx}: BAD REPLACEMENT '???' -> '{name}': " + "; ".join(problems))
            else:
                replacements.append((idx, name, r_body[:60]))
        else:
            errors.append(
                f"line {idx}: FORBIDDEN CHANGE (only '???:' speaker labels may change):\n"
                f"  original: {o.strip()[:100]}\n  resolved: {r.strip()[:100]}"
            )

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print("  " + e)
        return 1

    print(f"PASS: {len(replacements)} '???' speaker(s) resolved, all other lines byte-identical.")
    for idx, name, body in replacements:
        print(f"  line {idx}: ??? -> {name}  [{body}...]")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--scan" and len(args) == 2:
        return cmd_scan(Path(args[1]))
    if args[0] == "--check" and len(args) == 3:
        return cmd_check(Path(args[1]), Path(args[2]))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
