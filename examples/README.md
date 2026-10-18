# `examples/` — uruchamialny przykład

Minimalny, **kompletny** tom demonstracyjny, na którym można prześledzić cały
pipeline i przetestować każdą bramkę bez pobierania żadnej książki.
Tekst przykładowy napisany na potrzeby repo.

```
examples/demo-series/
├── characters.yaml                      # obsada (wspólna dla serii, po angielsku)
├── polonize.yaml                        # mapa EN→PL (Rei → Rej)
├── stats.md                             # log serii (realny format z log_stats.py)
└── VOL01/
    ├── DemoBook.txt                     # ① kanoniczny: mówcy jako ??? 
    ├── DemoBook-resolved.txt            # ② ??? rozwiązane
    ├── DemoBook-resolved-tagged.txt     # ③ tagi emocji <<...>>
    ├── DemoBook-resolved-tagged-plnames.txt  # ④ polonizacja imion
    └── DemoBook-plain.txt               # ⑤ czysty tekst do czytania
```

## Sprawdź bramki lokalnie

Wszystkie komendy uruchamiaj z **katalogu głównego repo**:

```bash
# 1. Rozwiązanie mówców (tylko ??? → Imię mogą się zmienić)
python3 tools/resolve_names.py --check \
    examples/demo-series/VOL01/DemoBook.txt \
    examples/demo-series/VOL01/DemoBook-resolved.txt
# → PASS: 3 '???' speaker(s) resolved, all other lines byte-identical.

# 2. Kompletność obsady
python3 tools/voice_casting.py \
    examples/demo-series/VOL01/DemoBook-resolved.txt \
    examples/demo-series/characters.yaml
# → PASS: every named speaker is cast.

# 3. Pokrycie linii po tagowaniu (bramka OBOWIĄZKOWA)
python3 tools/check_coverage.py \
    examples/demo-series/VOL01/DemoBook-resolved.txt \
    examples/demo-series/VOL01/DemoBook-resolved-tagged.txt
# → PASS — every readable line of the original is present, none deleted…

# 4. Reguły tagowania
python3 tools/tag_qa.py examples/demo-series/VOL01/DemoBook-resolved-tagged.txt
# → PASS — all tagging rules satisfied

# 5. Wariant „zdanie = linia" + jego bramka
python3 tools/plain_sentences.py \
    examples/demo-series/VOL01/DemoBook.txt /tmp/demo-sentences.txt
python3 tools/plain_sentences.py --check /tmp/demo-sentences.txt
# → PASS — no labels/???/tags, every line terminal-punctuated.
```

Wszystkie pięć bramek przechodzi na tym przykładzie (`exit 0`).

## Od czego zacząć czytanie

1. `VOL01/DemoBook.txt` — zobacz format kanoniczny (`docs/CONVENTIONS.md` §3).
2. `VOL01/DemoBook-resolved.txt` — porównaj: zmieniły się **tylko** prefiksy `???:`.
3. `VOL01/DemoBook-resolved-tagged.txt` — jeden tag `<<...>>` zaraz po `[`.
4. `VOL01/DemoBook-plain.txt` — efekt końcowy: żadnych labeli, nawiasów ani tagów.
