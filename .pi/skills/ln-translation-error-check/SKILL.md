---
name: ln-translation-error-check
description: Sprawdza i naprawia jakość tłumaczenia w chunkach oznaczonych potencjalnym błędem, np. "[BŁĄD TŁUMACZENIA — CHUNK 4]", w plikach wyjściowych translatora ln-translator. Porównuje wadliwy chunk PL z oryginałem EN (katalog original), pozwala poprawić tłumaczenie bez marnowania treści, weryfikuje zgodość liczby linii EN↔PL, zszywa naprawione chunki z powrotem do pliku wyjściowego i zapisuje raport "co poprawiono" do pliku .md. Użyj gdy użytkownik poprosi o sprawdzenie/poprawę błędów tłumaczenia w chunkach oznaczonych markerem [BŁĄD TŁUMACZENIA — CHUNK N] albo o raport naprawy chunków.
---

# Kontrola i naprawa błędnych chunków tłumaczenia (ln-translator)

Plik wyjściowy `ln-translator` ma obok siebie katalog chunków. Niektóre chunki są
oznaczone markerem potencjalnego błędu:

```
[BŁĄD TŁUMACZENIA — CHUNK 4]
```

Ten skill sprawdza poprawność takich chunków, poprawia je względem oryginału EN,
weryfikuje naprawę i zapisuje raport **co poprawiono** do pliku `.md`.

## Układ plików (rozpoznawany automatycznie)

```
<katalog>/<plik_stem>_chunks/chunk_NNN.txt         → tłumaczenie PL (niektóre z markerem)
<katalog>/<plik_stem>_chunks/original/chunk_NNN.txt → oryginał EN (wzorzec poprawności)
<katalog>/<plik_stem>_chunks/session.json           → overlap, total_chunks, failed_chunks
```

Przykład realny:
```
translator/ln-translator/output/Fate Strange Fake - Vol.1-plain_pl_…_204305.txt
translator/ln-translator/output/Fate Strange Fake - Vol.1-plain_pl_…_204305_chunks/
```

## Jak uruchomić

Scenariusz przykładowy (podaj pełną ścieżkę do pliku wyjściowego `.txt`):

```
F="translator/ln-translator/output/Fate Strange Fake - Vol.1-plain_pl_20260917_204305.txt"

# 1) WYKRYJ wadliwe chunki (EN↔PL: linie, rozmiar, fragmenty, krytyczne ucięcia)
python3 tools/fix_errors.py detect "$F"

# 2) POPRAW każdy wadliwy chunk (wykonuje agent, patrz niżej)

# 3) WERYFIKUJ w pętli aż do OK (exit 0 = gotowe)
python3 tools/fix_errors.py verify "$F"

# 4) ZSZYJ naprawione chunki z powrotem do pliku i wygeneruj raport .md
python3 tools/fix_errors.py stitch "$F"
```

Ścieżki rozwiązywane są względem katalogu roboczego. `verify` zwraca **1**, gdy
pozostały markery albo gdy naprawiony chunk nie zgadza się z EN pod względem
liczby linii — nie wolno dostarczać pliku, który nie przeszedł `verify`.

### Silnik wymusza format 1:1 (linijka po linijce)

Źródła `-plain.txt` są zdanie-w-linii, więc `translator.py`:
- numeruje linie wejścia (`1. …`, `2. …`) i żąda **dokładnie tej samej liczby linii**
  na wyjściu (`line_rule` w prompcie, `line_retries` w `prompt.yaml`),
- przy rozjeździe ponawia z informacją zwrotną („miałeś N linii, wymagane M”),
- gdy to nie pomoże, dzieli blok rekurencyjnie aż do pojedynczych linii.

Dzięki temu `uv run translator.py retry <plik>` **sam domyka** większość chunków
i `verify` dobiega do `OK`. Ręczna poprawa (krok 2) dotyczy wtedy tylko resztek
(np. realnie uciętych tłumaczeń). Uwaga na naprawione bugi: (1) `postprocess()`
używał wzorca `[^:]*` bez wykluczenia `\n`, przez co zjadał wiele linii — teraz
wzorce są ograniczone do jednej linii; (2) stary stitch dokładał puste linie
i przycinał tekst po znakach, gubiąc linie — teraz `stitch` (zarówno
`translator.py`, jak i `tools/fix_errors.py`) jest **wyrównany do źródła**: jedna
linia PL na jedną linię EN, połówki rozciętych linii scalane spacją, zero
zbędnych pustych linii. Nagłówek `[Fragment N z M]` nie trafia do tekstu do
tłumaczenia.

## Krok 1 — detect

Wypisuje posortowaną listę wszystkich chunków z markerem, a dla każdego:
- liczbę linii **EN** i **PL** (niepuste linie, tak samo liczy `translator.py`),
- rozmiar tłumaczenia,
- nagłówki PL i EN (pierwsze ~3 linie),
- flagę `⚠ KRYTYCZNE ucięcie`, gdy PL ma mniej niż 60% linii EN.

To wskazuje, które chunki są naprawdę zepsute (ucięte/obcięte), a które mają
tylko drobne rozbieżności — najpierw napraw najkrótsze (najmniejsze `PL linie`).

## Krok 2 — poprawa (robota agenta)

**Najpierw spróbuj szybkiej ścieżki:** `cd translator/ln-translator && uv run translator.py retry "<plik.txt>"`
— silnik wymusza teraz 1:1 (numeracja linii + ponowne próby + rekurencyjny podział)
i sam usuwa większość markerów. Dopiero to, co nadal nie przejdzie `verify`,
popraw ręcznie poniżej.

Dla każdego wadliwego chunku `N`:
1. Przeczytaj **pełny** `original/chunk_NNN.txt` (EN) i bieżący `chunk_NNN.txt` (PL).
2. Odtwórz kompletne, wierne tłumaczenie PL używając pełnego EN jako wzorca —
   szczególnie tam, gdzie `detect` pokazał ucięcie. **Zachowaj każdą linię/akapit
   EN** (nie łącz ani nie pomijaj treści, por. zasady tłumaczenia w
   `translator/ln-translator/prompt.yaml`).
3. Wpisz poprawione tłumaczenie do `chunk_NNN.txt` — **bez** linii markera
   `[BŁĄD TŁUMACZENIA — CHUNK N]`.
4. Nie ruszaj plików z katalogu `original/`.

Wskazówki jakości (spójność serii):
- nie tłumacz świętych nazw własnych (postaci, miejsca, klasa „Servant"/„Sługa"
  — trzymaj się ustalonej wcześniej konwencji serii),
- zachowuj wulgaryzmy i kolokwializmy (np. „chan", „Khaa…") bez łagodzenia,
- akapity/linie EN → akapity/linie PL jeden do jednego, tekst finalnie powinien
  kończyć się znakiem interpunkcyjnym.

## Krok 3 — verify (bramka jakości)

- wykrywa **pozostałe markery** (nienaprawione chunki) — FAIL,
- dla chunków z `failed_chunks`, które już nie mają markera: sprawdza **zgodność
  liczby linii EN vs PL** oraz czy PL nie jest podejrzanie krótki — FAIL w razie
  rozjazdu,
- `OK` (exit 0) dopiero gdy wszystkie markery zniknęły i naprawione chunki są
  spójne z EN.

Poprawiaj i uruchamiaj `verify` w pętli, aż przejdzie czysto. Jeśli chunk jest
tak zepsuty, że rekonstrukcja jest niejasna, przetłumacz go od nowa w całości
z EN (nie łatkuj fragmentarycznie).

## Krok 4 — stitch + raport .md

Zszywa wszystkie chunki (1..total_chunks, z overlapem z `session.json`) z
powrotem do pliku wyjściowego, czyści `failed_chunks` w `session.json` i
generuje raport **`<plik_stem>_FIX_raport.md`** obok pliku (lub z `--report <plik.md>`).

Raport zawiera sekcję dla każdego naprawianego chunku z tabelą
(linie EN / linie PL / znaki PL) oraz miejscem na **„Co poprawiono"**.

### Po wygenerowaniu raportu

Uzupełnij dla każdego chunku pole **`Co poprawiono:`** — zamiast kursywnego
placeholdera wpisz konkretny opis, np.:

```
Chunk 49: ucięcie — było 3/32 linii EN; odtworzone pełne tłumaczenie +30 linii.
Chunk 56: ucięcie o 12 linii, poprawiona interpunkcja i zamknięcie dialogów.
Chunk 35: zgoda linii, ale 4 linie nadmiarowe połączone — połączono z poprzednim akapitem.
```

Edytuj `.md` np. przez `edit` i dostarcz użytkownikowi gotowy raport razem ze
wskazaniem poprawionego pliku wyjściowego.

## Zasady

- **Nigdy nie dostarczaj** pliku z markerem ani niespójnym chunkem — `verify`
  musi przejść jako `OK`.
- Podmień tłumaczenie **tylko** w plikach `chunk_*.txt`; katalog `original/` jest
  wzorcem EN i pozostaje nietknięty.
- Po `stitch` szczególną uwagę zwróć na końcówkę pliku (chunki 86/104/108/109
  w Vol.1 były najmocniej ucięte w realnym przykładzie).

## Ścieżka skryptu w tym skillu

`tools/fix_errors.py` (skrypt pomocniczy) — wykonuje tylko detekcję,
weryfikację, zszywanie i szkielet raportu. Samą naprawę tłumaczenia wykonuje
agent, zgodnie z zasadami z `translator/ln-translator/prompt.yaml`
(szczegóły silnika: `translator/ln-translator/README.md`).

## Stats logging (mandatory)

Append one entry to the single per-series log when this skill finishes:

```
python3 tools/log_stats.py <slug> --step translation-error-check --file "<artifact>" \
    --duration <seconds> --resources "tools/fix_errors.py + agent" --result <PASS|OK|DONE> \
    --notes "<counts/decisions>"
```

`series/<slug>/stats.md` is the one log for the whole series (all volumes/files).
See `docs/STATS.md`.
