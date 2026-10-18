# tools/legacy — skrypty wycofane / jednorazowe

Skrypty, które **nie są już częścią aktywnego pipeline'u**. Trzymamy je tu dla
historii i na wypadek migracji starych danych. **Nie zaczynaj z nimi nowej pracy**
i nie linkuj ich ze skilli `ln-*`.

| Skrypt | Co robił | Czym to zastąpiono |
|---|---|---|
| `apply_speaker_map.py` | Nakładał „mapę linia→mówca" (plik tekstowy `123 Imię`) na plik z `???`, przepisując wyłącznie prefiksy mówców. | `ln-speaker-resolution`: agent edytuje plik bezpośrednio i weryfikuje przez `python3 tools/resolve_names.py --check <orig> <resolved>`. |

## Podobne, ale NIE legacy

- `tools/resolve_speakers_llm.py` — zostaje w `tools/`, bo odwołują się do niego
  skille `ln-speaker-resolution` / `ln-generate-full` jako *last-resort* akcelerator
  na bardzo duże książki (domyślnie **nie używać** — agent jest dokładniejszy).

## Zasada

Jeśli skrypt przestaje być używany: przenieś go tutaj, dopisz wiersz w tabeli
powyżej (co robił + czym zastąpiono) i usuń odwołania ze skilli oraz `docs/`.
