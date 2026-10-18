---
name: ln-emotion-tagging
description: Adds emotion direction tags (<<...>>) to light-novel / web-novel chapter dialogue lines for audiobook voice-direct TTS, preserving every line of the original file. This is the CANONICAL tagging format (the legacy 86 `tags*.json` workflow is deprecated). Use when the user asks to add emotions to a chapter file, tag dialogue with emotions, or prepare a text for audiobook generation. ALWAYS follow up by running the ln-tag-coverage-check skill on the generated file.
---

# Light-Novel Audiobook Emotion Tagging

Process a chapter text file and insert emotion direction tags into spoken dialogue lines, so a voice-direct audiobook generator can perform each character appropriately.

**Canonical format.** Inline `<<...>>` tags placed right after the opening `[` are the single canonical tagging format for this project. The old per-line JSON workflow (`tagsNN.json` + `apply_tags.py`) is **legacy** — do not start new work with it; migrate any remaining old files to inline tags when you touch them.

**Cast manifest.** Character identities, aliases and vocal registers are defined per series in `series/<slug>/characters.yaml` (see the `ln-voice-casting` skill). Tags here direct *performance*; the manifest supplies the character's `register` and keeps speaker labels stable.

**Core invariant: the tagged file must contain EVERY READABLE line of the original file, in the same order — no readable line may ever be deleted or added.** UNREADABLE lines (see "Lines removed as unreadable" below) are DELETED from the output, never copied and never tagged. After writing the tagged file you MUST run the `ln-tag-coverage-check` skill (see Output) — it knows about the unreadable-line exception.

## Input

The user provides a path to a text file containing the chapter. If the path is relative, resolve it against the current working directory.

**Volume layout.** Chapter files live in a volume folder `series/<slug>/VOLxx/`
(see `docs/CONVENTIONS.md` §1a); keep the tagged file in that same folder, next
to the input. The shared cast manifest stays at `series/<slug>/characters.yaml`.

## Format rules

The chapter consists of two kinds of lines:

1. **Dialogue lines** — format `CharacterName: [speech text]`. These get emotion tags.
2. **Narrator / narration lines** — plain prose without `Name: [...]` structure. These must NEVER get emotion tags.

Emotion tags use double angle brackets, placed immediately after the opening `[` of the dialogue, followed by a space.

Tags are **voice-direction instructions written in plain language**, not abstract emotion labels. **Tags are ALWAYS written in English**, regardless of the language of the chapter text. Each tag tells the TTS engine how to perform the line: a delivery verb/adverb, concrete audible traits (volume, pacing, vocal texture), and — when it sharpens the read — a short "as if …" motivation clause:

```
Filóre: [<<Say it brightly, with eager rising energy, as if she has just decided something wonderful>> I see! And as for that crate, I shall――]

Heinkel: [<<Snapping irritably, low and gravelly, as if fed up with the whole conversation>> Oi…]

Filóre: [<<Saying it with a cheerful laugh, quick and confident, brushing off the outburst>> ――Not do it, rather, I entrust it to you! After all, carrying things is your job!]
```

Every spoken line's text ends with a punctuation mark (`.`, `?`, `!`, `…`, `...`, `!?`, `?!`) — never a bare word or trailing dashes.

Concrete audible traits beat abstract personality words: "very quiet and tense" directs a performance, "angry" does not. The tag shapes how the line is delivered — emotion, pacing, volume, texture — never who the voice is.

## Tagging procedure

1. Read the entire input file.
2. Identify every dialogue line matching `^\s*[^:\[\]]+\s*:\s*\[` .
3. For each dialogue line, infer the emotion from:
   - The character's personality and known traits — take them from `series/<slug>/characters.yaml` (each entry has an English `register`, e.g. "cold, composed, clipped sentences" or "expressive, whiny, playfully offended"). The cast manifest is the source of truth for how a character should sound.
   - The content and punctuation of the line itself (!? → shock/excitement/anger, ―― dashes → hesitation or dramatic interruption, trailing … → low/reluctant/gloomy tone).
   - Context of surrounding lines (continuation of a previous reaction, escalation, etc.).
4. Compose the direction tag using the three-part formula **delivery + audible traits + motivation** (always in English):
   - **Delivery** — what the actor does: "Say it excitedly", "Snapping irritably", "Whispering", "Saying it while holding back tears", "With a dry, dismissive tone".
   - **Audible traits** — how it sounds: volume ("very quiet and tense", "loud enough to startle"), pacing ("slow and deliberate", "rushing the words", "with a nervous pause after the first phrase"), texture ("gravelly", "sing-song").
   - **Motivation (optional "as if …")** — the intent behind the line: "as if trying to hide panic behind humor", "as if afraid of being overheard", "as if bringing him here deeply hurt her".
   - Good: `<<Saying it sarcastically, with dry disbelief and a dismissive tone, as if this was obviously a terrible idea>>`, `<<Whispering, very quiet and tense, as if afraid of being overheard>>`.
   - Bad: `<<Angry>>`, `<<Nervously>>` — abstract labels; rewrite them as audible, performable directions.
   - Keep tags to one sentence fragment (roughly 8–20 words); long enough to direct the performance, short enough to stay readable in the file.
   - **Avoid multiple commas inside a tag.** TTS engines read commas as pauses even inside a direction tag, splitting the instruction into disconnected fragments and producing garbled audio. Use "and" to join descriptors instead of comma-separated lists. At most one comma is permissible (typically before an "as if …" clause).
5. **NEVER use sound-effect or vocal-noise words in tags.** The TTS engine renders these literally as sound effects instead of speech — producing long unwanted noises (e.g. 10 seconds of sighing), unintelligible mumbling, or extra phantom words. Banned word families (in English or Polish):
   - **Breath/sigh family** — `breath`, `breathing`, `breathy`, `catching breath`, `sigh`, `sighing`, `exhale`, `exhaling`, `inhale`, `gasp`, `gasping`, `pant`, `panting`, `wheeze`, `huff`, `westchnienie`, `wzdychając`, `łapiąc oddech`, `dyszący`.
   - **Vocal-noise family** — `moan`, `groan`, `sob`, `sobbing`, `whimper`, `wail`, `sputter`, `sputtering`, `choked`, `choking`, `strangled`, `jęk`, `szloch`, `jęk`, `charcząc`.
   - **Animal/onomatopoeia family** — `bark`, `barking`, `growl`, `growling`, `snarl`, `hiss`, `hissing`, `purr`, `howl`, `bleat`, `szczekać`, `warknąć`, `syczeć`.
   - **Stutter-as-direction (NARROWED)** — the single word `Stuttering` is now PERMITTED, but only when the written stutter has been normalized out of the text (see rule 7: `A-are` → `Are` + tag `<<Stuttering>>`). Never combine `Stuttering` with texture words, and never direct the engine to `stammer` or `sputter`.
   - Replace them with plain emotional delivery + state of voice. Examples of safe rewrites:
     - `<<Breath catching, whispered with raw anguish>>` → `<<Whispered with raw anguish, very soft and strained>>`
     - `<<Barking in exasperation, loud and incredulous>>` → `<<Snapping sharply, loud and incredulous>>`
     - `<<Saying it with a weary sigh>>` → `<<Saying it wearily, flat and tired>>`
6. **At most ONE texture descriptor per tag.** Do not stack heavy texture words ("choked" + "voice cracking" + "whispered"). The engine chokes on stacked texture directions and produces unintelligible speech. Pick the single most important audible trait and lean on delivery + volume + pacing for the rest.
7. **Special rule for lines with cut-off words, stutters, or truncated exclamations** — distinguish between:
   - **Full-word reactive exclamations** (1–2 syllables, complete words: `Ah?`, `Oh!`, `Huh?`, `What?`). These may take a normal short tag.
   - **Written stutters (`A-are`, `W-with`) — NORMALIZE the text.** A written stutter (`A-are you insane…!?`, `W-with our own hands!?`) is a trap for the TTS engine (hyphen read as a pause, half-word glitches). Collapse it to the full word and move the hesitation into the tag:
     - `Heinkel: [A-are you insane…!?]` → `Heinkel: [<<Stuttering, loud and alarmed>> Are you insane…!?]`
     - Keep the tag short and plain: `Stuttering` + volume/pacing (e.g. `<<Stuttering, loud and alarmed>>`); at most one comma; NO texture descriptors; never mention the stutter mechanics in the tag.
   - **Truncated / cut-off words** (`Idi…!`, `Wha`, `Stu-`). Do NOT reconstruct these into full words — keep them as-is (add `…` if needed). The TTS engine struggles to pronounce half-words, so use an **ultra-short, plain tag** (4–8 words, delivery + volume only, no texture descriptors, no commas, no "as if" clause). Never mention the cut-off itself in the tag.
   - Good (stutter): `<<Stuttering, loud and alarmed>> Are you insane…!?` on `A-are you insane…!?`.
   - Good (truncated): `<<Shouting in disbelief>>`, `<<Exclaimed fast and loud>>`.
   - Bad: `<<Blurted in choked shock, voice cracking with disbelief>>` on `Idi…! A-are you insane…!?` — stacked texture + comma + truncated word produced broken audio.
   - Bad: `<<Stuttering, with a voice cracking under disbelief>>` — `Stuttering` stacked with texture breaks the engine.
   - Good (full-word exclamation): `<<Exclaimed in shock, fast and raised>>` on `Ah?` — a complete word handles a slightly richer tag.
8. **Dash-only / empty dialogue lines are DELETED** — if the spoken text inside `[...]` consists ONLY of dashes (e.g. `[――]`, `[――――]`), or is empty, the line has nothing the TTS engine can read. DELETE the whole line from the output. NEVER convert it into a tag-only line (`Name: [<<...>>]`) — a line containing nothing but the tag has no spoken text and the TTS engine silently IGNORES it.
   - Example: `Heinkel: [――――]` → line removed entirely.
9. **Leading dashes before real speech** — if the line contains actual spoken words after the dashes (e.g. `――Heinkel Astrea-dono, there is an active order`), simply REMOVE the leading `――` dashes and tag the line normally. Do not remove anything else.
10. **Symbol-only filler lines are DELETED** — standalone lines containing no letters or digits, only decorative/symbol characters (dashes with dots `――.`, `――――.`, dot runs `………`, triangle patterns `△▼△▼△▼△`, `◆`, `※`, tildes, etc.) are unreadable for TTS. DELETE them from the output, never tag them. This applies to narration filler and dialogue alike.
11. Insert the tag right after `[` (with one space after the tag). If the dialogue continues over multiple consecutive lines by the same character (e.g. split by ―― or continued sentences), tag each spoken line/segment individually, choosing a fitting performance direction for each part — vary volume, pacing, and energy between the segments (e.g. building excitement, then breathless completion). Careful: "breathless" is fine as a word here only when it describes pacing, but prefer "rushing the words" to stay clear of the banned breath family.
12. **Every spoken line must end with a punctuation mark** — the words inside `[...]` (after the tag) must finish with `.`, `?`, `!`, `…`, `...`, `!?` or `?!`. If they don't (e.g. a word cut off mid-breath like `Wha`, or the trailing `――` dashes were stripped), append `…` — ellipsis is always the safe choice for interrupted or trailing speech. Examples:
    - `Heinkel: [Wha]` → `Heinkel: [<<tag>> Wha…]`
    - `Heinkel: [Wha――]` → dashes removed, `…` added → `[<<tag>> Wha…]`
    - `Filóre: [I see]` → `Filóre: [<<tag>> I see…]` (or `.` if the sentence is complete)
13. Never modify the dialogue text itself — only insert tags — EXCEPT for the cases above (rules 9 and 12: leading/trailing dashes, missing end punctuation). Otherwise preserve all original spacing, blank lines, punctuation, and special characters (…, etc.) exactly. **No line may be deleted under any circumstance.**
14. Never tag narrator lines, scene descriptions, or sound effects written as plain text.
14b. **No literal angle brackets in narration.** Emotion tags `<<...>>` are the only permitted
   use of angle brackets (the TTS pipeline strips them). Any literal `<<...>>` markup inside
   NARRATION (system/transmission lines like `<<No Face to network.>>`) must be converted to
   parentheses `(...)` in the tagged output — raw `<<`/`>>` outside emotion tags break sound
   generation. Verify: after stripping `<<tag>>` emotion tags, `grep -c '<<\|>>'` → 0.
14c. **Chapter/section headings must ALWAYS end with a period** — append `.` to any standalone
   heading line lacking terminal punctuation (`!`, `?`, `…` count as terminal).
15. **Unknown speaker `???` — resolve only at 100% certainty.** When a dialogue line's speaker is `???`, identify who is speaking from the surrounding context: narration directly before/after the line ("the Knights that surrounded him", "the girl clamorously flew out of her chair", "a voice resonated in his mind"), the character's own self-introduction, or another character addressing them by name (e.g. `Heinkel: [――Louanna.]`). If the identity is **certain beyond any doubt**, replace `???` with the character's real name, using the exact name/spelling that other lines of the chapter use for that character (e.g. `Knight`, `Filóre`, `Louanna`). If there is ANY doubt — no explicit contextual anchor, two plausible candidates, or a deliberately anonymized voice — keep `???` unchanged and tag the line normally. List every resolved speaker (line number: `???` → `Name`, and the evidence) in the output summary.
   - Good resolution: `???: [Ah! I've been waiting for you, Heinkel-sama!]` followed by "the girl … flew out of her chair" and `Girl: [I am Filóre Lugunica…]` → `Filóre: [<<tag>> Ah! …]`.
   - Keep as `???`: an overheard or disembodied voice with no naming anchor anywhere in the scene.

## Automated tagging helper (local, open source)

`tools/emotion_tagger.py` performs the tagging automatically with a **local
open-source LLM via Ollama** — no cloud, no proprietary API. It runs a light
structured analysis per line (emotion, intensity, volume, pacing, texture,
intent) and renders a short **English** performance-direction tag, then inserts
it into the canonical `Name: [<<tag>> speech]` format.

```bash
# 1) tag (chapter must already have Name: [...] labels, i.e. after speaker resolution)
# Default model is the best available locally: huihui_ai/gemma-4-abliterated:26b
python3 tools/emotion_tagger.py series/<slug>/VOLxx/<chapter>.txt \
    --cast series/<slug>/characters.yaml --out series/<slug>/VOLxx/<chapter>-tagged.txt

# 2) MANDATORY gate
python3 tools/check_coverage.py series/<slug>/VOLxx/<chapter>.txt series/<slug>/VOLxx/<chapter>-tagged.txt
```

**Model choice.** The tagger defaults to the strongest locally installed model
(`huihui_ai/gemma-4-abliterated:26b`). Reasoning-capable models (gemma-4, qwen3…)
must be called with `"think": false` — the tool sends it by default. Without it
they spend the whole token budget thinking and return EMPTY JSON, which silently
degrades every line to the deterministic fallback renderer. Use `--think` only to
re-enable reasoning deliberately, and `--model` to override the model.

Guarantees enforced in code (in addition to the rules above): English-only tags,
<=1 comma, no banned sound-effect words, <=1 texture, stutter lines get a short
`Stuttering` tag, dash-only/empty dialogue and symbol-only filler are deleted.
A per-line cache (`<out>.cache.json`) makes re-runs fast; the model-written tag
is used when valid and a deterministic fallback renderer is used otherwise.
The human/agent rules below still apply when tagging by hand or reviewing the
automatic output.

## Known-bad outputs (produced broken audio — never reproduce)

These real examples generated defective audio (long sigh/breath effects, unintelligible speech, extra words):

```
Heinkel: [<<Breath catching, whispered with raw anguish, as if the name tore through twenty years of silence>> Louanna.]        ← "Breath catching" → engine rendered breathing noise
Heinkel: [<<Barking in exasperation, loud and incredulous, as if scolding an obstinate child>> If that's the case then...]       ← "Barking" → onomatopoeia, unintelligible output
Heinkel: [<<Blurted in choked shock, voice cracking with disbelief>> Idi…! A-are you insane…!?]                                  ← stacked texture on a stutter/cut-off line → extra phantom words
Heinkel: [<<Quiet and wry, edged with self-reproach, as if bracing for her to reconsider>> You may end up regretting that you chose me, but…]  ← two commas inside the tag → fragmented, garbled instruction
```

## Lines removed as unreadable

The following lines are **DELETED** from the output (never copied, never tagged) because the TTS engine has nothing readable to speak in them:
- Dialogue lines with only dashes inside `[...]` (`Name: [――]`, `Name: [――――]`) or an empty `[...]`.
- Symbol-only filler lines (`――.`, `――――.`, `△▼△▼△▼△`, dot runs, `◆`, `※`, tildes, etc.) — any line with no letters or digits.

Every other line of the original file — narration, dialogue, blank lines — must also appear in the output, in the same order. The only permitted changes are: tag insertion after `[`, removal of leading/trailing `――` dashes around real speech, adding a trailing punctuation mark (`…`) per rule 12, and resolving a `???` speaker to a certain name per rule 15. The `ln-tag-coverage-check` script automatically skips the unreadable lines when comparing.

## Output

- Write the tagged result to a new file next to the input: `<original-name>-tagged.txt` (in the same `series/<slug>/VOLxx/`; do not overwrite the original unless the user explicitly asks).
- **MANDATORY: after writing the tagged file, run the coverage check skill** — execute:
  `python3 tools/check_coverage.py <original-file> <tagged-file>`
  It must exit with `PASS`. If it reports any error, fix the tagged file and re-run until it passes. Never present the result to the user without a passing check.
- Then run the tagging-rule QA:
  `python3 tools/tag_qa.py <tagged-file>` — must be `PASS` (one tag per dialogue line,
  English, 4–24 words, ≤1 comma, no banned sound-effect words, every spoken line
  terminal-punctuated).
- Print a summary **always in the form of a table** (markdown table), containing at minimum:
  - per character: number of dialogue lines tagged, and — when useful — the emotional register of their tags,
  - resolved `???` speakers (`???` → `Name`, with the contextual evidence) and any `???` kept unresolved,
  - counts: tagged lines, untouched narration lines, unreadable lines deleted, total lines in vs. out,
  - special rules applied (leading/trailing dashes, added `…`, short tags on cut-off lines, etc.),
  - the coverage-check result.
  Never present the summary as plain prose bullets only — the table is mandatory.

## Relation to the other skills

Pipeline: `ln-pdf-to-txt` → `ln-speaker-resolution` → `ln-voice-casting`
(cast from `series/<slug>/characters.yaml`) → **`ln-emotion-tagging`** →
`ln-tag-coverage-check` (mandatory gate) → `ln-plain-copy` for a human-reading copy.
Translation runs in parallel via `translator/ln-translator/`, with
`ln-translation-error-check` as its repair gate.

## Quality checklist

- **Every readable line of the original file exists in the output, in the same order — zero deletions of readable lines.**
- Every unreadable line (dash-only/empty dialogue, symbol-only filler) is deleted from the output.
- Every `Character: [...]` line contains exactly one tag placed right after `[`.
- No dialogue line consists of a tag alone (`Name: [<<...>>]`) — every tagged line has spoken words after the tag.
- Real speech lines that started with `――` no longer contain the leading dashes.
- No symbol-only filler lines (`――.`, `――――.`, `△▼△▼△▼△`, dot runs, etc.) remain in the output.
- Every spoken line ends with `.`, `?`, `!`, `…`, `...`, `!?` or `?!` — especially short cut-off words like `Wha…]`.
- No tag contains a banned sound-effect/vocal-noise word (breath, sigh, gasp, moan, groan, sob, whimper, sputter, choked, strangled, bark, growl, hiss, purr, howl, stammer, stutter — and their Polish equivalents).
- At most one texture descriptor per tag.
- Tags contain at most one comma (preferably none); never multiple comma-separated clauses inside a tag.
- Written stutters (`A-are`, `W-with`) are normalized to full words in the text and tagged with a short plain `Stuttering` tag (delivery + volume only, at most one comma, no texture, no "as if").
- Truncated / cut-off words (`Idi…`, `Wha`, `Stu-`) stay as-is and get ultra-short plain tags (delivery + volume only, no commas, no texture, no "as if"). Full-word exclamations (`Ah?`, `Oh!`) may use a short tag.
- No narrator lines contain tags.
- Emotions match context, not just punctuation — re-read the scene around each line if unsure.
- No duplicate or contradictory tags on the same line.
- Every tag is a concrete, audible performance direction (delivery + traits [+ "as if …"]), never a bare abstract label like `<<Angry>>`.
- Consecutive lines by the same character differ in at least one audible trait, so the delivery evolves instead of repeating.
- The coverage check script has been run and reported `PASS`.
- Every `???` speaker has either been resolved to a concrete name (with contextual evidence listed in the summary) or consciously kept as `???` — never guessed.

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step emotion-tagging --file "<artifact>" \
    --duration <seconds> --resources "ollama huihui_ai/gemma-4-abliterated:26b" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
