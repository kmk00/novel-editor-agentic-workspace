# `series/` — dane serii

Tu trafiają **dane** (źródła i artefakty). Repozytorium startuje z pustym
katalogiem — zakładasz `<slug>/` przy pierwszej książce.

```
series/<slug>/
├── characters.yaml      # obsada: etykiety, aliasy, register — JEDEN na serię (po angielsku)
├── polonize.yaml        # mapa EN→PL (wspólna dla serii)
├── stats.md             # JEDEN log serii (wszystkie tomy) — patrz docs/STATS.md
├── voices/<Postać>/     # (opcjonalnie) próbki głosu — głosy dobierasz ręcznie
└── VOL01/               # JEDEN KATALOG NA TOM — źródło + wszystkie artefakty
    ├── <source>.pdf|.epub
    ├── <stem>.txt                        # ① ekstrakcja
    ├── <stem>-resolved.txt               # ② mówcy
    ├── <stem>-resolved-tagged.txt        # ③ tagi emocji (+ .cache.json)
    ├── <stem>-plain.txt                  # ④ kopia do czytania
    └── glossary.md                       # (opcjonalnie) glossary EN→PL
```

Zasady:

- **Jeden katalog na tom** (`VOL01`…`VOL99`, dwucyfrowe zero-padding); dla pozycji
  nienumerowanych — slug tytułu (np. `Sword-Demon-Ballad/`).
- **Nie rozrzucaj plików tomów** w katalogu serii — wszystko, co należy do tomu,
  trzymaj w jego `VOLxx/`.
- **Pliki wspólne zostają na poziomie serii**: `characters.yaml`, `polonize.yaml`,
  `stats.md`.
- Serie rozdziałowe mogą użyć `chapters/` (jeden plik na rozdział).

Pełna konwencja: [`docs/CONVENTIONS.md`](../docs/CONVENTIONS.md) §1a.
