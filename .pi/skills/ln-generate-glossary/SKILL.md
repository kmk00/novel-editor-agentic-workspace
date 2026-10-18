---
name: ln-generate-glossary
description: Builds a per-book translation glossary (`glossary.md`) from an extracted plain text, so English→Polish light-novel translation can be pinned with a consistent EN→PL term list. Scans proper nouns / coined terms / multi-word phrases with occurrence counts, seeds already-decided renderings from `characters.yaml` and `polonize.yaml`, and emits a ready-to-paste `glossary:` YAML block for `translator/ln-translator/prompt.yaml`. Use after `ln-to-plain-txt-only` / `ln-pdf-to-txt` when the user asks for a glossary, term list, translation glossary, or "glossary.md" for a series/volume.
---

# Generate Glossary (EN → PL translation term list)

Produces `glossary.md` **in the volume folder** (next to the book / plain text):

```
series/<slug>/VOLxx/glossary.md
```

It is a human-reviewable superset of translation decisions — from it you copy the
entries you want into `translator/ln-translator/prompt.yaml` → `glossary:`.

The glossary holds **translation** renderings (EN term → Polish wording), not only
phonetic spellings: characters (`Rias Gremory` → `Rias Gremory`), places
(`Kuou Academy` → `Akademia Kuou`), concepts (`Sacred Gear` → `Święty Element`),
items/techniques (`Boosted Gear` → `Wzmocniony Element`), honorifics, and recurring
phrases. For pure TTS pronunciation of names use `ln-name-polonization`
(`series/<slug>/polonize.yaml`) — the glossary should stay consistent with it.

## When to run

After the English plain text exists (usually `<stem>-plain.txt` from
`ln-to-plain-txt-only`, or `<stem>.txt` from `ln-pdf-to-txt`), **before** the
translation run (`translator/ln-translator`). One glossary per volume folder.

## Paths

- Tool: `tools/glossary_build.py` (dependency-free; no PyYAML needed).
- Input: `series/<slug>/VOLxx/<stem>-plain.txt` (or `<stem>.txt`).
- Output: `series/<slug>/VOLxx/glossary.md`.
- Seeds (optional, shared per series): `series/<slug>/characters.yaml`,
  `series/<slug>/polonize.yaml`, a previous `series/<slug>/glossary.md`.
- Consumer: `translator/ln-translator/prompt.yaml` → `glossary:`.

## Procedure

### 1. Scan candidates

```bash
python3 tools/glossary_build.py scan \
    "series/<slug>/VOLxx/<stem>-plain.txt" \
    --slug "<slug>" --volume VOLxx --min-count 2 \
    --characters "series/<slug>/characters.yaml" \
    --polonize   "series/<slug>/polonize.yaml" \
    --glossary   "series/<slug>/glossary.md"        # only if it exists
```

The tool drops sentence-initial words / contractions / interjections, counts
single proper nouns and 2–4-word capitalised phrases, and writes `glossary.md`
with a candidate table (`EN | PL | Typ | Wyst. | Uwagi`) and an empty YAML block.
Already-decided forms from `characters.yaml` / `polonize.yaml` / a previous
glossary are pre-filled in the **PL** column and in the YAML block.

### 2. Agent review — fill PL, classify, curate (MANDATORY)

Read the top ~80 candidates and the whole `characters.yaml` for context, then edit
`glossary.md`:

1. **Fill the PL column** for every entry worth pinning. Leave blank or delete
   rows you don't want (noise, one-off phrases, common words).
2. **Set the Typ** column: `postać` / `miejsce` / `organizacja` / `termin` /
   `przedmiot` / `honoryfikacja` / `fraza`.
3. **Remove noise**: split phrases that are not real terms (e.g. `Asia I`), rows
   for words that are just capitalised sentence starts, duplicated variants you
   fold into one canonical entry.
4. **Add anything the scan missed**: honorifics (`-sama`, `-san`, `-kun`,
   `onii-sama`, `senpai`…), multi-word titles/epithets, onomatopoeia decisions,
   units/currency, previously hidden recurring names.
5. **Stay consistent with the series**: reuse forms from `characters.yaml`
   (`polonize`), `polonize.yaml`, and any existing series-level `glossary.md`.
   Do not invent a new spelling for an already-decided name.
6. **Mirror** every decided entry into the `## Gotowe do wklejenia (YAML)` block
   (same EN/PL, one `"EN": "PL"` line each).

### Choosing the Polish form

Priority:

1. **Existing series decision** — `polonize.yaml` / `characters.yaml` / a previous
   `glossary.md`. This always wins.
2. **Conventional Polish exonym / official Polish translation** of the franchise,
   if known (Elizabeth → Elżbieta, John → Jan), as long as it sounds natural.
3. **Translated term** for concepts/places/titles — natural literary Polish, not a
   calque (`Fallen Angel` → `Upadły Anioł`, `Occult Research Club` →
   `Klub Badań Okultystycznych`).
4. **Phonetic polonization** for names that stay foreign-sounding — follow
   `ln-name-polonization` rules (`Beatris`, `Andertejker`; German-origin: `eu→oj`,
   `ei→aj`, `z→c`). If a name is deliberately kept in English, PL = the English
   form (e.g. `Rias` → `Rias`).

In the **Uwagi** column note pronunciation, gender (for declension), or why a form
was chosen. Add the declined stem if it matters for Polish case forms.

### 3. Verify (MANDATORY gate)

```bash
python3 tools/glossary_build.py check "series/<slug>/VOLxx/glossary.md"   # MUST be PASS
```

`check` fails on: missing/non-parsing `glossary:` YAML block, empty key, entry
with no PL form, or duplicate key. Fix and re-run until `PASS`.

### 4. Use it

Copy the lines inside the `glossary:` block into the `glossary:` section of
`translator/ln-translator/prompt.yaml` and run the translation as usual:

```bash
cd translator/ln-translator
uv run translator translate <plik_EN.txt> -o output/<nazwa>_pl.txt
```

Keep `glossary.md` in the volume folder as the reviewable record; the YAML block
is the copy-paste source.

### 5. Log stats

```bash
python3 tools/log_stats.py <slug> --step generate-glossary \
    --file "series/<slug>/VOLxx/glossary.md" \
    --duration <seconds> --resources "tools/glossary_build.py + agent" \
    --result PASS --notes "<candidates / decided entries / YAML entries / seeds used>"
```

## Output

Print the summary **always as a markdown table**:

| Etap | Wynik |
|---|---|
| źródło / typ | `<stem>-plain.txt` (… znaków) |
| `glossary.md` | kandydaci / wpisy z PL / sekcje Typ |
| blok YAML | liczba wpisów `"EN": "PL"` |
| seed | `characters.yaml` / `polonize.yaml` / wcześniejszy `glossary.md` (ile form przejęto) |
| bramka `glossary_build.py check` | `PASS` |
| `stats.md` | wiersz `generate-glossary` |

Never present the result without a passing `check`.

## Quality checklist

- `glossary.md` lives in `series/<slug>/VOLxx/`.
- Every decided entry has both EN and a non-empty PL form; no duplicate keys.
- `Typ` filled for the entries you keep; noise rows removed.
- Forms consistent with `characters.yaml` / `polonize.yaml` / series glossary.
- YAML block matches the kept table rows exactly (copy-ready).
- `python3 tools/glossary_build.py check …` reported `PASS`.
- One `generate-glossary` entry appended to `series/<slug>/stats.md`.
- Summary table printed.
