# Konwencje — NOVEL EDITOR

Ten dokument jest źródłem prawdy dla nazewnictwa plików i formatów. Skille i
`AGENTS.md` odwołują się tutaj.

## 1. Układ katalogów

```
NOVEL EDITOR/
├── AGENTS.md                     # kontrakt dla agenta (czytaj najpierw)
├── docs/                         # ta dokumentacja
│   ├── PIPELINE.md               # workflow krok po kroku + komendy
│   ├── SKILLS.md                 # co generuje który skill (z przykładami)
│   ├── CONVENTIONS.md            # (ten plik)
│   ├── VOICES.md                 # casting głosów / characters.yaml
│   ├── STATS.md                  # log serii (series/<slug>/stats.md)
│   ├── characters.template.yaml  # szablon manifestu obsady
│   └── assets/                   # diagramy (SVG) używane w README
├── tools/                        # wspólne skrypty (nie duplikować!)
│   ├── pdf_to_txt.py             # ln-pdf-to-txt (PDF → chapter-format TXT)
│   ├── epub_to_txt.py            # EPUB → chapter-format TXT (zachowuje imiona mówców)
│   ├── plain_text.py             # ln-plain-copy / ln-pdf-to-plain-redacted
│   ├── plain_sentences.py        # ln-to-plain-txt-only (zdanie = linia, bez ???, kwestie w cudzysłowach)
│   ├── resolve_names.py          # ln-speaker-resolution
│   ├── resolve_speakers_llm.py   # ln-speaker-resolution (last-resort, domyślnie NIE używać)
│   ├── emotion_tagger.py         # ln-emotion-tagging (lokalny LLM → <<tagi>>)
│   ├── check_coverage.py         # ln-tag-coverage-check
│   ├── tag_qa.py                 # QA reguł tagowania (po check_coverage.py)
│   ├── polonize_scan.py          # ln-name-polonization
│   ├── polonize_apply.py         # ln-name-polonization
│   ├── glossary_build.py         # ln-generate-glossary (glossary.md EN→PL + check)
│   ├── voice_casting.py          # ln-voice-casting
│   ├── fix_errors.py             # ln-translation-error-check
│   ├── log_stats.py              # dopisuje wiersz do series/<slug>/stats.md
│   └── legacy/                   # skrypty jednorazowe / wycofane
├── series/                       # DANE per seria (początkowo pusty)
│   └── <slug>/
│       ├── characters.yaml       # obsada: etykiety, aliasy, register — JEDEN na serię, po angielsku (ln-voice-casting)
│       ├── polonize.yaml         # mapa EN→PL (ln-name-polonization)
│       ├── stats.md              # jeden log serii (wszystkie tomy)
│       ├── voices/<Postać>/      # (opcjonalnie) próbki głosu — głosy przypisujesz ręcznie
│       ├── tools/                # (opcjonalnie) skrypty specyficzne dla serii
│       └── VOLxx/                # JEDEN KATALOG NA TOM — patrz §1a
├── .pi/
│   ├── skills/                   # skille (nazwy `ln-*`)
│   └── prompts/                  # prompty `/...`
└── translator/                   # SILNIK tłumaczenia — NIE ruszać bez potrzeby
    ├── README.md                 # opis komponentów (indeks)
    ├── ln-translator/            # translator.py, gui.py, prompt.yaml, CLI → github.com/kmk00/ln-translator (main)
    ├── transcript/               # Whisper: audio/wideo → txt/srt/vtt (README.md + komendy.txt) → github.com/kmk00/transcript (master)
    └── workspace/                # robocze katalogi tłumaczeń (config/context/glossary/chapters/output)
```

**Trzy repozytoria zdalne (konto [kmk00](https://github.com/kmk00)):**

| Repo | Rola | Branch | W root repo? |
|---|---|---|---|
| [`translator/ln-translator/`](https://github.com/kmk00/ln-translator) | silnik EN→PL | `main` | ❌ (osobne repo, `.gitignore`) |
| [`translator/transcript/`](https://github.com/kmk00/transcript) | Whisper (audio → tekst) | `master` | ❌ (osobne repo, `.gitignore`) |
| [Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1) | **zewnętrzna** aplikacja TTS (podział na role, OmniVoice) — konsument naszych artefaktów | `master` | ❌ (nie klonowany tutaj) |

Root repo wersjonuje wyłącznie `translator/README.md`; reszta `translator/` jest
wykluczona (`translator/workspace/` = dane + klucze API). Szczegóły ekosystemu:
[`translator/README.md`](../translator/README.md) §„Ekosystem”.

> Podział odpowiedzialności: to repo produkuje **tekst gotowy pod TTS** (`<stem>-resolved-tagged.txt`,
> `<stem>-resolved-tagged-plnames.txt`), a Audiobook-maker robi z niego **audio**.
> Dlatego repo nie trzyma sampli ani plików audio — patrz [`VOICES.md`](VOICES.md).

`series/<slug>` — slug to krótka, stabilna nazwa serii, np. `moja-seria`, `rezero-arc10`.
Katalog `series/` startuje pusty; zakładasz `<slug>/` przy pierwszej książce.

### 1a. Jeden katalog na tom (`VOLxx/`) — OBOWIĄZKOWE

Każdy tom (albo osobna książka/side-story w obrębie serii) ma **własny katalog**
nazwany `VOLxx` (dwie cyfry, zero-padding), a dla pozycji nienumerowanych —
krótkim slugiem tytułu (np. `Sword-Demon-Ballad/`). W katalogu tomu leży źródło
i **wszystkie** artefakty tego tomu:

```
series/<slug>/
├── characters.yaml          # WSPÓLNE dla serii (nie per tom!)
├── polonize.yaml            # WSPÓLNE dla serii
├── glossary.md              # (opcjonalnie) wspólny glossary serii — seed dla tomów
├── stats.md                 # WSPÓLNY log serii
├── VOL01/
│   ├── <source>.pdf|.epub   # źródło tomu
│   ├── <stem>.txt
│   ├── <stem>-resolved.txt
│   ├── <stem>-resolved-tagged.txt
│   ├── <stem>-resolved-tagged.cache.json
│   ├── <stem>-plain.txt
│   ├── glossary.md           # glossary tłumaczeniowy EN→PL (ln-generate-glossary)
│   └── <stem>-polonized.txt
├── VOL02/
│   └── …
└── chapters/                # wyjątek: serie rozdziałowe (np. rezero-arc10)
```

Zasady:
- **Nie rozrzucaj plików tomów w katalogu serii.** Wszystko, co należy do tomu
  (źródło + pochodne), trzymaj w jego `VOLxx/`.
- **Pliki wspólne zostają na poziomie serii**: `characters.yaml`, `polonize.yaml`,
  `stats.md` (opcjonalnie też `glossary.md`, `voices/`, `tools/`) — nigdy nie
  duplikuj ich w tomach.
- Nazwa katalogu: `VOL01`…`VOL99`. Zero-padding dwucyfrowy.
- Serie bez numeracji tomów (prequele, side-story) → katalog per książka,
  slug tytułu (np. `Apocalypse-Girls/`, `Sword-Demon-Ballad/`).
- Domyślnie **źródło leży w katalogu tomu**. Wyjątek: duże serie trzymające
  wszystkie oryginały razem mogą użyć `series/<slug>/source/`, ale wtedy
  artefakty i tak lądują w `VOLxx/`.
- Katalog `chapters/` jest dozwolony dla serii rozdziałowej (jeden plik na
  rozdział, bez numeracji tomów).

## 2. Nazewnictwo plików rozdziału/tomu

Dla tomu `VOL03` lub rozdziału `ch25` używaj **jednego** schematu:

| Przyrostek | Znaczenie | Skill |
|---|---|---|
| `<stem>.txt` | wejściowy tekst z anonimowymi mówcami `???: [...]` | `ln-pdf-to-txt` |
| `<stem>-resolved.txt` | mówcy rozwiązani (`???` → `Imię`) | `ln-speaker-resolution` |
| `<stem>-tagged.txt` | tagi emocji `<<...>>` w dialogach | `ln-emotion-tagging` |
| `<stem>-resolved-tagged.txt` | jak wyżej, gdy plik wejściowy to `<stem>-resolved.txt` (wariant `ln-generate-full`) | `ln-generate-full` |
| `<stem>-plain.txt` | czysty tekst do czytania (bez labeli/nawiasów/tagów) | `ln-plain-copy` |
| `glossary.md` | glossary tłumaczeniowy EN→PL dla tomu (tabela + blok YAML do `prompt.yaml` → `glossary:`) | `ln-generate-glossary` |
| `<stem>-pl.txt` | tłumaczenie polskie | `translator/ln-translator` |

Zasada: **nowe pliki trzymają się schematu** i leżą w katalogu tomu (`VOLxx/`).
Pliki z dawnych serii zachowują oryginalne nazwy — nie zmieniaj ich hurtowo,
tylko przy okazji edycji. `<stem>` to nazwa pliku źródłowego (albo krótki stem,
np. `vol02`, gdy źródło też jest w tym katalogu).

One-shot `ln-generate-full` używa nazw pochodnych od wyniku rozwiązywania mówców:
`<stem>.txt` → `<stem>-resolved.txt` → `<stem>-resolved-tagged.txt` →
`<stem>-plain.txt` (+ `characters.yaml` w katalogu serii).

## 3. Kanoniczny format tekstu rozdziału

```
NARRACYJNY AKAPIT — jedna linia, bez tagów, bez labeli.

Imię: [<<Dyrektywa wykonania>> Treść kwestii…]

???: [Kwestia nierozwiązanego mówcy.]

<Linia systemowa / transmisja>

ROZDZIAŁ PIERWSZY.
```

Reguły:
- **Dialog** = `Etykieta: [treść]`. Etykieta to mówca albo `???`.
- **Narracja** = linia bez `Etykieta: [...]`. Nigdy nie dostaje tagów emocji.
- **Tag emocji** = `<<...>>` wstawiony **zaraz po `[`**, potem spacja. To
  **jedyny kanoniczny format tagowania** (patrz niżej).
- **Nagłówki** (ROZDZIAŁ/PROLOG/EPILOG/INTERLUDIUM) — osobna linia, kończą się kropką.
- **Linie systemowe** `<...>` — zostają; w plikach do TTS zamień `<<`/`>>` na `()`.
- Między blokami dokładnie jedna pusta linia.

### Kanoniczny format tagów emocji

```
Shin: [<<Say it level and cold, with quiet command>> Undertaker to all units.]
```

- Tylko inline `<<...>>` (jeden tag na linię, po `[`).
- Zakaz słów-efektów dźwiękowych (oddech, westchnienie, warknięcie, jęk…).
- Maks. jeden przecinek w tagu, maks. jedna cecha tekstury.
- **Legacy (wycofane):** per-liniowe JSON-y `tagsNN.json` + `apply_tags.py`.
  Nie zaczynaj tak nowej pracy; przy okazji edycji zmigruj do inline `<<...>>`.

## 4. Ścieżki w skillach

Skille **nie trzymają już własnych skryptów** — wszystkie leżą w `tools/`.
W `SKILL.md` komendy mają postać:

```bash
python3 tools/<skrypt>.py ...
```

Ścieżki rozwiązuj względem katalogu roboczego (root repo).

## 5. Zasady TTS-safety (obowiązują wszędzie)

- **Pliki do syntezy (plain / `-plain.txt`) nie mogą zawierać ŻADNYCH nawiasów
  kątowych** — ani `<<...>>`, ani `<...>`. Zamieniaj je na `(...)`. Jedyne
  dozwolone `<<...>>` to tagi emocji/voice-design w plikach kanonicznych/tagged,
  które pipeline i tak usuwa. Surowy `<`/`>` psuje generowanie dźwięku.
- Każde zdanie kończy się znakiem terminalnym (`.`, `?`, `!`, `…`).
- Żadna czytelna linia nie może zniknąć — bramką jest `ln-tag-coverage-check`.
