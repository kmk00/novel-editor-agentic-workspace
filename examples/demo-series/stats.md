# Stats — demo-series

One log for the whole series: every skill run, per file. Columns:

- **Timestamp** — when the run finished.
- **Step** — the skill / pipeline stage (e.g. `speaker-resolution`, `emotion-tagging`).
- **File** — the artifact produced (path relative to the repo root).
- **Duration** — wall-clock time (`12.3s`, `4m32s`, `1h02m`).
- **Resources** — model / tool / agent used.
- **Result** — `PASS`, `OK`, `DONE`, `FAIL`, …
- **Notes** — counts, decisions, caveats.

| Timestamp | Step | File | Duration | Resources | Result | Notes |
|---|---|---|---|---|---|---|
| 2026-10-18 12:16:11 | extract | examples/demo-series/VOL01/DemoBook.txt | 0.2s | agent (hand-written demo) | DONE | 8 blocks; 4 dialogue lines anonymized to ??? |
| 2026-10-18 12:16:11 | speaker-resolution | examples/demo-series/VOL01/DemoBook-resolved.txt | 0.4s | agent (no local model) | PASS | resolved 3 / left 0 / total 16 lines |
| 2026-10-18 12:16:11 | voice-casting | examples/demo-series/characters.yaml | 0.1s | tools/voice_casting.py | PASS | 2 speakers cast / 0 missing |
| 2026-10-18 12:16:11 | emotion-tagging | examples/demo-series/VOL01/DemoBook-resolved-tagged.txt | 0.1s | hand-written demo | DONE | 4 tagged, 0 fallbacks (demo) |
| 2026-10-18 12:16:11 | coverage-check | examples/demo-series/VOL01/DemoBook-resolved-tagged.txt | 0.1s | tools/check_coverage.py | PASS | 15 readable lines, 0 deleted |
| 2026-10-18 12:16:11 | plain-copy | examples/demo-series/VOL01/DemoBook-plain.txt | 0.1s | tools/plain_text.py | DONE | 0 labels, 0 tags, 0 angle brackets |
