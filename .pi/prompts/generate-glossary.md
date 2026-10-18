---
description: Wygeneruj glossary tłumaczeniowy (glossary.md) dla tomu — kandydaci EN→PL z licznikami, seed z characters.yaml/polonize.yaml, gotowy blok YAML do wklejenia do translator/ln-translator/prompt.yaml
argument-hint: "<ścieżka do <stem>-plain.txt albo katalogu tomu> [glossary.md]"
---
Wygeneruj glossary tłumaczeniowy dla `$1`, postępując dokładnie według skilla
`ln-generate-glossary` (najpierw przeczytaj
`.pi/skills/ln-generate-glossary/SKILL.md`). Wynikiem jest gotowy do przejrzenia
plik `glossary.md` w katalogu tomu (`series/<slug>/VOLxx/`), z którego kopiujesz
wybrane pozycje do `translator/ln-translator/prompt.yaml` → `glossary:`.

**Wejście:** `$1` to zwykle `<stem>-plain.txt` powstały po `ln-to-plain-txt-only`
(albo dowolny plik tekstowy tomu). `$2` to opcjonalna ścieżka wyjściowa
(domyślnie `glossary.md` obok wejścia).

1. **Skan kandydatów** — uruchom:
   ```bash
   python3 tools/glossary_build.py scan "$1" \
       --slug "<slug>" --volume VOLxx --min-count 2 \
       --characters "series/<slug>/characters.yaml" \
       --polonize   "series/<slug>/polonize.yaml" \
       --glossary   "series/<slug>/glossary.md"      # tylko jeśli istnieje
   ```
   (pomiń `--characters`/`--polonize`/`--glossary`, jeśli plików nie ma).
2. **Przegląd ręczny (obowiązkowy)** — uzupełnij kolumnę **PL**, nadaj **Typ**
   (`postać`/`miejsce`/`organizacja`/`termin`/`przedmiot`/`honoryfikacja`/`fraza`),
   usuń śmieci, dodaj pozycje, których skan nie złapał (honoryfikacje, epitety,
   onomatopeje). Formy spójne z `characters.yaml` / `polonize.yaml` / wcześniejszym
   glossary serii. Zdecydowane wpisy przenieś do bloku
   `## Gotowe do wklejenia (YAML)`.
3. **Bramka (obowiązkowa)**:
   `python3 tools/glossary_build.py check "<glossary.md>"` musi dać `PASS`
   (brak pustych wartości i duplikatów kluczy).
4. **Statystyki**: `python3 tools/log_stats.py <slug> --step generate-glossary ...`.

Zakończ obowiązkową **tabelą** podsumowania (kandydaci / wpisy z PL / wpisy YAML /
użyte seed-y / wynik `check`). Nie prezentuj wyniku bez `PASS`.

Jeśli `$1` jest pusty, zapytaj użytkownika, dla którego tomu/pliku wygenerować
glossary.
