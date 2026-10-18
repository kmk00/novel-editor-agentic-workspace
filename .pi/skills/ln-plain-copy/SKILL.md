---
name: ln-plain-copy
description: "Converts a canonical chapter-format story file (see docs/CONVENTIONS.md) (dialogue lines `Name: [text]` / `???: [text]`, optionally with <<emotion>> tags) into clean, readable plain text for human reading — speaker labels, brackets and tags removed, dialogue as normal prose paragraphs. Use when the user asks for a version of the text without the ???/speaker tags, a \"clean\" or \"plain\" reading copy, or text for reading without the markup."
---

# Book TXT (tagged) → plain readable text

Takes a file in the the canonical chapter block format (see `docs/CONVENTIONS.md`) — narration paragraphs, dialogue lines
`???: [text]` or `Name: [text]`, ALL-CAPS headings, `<...>` system/transmission lines —
and produces a clean plain-text copy meant for *reading* (not for TTS/tagging):

```
Narration paragraph — plain prose, one paragraph per line, blank line between paragraphs.

Dialogue line becomes its own paragraph with the label and brackets removed:
Hello there. Good to see you.

More narration.

AFTERWORD-STYLE ALL-CAPS HEADINGS are kept as their own block.
(System transmission lines are kept, converted to parentheses.)
```

## Input

A path to a `.txt` file in the chapter format (output of `ln-pdf-to-txt`,
optionally speaker-resolved and/or emotion-tagged). Relative paths resolve
against the current working directory.

The input and output stay in the same volume folder `series/<slug>/VOLxx/`
(see `docs/CONVENTIONS.md` §1a).

## Procedure

### 1. Run the script

```bash
python3 tools/plain_text.py IN.txt [OUT.txt] [--quotes]
```

- Default output: `<input-basename>-plain.txt` next to the input (never overwrite the input).
- `--quotes` wraps dialogue in typographic quotes (“...”) instead of leaving it bare.

The script automatically:
- converts every `Name: [text]` / `???: [text]` line into its own paragraph containing just `text`
  (speaker label, colon and brackets removed; wording untouched),
- strips emotion/direction tags `<<...>>` (so `-tagged.txt` files work too),
- converts **any angle brackets to parentheses** — `<...>` / `<<...>>` → `(...)`
  (raw `<>` breaks TTS),
- keeps narration paragraphs and ALL-CAPS headings exactly as they are,
- normalizes blank lines to exactly one between blocks (none at the file edges),
- drops dialogue lines whose bracket content is empty (they become blank separators).

### 2. Spot-check the result (MANDATORY)

Read the beginning and end of the output and scan a few middle sections:

1. **No leftover brackets** — run `grep -n "\[" OUT.txt`; every hit should be narration
   that legitimately contains brackets in the source (e.g. `[sic]`, phonetics). If a
   dialogue line kept its brackets, fix it by hand.
2. **No leftover labels** — run `grep -nE "^(???:|[A-Z][^:]*):" OUT.txt` and review hits;
   speaker labels must not survive.
3. **Multi-paragraph quotes** — if the source split one spoken line across several
   `???: [...]` blocks (continuation lines), the output will show them as separate
   paragraphs. That is acceptable; do NOT merge or reword them.
4. **Nothing added, nothing rewritten** — the output must preserve the book's wording
   exactly; the only allowed changes are removal of the `Label: [ ]` wrapper, `<<...>>`
   tags, and blank-line normalization.
5. **No angle brackets** — raw `<>` breaks TTS. Run `grep -n '[<>]' OUT.txt`;
   every hit must have been converted to `(...)` (the script does this
   automatically). If any `<` or `>` survives, fix it.

## Output

- Write the final file (default `<input-basename>-plain.txt`, or the name the user gave) and confirm the path.
- Print a summary **always in the form of a markdown table** containing:
  - input file and final output file,
  - counts: dialogue lines converted, narration paragraphs, headings/system blocks kept,
  - whether `--quotes` was used,
  - any manual fixes applied in step 2 (with line numbers),
  - anything intentionally KEPT (e.g. `<...>` transmission lines, ALL-CAPS headings).
- Never present the summary as plain prose bullets only — the table is mandatory.

## Relation to the other skills

- Pipeline: `ln-pdf-to-txt` → (optional) `ln-speaker-resolution` →
  (optional) `ln-emotion-tagging` → **`ln-plain-copy`** for the human-reading copy.
- This skill NEVER feeds back into the TTS workflow: `???` anonymization and emotion tags
  in the tagged files stay untouched there; run this skill on a copy only.
- Do not resolve `???` speakers here — labels are simply dropped, not replaced.

## Quality checklist

- Output file exists next to the input (in the same `series/<slug>/VOLxx/`); input file untouched.
- No `Label: [` or `]` wrappers remain on dialogue lines.
- No `<<...>>` tags and **no raw `<`/`>` angle brackets** remain (converted to `()`).
- Narration wording, headings, and system lines are byte-identical to the input except for the `<>` → `()` conversion.
- Exactly one blank line between paragraphs; no leading/trailing blank lines.
- Summary table printed with counts and manual fixes.

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step plain-copy --file "<artifact>" \
    --duration <seconds> --resources "tools/plain_text.py" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
