# Manifest obsady — `characters.yaml`

Cel: „przystosować light novel do postaci, jakie chcemy” — czyli ustalić **kto jest kim**
w tekście: kanoniczne etykiety mówców, ich aliasy (imiona, przezwiska, callsigny),
formy fonetyczne PL i sposób mówienia (`register`), który potem napędza tagi emocji.

**Głosy przypisujesz ręcznie w zewnętrznej aplikacji**
([Audiobook-maker-v0.1](https://github.com/kmk00/Audiobook-maker-v0.1)) — dlatego manifest
**nie zawiera** pól `voice` ani `sample`.

## Gdzie to leży

```
series/<slug>/characters.yaml      # JEDEN wspólny manifest na serię (szablon: docs/characters.template.yaml)
series/<slug>/polonize.yaml        # EN→PL formy fonetyczne (seed z pól `polonize`)
```

**Jeden plik na serię** (wszystkie tomy w `series/<slug>/` używają tego samego),
**zawsze po angielsku** — dotyczy każdego nowego manifestu generowanego dla kolejnej
książki. Wyjątek: pola `polonize`, które z definicji są polskimi formami wymowy.

Katalog `series/` startuje pusty — manifest powstaje przy pierwszej książce danej
serii (szablon: `docs/characters.template.yaml`, np. `series/moja-seria/characters.yaml`).

## Schemat

```yaml
series: <slug>

narrator:                      # głos narracji (nie jest mówcą `Imię: [...]`)
  register: "calm, literary, medium pace"

characters:
  Shin:
    polonize: Szin             # forma PL dla polskiego TTS (opcjonalna)
    aliases: [Undertaker, Reaper, Shinei]   # callsigny / przezwiska / warianty
    register: "cold, composed, clipped sentences"
```

- Klucz pod `characters:` = **dokładna etykieta mówcy z tekstu** (`Shin:`, `Yanami:`).
- `aliases` = każda inna etykieta odnosząca się do tej samej postaci.
- `polonize` = forma, którą TTS ma wymówić (spójna z `series/<slug>/polonize.yaml`).
- `register` = krótki opis barwy/tempa **po angielsku** — kontekst dla `ln-emotion-tagging`.
- **Brak** `voice`/`sample` — głosy dobierasz ręcznie poza repo.

## Weryfikacja obsady

```bash
python3 tools/voice_casting.py series/<slug>/VOLxx/<stem>-resolved.txt
```

Wypisuje: obsadzeni mówcy, nierozwiązani `???`, braki w manifeście. Kod wyjścia `1`,
gdy nazwany mówca nie ma wpisu (`--allow-missing` = tylko ostrzeżenie).

Procedura i checklista: skill **`ln-voice-casting`** (`.pi/skills/ln-voice-casting/SKILL.md`).

## Przepływ

1. `ln-speaker-resolution` — rozwiąż `???` (tylko przy 100% pewności); `aliases` z manifestu
   pomagają rozpoznać mówcę.
2. `ln-voice-casting` — uzupełnij `characters.yaml`, sprawdź `PASS`.
3. `ln-name-polonization` — zbuduj `polonize.yaml` z pól `polonize`.
4. `ln-emotion-tagging` — tagi dopasowane do `register` postaci.
5. `ln-tag-coverage-check` — bramka jakości.
6. `ln-plain-copy` — kopia do czytania.

Głosy (poza repo): przypisz postacie ręcznie w swojej aplikacji TTS, korzystając
z kluczy i `register` z manifestu. Referencyjna implementacja takiej aplikacji:
[**Audiobook-maker-v0.1**](https://github.com/kmk00/Audiobook-maker-v0.1) — aplikacja
webowa z podziałem na role (OmniVoice), keyowana właśnie po etykietach z manifestu.
