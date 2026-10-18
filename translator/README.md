# `translator/` — komponenty tłumaczenia i transkrypcji

Ten katalog leży **poza kodem edytora** (`tools/`, `.pi/`, `docs/`) i zawiera trzy
**osobne** komponenty + dane robocze. Edytor łączy się z nimi tylko
**formatem plików** (`-plain.txt`, „zdanie = linia”) oraz narzędziem
[`tools/fix_errors.py`](../tools/fix_errors.py).

Czwartym, **zewnętrznym** ogniwem jest aplikacja TTS
[**Audiobook-maker-v0.1**](https://github.com/kmk00/Audiobook-maker-v0.1) — tam
ręcznie przypisujesz głosy i syntezujesz audiobooka. Nie leży w tym repo i nie ma
tu żadnego kodu, który ją obsługuje; łączy nas **format artefaktów**.

<p align="center">
  <img src="../docs/assets/translator.svg" alt="Komponenty translator/ i przepływ EN→PL" width="100%">
</p>

| Katalog | Co to | Repo git |
|---|---|---|
| `ln-translator/` | silnik tłumaczenia EN→PL (CLI + GUI) | [github.com/kmk00/ln-translator](https://github.com/kmk00/ln-translator) (`main`) |
| `transcript/` | transkrypcja audio/wideo (Whisper) | [github.com/kmk00/transcript](https://github.com/kmk00/transcript) (`master`) |
| `workspace/` | dane robocze tłumaczenia (per książka) | — (dane lokalne + klucze API) |

W root repo wersjonowany jest wyłącznie ten plik — `.gitignore` wyklucza resztę
`translator/` (zagnieżdżone repozytoria i dane robocze).

---

## Ekosystem — repozytoria zdalne

Trzy repozytoria na GitHubie (konto [**kmk00**](https://github.com/kmk00)). Dwa są
**zagnieżdżone lokalnie** (i dlatego wykluczone z root repo), trzecie jest w pełni
zewnętrzne:

| Repozytorium | Rola | Branch | W root repo? |
|---|---|---|---|
| [**ln-translator**](https://github.com/kmk00/ln-translator) | silnik tłumaczenia EN→PL (CLI + GUI, chunki, retry/resume) | `main` | ❌ (osobne repo) |
| [**transcript**](https://github.com/kmk00/transcript) | transkrypcja audio/wideo (Whisper → txt/srt/vtt) | `master` | ❌ (osobne repo) |
| [**Audiobook-maker-v0.1**](https://github.com/kmk00/Audiobook-maker-v0.1) | aplikacja webowa TTS (podział na role, OmniVoice) — **konsument** artefaktów tego repo | `master` | ❌ (nie klonowane tutaj) |

Każde z zagnieżdżonych repozytoriów ma własny `origin` i wersjonowane jest
niezależnie od root repo (`translator/ln-translator/` → `main`,
`translator/transcript/` → `master`).

---

## `ln-translator/` — silnik EN→PL

Tłumaczy plik tekstowy z angielskiego na polski, chunk po chunku, z podglądem
na żywo, wznawianiem i automatyczną naprawą błędnych fragmentów. Pełny opis:
[`ln-translator/README.md`](ln-translator/README.md).

**Zawartość:**

| Plik / katalog | Rola |
|---|---|
| `translator.py` | CLI + cały silnik (chunkowanie, format 1:1, retry, resume, stitch) |
| `gui.py` | okno podglądu tłumaczenia **EN \| PL** na żywo (PySide6) + edytor `prompt.yaml` |
| `prompt.yaml` | konfiguracja: backend, model, `glossary:`, `additional_info`, parametry chunków (**gitignored**) |
| `prompt.example.yaml` | wzorzec konfiguracji (bez kluczy) |
| `.env` / `.env.example` | klucze API (`DEEPSEEK_API_KEY`, …) — **gitignored** |
| `output/` | wyniki tłumaczeń (`<Book>-plain_pl_<ts>/` + `chunks/`) — **gitignored** |
| `scripts/` | narzędzia poboczne w Go (patrz niżej) |
| `series/` | materiały źródłowe (nieużywane przez silnik) |

### Instalacja i uruchomienie

```bash
cd translator/ln-translator
uv sync                       # venv + zależności
uv run translator info        # sprawdź konfigurację i dostępne modele Ollamy
```

### Podkomendy CLI

| Komenda | Alias | Co robi |
|---|---|---|
| `translate` | `t` | tłumaczy plik EN → PL (chunki, format 1:1) |
| `refine` | `r` | korekta gotowego PL względem oryginału EN (`-e/--original`) |
| `diagnose` | `d` | diagnoza problemów w PL **bez** uruchamiania modelu |
| `info` | `i` | konfiguracja + dostępne modele |
| `retry` | — | regeneracja **błędnych** chunków (`--chunks 6 8` = tylko wybrane) |
| `resume` | `res` | wznowienie przerwanej sesji (generuje tylko brakujące chunki) |

Najważniejsze flagi `translate`: `-o/--output`, `-m/--model`, `-b/--backend`
(`ollama` \| `deepseek` \| `opencode-go`), `-r/--reasoning` (`low…max`),
`--chunk-size`, `--temperature`, `--dry-run` (podgląd planu chunków),
`--refine` (tłumacz i od razu koryguj), `--max-time N` (auto-stop),
`--gui` (podgląd na żywo), `--prompt` (edytor `prompt.yaml`), `-q/--quiet`.

### Przykłady

```bash
# tłumaczenie
uv run translator translate "ksiazka-plain.txt" -o "output/ksiazka_pl.txt"

# plan chunków bez wysyłania do modelu
uv run translator translate "ksiazka-plain.txt" --dry-run

# podgląd EN | PL na żywo (i edytor prompt.yaml)
uv run translator translate "ksiazka-plain.txt" --gui

# inny backend / model
uv run translator translate "ksiazka-plain.txt" -b deepseek -m deepseek-chat

# korekta i diagnoza
uv run translator refine    "output/ksiazka_pl.txt" -e "ksiazka-plain.txt"
uv run translator diagnose  "output/ksiazka_pl.txt"

# naprawa / wznowienie
uv run translator retry     "output/ksiazka_pl.txt" --chunks 6 8
uv run translator resume    "output/ksiazka_pl.txt" --max-time 1800
```

### Układ wyjścia

```
output/<Book>-plain_pl_<ts>/
├── <Book>-plain_pl_<ts>.txt      # wynik (zszyty)
├── errors.md                     # raport wykrytych błędów
└── chunks/
    ├── chunk_NNN.txt             # PL (niektóre z markerem [BŁĄD TŁUMACZENIA — CHUNK N])
    ├── original/chunk_NNN.txt    # EN — wzorzec (NIE ruszać)
    └── session.json              # total_chunks, overlap, failed_chunks
```

### Format 1:1 i naprawa błędów

Wejście jest numerowane liniami, a model dostaje twarde polecenie oddania **tej
samej liczby linii**. Jeśli scali/rozdzieli linie, prompt jest powtarzany, a gdy
to nie pomoże — blok jest dzielony rekurencyjnie (aż do pojedynczych linii;
parametr `line_retries`). Stitch składa PL **linia po linii względem EN**, więc
liczba niepustych linii wyjścia = liczbie niepustych linii wejścia.

Gdy w pliku zostaną markery `[BŁĄD TŁUMACZENIA — CHUNK N]`, użyj
[`tools/fix_errors.py`](../tools/fix_errors.py):

```bash
python3 tools/fix_errors.py detect <output.txt>   # które chunki i dlaczego
# poprawa: /ln-fix-translation (agent odtwarza PL 1:1 z EN) albo `translator retry`
python3 tools/fix_errors.py verify <output.txt>   # bramka → OK
python3 tools/fix_errors.py stitch <output.txt>   # zszycie + <stem>_FIX_raport.md
```

### `scripts/` (narzędzia poboczne, Go)

| Element | Co robi |
|---|---|
| `converter/` | `main.go` + `go.mod` — PDF → tekst, opcjonalnie podział na pliki rozdziałów (`--split`) |
| `fix_rezero_names.go` | jednorazowa poprawka nazw w pliku tekstowym |
| `sloth/` | **dane** (pliki rozdziałów jednej książki) — nie kod |

> `scripts/converter/` zawiera przykładowy PDF, a `scripts/sloth/` — pliki tekstowe;
> to przykładowe treści osób trzecich.

---

## `transcript/` — Whisper (audio/wideo → tekst)

Lokalna transkrypcja nagrań modelem **OpenAI Whisper**. Obsługuje
`.mp3 .wav .m4a .flac .ogg .mp4 .webm .aac`. Pełny opis:
[`transcript/README.md`](transcript/README.md); ściąga komend:
[`transcript/komendy.txt`](transcript/komendy.txt).

**Wymagania:** Python 3.14 · `uv` · **`ffmpeg`** w `PATH` · `openai-whisper` (przez `uv sync`).

**Zawartość:** `transkrypcja.py` (skrypt — uwaga na pisownię: *transkrypcja*,
nie „transkrybcja”), `pyproject.toml`, `transkrypcje/` (wyjście), `komendy.txt`.

### Instalacja i uruchomienie

```bash
cd translator/transcript
uv sync
uv run transkrypcja.py <plik_lub_folder> [opcje]
```

> Projekt to **pojedynczy skrypt**, więc `pyproject.toml` ma `[tool.uv] package = false`
> — nie ma komendy `uv run transcript`. Kanoniczna forma to `uv run transkrypcja.py …`.

### Opcje

| Opcja | Wartości | Domyślnie |
|---|---|---|
| `sciezka` | plik audio/wideo **lub** folder (skan rekurencyjny) | — (wymagane) |
| `--model` | `tiny` `base` `small` `medium` `large` `large-v2` `large-v3` (+ warianty `.en`) | `medium` |
| `--jezyk` / `--lang` / `-l` | kod ISO-639-1 (`en`, `pl`, `de`, …) lub `auto` | `en` |
| `--format` | `txt` \| `srt` \| `vtt` \| `all` | `txt` |
| `--wyjscie` | folder wynikowy | `./transkrypcje` |
| `--cichy` | wyłącza podgląd tekstu na żywo | — |
| `--no-transcript` | TXT jako jeden ciągły akapit (bez nowych linii) | — |

> ⚠️ Domyślny język to **angielski**. Dla polskiego nagrania **zawsze** podaj `-l pl`
> (albo `--lang auto`).

### Przykłady

```bash
# podstawowa transkrypcja (angielski, txt)
uv run transkrypcja.py nagranie.mp3

# polskie nagranie (WAŻNE: -l pl)
uv run transkrypcja.py nagranie.mp3 -l pl

# napisy SRT, polski, dokładny model
uv run transkrypcja.py wyklad.mp3 -l pl --format srt --model large-v3

# cały folder, wszystkie formaty, autodetekcja języka
uv run transkrypcja.py nagrania/ -l auto --format all --wyjscie wyniki

# szybciej / mniej VRAM
uv run transkrypcja.py podcast.mp3 --model small --cichy
```

Wynik: `transkrypcje/<stem>.txt` (jeden segment na linię), `.srt`, `.vtt`.

### Wydajność

Model `medium` potrzebuje ok. **5 GB VRAM**. Przy `CUDA out of memory`:
zamknij inne procesy GPU (`nvidia-smi`), zejdź do `--model small` albo ustaw
`export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. Uwaga: skrypt ma
`fp16=False` na sztywno, więc na GPU liczy w fp32 (więcej VRAM, wolniej).

---

## `workspace/` — dane robocze tłumaczenia

Konwencja **jednego katalogu na książkę**, niezależna od samego silnika: trzyma
konfigurację, kontekst fabuły i słowniki obok rozdziałów i wyników.

```
workspace/<book>/
├── config.yaml       # backend, model, chunk_size, output_dir, additional_info (prompt)
├── context.md        # „story so far” + postacie + notatki o tonie/stylu
├── glossary.yaml     # słownik terminów EN→PL (spójność w całej serii)
├── names.yaml        # nazwy własne / formy docelowe
├── chapters/         # wejście rozbite na rozdziały (00_prologue.txt, 01_chapter1.txt, …)
└── output/           # wyniki + katalogi *_chunks/ (jak w ln-translator/output)
```

To **konwencja pracy** (używana przy tłumaczeniach serii), a nie API silnika —
`translator.py` czyta `prompt.yaml`/`config.yaml` i pliki wejściowe, a `context.md`
i `names.yaml` służą jako materiał referencyjny (np. wklejany do `additional_info`
albo `glossary:`). Utrzymuj spójność z [`docs/CONVENTIONS.md`](../docs/CONVENTIONS.md)
i [`docs/VOICES.md`](../docs/VOICES.md) (`characters.yaml`, `polonize.yaml`).

---

## 🔐 Bezpieczeństwo — klucze API

Konfiguracja może trzymać klucze API w plaintekście:

| Plik | Co zawiera | Wersjonowanie |
|---|---|---|
| `ln-translator/.env` | `DEEPSEEK_API_KEY=sk-…` | `.gitignore` |
| `ln-translator/prompt.yaml` | `opencode_go_api_key: "sk-…"`, `deepseek_api_key` | `.gitignore` |
| `workspace/*/config.yaml` | `deepseek_api_key: sk-…` | `.gitignore` |

Wzorce do skopiowania to `prompt.example.yaml` i `.env.example` (puste wartości),
a sekrety podawaj przez zmienne środowiskowe. Jeśli klucz trafi kiedykolwiek do
historii gita, **zrotuj go** w panelu DeepSeek / OpenCode i wyczyść historię.
