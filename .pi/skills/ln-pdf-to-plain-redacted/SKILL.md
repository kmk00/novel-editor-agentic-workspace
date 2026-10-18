---
name: ln-pdf-to-plain-redacted
description: Full pipeline converting a book PDF into a clean, human-readable plain-text copy — extract from PDF, remove junk/front/back matter, anonymized dialogue flattened (no ??? labels, no brackets), chapter headings dotted (CHAPTER X. NAME.), every sentence terminal-punctuated, and empty/no-text lines (…, !…, dashes) removed. Use when the user asks to convert a PDF book straight to a plain reading copy in one go, or asks for a "redacted" / "plain" / "clean reading" version of a book PDF.
---

# PDF → plain redacted text (one-shot pipeline)

End-to-end conversion of a book PDF into a clean readable `.txt`:
**PDF → tagged txt → plain txt**, with all cleanup rules applied.
This skill composes the existing `ln-pdf-to-txt` and `ln-plain-copy` skills
(reusing their scripts) plus two extra passes (punctuation + heading dots +
no-text-line removal) that were added to those skills' rules.

## Input

A path to a book PDF (light novel / web novel). Relative paths resolve against
the working directory. Requires `pdftotext` (poppler-utils) and `python3`.

The PDF and both outputs live in the volume folder `series/<slug>/VOLxx/`
(see `docs/CONVENTIONS.md` §1a). If the PDF sits flat in `series/<slug>/`, move
it into its `VOLxx/` first.

## Output files (both are kept)

1. `<pdf-basename>.txt` — tagged intermediate (`???: [...]` dialogue, dotted headings) next to the PDF (in `VOLxx/`).
2. `<pdf-basename>-plain.txt` — final plain redacted copy next to it.

## Procedure

### Step 1 — Extract (ln-pdf-to-txt)

```bash
python3 tools/pdf_to_txt.py BOOK.pdf [OUT.txt] [--first-page N] [--last-page N]
```

Then perform the MANDATORY manual passes from `ln-pdf-to-txt` SKILL.md steps 2–3:
- remove front/back matter (copyright, TOC, publisher ads, afterword, newsletter),
- fix mis-detected dialogue / wrongly split scare quotes / scrambled reflow,
- **normalize chapter headings** to `CHAPTER X. CHAPTER NAME.` (dot after the
  number AND a final dot after the name; PROLOGUE/EPILOGUE with a name too),
- **every sentence must end with terminal punctuation** (`.`, `?`, `!`, `…`);
  verify each flagged line against the raw PDF text — do NOT add fake periods
  to genuine mid-sentence fragments that feed into a following quote.

### Step 2 — Flatten to plain (ln-plain-copy)

```bash
python3 tools/plain_text.py IN.txt
```

This strips all `???` / `Name:` labels and `[ ]` brackets, dialogue becomes
bare paragraphs, and **any angle brackets are converted to parentheses**
(`<...>` / `<<...>>` → `(...)`, so no raw `<>` remains — raw `<>` breaks TTS).
Spot-check for leftover labels/brackets per that skill and verify with
`grep -n '[<>]' OUT.txt` → no hits.

### Step 3 — Remove no-text lines (extra pass, REQUIRED)

Delete every non-heading line that contains no letters/digits (only
punctuation like `…`, `!…`, `—`, `…?!` — pure interjections/ellipses with no
readable content), then re-normalize blank lines to exactly one between blocks.
Example pass:

```python
import re
lines = open(p, encoding="utf-8").read().split("\n")
out = [l for l in lines
       if re.search(r"[0-9A-Za-z\u00C0-\u024F]", l) or re.match(r"^[A-Z0-9 .,:!?’‘—-]+$", l) or not l.strip()]
res, blank = [], True
for l in out:
    b = not l.strip()
    if b and blank: continue
    res.append(l); blank = b
open(p, "w", encoding="utf-8").write("\n".join(res).strip() + "\n")
```

### Step 4 — Final verification

- No `???:` labels, no `[ ]` wrappers, no `<<...>>` tags and no raw `<`/`>`
  (all angle brackets converted to `()`).
- All chapter headings present and dotted.
- No letter-free junk lines remain.
- Wording of the book never rewritten beyond the allowed transformations.

### Summary

Always print a markdown summary table: source PDF → both output files, blocks
removed (junk / front-back matter / no-text lines, with counts), headings
normalized, counts of dialogue & narration paragraphs, and manual fixes with
line numbers.

## Relation to the other skills

- `ln-pdf-to-txt` — produces the tagged intermediate (steps and rules inherited).
- `ln-plain-copy` — produces the readable copy (step 2).
- The redacted `-plain.txt` output is for human reading; it does NOT feed the
  TTS/emotion-tagging workflow (that needs the tagged file).

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step pdf-to-plain-redacted --file "<artifact>" \
    --duration <seconds> --resources "pdftotext + agent" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
