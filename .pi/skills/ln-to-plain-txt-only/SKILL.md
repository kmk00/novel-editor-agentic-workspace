---
name: ln-to-plain-txt-only
description: "One-shot conversion of a book PDF or EPUB into a clean PLAIN reading text only — no speaker labels, no `???`, no `[ ]` brackets, no `<<emotion>>` tags, EVERY sentence and dialogue line on its own line, every spoken line wrapped in double quotation marks, every line terminal-punctuated. Skips speaker resolution, casting and emotion tagging. Use when the user asks for a plain/readable text from a PDF or EPUB with one sentence per line, or a 'plain only' / 'bez ???' version, without building the full audiobook pipeline."
---

# PDF / EPUB → plain text only (one sentence per line)

End-to-end conversion of a single book (**PDF or EPUB**) into a clean plain-text
reading copy — the final artifact of the pipeline, but produced directly, with
**no `???`**, no speaker labels, no brackets and no emotion tags:

```
PROLOGUE.

I was on the way home from the Seibunkan Bookstore near the station.

As I stepped off the tram with its bright red body, the intense sunlight forced me to avert my eyes.

Crossing the pedestrian walkway, I couldn't help but let a grin slip as the texture of the book cover in my hand registered in my palm.
That's right.
I have finally gotten my hands on the latest volume of (Anyone Who Calls Me Flat-Chested Can Step On Dog Poop).

“Welcome home, onii-sama!”
```

**Goal:** a file meant for *reading* (and TTS), where **every sentence and every
dialogue line is its own line** — each separated from the next by a blank line
(line-blank-line-blank) — and **every line ends with terminal punctuation**
(`.`, `?`, `!`, `…`). No `Name:`, no `???:`, no `[ ]`, no `<<...>>`. Every
spoken line is **wrapped in double quotation marks** (`“...”`) so the dialogue
is always distinguishable from the narration.

This skill **skips** `ln-speaker-resolution`, `ln-voice-casting` and
`ln-emotion-tagging` — it never needs to know who is speaking.

Read `docs/CONVENTIONS.md` (especially §1a volume layout) and `docs/PIPELINE.md`.

## Relation to the other skills

| Skill | Input | Output | Sentence per line? |
|---|---|---|---|
| **`ln-to-plain-txt-only`** (this) | PDF **or** EPUB | only `<stem>-plain.txt` | **yes** |
| `ln-pdf-to-txt` | PDF | `<stem>.txt` with `???: [...]` | no |
| `ln-pdf-to-plain-redacted` | PDF | `<stem>.txt` + `<stem>-plain.txt` | no (paragraphs kept) |
| `ln-plain-copy` | canonical TXT | `<stem>-plain.txt` | no (paragraphs kept) |
| `ln-generate-full` | PDF or EPUB | full set incl. `-resolved`, `-tagged` | no |

Use this skill when the user wants **just a clean plain text**, quickly, from a
source book — not the audiobook tagging chain.

## Input

- A path to a `.pdf` or `.epub` (relative paths resolve against the repo root).
- Optional: an output path (default: `<stem>-plain.txt` next to the source).

**Volume layout.** The source and the produced files belong in the volume folder
`series/<slug>/VOLxx/` (see `docs/CONVENTIONS.md` §1a). If the book sits flat in
`series/<slug>/`, move it into its `VOLxx/` first. Never place volume files in the
series root.

## Procedure

### 1. Extract the source into the canonical chapter format

Detect the extension and produce `<stem>.txt` (the intermediate; it may still
contain `???` for PDFs — that is fine, the plain pass removes all labels):

- **PDF** — anonymizes every speaker as `???` on purpose:
  ```bash
  python3 tools/pdf_to_txt.py "series/<slug>/VOLxx/<Book>.pdf" "series/<slug>/VOLxx/<stem>.txt" [--first-page N] [--last-page N]
  ```
- **EPUB** — keeps the source speaker labels:
  ```bash
  python3 tools/epub_to_txt.py "series/<slug>/VOLxx/<Book>.epub"
  ```
  Check the reported `ANOMALIES` list.

### 2. Manual cleanup of the intermediate (MANDATORY)

Read the beginning and end of `<stem>.txt` and fix by editing the file — follow
`ln-pdf-to-txt/SKILL.md` steps 2–3:

1. **Remove front/back matter**: copyright, publisher info, ISBNs, TOC, ads,
   newsletter, afterword, acknowledgments, previews, "about the author".
2. **Fix extraction artifacts**: mangled dialogue, spoken quotes left inline in
   narration, scare quotes wrongly extracted, mid-sentence paragraph splits,
   leftover junk lines.
3. **Normalize headings**: `CHAPTER X NAME` → `CHAPTER X. NAME.` (dot after the
   number AND at the end); PROLOGUE/EPILOGUE/INTERLUDE with a name get a trailing
   dot; bare `EPILOGUE` stays as-is.
4. **Terminal punctuation**: every sentence inside dialogue and narration must end
   with `.`, `?`, `!` or `…` before the plain pass (the plain pass can only add a
   safe `…`, it cannot recover a mangled sentence).

Do **not** resolve `???` to names — this skill does not care about speakers.

### 3. Flatten to plain, one sentence per line

```bash
python3 tools/plain_sentences.py "series/<slug>/VOLxx/<stem>.txt" "series/<slug>/VOLxx/<stem>-plain.txt"
```

(`--quotes` — wrap spoken lines in `“...”` — is the **default**; use
`--no-quotes` only if the user explicitly wants bare prose dialogue.)

The script:
- removes every `Name: [...]` / `???: [...]` wrapper (label + brackets),
- **wraps every spoken line in double quotation marks** (`“...”`) so dialogue is
  always distinguishable from narration (`--no-quotes` opts out),
- strips `<<...>>` emotion/direction tags,
- **converts ANY angle brackets to parentheses** — `<<...>>` / `<...>` → `(...)`
  (raw `<>` breaks TTS; plain text has no voice-design instructions),
- splits **narration and dialogue into sentences**, one per line,
- with the default `--spaced` behaviour, puts a **blank line after every line** (line-blank-line-blank), so each sentence/dialogue turn is visually and TTS-wise isolated (`--compact` opts out),
- guarantees **terminal punctuation** on every line (appends `…` when missing),
- keeps ALL-CAPS headings standalone, dotted,
- keeps `<...>` system/transmission lines as their own block, converted to `(...)`,
- drops unreadable lines (no letters/digits),
- normalizes blank lines to exactly one between blocks.

### 4. Verification gate (MANDATORY)

```bash
python3 tools/plain_sentences.py --check "series/<slug>/VOLxx/<stem>-plain.txt"   # MUST be PASS
```

`--check` fails on any leftover speaker label, `???`, **any raw `<` or `>`**,
unreadable line, or line without terminal punctuation. On FAIL, fix the source or
re-run.

Quick greps (belt and braces):

```bash
grep -cE '^[^:]+: \[' "series/<slug>/VOLxx/<stem>-plain.txt"   # -> 0 labels
grep -c '???'          "series/<slug>/VOLxx/<stem>-plain.txt" # -> 0
grep -c '[<>]'         "series/<slug>/VOLxx/<stem>-plain.txt" # -> 0 (angle brackets -> parentheses)
grep -c '\['           "series/<slug>/VOLxx/<stem>-plain.txt" # -> 0 brackets
```

### 5. Log stats

```bash
python3 tools/log_stats.py <slug> --step to-plain-txt-only \
    --file "series/<slug>/VOLxx/<stem>-plain.txt" \
    --duration <seconds> --resources "pdftotext|epub_to_txt + plain_sentences.py + agent" \
    --result PASS --notes "<sentences / dialogue / headings / unreadable dropped>"
```

## Output

- Write the result to `series/<slug>/VOLxx/<stem>-plain.txt` (never overwrite the
  source). Keep the intermediate `<stem>.txt` next to it (useful for re-runs).
- Print a summary **always as a markdown table**:

| Etap | Wynik |
|---|---|
| źródło / typ (pdf/epub) | … |
| `<stem>.txt` (intermediate) | bloki narracji / dialogi / nagłówki; usunięty front/back matter |
| `<stem>-plain.txt` | zdania, tury dialogowe (w cudzysłowach `“...”`), nagłówki, linie systemowe, nieczytelne usunięte |
| bramka `plain_sentences.py --check` | `PASS` |
| braki | 0 labeli / 0 `???` / 0 nawiasów `[ ]` / 0 tagów / **0 nawiasów kątowych `<>`**; każda linia z interpunkcją |
| `stats.md` | wiersz `to-plain-txt-only` |

Never present the result without a passing `--check`.

## Quality checklist

- Source is a PDF or EPUB; the output is a single `<stem>-plain.txt` in `VOLxx/`.
- **Zero** `Name: [` labels, `???:`, `[ ]` brackets, `<<...>>` tags and **any `<`/`>` angle brackets** (converted to `()`).
- **Every non-blank line ends** with `.`, `?`, `!` or `…`.
- **Every sentence / dialogue line is on its own line** (narration split too).
- **Every spoken line is wrapped in double quotation marks** (`“...”`).
- ALL-CAPS headings present and dotted; `<...>` system lines kept and converted to `(...)`.
- No unreadable (letter/digit-free) lines remain.
- Front/back matter and junk removed in the manual pass.
- `python3 tools/plain_sentences.py --check <plain>` reported `PASS`.
- One `to-plain-txt-only` entry appended to `series/<slug>/stats.md`.
- Summary table printed.
