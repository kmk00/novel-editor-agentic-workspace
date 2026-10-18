---
description: Convert a book PDF to a clean plain-text reading copy (no ??? labels, no brackets, dotted chapter headings, empty lines removed)
argument-hint: "<path-to-pdf>"
---
Convert the book PDF `$1` into a plain redacted text file using the full pipeline described in the skill `ln-pdf-to-plain-redacted` (read `.pi/skills/ln-pdf-to-plain-redacted/SKILL.md` first and follow it exactly). The PDF and both outputs stay in the volume folder `series/<slug>/VOLxx/` (see `docs/CONVENTIONS.md` §1a); if the PDF sits flat in the series dir, move it into its `VOLxx/` first:

1. Extract with `python3 tools/pdf_to_txt.py` into `<pdf-basename>.txt` next to the PDF (in `VOLxx/`).
2. Remove front/back matter and junk, fix extraction artifacts, normalize chapter headings to `CHAPTER X. CHAPTER NAME.`, and make sure every sentence ends with terminal punctuation (verify each fix against the raw PDF — never add fake periods to real mid-sentence fragments).
3. Flatten with `python3 tools/plain_text.py` into `<pdf-basename>-plain.txt` (no `???` labels, no brackets).
4. Delete every line with no letters/digits (pure `…`, `!…`, dashes) and re-normalize blank lines.
5. Verify the final file and print a markdown summary table.

If `$1` is empty, ask the user which PDF to convert.
