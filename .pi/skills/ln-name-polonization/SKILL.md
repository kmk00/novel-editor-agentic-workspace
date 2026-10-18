---
name: ln-name-polonization
description: Polonizes (transliterates) English names and proper nouns into Polish phonetic spelling for Polish audiobook/TTS generation — e.g. Beatrice → Beatris, Undertaker → Andertejker. Scans a text for proper nouns, builds an EN→PL mapping file (with conventional Polish forms where they exist), applies it with case preservation, and runs a verification pass. Use when the user asks to polonize/Polish-ify names, transliterate character names, or prepare an English-named text for Polish TTS.
---

# Name Polonization (EN → PL phonetic)

Converts English proper nouns (character names, callsigns, epithets used as names)
into Polish phonetic spelling so a Polish TTS engine pronounces them naturally
(Undertaker read as "andertejker", not "andertejkejr" or worse).

**Deliverables per text:**

1. `<book-slug>-polonize.yaml` — the EN→PL mapping (human-reviewable, reusable across chapters/volumes),
2. `<input-stem>-plnames.txt` — the text with names polonized,
3. a verification pass + summary table.

## Paths

- Project root: the repository root (run every command from there)
- Scripts: `tools/polonize_scan.py`, `tools/polonize_apply.py`
- Per-series mapping: `series/<slug>/polonize.yaml` — **one shared file per
  series**, at the series level (not per volume).
- Chapter input/output files live in the volume folder `series/<slug>/VOLxx/`
  (see `docs/CONVENTIONS.md` §1a); keep `<input-stem>-plnames.txt` in that folder.

## Procedure

### 1. Scan for candidates

```bash
python3 tools/polonize_scan.py series/<slug>/VOLxx/<input>.txt > candidates.txt
```

Prints capitalized tokens with frequencies (heuristic filters out sentence-initial
common words). Also grep speaker labels — for `???: [ ... ]` / `Name: [ ... ]` files the
labels themselves are candidates. Review the list by hand: keep real proper nouns,
drop common words flagged by accident.

### 2. Build the mapping (`polonize.yaml`)

```yaml
"Beatrice": "Beatris"
"Undertaker": "Andertejker"
"Federacy": "Federacja"        # conventional Polish word, if one exists
"Kreutzbeck": "Krojcbek"       # German-origin names: use German→Polish phonetics
```

**Priority order when choosing the Polish form:**

1. **Conventional Polish exonym** if one exists and sounds natural (Elizabeth → Elżbieta,
   John → Jan, Catherine → Katarzyna). Do NOT force conventions that would sound archaic
   in a fantasy/sci-fi context (selling "Shin" as "Szin" may be better than a convoluted form) — when in doubt, ask the user.
2. **In-universe established Polish renderings** (e.g. official Polish translations of the franchise), if known.
3. **Phonetic transliteration** (rules below).

### 3. Transliteration rules (English phonetics → Polish spelling)

| English | Polish | Examples |
|---|---|---|
| a /eɪ/ (ay, a+e) | ej | Shane → Shejn, Kate → Kejt |
| i /aɪ/ (i, y, igh) | aj | Kai → Kaj, Ryne → Rajn |
| e /iː/ (ee, ea) | i | Keith →Kit→ Kit; Leaf → Lif |
| oo /uː/ | u | Cooper → Kuper |
| o /əʊ/ (o, oa, ow) | o | Roman stays Roman |
| u /juː/ | ju | Eugene → Ju-Dżin? → **Eudżin** (conventional) |
| sh | sz | Sheila → Szila |
| ch /tʃ/ | cz | Churchill → Czerczil |
| ch /k/ (Greek/germ. ch) | k | Chris → Kris |
| ck, k, c /k/ | k | Jack → Dżek |
| c /s/ (before e/i) | s | Cecil → Sesil |
| g /dʒ/ (before e/i) | dż | Ginny → Dżini |
| j | dż | Jack → Dżek |
| qu | kw | Quinn → Kwin |
| th | t (d in proven Greek forms) | Judith → Dżudit; Arthur → Artur |
| w /w/ | w | Wayne → Wejn |
| x | ks | Max → Maks |
| -er /ər/ | er | Undertaker → Andertejker |
| -or /ər/ | or | Victor → Wiktor |
| final silent e | drop | Rose → Roz |
| doubled consonants | single | Tanya → Tania |

German-origin names keep German phonetics read the Polish way: **eu → oj** (Kreutzer → Krojcer), **ei → aj** (Weisel → Wajzel), **ie → i**, **z → c** (Kreuz → Krojc), **sch → sz**, **v → f**, **u → u**.

Ask the user to review the mapping file before applying — this is the one gate worth a human eye.

### 4. Apply

```bash
python3 tools/polonize_apply.py series/<slug>/VOLxx/<input>.txt polonize.yaml series/<slug>/VOLxx/<output>.txt
```

Whole-word replacement, case-preserving (Title/lower/UPPER variants handled).
The mapping file is reusable for later chapters/volumes of the same series.

### 5. Declension pass (MANDATORY for Polish text)

Base-form replacement is not enough in Polish: *Andertejker walczy → bez Andertejkera*.
After `tools/polonize_apply.py`:

1. `grep -n -i "<pl-name>" <output>` — check every occurrence's grammatical case.
2. Fix inflected forms manually (gen. `-a/-u`, dat. `-owi/-ie`, etc. following Polish
   phonetic spelling rules). This pass needs the agent, not a script.
3. Re-check any *untranslated* English words still standing next to the polonized names —
   list leftovers and either map them too (loop to step 2) or leave deliberately.

### 6. Verify & report

- Confirm 0 remaining source-form occurrences: `grep -c -w "<EN name>" <output>` → 0 per entry.
- Confirm the mapping file was saved next to the workspace/output for reuse.
- Print the mandatory summary table: input, output, mapping file, names mapped,
  declension fixes applied, leftovers intentionally kept (with reason).

## Hard text rules (TTS safety)

- **NO angle brackets `<<` / `>>` anywhere in the output text.** Angle brackets break TTS/sound
  generation (the engine either eats them, garbles the sentence, or reads them aloud). If the
  source contains `<<...>>` markup (emotion tags, system lines), convert to parentheses `(...)`
  before/at application, and verify with `grep -c '<<\|>>' <output>` → 0.
- **Chapter/section headings must ALWAYS end with a period.** Every standalone heading line
  (e.g. `ROZDZIAŁ PIERWSZY`, `INTERLUDIUM`, `EPILOG II`, or an English `PROLOGUE`) gets a
  trailing `.` if it doesn't already end in terminal punctuation. Verify by grepping all-caps
  lines and checking each one ends in `.`, `!`, `?` or `…`.

## Relation to the translator (`translator/ln-translator/`)

The translator engine keeps a `glossary:` section in `translator/ln-translator/prompt.yaml`
that pins specific EN→PL renderings during translation. It has **no** `names.yaml` /
`polonizable.yaml` feature — do not assume one exists.

Workflow when a text is both translated and polonized:
1. Run the translator (`translate` / `refine`) with its glossary as usual.
2. Run this skill on the **Polish output** to phonetically polonize any names that stayed
   in English (e.g. callsigns like `Undertaker`), recording them in
   `series/<slug>/polonize.yaml` for reuse across volumes.

If you want a name rendered a specific way already at translation time, add it to the
translator's `glossary:` instead — but keep the polonization mapping as the single source
of truth for TTS pronunciation.

## Quality checklist

- Every mapped name is whole-word replaced, case-preserving.
- Conventional Polish exonyms used where they exist and sound natural.
- Phonetic rules applied consistently (same EN pattern → same PL pattern across all names).
- Declension pass done — no bare nominative forms stuck in oblique cases.
- 0 residual source-form occurrences (except ones deliberately kept, listed in summary).
- Summary printed as a markdown table.

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step name-polonization --file "<artifact>" \
    --duration <seconds> --resources "tools/polonize_scan.py + polonize_apply.py + agent" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
