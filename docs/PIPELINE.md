# Pipeline — od PDF/tekstu do audiobooka z wybranymi postaciami

> Który skill generuje jaki plik (z przykładami tekstu i wyników): `docs/SKILLS.md`.

Dwie równoległe ścieżki, które spotykają się na końcu:

```
A) OBRÓBKA (EN lub PL)                         B) TŁUMACZENIE EN→PL
   PDF ──ln-pdf-to-txt──▶ <stem>.txt              EN txt ──translator──▶ <stem>-pl.txt
        │                                              │
        ├─ln-speaker-resolution─▶ -resolved.txt        └─ln-translation-error-check (bramka)
        │        │
        │        └─ln-voice-casting  (characters.yaml: kanoniczne etykiety/aliasy/register)
        │                 │
        │                 └─ln-emotion-tagging─▶ -tagged.txt
        │                          │
        │                          └─ln-tag-coverage-check (bramka, PASS)
        │
        ├─ln-name-polonization─▶ polonize.yaml + *-plnames.txt
        └─ln-plain-copy─▶ -plain.txt (kopia do czytania)
```

## A. Obróbka rozdziału/tomu

Wszystkie komendy z katalogu głównego repo. `<slug>` to nazwa serii (np. `moja-seria`).
**Każdy tom ma własny katalog `series/<slug>/VOLxx/`** (źródło + artefakty); pliki
wspólne serii (`characters.yaml`, `polonize.yaml`, `stats.md`) zostają na poziomie
`series/<slug>/`. Szczegóły: `docs/CONVENTIONS.md` §1a.

### One-shot: cała książka (`ln-generate-full`)
```bash
/ln-generate-full "series/<slug>/VOLxx/<Book>.pdf"      # albo .epub
/ln-generate-full "series/<slug>/VOLxx/<Book>.epub" "series/<slug>/VOLxx"
```
Uruchamia cały łańcuch dla **jednej książki** (PDF lub EPUB) i pilnuje wszystkich
bramek: `<stem>.txt` → `<stem>-resolved.txt` → `characters.yaml` →
`<stem>-resolved-tagged.txt` → `<stem>-plain.txt`. Skill:
`.pi/skills/ln-generate-full/SKILL.md`. Kroki 1–7 poniżej to ten sam łańcuch
ręcznie, gdy trzeba wejść w środek.

### 1. PDF → tekst (`ln-pdf-to-txt`)
```bash
python3 tools/pdf_to_txt.py series/<slug>/VOLxx/BOOK.pdf series/<slug>/VOLxx/<stem>.txt
```
Następnie ręcznie (obowiązkowo, wg SKILL.md): usuń front/back matter, popraw
artefakty, nadaj nagłówkom kropki, upewnij się, że każde zdanie ma znak końcowy.

### 2. Rozwiązanie mówców (`ln-speaker-resolution`)
```bash
python3 tools/resolve_names.py --scan  series/<slug>/VOLxx/<stem>.txt
# ... popraw tylko przy 100% pewności ...
python3 tools/resolve_names.py --check series/<slug>/VOLxx/<stem>.txt \
                                        series/<slug>/VOLxx/<stem>-resolved.txt
```

### 3. Casting (`ln-voice-casting`)
```bash
python3 tools/voice_casting.py series/<slug>/VOLxx/<stem>-resolved.txt
# uzupełnij series/<slug>/characters.yaml, aż PASS
```

### 4. Tagowanie emocji (`ln-emotion-tagging`)
Robi agent wg `.pi/skills/ln-emotion-tagging/SKILL.md`; wynik:
`<stem>-tagged.txt` (inline `<<...>>`, kanoniczny format).

### 5. Bramka (`ln-tag-coverage-check`) — OBOWIĄZKOWA
```bash
python3 tools/check_coverage.py series/<slug>/VOLxx/<stem>-resolved.txt \
                                series/<slug>/VOLxx/<stem>-tagged.txt
# musi zwrócić PASS (exit 0)
```

### 6. Polonizacja imion (`ln-name-polonization`) — dla polskiego TTS
```bash
python3 tools/polonize_scan.py  series/<slug>/VOLxx/<stem>-tagged.txt > /tmp/candidates.txt
# zbuduj/uzupełnij series/<slug>/polonize.yaml
python3 tools/polonize_apply.py series/<slug>/VOLxx/<stem>-tagged.txt \
                                series/<slug>/polonize.yaml \
                                series/<slug>/VOLxx/<stem>-tagged-plnames.txt
# potem ręczny pass deklinacji (skill)
```

### 7. Kopia do czytania (`ln-plain-copy`)
```bash
python3 tools/plain_text.py series/<slug>/VOLxx/<stem>-tagged.txt \
                            series/<slug>/VOLxx/<stem>-plain.txt
```

### One-shot: PDF → plain (`ln-pdf-to-plain-redacted`)
```bash
/ln-pdf-to-plain  "series/<slug>/VOLxx/BOOK.pdf"
```
Prompt uruchamia cały łańcuch i drukuje tabelę podsumowania.

### One-shot: PDF/EPUB → tylko plain, zdanie w linii (`ln-to-plain-txt-only`)
```bash
/ln-to-plain-txt-only  "series/<slug>/VOLxx/BOOK.pdf"    # albo .epub
```
Prompt uruchamia cały łańcuch i drukuje tabelę podsumowania. Ręcznie:
```bash
python3 tools/pdf_to_txt.py  series/<slug>/VOLxx/BOOK.pdf  series/<slug>/VOLxx/<stem>.txt   # albo epub_to_txt.py
# ręczny cleanup (front/back matter, nagłówki, interpunkcja)
python3 tools/plain_sentences.py series/<slug>/VOLxx/<stem>.txt series/<slug>/VOLxx/<stem>-plain.txt   # domyślnie: pusta linia po każdej linii + kwestie w cudzysłowach “...”
python3 tools/plain_sentences.py --check series/<slug>/VOLxx/<stem>-plain.txt   # PASS
```
Pomija `ln-speaker-resolution`, `ln-voice-casting` i `ln-emotion-tagging` — nie
potrzebuje wiedzieć, kto mówi. Wynik: 0 labeli / 0 `???` / 0 nawiasów / 0 tagów,
każde zdanie (i każda kwestia) w osobnej linii, każda kwestia mówiona w
cudzysłowach `“...”` (`--no-quotes` wyłącza), każda linia z interpunkcją.
Skill: `.pi/skills/ln-to-plain-txt-only/SKILL.md`.

## B. Tłumaczenie (`translator/`)

Komponenty (opis: `translator/README.md`, diagram: `docs/assets/translator.svg`):
`ln-translator/` (silnik EN→PL, CLI + GUI) · `transcript/` (Whisper: audio/wideo →
txt/srt/vtt; opis: `transcript/README.md`, ściąga: `transcript/komendy.txt`) · `workspace/` (dane robocze per
książka: `config.yaml`, `context.md`, `glossary.yaml`, `names.yaml`, `chapters/`, `output/`).

Repozytoria zdalne (konto [kmk00](https://github.com/kmk00)) — **osobne od root repo**:

| Repo | Katalog | Branch | Rola |
|---|---|---|---|
| [ln-translator](https://github.com/kmk00/ln-translator) | `translator/ln-translator/` | `main` | silnik EN→PL |
| [transcript](https://github.com/kmk00/transcript) | `translator/transcript/` | `master` | Whisper (audio → tekst) |
| [Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1) | *(poza repo)* | `master` | **zewnętrzna aplikacja TTS** — konsument artefaktów |

> **Domknięcie pipeline'u.** Kroki ①–④ dają tekst gotowy pod TTS, ale **audio
> powstaje poza tym repo** — w aplikacji
> [Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1) (podział na
> role, OmniVoice), keyowanej po etykietach z `characters.yaml`. Dlatego głosy
> dobierasz ręcznie, a repo nie trzyma sampli ani plików audio (`VOICES.md`).

```bash
cd translator/ln-translator
uv run translator info                                       # konfiguracja + modele
uv run translator translate <plik_EN.txt> -o output/<nazwa>_pl.txt
uv run translator refine    output/<nazwa>_pl.txt -e <plik_EN.txt>
uv run translator diagnose  output/<nazwa>_pl.txt
uv run translator retry     output/<nazwa>_pl.txt            # regeneracja błędnych chunków
uv run translator resume    output/<nazwa>_pl.txt            # wznowienie przerwanej sesji
```

> 🔐 `ln-translator/.env`, `prompt.yaml` i `workspace/*/config.yaml` mogą zawierać
> klucze API w plaintekście — trzymaj je poza gitem i rotuj, jeśli wyciekną.

### Transkrypcja (`translator/transcript/`) — osobne narzędzie

Repo zdalne: [github.com/kmk00/transcript](https://github.com/kmk00/transcript)
(branch `master`).

```bash
cd translator/transcript
uv sync                                       # wymaga też ffmpeg w PATH
uv run transkrypcja.py <plik_lub_folder> -l pl --format txt
```

Domyślny język to **angielski** — dla polskich nagrań podaj `-l pl` (albo `--lang auto`).
Pełny opis: `transcript/README.md`; ściąga: `transcript/komendy.txt`.
Nie należy do pipeline'u audiobookowego — wynikowy tekst możesz podać dalej
do `tools/plain_sentences.py`.

### 0. Glossary tłumaczeniowy (`ln-generate-glossary`)
```bash
/generate-glossary "series/<slug>/VOLxx/<stem>-plain.txt"
```
Prompt buduje `series/<slug>/VOLxx/glossary.md` (kandydaci EN→PL + gotowy blok
YAML). Ręcznie:
```bash
python3 tools/glossary_build.py scan series/<slug>/VOLxx/<stem>-plain.txt \
    --slug "<slug>" --volume VOLxx --min-count 2 \
    --characters series/<slug>/characters.yaml --polonize series/<slug>/polonize.yaml
# agent uzupełnia PL + Typ, potem:
python3 tools/glossary_build.py check series/<slug>/VOLxx/glossary.md   # PASS
```
Wybrane pozycje z bloku `glossary:` kopiujesz do `translator/ln-translator/prompt.yaml`
→ `glossary:`. Skill: `ln-generate-glossary`.

Gdy pojawią się markery `[BŁĄD TŁUMACZENIA — CHUNK N]`:
```bash
python3 tools/fix_errors.py detect <output.txt>
# agent poprawia chunk_NNN.txt (wzorzec: original/chunk_NNN.txt)
python3 tools/fix_errors.py verify <output.txt>
python3 tools/fix_errors.py stitch <output.txt>              # + raport *_FIX_raport.md
```

Zasady stylu i glosariusz: `translator/ln-translator/prompt.yaml`.
Skill: `ln-translation-error-check`.

## Bramki jakości (nie wolno ich pominąć)

| Bramka | Skrypt | Warunek |
|---|---|---|
| Pokrycie linii po tagowaniu | `tools/check_coverage.py` | `PASS` |
| Reguły tagowania (tag/linia, EN, ≤1 przecinek, brak słów-efektów) | `tools/tag_qa.py` | `PASS` |
| Rozwiązanie mówców | `tools/resolve_names.py --check` | `PASS` |
| Kompletność obsady | `tools/voice_casting.py` | `PASS` (lub świadome `--allow-missing`) |
| Spójność chunków tłumaczenia | `tools/fix_errors.py verify` | `OK` |
| Glossary (EN→PL) | `tools/glossary_build.py check` | `PASS` |
