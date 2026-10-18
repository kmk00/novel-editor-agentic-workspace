# AGENTS.md — NOVEL EDITOR

Kontrakt dla agenta pracującego w tym repozytorium. Czytaj to najpierw; szczegóły
w `docs/`.

## Cel projektu

Przygotowywanie light novel / web novel do **audiobooka z wybranymi postaciami
i głosami**: ekstrakcja z PDF, czyszczenie, rozwiązanie mówców, obsadzenie głosów,
tagowanie emocji, polonizacja imion i tłumaczenie EN→PL.

## Struktura (skrót)

| Ścieżka | Co tam jest |
|---|---|
| `docs/` | PIPELINE.md, CONVENTIONS.md, VOICES.md, **SKILLS.md** (co generuje który skill + przykłady), STATS.md, szablon obsady, `assets/` (diagramy) |
| `README.md` | przegląd projektu dla człowieka (GitHub) — szybki start, pipeline, przykłady |
| `examples/` | mały, uruchamialny przykład tomu (wejście → resolved → tagged → plain + bramki) |
| `tools/` | wspólne skrypty (skille ich używają, NIE duplikuj) |
| `series/<slug>/` | dane serii: `characters.yaml`, `polonize.yaml`, `stats.md` (wspólne) + `VOLxx/` — **jeden katalog na tom** (źródło + artefakty) |
| `.pi/skills/` | skille `ln-*` (instrukcje + bramki) |
| `.pi/prompts/` | prompty `/...` |
| `translator/README.md` | opis komponentów tłumaczenia (indeks) |
| `translator/ln-translator/` | silnik tłumaczenia EN→PL, CLI + GUI (osobny git: [kmk00/ln-translator](https://github.com/kmk00/ln-translator), `main`) — **nie ruszać** bez wyraźnej potrzeby |
| `translator/transcript/` | Whisper: audio/wideo → txt/srt/vtt (osobny git: [kmk00/transcript](https://github.com/kmk00/transcript), `master`; `README.md` + ściąga `komendy.txt`; dom. język `en`) |
| `translator/workspace/` | robocze katalogi tłumaczeń (`config.yaml`, `context.md`, `glossary.yaml`, `names.yaml`, `chapters/`, `output/`) |
| *(zewnętrzne)* [Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1) | aplikacja webowa TTS (podział na role, OmniVoice) — **konsument** artefaktów; nie leży w tym repo |

### Repozytoria zdalne

Root repo wersjonuje **tylko** `translator/README.md`; reszta `translator/` jest w
`.gitignore` (zagnieżdżone repo + dane). Każde z tych repozytoriów wersjonowane jest
osobno, z własnego katalogu:

| Repo | Katalog | Branch |
|---|---|---|
| [kmk00/ln-translator](https://github.com/kmk00/ln-translator) | `translator/ln-translator/` | `main` |
| [kmk00/transcript](https://github.com/kmk00/transcript) | `translator/transcript/` | `master` |
| [kmk00/Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1) | *(poza repo)* | `master` |

Szczegółowy układ i nazewnictwo plików: `docs/CONVENTIONS.md`.
Workflow i komendy: `docs/PIPELINE.md`. Casting: `docs/VOICES.md`.

## Skille (`ln-*`)

| Skill | Rola |
|---|---|
| `ln-generate-full` | **one-shot dla jednej książki (PDF/EPUB)**: ekstrakcja → rozwiązanie mówców → `characters.yaml` → tagi emocji → bramka pokrycia → plain copy |
| `ln-pdf-to-txt` | PDF → `<stem>.txt` z `???: [...]` |
| `ln-pdf-to-plain-redacted` | one-shot PDF → czysty tekst do czytania |
| `ln-to-plain-txt-only` | one-shot **PDF/EPUB → tylko plain** (bez `???`, zdanie/kwestia w osobnej linii, interpunkcja) — pomija resolution/casting/tagging |
| `ln-speaker-resolution` | `???` → imię (tylko 100% pewności) |
| `ln-voice-casting` | `characters.yaml`: kanoniczne etykiety, aliasy, `register`; weryfikacja obsady (głosy przypisujesz ręcznie) |
| `ln-emotion-tagging` | tagi `<<...>>` w dialogach (kanoniczny format) |
| `ln-tag-coverage-check` | bramka: żadna czytelna linia nie zniknęła |
| `ln-plain-copy` | wersja do czytania bez labeli/nawiasów/tagów |
| `ln-name-polonization` | EN→PL fonetyczna polonizacja imion + deklinacja |
| `ln-generate-glossary` | `glossary.md` dla tomu: kandydaci EN→PL + blok YAML do `prompt.yaml` → `glossary:` |
| `ln-translation-error-check` | naprawa błędnych chunków tłumaczenia |

## Twarde reguły

1. **Nie zgaduj mówcy.** `???` rozwiązuj tylko przy jednoznacznym kontekście.
2. **Nie usuwaj czytelnych linii.** Po tagowaniu uruchom `tools/check_coverage.py`
   i nie prezentuj wyniku bez `PASS`.
3. **Jeden kanoniczny format tagów:** inline `<<...>>` po `[`. Per-liniowe JSON-y
   (`tagsNN.json` + `apply_tags.py`) są **legacy** — nie zaczynaj tak nowej pracy.
4. **Narracja bez tagów.** Tagi tylko w liniach `Imię: [...]`.
5. **TTS-safety:** brak surowych `<<`/`>>` poza tagami (zamień na `()`); w plikach
   plain/do syntezy **żadnych nawiasów kątowych** — `<...>` też zamień na `()`;
   każde zdanie kończy się znakiem terminalnym; brak słów-efektów dźwiękowych w tagach.
6. **Skrypty są w `tools/`** — w skillach i dokumentacji używaj `python3 tools/<skrypt>.py`.
7. **Nie ruszaj `translator/ln-translator/`** ani nie zmieniaj jego zawartości
   (poza wyraźnym poleceniem użytkownika).
8. **Nazwy własne:** trzymaj się formy z `characters.yaml` / `polonize.yaml` danej serii.
9. **Jeden katalog na tom:** źródło i artefakty tomu leżą w `series/<slug>/VOLxx/`;
   pliki wspólne serii (`characters.yaml`, `polonize.yaml`, `stats.md`) zostają na
   poziomie serii. Nie rozrzucaj plików tomów w katalogu serii. Szczegóły:
   `docs/CONVENTIONS.md` §1a.
10. **Podsumowania:** każdy skill kończy się **tabelą** (markdown), nie tylko prozą.

## Bramki jakości (obowiązkowe)

| Bramka | Komenda | Warunek |
|---|---|---|
| Pokrycie linii | `python3 tools/check_coverage.py <orig> <tagged>` | `PASS` |
| Reguły tagowania | `python3 tools/tag_qa.py <tagged>` | `PASS` |
| Rozwiązanie mówców | `python3 tools/resolve_names.py --check <orig> <resolved>` | `PASS` |
| Kompletność obsady | `python3 tools/voice_casting.py <chapter>` | `PASS` |
| Chunks tłumaczenia | `python3 tools/fix_errors.py verify <output>` | `OK` |

## Typowy przebieg

`docs/PIPELINE.md`. W skrócie:
`ln-pdf-to-txt` → `ln-speaker-resolution` → `ln-voice-casting` →
`ln-emotion-tagging` → `ln-tag-coverage-check` → (`ln-name-polonization`) →
`ln-plain-copy`; tłumaczenie równolegle przez `translator/ln-translator/`
(poprzedzone `ln-generate-glossary` → `glossary.md`).

**Domknięcie:** ostatni krok (synteza audio) dzieje się **poza tym repo** — w
zewnętrznej aplikacji TTS [Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1),
keyowanej po etykietach z `characters.yaml`. Dlatego trzymaj etykiety stabilne, a
żadnych sampli ani plików audio nie commituj (`.gitignore`).
