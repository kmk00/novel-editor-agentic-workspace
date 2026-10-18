---
name: ln-speaker-resolution
description: "Resolves `???: [ ... ]` speaker labels in light-novel / web-novel chapter files to the correct character names based on context. The AGENT does the resolution itself (reading the chapter and reasoning from explicit anchors) — never a local LLM. Uses AGGRESSIVE matching to maximise coverage while still grounding every attribution in the text. Use when the user asks to resolve unknown speakers, fill in character names for `???` dialogue lines, or fix speaker labels before emotion tagging. ALWAYS follow up by running the built-in `--check` verification (and re-run the ln-tag-coverage-check if the file is a tagged output)."
---

# Speaker Resolution (`???` → Name) — AGENT-DRIVEN

Process a chapter text file and replace unknown-speaker labels `???` in dialogue lines with the correct character names, inferred from context. The output must be **byte-identical to the original except for the `???:` prefixes that were resolved** — no other character may change anywhere in the file.

**The AGENT resolves the speakers — not a local model.** Read the chapter, reason about the scene, and decide the speakers yourself. Do **not** call `tools/resolve_speakers_llm.py` (the local-model helper): it is too slow and less accurate than the agent. It stays in the repo only as a last-resort accelerator for huge books when the user explicitly asks for it.

**Aggressive matching is the default.** Aim to resolve *every* `???` line whose speaker the text determines — including by unambiguous speaker alternation within a two/three-person scene, by a unique role/description anchor, and by a character addressing the speaker by name. Do not leave a line as `???` merely because it lacks a formal speech-verb tag if the scene makes the speaker unambiguous. At the same time, never attribute a line to a character who is merely mentioned or addressed: if two candidates genuinely remain, keep `???`.

**Core invariant: only `???:` speaker labels may change.** The dialogue text inside `[...]`, all narration, blank lines, punctuation, tags (if present), and every other line must remain exactly as in the original. A named speaker (`Heinkel:`, `Filóre:`…) must NEVER be renamed.

## Input

The user provides a path to a text file containing the chapter. If the path is relative, resolve it against the current working directory. Optionally a second path for the output file; otherwise the default is `<original-name>-resolved.txt` next to the input (never overwrite the original unless explicitly asked).

**Volume layout.** Chapter files live in a volume folder `series/<slug>/VOLxx/`
(see `docs/CONVENTIONS.md` §1a); keep the resolved file in that same folder, next
to the input. The shared cast manifest stays at `series/<slug>/characters.yaml`.

## Workflow

1. **Scan** to enumerate the work:
   ```
   python3 tools/resolve_names.py --scan <file>
   ```
   If it reports `OK: no '???:' dialogue lines found`, the job is done — report it and stop.
2. **Read the chapter** in full, scene by scene, with `series/<slug>/characters.yaml` open for canonical spellings and aliases. Do not rely on isolated windows.
3. **Resolve aggressively** every `???` line the context determines (rules below).
4. **Write** `<original-name>-resolved.txt` and run the mandatory `--check`.
5. **Log stats** to `series/<slug>/stats.md` (see below).

## Resolution rules

1. Ground every attribution in the text: narration before/after the line, self-introduction, another character addressing the speaker by name, a unique role/detail anchor, or an unambiguous speaker alternation in a small scene.
2. **Be aggressive.** Resolve every line whose speaker the scene determines — including replies that alternate between two named characters. Do not withhold a name only because there is no literal “X said”.
3. **Never attribute to a mentioned/addressed character.** If a character is only talked about or spoken to, they are not the speaker. If two candidates genuinely remain, keep `???`.
4. **Use the exact spelling the chapter uses** (from other speaker labels or narration). Prefer the short label form used elsewhere; never invent spellings or anglicized forms.
5. Only the speaker label changes: `???: [text]` → `Name: [text]`. The text inside `[...]` stays byte-identical (including `<<...>>` tags).
6. Do not touch anything else: no renaming of known speakers, no text edits, no tag changes, no line deletions/additions, no reflowing of blanks.
7. Never resolve from tone/style alone or from outside knowledge/spoilers unless the chapter itself anchors the identity.

## Output

- Write the result to `<original-name>-resolved.txt` (default; do not overwrite the original unless the user explicitly asks).
- **MANDATORY: run the built-in verification** — it must exit with `PASS`:
  ```
  python3 tools/resolve_names.py --check <original-file> <resolved-file>
  ```
  The checker confirms: identical line count, only `???:` prefixes changed, dialogue bodies byte-identical, every new name is a plausible character name that actually appears in the file. On `FAIL`, fix the resolved file and re-run until `PASS`. Never present the result without a passing check.
- If the input file is an already emotion-tagged output (`-tagged.txt`), additionally re-run the coverage check afterwards:
  `python3 tools/check_coverage.py <original> <tagged-file>`
- Print a summary **always in the form of a table** (markdown table), containing at minimum:
  - each `???` line: line number, resolved name (or `kept as ???`), and the contextual evidence used,
  - counts: `???` lines found, resolved, kept unresolved, total lines in file,
  - the `--check` result (and coverage-check result if run).

## Stats logging (mandatory)

After the run, append one entry to the series stats file:
```
python3 tools/log_stats.py <slug> --step speaker-resolution --file "<resolved file>" \
    --duration <seconds> --resources "agent (no local model)" \
    --result "PASS" --notes "resolved X / left Y / total Z"
```
`series/<slug>/stats.md` is the single per-series log (created if missing). See `docs/STATS.md`.

## Quality checklist

- Every resolved speaker is grounded in an explicit contextual anchor (aggressive but not guessing).
- Every new name uses the chapter's own exact spelling and matches an existing label form.
- No dialogue text, tag, narration line, blank line, or punctuation changed anywhere.
- No named speaker was renamed; no line resolved from tone or outside knowledge.
- Unresolved `???` lines remain exactly as `???:` — consciously kept, listed in the summary.
- `tools/resolve_names.py --check` reported `PASS`.
- One entry appended to `series/<slug>/stats.md`.
- Summary presented as a markdown table with per-line evidence.

## Reference examples

```
???: [Yes. The traffic of dragon carriages…]        →  resolved only if the narration names the young man with the catalog nearby; otherwise kept as ???
???: [――You're a harder worker than I thought…]     →  Tiga: [――You're a harder worker than I thought…]   ← "a voice called out from behind Heinkel… the clergyman… Tiga Rauleon"

Heinkel: [Well, that's only natural…]               →  unchanged (never rename a named speaker)
???: [Eh!? W-with our own hands!?]                  →  unchanged if two candidates are plausible — no guessing
```
