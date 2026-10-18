---
description: Sprawdź jakość tłumaczenia i napraw błędne chunki (markery [BŁĄD TŁUMACZENIA — CHUNK N]) w wyjściu translatora ln-translator — detect → poprawa → verify (PASS) → stitch + raport .md
argument-hint: "<ścieżka do pliku PL .txt lub katalogu output/...>"
---
Sprawdź i napraw tłumaczenie dla `$1`, postępując dokładnie według skilla
`ln-translation-error-check` (najpierw przeczytaj
`.pi/skills/ln-translation-error-check/SKILL.md`).

`$1` może być plikiem wyjściowym `.txt` translatora **albo** katalogiem
`output/<...>_pl_<ts>/` — w drugim przypadku użyj leżącego w nim pliku `.txt`
(narzędzie samo znajdzie katalog `chunks/`).

1. **detect** — `python3 tools/fix_errors.py detect "<plik.txt>"`; ustal, które
   chunki są naprawdę ucięte (`⚠ KRYTYCZNE ucięcie`), a które mają drobny rozjazd linii.
2. **popraw** — dla każdego wadliwego chunku odtwórz pełne, wierne tłumaczenie PL
   na podstawie pełnego `chunks/original/chunk_NNN.txt` (EN), zachowując **jeden
   akapit EN → jeden akapit PL** i usuwając linię markera `[BŁĄD TŁUMACZENIA — CHUNK N]`.
   Szybka ścieżka dla całej partii: `cd translator/ln-translator && uv run translator.py retry "<plik.txt>"`
   (regeneruje wadliwe chunki lokalnym modelem z `prompt.yaml`), a potem ręcznie
   domknij to, co nadal nie przechodzi `verify`.
3. **verify** — `python3 tools/fix_errors.py verify "<plik.txt>"` w pętli, aż
   zwróci `OK` (exit 0). Nie wolno dostarczyć pliku z markerem ani z rozjazdem
   liczby linii EN↔PL.
4. **stitch + raport** — `python3 tools/fix_errors.py stitch "<plik.txt>"`, następnie
   uzupełnij w wygenerowanym `<stem>_FIX_raport.md` pole `Co poprawiono:`
   konkretnym opisem dla każdego chunku.

Nie ruszaj plików w `chunks/original/`. Zakończ obowiązkową tabelą
podsumowania (per chunk: linie EN/PL, co poprawiono) + wynik `verify`.

Jeśli `$1` jest pusty, zapytaj użytkownika, który plik/katalog naprawić.
