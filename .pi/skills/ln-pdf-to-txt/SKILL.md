---
name: ln-pdf-to-txt
description: "Converts a book PDF (light novel / web novel) into a clean chapter-format plain text file — narration paragraphs with dialogue lines anonymized as `???: [...]`, with junk (URLs, ads, publisher info, page numbers, running headers, images) removed. Use when the user asks to convert/extract a PDF book to txt, prepare a PDF for audiobook/chapter conversion, or clean a PDF of links/ads/images."
---

# Book PDF → chapter-format TXT

Convert a book PDF into a plain-text file in the project's canonical chapter format
(see `docs/CONVENTIONS.md`) — but with EVERY speaker anonymized as `???`:

```
Narration paragraph — plain prose, one paragraph per line, blank line between paragraphs.

???: [Dialogue line — EVERY character's spoken line becomes ???: [text], even when the book names the speaker.]

More narration.

AFTERWORD-STYLE ALL-CAPS HEADINGS are kept as their own block.
```

**All speakers stay `???` on purpose.** Do not resolve them to names — the speaker names are deliberately erased (the user tags speakers/voices in a later, separate workflow).

## Input

The user provides a path to a book PDF. If the path is relative, resolve it against the current working directory. Requires `pdftotext` (poppler-utils).

**Volume layout.** The PDF and its output belong in the volume folder
`series/<slug>/VOLxx/` (see `docs/CONVENTIONS.md` §1a). If the PDF sits flat in
`series/<slug>/`, move it into its `VOLxx/` first, then run the extraction there.

## Procedure

### 1. Run the extraction script

```bash
python3 tools/pdf_to_txt.py BOOK.pdf [OUT.txt] [--first-page N] [--last-page N]
```

- Default output: `<pdf-basename>.txt` next to the PDF (never overwrite the PDF).
  Keep both inside the volume folder `series/<slug>/VOLxx/`.
- Use `--first-page` / `--last-page` to cut obvious cover/title pages or afterword pages when you already know the story's page range (check with `pdfinfo` and spot-read pages).

The script automatically:
- removes URL/ad/ISBN/publisher lines (`http`, `www.`, `visit us at`, `ISBN`, `pdfroom`, `t.me`, watermarks, "Created with", etc.),
- removes standalone page numbers and repeated running headers/footers,
- drops image-only pages,
- reflows hard-wrapped PDF lines into paragraphs (dehyphenates, fixes mid-word letter-run wraps like `Kyaaaaaa a!`),
- converts quoted text into `???: [text]` lines: paragraph-length quotes, quotes woven INTO THE MIDDLE of a narration sentence (the narration splits into fragments around the quote), consecutive quotes, quotes at a paragraph's end, and multi-paragraph quotes,
- keeps single-word inline scare quotes in narration (e.g. `the “voice” of a young man`, `a “path,”`, `were “demoted”`) — these are not spoken lines,
- keeps `<...>` system/transmission lines and ALL-CAPS headings as plain blocks.

### 2. Remove front/back matter (semantic review — MANDATORY)

Read the beginning and end of the output and **delete** (edit the file) every non-story block:
- copyright page, publisher info, ISBNs, translation credits,
- table of contents / chapter list,
- cover art and insert pages mentions, "Yen Newsletter" and other subscription ads,
- epigraphs ONLY if the user asks (they are often story content — when unsure, keep and mention it),
- afterword, acknowledgments, author afterwords, previews of other books, about-the-author blocks.

Cut them with a text editor (or re-run the script with tighter `--first-page/--last-page` when they occupy whole page ranges).

### 3. Fix residual errors (spot-check — MANDATORY)

Scan the output for these known residual cases and fix by editing the file:
1. **Mangled dialogue** — a `???: [...]` line whose inner text contains narration fragments or an unclosed quote (rare runaway quotes, e.g. a `‘`-quote absorbing later narration). Split into `???: [quote]` + narration line, or merge back into narration — follow the source paragraph.
2. **Spoken quotes left inline** — a narration line containing a *spoken* quote that the script kept inline (e.g. `He gave a surprised “Huh” and fell silent.`, `murmured “No kidding” with a smile.`). Extract it as its own `???: [...]` line; the narration splits into fragments around it (before-fragment and after-fragment stay as separate narration lines).
3. **Scare quotes wrongly extracted** — the opposite error: a metaphorical/ironic inline quote of 2+ words that the script extracted as `???: [...]` (e.g. `the “collective unconscious” of humankind`). Merge it back into the narration line. Rule of thumb: a quote is DIALOGUE only if someone actually speaks/thinks it aloud in the scene — ironic quotes naming a word or concept are NOT dialogue.
4. **`???: [...]` lines with no readable content** (only dashes/ellipses) — the script already removes them; if any remain, delete them.
5. **Mid-sentence paragraph splits** — a narration line ending without terminal punctuation followed by a line starting with a lowercase letter are joined by the script; fix any leftovers.
6. **Junk lines** — any leftover publisher/website/scan-credit text; delete.
7. **Missing sentence-final punctuation** — EVERY sentence must end with terminal punctuation (`.`, `?`, `!`, `…`). Scan every narration and `???: [...]` line (and the inside of dialogue lines) for text that ends a sentence without a terminal mark (a paragraph rarely ends mid-sentence; if one does because of an extraction artifact, add the appropriate `.` / `?` / `!`). This overrides the "do not add text" rule — restoring missing sentence-final punctuation is required, not a rewrite.
8. **Chapter heading punctuation** — chapter/section headings of the form `CHAPTER X` + `CHAPTER NAME` (often extracted as one heading block, e.g. `CHAPTER 1 CALL ON DUTY`) must be normalized to `CHAPTER X. CHAPTER NAME.` — a dot after the chapter number AND a final dot after the chapter name (e.g. `CHAPTER 1. CALL ON DUTY.`). The same trailing-dot rule applies to PROLOGUE/EPILOGUE/INTERLUDE headings when they carry a name; bare unnumbered headings like `EPILOGUE` stay as-is.

Quick checks you can run:

```bash
grep -n "???: \[.*[”»]" OUT.txt        # stray closers inside dialogue
grep -n "^[“„‘]" OUT.txt               # narration lines that still start with a quote
grep -nE "^[^???].*[“”„‘’]" OUT.txt     # quotes still inline in narration — review each
grep -n "http\|www\.\|ISBN\|Newsletter" OUT.txt   # leftover junk
```

### 4. Optional: trim/normalize

- Do NOT add or rewrite any text. The output must preserve the book's wording exactly (aside from quote-char stripping when a quote becomes `???: [...]` and paragraph reflow).
- Preserve blank lines between paragraphs (exactly one).
- Do not resolve `???` to names — even when context makes the speaker obvious.

## Output

- Write the final cleaned file (default `<pdf-basename>.txt`, or the name the user gave) and confirm the path.
- Print a summary **always in the form of a markdown table** containing:
  - source PDF and final output file (+ page range used),
  - blocks removed as junk (junk lines, image pages, running headers — approx. counts),
  - front/back matter blocks removed manually (list them: copyright page, TOC, afterword, …),
  - counts: `???: [...]` dialogue lines, narration paragraphs, headings,
  - manual fixes applied in step 3 (with line numbers),
  - anything intentionally KEPT although it looked like junk (e.g. an epigraph).
- Never present the summary as plain prose bullets only — the table is mandatory.

## Relation to ln-plain-copy

If the user wants a clean **human-reading copy** without the `???: [...]` / `Name: [...]`
dialogue wrappers (and without `<<emotion>>` tags), run the separate skill
`ln-plain-copy` on this file — it outputs `<name>-plain.txt` with labels and brackets
stripped. Do not modify this file itself.

## Relation to the ln-emotion-tagging skill

If the user later asks to emotion-tag the generated file with `ln-emotion-tagging`:
- run it normally, but **do not resolve `???` speakers to names** — that skill's rule 15 (resolve `???` only at 100% certainty) must be OVERRIDDEN for files generated by this skill: `???` is an intentional anonymization, so keep `???` unchanged in `-tagged.txt` output.

## Quality checklist

- Output file exists next to the PDF (in the volume folder `series/<slug>/VOLxx/`), PDF untouched.
- No URLs, publisher text, ISBNs, page numbers, running headers, or image pages remain.
- Copyright page, TOC, subscription ads, and afterword/acknowledgment blocks are removed.
- Every spoken line of the book is a `???: [...]` line (wording preserved, only outer quotes stripped) — including quotes woven into the middle of a narration sentence.
- No narration line contains a spoken quote inline; scare quotes (single-word, or clearly ironic) remain inline by design.
- Narration fragments around an extracted mid-sentence quote remain as their own narration lines.
- Every narration paragraph is plain prose on one line; exactly one blank line between blocks.
- No `???: [...]` line lacks readable content (dashes/ellipses only → deleted).
- ALL-CAPS chapter/interlude/epilogue headings are present and standalone.
- The wording of the book is never rewritten, added to, or summarized.
- Summary table printed with junk removal counts and manual fixes.

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step pdf-to-txt --file "<artifact>" \
    --duration <seconds> --resources "pdftotext + agent review" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
