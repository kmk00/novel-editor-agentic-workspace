---
name: ln-tag-coverage-check
description: Verifies that an emotion-tagged chapter file preserves EVERY readable line of the original file — no readable line deleted, no dialogue text altered beyond allowed transformations (tag insertion, dash stripping, added end punctuation); unreadable lines (dash-only/symbol-only) must be absent. MUST be run after every ln-emotion-tagging tagging session, and any time the user asks to check/verify line coverage of a tagged chapter.
---

# Tagged Chapter Coverage Check

Compare the original chapter file with its `-tagged.txt` output and prove that **no readable line was deleted, added, or improperly modified**. Unreadable lines (dash-only/empty dialogue, symbol-only filler) must be ABSENT from the tagged output. This check is mandatory after every tagging run of the `ln-emotion-tagging` skill.

## When to run

- Always, immediately after writing a new `-tagged.txt` file (the emotions skill mandates this in its Output section).
- Any time the user asks to verify that all lines/kwestie are covered.

## How to run

```
python3 tools/check_coverage.py <original-file> <tagged-file>
```

Paths are resolved against the current working directory. If the tagged path isn't given explicitly, it is the original filename with `-tagged` appended before the `.txt` extension.

## What the checker verifies

1. **Line count equality** — the tagged file must have exactly as many lines as the original minus its unreadable lines. Lines are compared 1:1 by index after the original's unreadable lines are skipped (see below).
2. **Text coverage** — for each line pair, the tagged line (after removing `<<...>>` tags) must be equal to the original, or differ ONLY by the allowed transformations:
   - an inserted tag (`<<...>> ` right after the opening `[`),
   - removal of leading `――` dashes before real speech,
   - removal of trailing `――` dashes with a compensating `…` (or `.`) appended,
   - a trailing `…` (or `.`) appended to complete a cut-off line,
   - a `???` speaker resolved to a certain character name (only when identity is 100% certain; renaming a known speaker is forbidden).
3. **Tag placement** — a changed dialogue line must contain exactly one tag, placed immediately after `[`, followed by actual spoken text (never a tag-only line).
4. **Unreadable lines are absent** — dash-only dialogue lines (`Name: [――]`, empty `[...]`) and symbol-only filler lines (`――.`, `△▼△▼△▼△`, dot runs, etc.) must NOT appear in the tagged output at all (deleted, not tagged).
5. **Narration purity** — no narrator line may receive a tag; narration lines must be byte-identical to the original.
6. **End punctuation** — every tagged line's spoken text must end with `.`, `?`, `!`, `…`, `...`, `!?` or `?!`.
7. **No banned sound-effect words in tags** — tags must not contain breath/sigh/gasp/vocal-noise/onomatopoeia words (English and Polish): `breath`, `breathing`, `breathy`, `sigh`, `sighing`, `exhale`, `inhale`, `gasp`, `gasping`, `pant`, `wheeze`, `huff`, `moan`, `groan`, `sob`, `sobbing`, `whimper`, `wail`, `sputter`, `sputtering`, `choked`, `choking`, `strangled`, `bark`, `barking`, `growl`, `growling`, `snarl`, `hiss`, `hissing`, `purr`, `howl`, `bleat`, `stammer`, `stutter`, `westchn`, `wzdych`, `łapiąc oddech`, `dyszą`, `jęk`, `szloch`, `charcz`, `szczeka`, `warkn`, `sycz`, plus a few Safe-listed false-positive guards (e.g. "wearily", "sharp" alone are fine).

## Result handling

- `PASS` (exit 0): report the summary (lines checked, tagged lines, untouched lines) to the user.
- `FAIL` (exit 1): the checker prints each offending line with the reason. Fix the tagged file (restore the missing line / correct the text / fix the tag), then re-run until `PASS`. Never deliver a tagged file that has not passed.

If the original and tagged files are so different that automatic repair is unclear, re-tag from the original file rather than patching.

## Reference: known allowed vs forbidden changes

Allowed (tagged vs original):
```
Heinkel: [Oi…]                                   →  Heinkel: [<<Snapping irritably, low and gravelly>> Oi…]
Heinkel: [――Heinkel Astrea-dono, there is…]      →  Heinkel: [<<tag>> Heinkel Astrea-dono, there is…]
Heinkel: [Wha――]                                 →  Heinkel: [<<tag>> Wha…]
???: [Ah! I've been waiting for you…]            →  Filóre: [<<tag>> Ah! I've been waiting for you…]   ← ??? resolved with certainty
Heinkel: [――――]                                  →  (line absent)           ← unreadable, DELETED, PASS
――――.                                            →  (line absent)           ← unreadable, DELETED, PASS
```

Forbidden:
```
Heinkel: [Heinkel Astrea-dono, there is…]        →  (line missing)           ← readable line deleted, FAIL
Heinkel: [――――]                                  →  Heinkel: [<<A strangled exhale>>]   ← tag-only, FAIL
Heinkel: [<<tag>> Louanna]                       →  Heinkel: [<<tag>> Louise]  ← text altered, FAIL
Knight: [Unfortunately, we lack…]                →  Guard: [<<tag>> Unfortunately…]  ← known speaker renamed, FAIL
```

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step tag-coverage-check --file "<artifact>" \
    --duration <seconds> --resources "tools/check_coverage.py + tools/tag_qa.py" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
