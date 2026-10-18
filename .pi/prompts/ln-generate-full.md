---
description: Full one-command pipeline for a single book (PDF or EPUB) — extract, resolve ??? speakers, build characters.yaml, emotion-tag with the best local model, coverage gate, plain reading copy
argument-hint: "<path-to-book.pdf|book.epub> [volume-dir]"
---
Run the **complete single-book pipeline** for `$1` by following the skill
`ln-generate-full` (read `.pi/skills/ln-generate-full/SKILL.md` first and follow
it exactly), plus `docs/CONVENTIONS.md` and `docs/PIPELINE.md`.

**Volume layout:** each book lives in its own folder `series/<slug>/VOLxx/`
(shared series files — `characters.yaml`, `polonize.yaml`, `stats.md` — stay at
`series/<slug>/`; see `docs/CONVENTIONS.md` §1a).

Target volume dir: `$2` if given, otherwise the directory containing the book
(move it into the right `VOLxx/` first if it sits flat in the series dir).
Produce, inside the volume folder:

1. `<stem>.txt` — canonical chapter format
   - `.epub` → `python3 tools/epub_to_txt.py "$1"`
   - `.pdf`  → `python3 tools/pdf_to_txt.py "$1"` + mandatory manual cleanup
     (front/back matter, artifacts, sentence punctuation, headings).
2. `<stem>-resolved.txt` — run `python3 tools/resolve_names.py --scan`, resolve
   `???` **only at 100% certainty**, then `--check` must be **PASS**.
3. `characters.yaml` — series-level file at `series/<slug>/characters.yaml`
   (create from `docs/characters.template.yaml` if missing, **not** per volume),
   fill every MISSING speaker, `python3 tools/voice_casting.py` must be **PASS**.
4. `<stem>-resolved-tagged.txt` —
   `python3 tools/emotion_tagger.py "<stem>-resolved.txt" --cast characters.yaml`
   (default model `huihui_ai/gemma-4-abliterated:26b`, `think:false`; for long
   books run in the background with a log and poll it).
5. `python3 tools/check_coverage.py "<stem>-resolved.txt" "<stem>-resolved-tagged.txt"`
   must be **PASS**; fix and re-run on failure.
6. `<stem>-plain.txt` — `python3 tools/plain_text.py "<stem>-resolved-tagged.txt" "<stem>-plain.txt"`.

Do not stop at a failing gate. Finish by printing the mandatory markdown summary
table (per-stage counts, resolved + deliberately-kept `???`, all gate results).

If `$1` is empty, ask the user which PDF/EPUB to process.
