#!/usr/bin/env python3
"""Apply an EN->PL name-polonization mapping to a text file.

Usage: apply.py <input.txt> <polonize.yaml> <output.txt>

The YAML file maps source names to Polish forms:
    "Beatrice": "Beatris"
    "Undertaker": "Andertejker"

Replacement is whole-word and case-preserving:
  - "Beatrice"   -> "Beatris"
  - "beatrice"   -> "beatris"
  - "BEATRICE"   -> "BEATRIS"
  - "Beatrice's" -> "Beatris's"  (possessive kept)
Requires PyYAML; falls back to a simple "Key": "Value" line parser.
"""
import re
import sys


def load_mapping(path):
    mapping = {}
    try:
        import yaml
        data = yaml.safe_load(open(path, encoding="utf-8"))
        mapping.update(data or {})
    except Exception:
        for line in open(path, encoding="utf-8"):
            m = re.match(r'^\s*-?\s*["\']?(.+?)["\']?\s*:\s*["\']?(.+?)["\']?\s*$', line)
            if m and not line.lstrip().startswith("#"):
                mapping[m.group(1)] = m.group(2)
    return {str(k).strip().lower(): str(v).strip() for k, v in mapping.items()}


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    src, yml, dst = sys.argv[1:4]
    mapping = load_mapping(yml)
    if not mapping:
        print("ERROR: empty mapping file")
        return 1
    text = open(src, encoding="utf-8").read()

    def repl(match):
        word = match.group(0)
        core, trail = word[0], word[1:]
        # separate trailing possessive/letters
        m = re.match(r"([A-Za-zÀ-ž]+)('.*)?$", word)
        base = m.group(1) if m else word
        tail = word[len(base):]
        pl = mapping.get(base.lower())
        if pl is None:
            return word
        if base.isupper():
            pl = pl.upper()
        elif base[0].isupper():
            pl = pl[0].upper() + pl[1:]
        else:
            pl = pl.lower()
        return pl + tail

    pattern = re.compile(
        r"\b(?:"
        + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
        + r")(\s*'(?:s|))?\b",
        re.IGNORECASE,
    )
    result = pattern.sub(repl, text)
    open(dst, "w", encoding="utf-8").write(result)

    # report residuals
    remaining = {}
    for k in mapping:
        c = len(re.findall(r"\b" + re.escape(k) + r"\b", result, re.IGNORECASE))
        if c:
            remaining[k] = c
    print(f"Applied {len(mapping)} mappings -> {dst}")
    if remaining:
        print("RESIDUAL source forms (check declensions/context):")
        for k, c in sorted(remaining.items(), key=lambda x: -x[1]):
            print(f"  {k}: {c}")
    else:
        print("No residual source forms found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
