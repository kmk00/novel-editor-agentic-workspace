# Skille — co generuje który (z przykładami)

Źródło prawdy: który skill bierze **jaki plik**, robi **co** i zostawia **jaki
artefakt**. Format i nazewnictwo: `docs/CONVENTIONS.md`. Workflow krok po kroku:
`docs/PIPELINE.md`. Kontrakt agenta: `AGENTS.md`.

Wszystkie skrypty uruchamiane z katalogu głównego repo: `python3 tools/<skrypt>.py`.
Każdy tom leży w swoim katalogu `series/<slug>/VOLxx/` (patrz `CONVENTIONS.md` §1a).

---

## 0. Tabela zbiorcza

| Skill | Wejście | Wyjście (artefakt) | Bramka |
|---|---|---|---|
| `ln-generate-full` | `BOOK.pdf` / `BOOK.epub` | **cały zestaw** (patrz §10) | wszystkie bramki |
| `ln-pdf-to-txt` | `BOOK.pdf` | `<stem>.txt` (mówcy `???`) | — (ręczny review) |
| `ln-pdf-to-plain-redacted` | `BOOK.pdf` | `<stem>.txt` + `<stem>-plain.txt` | — (ręczny review) |
| `ln-to-plain-txt-only` | `BOOK.pdf` / `BOOK.epub` | `<stem>-plain.txt` (tylko plain, zdanie=linia, kwestie w cudzysłowach) | `plain_sentences.py --check` |
| `ln-speaker-resolution` | `<stem>.txt` | `<stem>-resolved.txt` | `resolve_names.py --check` |
| `ln-voice-casting` | `<stem>-resolved.txt` | `series/<slug>/characters.yaml` (update) | `voice_casting.py` |
| `ln-emotion-tagging` | `<stem>-resolved.txt` | `<stem>-resolved-tagged.txt` (+ `.cache.json`) | `tag_qa.py` |
| `ln-tag-coverage-check` | `<stem>-resolved.txt` + `-tagged.txt` | *(brak — bramka)* | `check_coverage.py` |
| `ln-plain-copy` | `<stem>-tagged.txt` / `-resolved.txt` | `<stem>-plain.txt` | — (ręczny spot-check) |
| `ln-name-polonization` | `<stem>-tagged.txt` | `series/<slug>/polonize.yaml` + `<stem>-plnames.txt` | grep 0 resztek EN |
| `ln-generate-glossary` | `<stem>-plain.txt` / `<stem>.txt` | `series/<slug>/VOLxx/glossary.md` (EN→PL + blok YAML) | `glossary_build.py check` |
| `ln-translation-error-check` | PL `<output>.txt` + `chunks/` | naprawiony `<output>.txt` + `<stem>_FIX_raport.md` | `fix_errors.py verify` → `OK` |

Uwaga: **EPUB** nie ma osobnego skilla — ekstrakcję robi `tools/epub_to_txt.py`
w ramach `ln-generate-full` / `ln-to-plain-txt-only`.

---

## 1. Ten sam fragment przez cały łańcuch

Fragment prologu (Makeine, tom 2) pokazuje, jak zmienia się tekst na każdym etapie.

**① Kanoniczny po ekstrakcji — `ln-pdf-to-txt` → `<stem>.txt`** (wszyscy mówcy `???`):
```
As the sound of cicadas poured over my back, I arrived home, only to be greeted by a clear voice ringing out in the entryway.

???: [Welcome home, onii-sama!]

Running toward me is my little sister, who is two years younger, Kaju Nukumizu.

???: [What's the matter? Why are you so flustered?]
```

**② Po rozwiązaniu mówców — `ln-speaker-resolution` → `<stem>-resolved.txt`**:
```
Kaju: [Welcome home, onii-sama!]

Running toward me is my little sister, who is two years younger, Kaju Nukumizu.

Nukumizu: [What's the matter? Why are you so flustered?]
```

**③ Po tagowaniu emocji — `ln-emotion-tagging` → `<stem>-resolved-tagged.txt`**:
```
Kaju: [<<Exclaiming brightly and loudly, with a high-pitched and cheerful tone>> Welcome home, onii-sama!]

Running toward me is my little sister, who is two years younger, Kaju Nukumizu.

Nukumizu: [<<Asking with a flat and even tone, maintaining a detached curiosity>> What's the matter? Why are you so flustered?]
```

**④ Kopia do czytania — `ln-plain-copy` → `<stem>-plain.txt`** (akapit = linia):
```
Welcome home, onii-sama!

Running toward me is my little sister, who is two years younger, Kaju Nukumizu.

What's the matter? Why are you so flustered?
```

**⑤ Wariant „zdanie = linia” — `ln-to-plain-txt-only` → `<stem>-plain.txt`**:
```
Welcome home, onii-sama!

Running toward me is my little sister, who is two years younger, Kaju Nukumizu.

What's the matter?
Why are you so flustered?
```

---

## 2. `ln-pdf-to-txt` — PDF → kanoniczny TXT

- **Wejście:** `BOOK.pdf`
- **Wyjście:** `<stem>.txt` — kanoniczny format, **wszyscy mówcy anonimizowani do `???: [...]`**
- **Robię:** `tools/pdf_to_txt.py` + obowiązkowy ręczny review (usuwanie front/back
  matter, artefaktów reflow, normalizacja nagłówków `CHAPTER X. NAME.`, znaki końcowe zdań).
- **Bramka:** brak automatycznej — to plik wejściowy, nie wynik.

Przykład:
```
The girl slammed her hands on the table and leaned forward.

???: [There's no way I'm accepting that!]

Kazuhiko Nukumizu, Class 1-C, watched her silently.
```
> `???` jest **celowe** — rozwiązanie mówców to osobny, późniejszy krok.

---

## 3. `ln-pdf-to-plain-redacted` — PDF → plain (akapit = linia)

- **Wejście:** `BOOK.pdf`
- **Wyjście:** `<stem>.txt` (pośredni) + `<stem>-plain.txt` (finalny)
- **Robię:** PDF → kanoniczny → `tools/plain_text.py` → dodatkowy pass (kropki w
  nagłówkach, usuwanie linii bez liter/cyfr). **Zachowuje akapity** (nie dzieli zdań).
- **Uwaga:** to skill **tylko dla PDF**. Dla EPUB i wariantu „zdanie = linia” użyj
  `ln-to-plain-txt-only`.

Przykład (`-plain.txt`):
```
PROLOGUE.

I was on the way home from the Seibunkan Bookstore near the station.

Welcome home, onii-sama!
```

---

## 4. `ln-to-plain-txt-only` — PDF/EPUB → tylko plain, zdanie = linia

- **Wejście:** `BOOK.pdf` **albo** `BOOK.epub`
- **Wyjście:** `<stem>-plain.txt` (oraz pośredni `<stem>.txt`)
- **Robię:** `tools/pdf_to_txt.py` **lub** `tools/epub_to_txt.py` → ręczny cleanup →
  `tools/plain_sentences.py`. Pomija resolution/casting/tagging.
- **Cechy wyniku:** 0 labeli, 0 `???`, 0 `[ ]`, 0 `<<...>>`, **0 `<...>`** (zamienione
  na `()`), **każde zdanie i kwestia w osobnej linii**, **każda kwestia mówiona
  w cudzysłowach `“...”`** (domyślnie; `--no-quotes` wyłącza), każda linia z
  interpunkcją.
- **Bramka:** `python3 tools/plain_sentences.py --check <plain>` → `PASS`.

Przykład (transformacja):

| Przed (`<stem>.txt`) | Po (`<stem>-plain.txt`) |
|---|---|
| `???: [Welcome home, onii-sama!]` | `“Welcome home, onii-sama!”` |
| `Narration with two sentences. Second one here.` | `Narration with two sentences.`<br>`Second one here.` |
| `<Komari: You're early. Just read a book.>` | `(Komari: You're early. Just read a book.)` |
| `the volume <Anyone Who Calls Me Flat-Chested…>` | `the volume (Anyone Who Calls Me Flat-Chested…)` |
| `<<Exclaiming brightly>> Hello!` | `Hello!` (tag usunięty) |

---

## 5. `ln-speaker-resolution` — `???` → imię

- **Wejście:** `<stem>.txt` (mówcy `???`)
- **Wyjście:** `<stem>-resolved.txt`
- **Robię:** **agent** czyta scenę i rozwiązuje mówcę **tylko przy 100% pewności**
  (dowód: narracja, self-introduction, zwrot po imieniu, jednoznaczna alternacja).
  Zmienia się **wyłącznie prefiks** `???:` → `Imię:`; treść `[...]` zostaje byte-identical.
- **Bramka:** `python3 tools/resolve_names.py --check <stem>.txt <stem>-resolved.txt` → `PASS`.

Przykład:
```
???: [Welcome home, onii-sama!]          →   Kaju: [Welcome home, onii-sama!]
???: [What's the matter? …]              →   Nukumizu: [What's the matter? …]
???: [Muttered a voice from the crowd.]  →   ???: [Muttered a voice from the crowd.]   (brak kotwicy — zostaje)
```

---

## 6. `ln-voice-casting` — manifest obsady

- **Wejście:** `<stem>-resolved.txt` + `series/<slug>/characters.yaml`
- **Wyjście:** zaktualizowany **`series/<slug>/characters.yaml`** (jeden na serię,
  nie na tom; po angielsku, tylko `polonize` po polsku).
- **Robię:** `tools/voice_casting.py` → lista `CAST` / `???` / `MISSING`; uzupełniam
  brakujące postacie (`polonize`, `aliases`, `register`).
- **Bramka:** `python3 tools/voice_casting.py <stem>-resolved.txt <characters.yaml>` → `PASS`.

Przykład wpisu:
```yaml
characters:
  Yanami:
    polonize: Janami
    aliases: [Anna, Anna Yanami, Yanami-san]
    register: "expressive, whiny, playfully offended"
```
Wynik skryptu:
```
Speakers: 17 distinct, 1731 dialogue lines
CAST: Nukumizu 570, Yanami 326, Yakishio 261, …
UNRESOLVED (`???`): 11 lines
PASS: every named speaker is cast.
```

---

## 7. `ln-emotion-tagging` — tagi `<<...>>` w dialogach

- **Wejście:** `<stem>-resolved.txt` (mówcy już nazwani)
- **Wyjście:** `<stem>-resolved-tagged.txt` + `<stem>-resolved-tagged.cache.json`
- **Robię:** `tools/emotion_tagger.py` — lokalny LLM (Ollama, domyślnie
  `huihui_ai/gemma-4-abliterated:26b`, `think:false`) wstawia **jeden** tag po `[`,
  w języku angielskim, jako reżyserię wykonania. Normalizuje stuttery (`A-are` →
  `Are` + `<<Stuttering>>`), ucina myślniki, dodaje `…`, usuwa linie nieczytelne.
- **Bramka:** `python3 tools/tag_qa.py <stem>-resolved-tagged.txt` → `PASS`.

Przykład:
```
Kaju: [Welcome home, onii-sama!]
   ↓
Kaju: [<<Exclaiming brightly and loudly, with a high-pitched and cheerful tone>> Welcome home, onii-sama!]

Nukumizu: [U-Uh…]
   ↓
Nukumizu: [<<Stuttering, soft and slow>> Uh…]
```

---

## 8. `ln-tag-coverage-check` — bramka pokrycia

- **Wejście:** `<stem>-resolved.txt` (lub `<stem>.txt`) + `<stem>-resolved-tagged.txt`
- **Wyjście:** brak pliku — tylko werdykt.
- **Robię:** `tools/check_coverage.py` sprawdza, że **żadna czytelna linia nie
  zniknęła**, kolejność się zgadza, a zmiany mieszczą się w dozwolonych (wstawienie
  tagu, zdjęcie myślników, dodanie `…`, usunięcie linii nieczytelnych).
- **Bramka:** `python3 tools/check_coverage.py <orig> <tagged>` → `PASS`.

```
Coverage check: …-resolved-tagged.txt
  lines total:         7123 readable
  unreadable removed:  1 (dash-only/symbol-only, absent from output)
  tagged lines:        1731
PASS — every readable line of the original is present, none deleted.
```

---

## 9. `ln-plain-copy` — wersja do czytania

- **Wejście:** `<stem>-tagged.txt` / `<stem>-resolved.txt` (dowolny kanoniczny)
- **Wyjście:** `<stem>-plain.txt` (akapit = linia)
- **Robię:** `tools/plain_text.py` usuwa label `Name:`/`???`, nawiasy `[ ]`, tagi
  `<<...>>`, a **nawiasy kątowe `<...>` zamienia na `()`** (TTS-safety).
- **Bramka:** ręczny spot-check (`grep '[<>]'` → 0, brak labeli).

Przykład:
```
Nukumizu: [<<Speaking flatly and slowly>> What's the matter? Why are you so flustered?]
   ↓
What's the matter? Why are you so flustered?
```

---

## 10. `ln-generate-full` — one-shot dla jednej książki

- **Wejście:** `BOOK.pdf` **lub** `BOOK.epub`
- **Wyjście (w `series/<slug>/VOLxx/`):**

| Plik | Etap |
|---|---|
| `<stem>.txt` | ekstrakcja (PDF → `???`, EPUB → etykiety z epuba) |
| `<stem>-resolved.txt` | rozwiązanie mówców |
| `<stem>-resolved-tagged.txt` (+ `.cache.json`) | tagi emocji |
| `<stem>-plain.txt` | kopia do czytania |
| `series/<slug>/characters.yaml` | obsada (jeden na serię) |
| *(opcjonalnie)* `<stem>-polonized.txt` | polonizacja imion |

- **Bramki w łańcuchu:** `resolve_names --check`, `voice_casting`, `check_coverage`,
  `tag_qa` — wszystkie muszą dać `PASS`; plus finalna tabela podsumowania.

---

## 11. `ln-name-polonization` — EN → PL fonetycznie

- **Wejście:** `<stem>-tagged.txt` (lub PL po tłumaczeniu)
- **Wyjście:** `series/<slug>/polonize.yaml` (mapa, wspólna dla serii) +
  `<stem>-plnames.txt` (w `ln-generate-full`: `<stem>-polonized.txt`)
- **Robię:** `tools/polonize_scan.py` → budowa mapy → `tools/polonize_apply.py`
  (zamiana całowyrazowa, z zachowaniem wielkości liter) → ręczny **pass deklinacji**.
- **Bramka:** `grep -c -w "<EN name>" <output>` → 0 na wpis.

Przykład mapy (`series/<slug>/polonize.yaml`):
```yaml
"Shin": "Szin"
"Lena": "Lena"
"Raiden": "Rajden"
```
```
Shin: [I'm going.]   →   Szin: [Idę.]
```

---

## 12. `ln-generate-glossary` — glossary tłumaczeniowy EN→PL

- **Wejście:** `<stem>-plain.txt` (po `ln-to-plain-txt-only`) lub dowolny tekst tomu
- **Wyjście:** `series/<slug>/VOLxx/glossary.md` — tabela kandydatów
  (`EN | PL | Typ | Wyst. | Uwagi`) + gotowy blok `glossary:` do wklejenia do
  `translator/ln-translator/prompt.yaml`
- **Seed (spójność serii):** `series/<slug>/characters.yaml` (pola `polonize`),
  `series/<slug>/polonize.yaml`, wcześniejszy `glossary.md`
- **Robię:** `tools/glossary_build.py scan` → ręczny przegląd (PL + `Typ`, usunięcie
  śmieci, dodanie honoryfikacji/epitetów) → `tools/glossary_build.py check`
- **Bramka:** `python3 tools/glossary_build.py check <glossary.md>` → `PASS`
  (brak pustych wartości i duplikatów kluczy)

```bash
python3 tools/glossary_build.py scan "series/<slug>/VOLxx/<stem>-plain.txt" \
    --slug "<slug>" --volume VOLxx --min-count 2 \
    --characters "series/<slug>/characters.yaml" \
    --polonize   "series/<slug>/polonize.yaml"
python3 tools/glossary_build.py check "series/<slug>/VOLxx/glossary.md"   # PASS
```

Gotowy blok (kopiujesz wybrane pozycje do `prompt.yaml` → `glossary:`):
```yaml
glossary:
  "Rias Gremory": "Rias Gremory"
  "Sacred Gear": "Święty Element"
  "Fallen Angel": "Upadły Anioł"
```

---

## 13. `ln-translation-error-check` — naprawa chunków tłumaczenia

- **Wejście:** wyjściowy PL `<output>.txt` translatora + jego `<output>_chunks/`
  (`chunk_NNN.txt`, `original/chunk_NNN.txt`, `session.json`)
- **Wyjście:** naprawiony `<output>.txt` + raport `<stem>_FIX_raport.md`
- **Robię:** `tools/fix_errors.py detect` → agent odtwarza wierne PL z `original/` →
  `verify` → `stitch` (zszycie liniowo, wyrównane do EN).
- **Bramka:** `python3 tools/fix_errors.py verify <output>` → `OK` (brak markerów,
  zgodność liczby linii EN↔PL).

Przykład markera i naprawy:
```
[BŁĄD TŁUMACZENIA — CHUNK 4]           →   (usunięty; chunk zastąpiony pełnym, wiernym PL)
```

---

## 14. Bramki — pełna tabela

| Bramka | Komenda | Warunek | Kto używa |
|---|---|---|---|
| Pokrycie linii | `tools/check_coverage.py <orig> <tagged>` | `PASS` | `ln-tag-coverage-check`, `ln-generate-full` |
| Reguły tagowania | `tools/tag_qa.py <tagged>` | `PASS` | `ln-emotion-tagging`, `ln-generate-full` |
| Rozwiązanie mówców | `tools/resolve_names.py --check <orig> <resolved>` | `PASS` | `ln-speaker-resolution`, `ln-generate-full` |
| Kompletność obsady | `tools/voice_casting.py <rozdział> [characters.yaml]` | `PASS` | `ln-voice-casting`, `ln-generate-full` |
| Plain (bez `<>`/`???`) | `tools/plain_sentences.py --check <plain>` | `PASS` | `ln-to-plain-txt-only` |
| Glossary (EN→PL) | `tools/glossary_build.py check <glossary.md>` | `PASS` | `ln-generate-glossary` |
| Chunks tłumaczenia | `tools/fix_errors.py verify <output>` | `OK` | `ln-translation-error-check` |

Nigdy nie prezentuj wyniku bez `PASS`/`OK` na wszystkich istotnych bramkach.
