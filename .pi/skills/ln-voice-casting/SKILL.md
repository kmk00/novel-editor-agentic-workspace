---
name: ln-voice-casting
description: Defines and verifies the per-series character cast manifest `series/<slug>/characters.yaml` — canonical speaker labels, aliases (given names, nicknames, callsigns), `polonize` forms and `register` (vocal baseline) — and checks that every speaker appearing in a chapter has an entry. Voices themselves are assigned manually in an external TTS app, so the manifest carries no `voice`/`sample` fields. Use when the user asks to build/update characters.yaml, map a character's aliases, check which characters still need an entry, or "adapt the light novel to the characters we want".
---

# Light-Novel Cast Manifest

The bridge between the raw chapter text and the characters we want: it fixes **who is who**
in a series. **One shared manifest per series** — every book in `series/<slug>/` uses the
same file:

```
series/<slug>/characters.yaml
```

**Write the manifest in English** (registers, aliases, notes). The only exception is the
`polonize` field, which is the target Polish phonetic form by design. This applies to
every new `characters.yaml` generated for any book/series.

It maps each speaker label used in the text to a **canonical character** with its
**aliases** (given names, nicknames, callsigns, variants), an optional **polonize**
form (EN→PL phonetic spelling for Polish TTS) and a **register** (short English vocal
baseline).

Downstream:
- `ln-speaker-resolution` uses the aliases to recognise a speaker behind `???` / role labels.
- `ln-emotion-tagging` uses `register` as context when writing performance tags.
- `ln-name-polonization` uses the `polonize` fields to seed `series/<slug>/polonize.yaml`.

**Voices are assigned manually in an external TTS app** — the manifest deliberately has
no `voice`/`sample` fields.

## Manifest schema

```yaml
series: <slug>

narrator:                       # the narration voice (not a `Name: [...]` speaker)
  register: "calm, literary, medium pace"

characters:
  Shin:
    polonize: Szin              # EN -> PL phonetic form (optional)
    aliases: [Undertaker, Reaper, Shinei]   # callsigns / nicknames / variants
    register: "cold, composed, clipped sentences"
```

Rules:
- **One shared file per series** (`series/<slug>/characters.yaml`), never one per volume.
- **The manifest is written in English** (registers, aliases, notes); only `polonize`
  holds Polish forms.
- Keys under `characters:` are the **canonical speaker labels exactly as they appear**
  in the chapter text (`Shin:`, `Yanami:`, …). Spelling must match the text.
- `aliases` lists every other label/nickname that refers to the same character
  (given name, full name, honorific forms, callsigns).
- `polonize` is the form the TTS should pronounce; keep it consistent with
  `series/<slug>/polonize.yaml`.
- `register` is a short **English** description of the character's vocal baseline
  (used as context when writing emotion tags) — not a role summary.
- No `voice` / `sample` fields.

## Procedure

### 1. Find the series manifest
Resolve the series directory from the chapter path: `series/<slug>/VOLxx/<chapter>.txt`
→ series dir is `series/<slug>/` (the parent of `VOLxx/`). See `docs/CONVENTIONS.md` §1a.
There is exactly **one shared `characters.yaml` per series** — do not create one per
volume. If it does not exist, create it from `docs/characters.template.yaml` and write
it in English.

### 2. Scan the chapter for speakers

```bash
python3 tools/voice_casting.py series/<slug>/VOLxx/<chapter>.txt [series/<slug>/characters.yaml]
```

- Lists every distinct speaker with its dialogue-line count.
- Splits them into **CAST**, **UNRESOLVED (`???`)** and **MISSING FROM CAST**.
- Exits `1` when a named speaker has no manifest entry (use `--allow-missing` to only warn).

### 3. Fill the gaps
For every **MISSING** speaker, add an entry with `polonize`, `aliases` and `register`.
If identity is unclear, still add the label with a best-effort `register` and note it in
the summary — do not merge two distinct labels into one entry by guesswork.

### 4. Re-run until `PASS`
Re-run the checker after every edit. `PASS` means every named speaker in the chapter
has an entry. `???` lines are fine — they are resolved later by `ln-speaker-resolution`
(only at 100% certainty) and re-checked here.

### 5. Hand off
- Feed `polonize` fields to `ln-name-polonization` (build/refresh `series/<slug>/polonize.yaml`).
- Feed `register` to `ln-emotion-tagging` (tags must fit the character).
- The external TTS app is keyed by the manifest's character names — keep keys stable.

## Output

Print a markdown summary table:

| Speaker | Lines | Polonize | Aliases | Register | Status |
|---|---|---|---|---|---|
| Shin | 42 | Szin | Undertaker, Reaper, Shinei | cold, composed | cast |
| Lena | 30 | Lena | Vladilena, Handler One | composed, warm | cast |
| ??? | 5 | — | — | — | unresolved |

Plus: manifest path, total distinct speakers, cast / unresolved / missing counts,
and the checker's exit result (`PASS` / `FAIL`).

## Quality checklist

- **One shared `characters.yaml` per series** (not per volume).
- **Manifest written in English** (only `polonize` holds Polish forms).
- Every named speaker in the chapter has a `characters.yaml` entry (or is explicitly `TBD`).
- Canonical key spelling matches the chapter's speaker labels exactly.
- All aliases/nicknames of a character point to the same entry.
- `polonize` forms are consistent with `series/<slug>/polonize.yaml`.
- No `voice`/`sample` fields (voices are assigned externally).
- `tools/voice_casting.py` exits `PASS` (or `--allow-missing` used deliberately).
- Summary table printed; unresolved `???` listed, not guessed.

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step voice-casting --file "<artifact>" \
    --duration <seconds> --resources "tools/voice_casting.py" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
