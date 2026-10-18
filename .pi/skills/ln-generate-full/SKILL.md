---
name: ln-generate-full
description: "One-command full pipeline for a SINGLE book (PDF or EPUB): extract → canonical chapter TXT → resolve ??? speakers → build/verify characters.yaml → emotion-tag with the best local model → mandatory coverage gate → plain reading copy. Produces `<stem>.txt`, `<stem>-resolved.txt`, `<stem>-resolved-tagged.txt`, `<stem>-plain.txt` and updates `characters.yaml`. Use when the user asks to generate all files for a book in one go, 'full pipeline', '/ln-generate-full', or prepare a whole novel for audiobook TTS."
---

# Full book pipeline (one command)

Takes **one source book** (`.pdf` or `.epub`) and produces the complete set of
artifacts needed for audiobook TTS, running every sub-skill in order and stopping
at each mandatory gate. This is the orchestration layer over:

`ln-pdf-to-txt` / `epub_to_txt` → `ln-speaker-resolution` → `ln-voice-casting`
→ `ln-emotion-tagging` → `ln-tag-coverage-check` → `ln-plain-copy`.

Read `docs/CONVENTIONS.md` and `docs/PIPELINE.md` for the format/naming source of
truth. **Never skip a gate.**

## Input

- A path to a `.pdf` or `.epub` (relative paths resolve against the repo root).
- Optional: target directory (default: the directory containing the book, i.e.
  `series/<slug>/VOLxx/`), and a series slug (default: the series directory name,
  i.e. the parent of `VOLxx/`).

**Volume layout.** Every book lives in its own volume folder
`series/<slug>/VOLxx/` (or a title-slug folder for unnumbered books). The source
and ALL its artifacts stay in that folder; only the shared series files
(`characters.yaml`, `polonize.yaml`, `stats.md`) live one level up in
`series/<slug>/`. See `docs/CONVENTIONS.md` §1a. When the user passes a book in a
flat series dir, propose/move it into its `VOLxx/` first.

If the path is missing, ask the user which book to process.

## Output naming (all inside the volume folder `series/<slug>/VOLxx/`)

| File | Content | Produced by |
|---|---|---|
| `<stem>.txt` | canonical chapter format; dialogue `Name: [text]` or `???: [text]` | step 1 |
| `<stem>-resolved.txt` | `???` → real names (only 100% certain) | step 2 |
| `<stem>-resolved-tagged.txt` | inline `<<...>>` emotion tags | step 4 |
| `<stem>-resolved-tagged.cache.json` | per-line tag cache (safe to delete; makes re-runs cheap) | step 4 |
| `<stem>-plain.txt` | clean reading copy (no labels/brackets/tags) | step 6 |
| `characters.yaml` | cast manifest for the series (shared by all volumes, kept in `series/<slug>/`) | step 3 |

Optional (only when the user asks for Polish TTS): `polonize.yaml` and
`<stem>-polonized.txt` via `ln-name-polonization` (step 7).

## Procedure

### 1. Extract the book → canonical TXT

Detect the extension:

- **EPUB** — labels usually survive from the source (`Wilhelm: “…”`):
  ```bash
  python3 tools/epub_to_txt.py "series/<slug>/VOLxx/<Book>.epub"
  ```
  Drops cover/TOC/foreword/afterword/insert pages by default (`--keep`/`--drop` to
  override), keeps speaker labels, normalizes headings to `CHAPTER 1. NAME.`,
  reports anomalies. Check the reported `ANOMALIES` list.
- **PDF** — the PDF tool anonymizes EVERY speaker to `???` on purpose:
  ```bash
  python3 tools/pdf_to_txt.py "series/<slug>/VOLxx/<Book>.pdf" "series/<slug>/VOLxx/<stem>.txt" [--first-page N] [--last-page N]
  ```
  Then do the MANDATORY manual review from `ln-pdf-to-txt/SKILL.md`: remove
  front/back matter, fix mangled/inline dialogue, restore missing sentence-final
  punctuation, normalize chapter headings.

Both paths must end with exactly one blank line between blocks and no junk
(URLs, ISBNs, page numbers, running headers).

### 2. Resolve `???` speakers (AGENT-driven, aggressive)

The **agent** resolves the speakers — not a local model. Read the chapter scene by
scene, keep `series/<slug>/characters.yaml` open, and resolve aggressively: every
line whose speaker the text determines (explicit anchors, self-introduction, a name
addressed, a unique role, or unambiguous alternation in a small scene). Do not call
`tools/resolve_speakers_llm.py` unless the user explicitly asks for the local-model
accelerator. Never attribute a line to a merely mentioned/addressed character; if two
candidates genuinely remain, keep `???`.

All paths below are inside the volume folder (`VOLxx/`).

```bash
python3 tools/resolve_names.py --scan "series/<slug>/VOLxx/<stem>.txt" > /tmp/scan.txt
```
Edit the file (or apply a line→name map), then:
```bash
python3 tools/resolve_names.py --check "series/<slug>/VOLxx/<stem>.txt" "series/<slug>/VOLxx/<stem>-resolved.txt"   # MANDATORY → PASS
```
If nothing is resolved, still write `<stem>-resolved.txt` (identical content) so
downstream paths are stable. Keep the file's own spelling of each name.

For PDFs every dialogue line is `???`, so this step is large — work scene by scene.

### 3. Cast manifest → `characters.yaml`

There is exactly **one shared `characters.yaml` per series** (all volumes in
`series/<slug>/` use it) and it is **written in English** (only `polonize` holds
Polish forms). Create it from the template only if missing:

```bash
cp -n docs/characters.template.yaml "series/<slug>/characters.yaml"   # only if missing
python3 tools/voice_casting.py "series/<slug>/VOLxx/<stem>-resolved.txt" "series/<slug>/characters.yaml"
```
Add every **MISSING FROM CAST** speaker (canonical key = exact label, plus
`polonize`, `aliases`, English `register`). Re-run until **PASS**. `???` is fine here
(resolved later). Keep existing keys stable — the external TTS app is keyed by them.

### 4. Emotion-tag with the best local model

```bash
python3 tools/emotion_tagger.py "series/<slug>/VOLxx/<stem>-resolved.txt" --cast "series/<slug>/characters.yaml"
```
- Default model: **`huihui_ai/gemma-4-abliterated:26b`** with `"think": false`
  (reasoning models return empty JSON otherwise and everything falls back).
  Override with `--model`; `--think` re-enables reasoning (not recommended).
- Output: `series/<slug>/VOLxx/<stem>-resolved-tagged.txt` (+ `.cache.json`).
- Long books: run in the background and poll the log, e.g.
  ```bash
  nohup python3 tools/emotion_tagger.py "series/<slug>/VOLxx/<stem>-resolved.txt" \
      --cast "series/<slug>/characters.yaml" > /tmp/tag_<stem>.log 2>&1 &
  ```
  ~1.5–2 s/dialogue line on the default model. Re-runs reuse the cache.

### 5. Coverage gate (MANDATORY)

```bash
python3 tools/check_coverage.py "series/<slug>/VOLxx/<stem>-resolved.txt" "series/<slug>/VOLxx/<stem>-resolved-tagged.txt"   # MUST be PASS
```
On FAIL, fix the tagged file and re-run. Also run the tagging QA:
```bash
python3 tools/tag_qa.py "series/<slug>/VOLxx/<stem>-resolved-tagged.txt"    # MUST be PASS
```
It checks: dialogue lines == tagged lines, 0 untagged, 0 raw `<<`/`>>` outside
tags, 0 tags with >1 comma, 0 banned sound-effect words, tags start uppercase,
English-only, 4–24 words, and every spoken line ends with `.?!…`. Fallbacks are
allowed but should be few — with the default model expect <1% (a few per book).

### 6. Plain reading copy

```bash
python3 tools/plain_text.py "series/<slug>/VOLxx/<stem>-resolved-tagged.txt" "series/<slug>/VOLxx/<stem>-plain.txt"
```
Verify: 0 remaining `Name: [` labels, 0 `<<...>>`, 0 `[`/`]` in the plain file.

### 7. Polonization (OPTIONAL — only for Polish TTS, on request)

```bash
python3 tools/polonize_scan.py "series/<slug>/VOLxx/<stem>-resolved-tagged.txt" > /tmp/candidates.txt
# build/update series/<slug>/polonize.yaml, then:
python3 tools/polonize_apply.py "series/<slug>/VOLxx/<stem>-resolved-tagged.txt" \
    "series/<slug>/polonize.yaml" "series/<slug>/VOLxx/<stem>-polonized.txt"
# then manual declension pass (ln-name-polonization)
```

## Output

**Log every stage** to the single per-series stats file
(`series/<slug>/stats.md`, see `docs/STATS.md`) via
`python3 tools/log_stats.py <slug> --step <stage> --file "<artifact>" --duration <s>
--resources "<tool/agent/model>" --result <PASS|DONE> --notes "..."`, plus one
final `--step generate-full` row summarising the whole book.

Print a markdown summary table (mandatory), containing at minimum:

| Etap | Wynik |
|---|---|
| źródło / typ (pdf/epub) | … |
| `<stem>.txt` | bloki narracji / dialogi / nagłówki, usunięte front-back matter |
| `<stem>-resolved.txt` | `???` znalezione / rozwiązane / pozostawione (`resolve_names.py --check` → PASS) |
| `characters.yaml` | one shared per series (English; `polonize` PL) — speakers cast / `???` / missing (`voice_casting.py` → PASS) |
| `<stem>-resolved-tagged.txt` | otagowane linie, fallbacki, stutter, usunięte nieczytelne |
| bramki | `check_coverage.py` → PASS i `tag_qa.py` → PASS |
| `<stem>-plain.txt` | linie, 0 etykiet / 0 tagów |
| `stats.md` | jeden log serii: wiersz na każdy etap + zbiorczy `generate-full` |
| (opcjonalnie) polonizacja | pokryte nazwy / pliki |

Plus: lista rozwiązanych mówców (`linia: ??? → Imię` + dowód) i lista świadomie
pozostawionych `???`. Nigdy nie prezentuj wyniku bez PASS na wszystkich bramkach.

## Quality checklist

- Extraction produced the canonical format; headings normalized; front/back matter gone.
- Only `???` speaker labels changed in `-resolved.txt`; `--check` = PASS.
- Every named speaker has a `characters.yaml` entry; `voice_casting.py` = PASS. One
  shared manifest per series, written in English (only `polonize` is Polish).
- Tagged file: every dialogue line has exactly one `<<tag>>` after `[`, nothing else changed; `check_coverage.py` = PASS.
- Tags: English, concrete audible direction, ≤1 comma, no banned sound-effect words, no tag-only lines.
- `-plain.txt` has no labels, brackets or tags.
- All four (or five with polonization) files exist in the volume folder `series/<slug>/VOLxx/`; `characters.yaml` stays at the series level.
- `series/<slug>/stats.md` has one row per stage plus a final `generate-full` row.
- Summary table printed with per-stage counts and every gate result.

## Notes / gotchas

- **PDF** loses all speaker names (by design) — budget time for step 2; **EPUB**
  keeps most labels, only a handful of `???` remain.
- Do not run `ln-emotion-tagging` before steps 2–3: tags must be written against
  resolved names and the character `register`s.
- Same input twice = same output: the tag cache plus deterministic tools make
  re-runs and gate re-checks reproducible.
