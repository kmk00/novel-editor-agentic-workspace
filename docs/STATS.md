# Stats — jeden log na serię

Każdy skill `ln-*` na końcu zapisuje wpis do **jednego** pliku na serię:

```
series/<slug>/stats.md
```

To jedyne miejsce, gdzie ląduje „co zostało zrobione, w ile, jakim kosztem”.
Format to tabela markdown (nagłówek + wiersze), tworzona automatycznie przy
pierwszym wpisie.

## Jak zapisywać

Zamiast edytować plik ręcznie, użyj wspólnego skryptu:

```bash
python3 tools/log_stats.py <slug> --step <etap> --file "<plik>" \
    --duration <sekundy|tekst> --resources "<model/narzędzie/agent>" \
    --result <PASS|OK|DONE|FAIL> --notes "<liczby, decyzje, zastrzeżenia>"
```

Przykład:

```bash
python3 tools/log_stats.py moja-seria --step emotion-tagging \
    --file "series/moja-seria/VOL02/<stem>-resolved-tagged.txt" \
    --duration 3421 --resources "ollama huihui_ai/gemma-4-abliterated:26b" \
    --result PASS --notes "1731 tagged, 0 fallbacks"
```

## Kolumny

| Kolumna | Znaczenie |
|---|---|
| Timestamp | kiedy zakończono przebieg |
| Step | etap / skill (`speaker-resolution`, `emotion-tagging`, `coverage-check`…) |
| File | wytworzony artefakt (ścieżka względem root repo) |
| Duration | czas zegarowy (`12.3s`, `4m32s`, `1h02m`) |
| Resources | model / narzędzie / agent (np. `agent (no local model)`, `ollama …`) |
| Result | `PASS`, `OK`, `DONE`, `FAIL`… |
| Notes | liczby, decyzje, zastrzeżenia |

## Zasady

- **Jeden plik na serię** — wszystkie tomy i pliki tej samej serii dopisują
  wiersze do tego samego `series/<slug>/stats.md` (na poziomie serii, nie w `VOLxx/`).
- **Jeden katalog na tom** — artefakty, których dotyczą wpisy, leżą w
  `series/<slug>/VOLxx/` (patrz `docs/CONVENTIONS.md` §1a).
- Wpis dodaje **każdy** skill po zakończeniu pracy (także bramki jakości).
- `ln-generate-full` dopisuje wpis po każdym etapie oraz jeden zbiorczy na końcu.
- Plik jest źródłem prawdy o historii obróbki — nie kasuj wierszy, dopisuj nowe.
