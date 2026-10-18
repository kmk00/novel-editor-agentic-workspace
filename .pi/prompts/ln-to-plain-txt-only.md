---
description: One-shot PDF/EPUB → tylko plain reading copy (bez ???, bez labeli mówców, bez nawiasów i tagów; zdanie/kwestia w osobnej linii, każda kwestia w cudzysłowach, każda linia z interpunkcją)
argument-hint: "<ścieżka do book.pdf|book.epub> [katalog tomu]"
---
Wykonaj konwersję **tylko do plain** dla `$1`, postępując dokładnie według skilla
`ln-to-plain-txt-only` (najpierw przeczytaj
`.pi/skills/ln-to-plain-txt-only/SKILL.md`). Skill pomija rozwiązywanie mówców,
casting i tagowanie emocji — powstaje wyłącznie czytelny tekst.

**Układ tomu:** źródło i artefakty leżą w `series/<slug>/VOLxx/`
(pliki wspólne serii zostają na poziomie `series/<slug>/`; patrz
`docs/CONVENTIONS.md` §1a). Katalog docelowy: `$2`, inaczej katalog ze źródłem
(jeśli książka leży płasko w katalogu serii — najpierw przenieś ją do `VOLxx/`).

1. **Ekstrakcja** do `<stem>.txt`:
   - `.pdf` → `python3 tools/pdf_to_txt.py "..."` (mówcy jako `???` — to OK),
   - `.epub` → `python3 tools/epub_to_txt.py "..."` (sprawdź listę `ANOMALIES`).
2. **Ręczne czyszczenie** `<stem>.txt`: usuń front/back matter (copyright, ISBN,
   spis treści, reklamy, afterword, zapowiedzi), napraw artefakty ekstrakcji,
   znormalizuj nagłówki do `CHAPTER X. NAME.` i dopilnuj terminalnej interpunkcji
   (`.`, `?`, `!`, `…`) w każdym zdaniu. **Nie** rozwiązuj `???`.
3. **Spłaszczenie**:
   `python3 tools/plain_sentences.py "<stem>.txt" "<stem>-plain.txt"`
   (usuwa etykiety `Name: [...]`/`???: [...]`, nawiasy `[ ]`, tagi `<<...>>`,
   zamienia **wszystkie** nawiasy kątowe `<...>` na `(...)`, dzieli narrację
   i dialog na zdania — jedno na linię, a domyślnie wstawia **pustą linię po
   każdej linii** (linijka–odstęp–linijka; `--compact` wyłącza);
   **każda kwestia mówiona jest domyślnie w cudzysłowach `“...”`**
   (`--no-quotes` wyłącza); dopełnia interpunkcję).
4. **Bramka (obowiązkowa)**:
   `python3 tools/plain_sentences.py --check "<stem>-plain.txt"` musi dać `PASS`.
   Kontrolnie: 0 labeli, 0 `???`, 0 `[`, 0 `<`/`>`.
5. **Statystyki**: `python3 tools/log_stats.py <slug> --step to-plain-txt-only ...`.

Nie prezentuj wyniku bez `PASS`. Zakończ obowiązkową **tabelą** podsumowania
(bloki/zdania/dialogi/nagłówki, wynik `--check`, braki, wiersz w `stats.md`).

Jeśli `$1` jest pusty, zapytaj użytkownika, którą książkę (PDF/EPUB) przetworzyć.
