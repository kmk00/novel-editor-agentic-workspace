#!/usr/bin/env python3
"""Kontrola i naprawa błędnych chunków tłumaczenia translatora ln-translator.

Chunki wadliwe są oznaczane w pliku markerem:
    [BŁĄD TŁUMACZENIA — CHUNK <N>]

Tryby:
  detect  <plik_wyjsciowy>         lista zepsutych chunków: EN↔PL linie/znaki + fragmenty
  verify  <plik_wyjsciowy>         bramka jakości — czy zostały markery, czy naprawione chunki
                                   zgadzają się z EN pod względem liczby linii (exit 1 = problemy)
  stitch  <plik_wyjsciowy> [--report <plik.md>]
                                   zszywa naprawione chunki z powrotem do <plik_wyjsciowy>,
                                   czyści failed_chunks w session.json i generuje raport .md

Układ katalogów (taki sam jak w translator.py):
  <katalog>/<stem>_chunks/chunk_NNN.txt        → PL (niektóre z markerem)
  <katalog>/<stem>_chunks/original/chunk_NNN.txt → oryginał EN
  <katalog>/<stem>_chunks/session.json         → metadane (overlap, failed_chunks)
"""
import json
import re
import sys
from pathlib import Path

MARKER = "[BŁĄD TŁUMACZENIA — CHUNK"
MARKER_RE = re.compile(r"\[BŁĄD TŁUMACZENIA — CHUNK (\d+)\]")
CHUNK_RE = re.compile(r"chunk_(\d{3})\.txt")

DEFAULT_REPORT = "_FIX_raport.md"


# ── pomocnicze ───────────────────────────────────────────────────────────────
def find_chunks_dir(output_path: str) -> Path | None:
    out = Path(output_path)
    for d in (out.parent / "chunks", out.parent / f"{out.stem}_chunks"):
        if (d / "session.json").exists():
            return d
    return None


def load_session(output_path: str) -> dict | None:
    chunks_dir = find_chunks_dir(output_path)
    if not chunks_dir:
        return None
    return json.loads((chunks_dir / "session.json").read_text(encoding="utf-8"))


def nonzero_lines(text: str) -> int:
    return len([l for l in text.split("\n") if l.strip()])


def strip_chunk_marker(text: str) -> str:
    """Usuwa linię z markerem [BŁĄD TŁUMACZENIA — CHUNK N], jeśli jest."""
    lines = text.split("\n")
    out = [l for l in lines if not MARKER_RE.search(l)]
    return "\n".join(out).strip()


def read_chunk(chunks_dir: Path, num: int, subdir: str = "") -> str:
    p = chunks_dir
    if subdir:
        p = p / subdir
    f = p / f"chunk_{num:03d}.txt"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def iter_marked(chunks_dir: Path, total: int | None = None):
    """Zwraca posortowane numery chunków zawierających marker."""
    found = []
    if total is None:
        files = sorted(chunks_dir.glob("chunk_*.txt"))
    else:
        files = [chunks_dir / f"chunk_{i:03d}.txt" for i in range(1, total + 1)]
    for f in files:
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8")
        m = MARKER_RE.search(txt)
        if m:
            found.append(int(m.group(1)))
    return sorted(set(found))


def num_from_filename(f: Path) -> int:
    m = CHUNK_RE.search(f.name)
    return int(m.group(1)) if m else -1


def en_pl_pair(chunks_dir: Path, num: int) -> tuple[str, str]:
    en = strip_bom(read_chunk(chunks_dir, num, "original"))
    pl = read_chunk(chunks_dir, num)
    pl_clean = strip_chunk_marker(pl)
    return en, pl_clean


def strip_bom(s: str) -> str:
    return s.lstrip("\ufeff")


# ── detect ───────────────────────────────────────────────────────────────────
def cmd_detect(output_path: str) -> int:
    chunks_dir = find_chunks_dir(output_path)
    if not chunks_dir:
        print(f"✗ Brak katalogu chunków dla: {output_path}")
        return 1
    total = (load_session(output_path) or {}).get("total_chunks")
    marked = iter_marked(chunks_dir, total)

    if not marked:
        print("✓ Brak chunków z markerem [BŁĄD TŁUMACZENIA].")
        return 0

    print(f"Znaleziono {len(marked)} wadliwych chunków:\n")
    for num in marked:
        en, pl = en_pl_pair(chunks_dir, num)
        en_l, pl_l = nonzero_lines(en), nonzero_lines(pl)
        pl_raw = read_chunk(chunks_dir, num)
        head_pl = " | ".join(pl_raw.strip().splitlines()[:3])
        head_en = " | ".join(en.strip().splitlines()[:3])
        print(f"── Chunk {num} ────────────────────────────────")
        print(f"  EN linie: {en_l:<4}  PL linie: {pl_l:<4}  (rozmiar PL: {trans_len(pl_raw)} zn.)")
        print(f"  PL ▶  {head_pl[:150]}")
        print(f"  EN ▶  {head_en[:150]}")
        if len(en) > 0 and pl_l > 0 and pl_l < en_l * 0.6:
            print(f"  ⚠ KRYTYCZNE ucięcie — PL ma tylko {pl_l}/{en_l} linii EN.")
        print()
    return 0


def trans_len(text: str) -> int:
    pl = strip_chunk_marker(text)
    return len(pl.strip())


# ── verify (bramka jakości) ──────────────────────────────────────────────────
def cmd_verify(output_path: str) -> int:
    chunks_dir = find_chunks_dir(output_path)
    if not chunks_dir:
        print(f"✗ Brak katalogu chunków dla: {output_path}")
        return 1
    session = load_session(output_path) or {}
    total = session.get("total_chunks")
    overlap = session.get("overlap", 0)

    marked = iter_marked(chunks_dir, total)
    problems = []

    if marked:
        problems.append(f"Jeszcze {len(marked)} chunków z markerem (nienaprawione): {marked}")

    # chunki z failed_chunks, które teraz nie mają markera — sprawdź zgodność z EN
    failed = [int(n) for n in session.get("failed_chunks", []) if str(n).isdigit()]
    for num in sorted(set(failed)):
        en, pl = en_pl_pair(chunks_dir, num)
        if not en:
            continue
        en_l, pl_l = nonzero_lines(en), nonzero_lines(pl)
        if pl_l != en_l:
            problems.append(
                f"Chunk {num}: nadal rozjazd linii — EN {en_l} ≠ PL {pl_l} "
                f"(może być jeszcze ucięty). Popraw i usuń marker.")
        elif trans_len_too_small(en, pl):
            problems.append(
                f"Chunk {num}: linie się zgadzają, ale PL podejrzanie krótki "
                f"({len(pl.strip())} zn. vs {len(en.strip())} zn. EN) — sprawdź treść.")

    if problems:
        print("PROBLEMY:")
        for p in problems:
            print("  •", p)
        return 1
    print("OK — wszystkie markery usunięte, naprawione chunki zgodne z EN.")
    return 0


def trans_len_too_small(en: str, pl: str) -> bool:
    le, lpl = len(en.strip()), len(pl.strip())
    if lpl == 0:
        return True
    return lpl < le * 0.5


# ── stitch ───────────────────────────────────────────────────────────────────
def cmd_stitch(output_path: str, report: str | None) -> int:
    chunks_dir = find_chunks_dir(output_path)
    if not chunks_dir:
        print(f"✗ Brak katalogu chunków dla: {output_path}")
        return 1
    session = load_session(output_path) or {}
    total = session.get("total_chunks")
    overlap = session.get("overlap", 0)
    out = Path(output_path)

    marked_before = set(iter_marked(chunks_dir, total))
    failed_orig = sorted(int(n) for n in (session or {}).get("failed_chunks", []) if str(n).isdigit())
    if marked_before:
        print(f"⚠ Uwaga: {len(marked_before)} chunków ma nadal marker: {sorted(marked_before)}")
        print("   Zostaną wstawione bez poprawy (z markerem). Użyj najpierw verify.")
    else:
        print(f"✓ 0 chunków z markerem — zszywam czysto.")

    parts = []
    ens = []
    for i in range(1, (total or 0) + 1):
        pl = strip_chunk_marker(read_chunk(chunks_dir, i))
        if not pl.strip():
            print(f"  • pusty chunk {i}, pomijam")
            continue
        parts.append(pl.strip())
        ens.append(read_chunk(chunks_dir, i, "original"))

    if not parts:
        print("✗ Brak chunków do zszycia.")
        return 1

    def stitch(parts, overlap, en_chunks=None):
        """Align PL 1:1 with the SOURCE lines; join pieces split by mid-line cuts."""
        if len(parts) == 1:
            return parts[0]
        if en_chunks and len(en_chunks) == len(parts):
            source = "".join(en_chunks)
            bounds, pos = [], 0
            for en in en_chunks[:-1]:
                pos += len(en)
                bounds.append(pos)
            pl_pieces = []
            for pl in parts:
                pl_pieces += [l for l in pl.strip("\n").split("\n") if l.strip()]
            out_lines, idx, line_start = [], 0, 0
            for line in source.split("\n"):
                line_end = line_start + len(line)
                if line.strip():
                    n = 1 + sum(1 for b in bounds if line_start < b < line_end)
                    out_lines.append(" ".join(p.strip() for p in pl_pieces[idx:idx + n]))
                    idx += n
                else:
                    out_lines.append("")
                line_start = line_end + 1
            return "\n".join(out_lines)
        return "\n".join(c.strip("\n") for c in parts)

    final = stitch(parts, overlap, ens)
    out.write_text(final, encoding="utf-8")
    print(f"✓ Zapisano: {out}  ({len(final):,} znaków)")

    # zaktualizuj session.json
    orig_out = None
    if session:
        orig_out = out.read_text(encoding="utf-8") if out.exists() else ""
        session["failed_chunks"] = []
        (chunks_dir / "session.json").write_text(
            json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
        print("✓ failed_chunks wyczyszczone w session.json")

    # raport .md — używamy listy sprzed wyczyszczenia
    if report is None:
        report = str(out.with_name(out.stem + DEFAULT_REPORT))
    write_report(report, out, chunks_dir, marked_before, failed_orig)
    print(f"✓ Raport: {report}")
    return 0


def write_report(report_path: str, out: Path, chunks_dir: Path, marked_before: set, failed_orig: list):
    ts = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nums = sorted(set(list(marked_before) + failed_orig))

    L = [f"# 📝 Raport naprawy błędnych chunków", f"", f"- **Plik wyjściowy:** `{out}`",
         f"- **Katalog chunków:** `{chunks_dir}`", f"- **Naprawiane chunki:** {len(nums)}",
         f"- **Czas:** {ts}", "", "---", ""]
    if not nums:
        L += ["Nie znaleziono żadnych oznaczonych chunków do naprawy.", ""]
    for num in nums:
        en, pl = en_pl_pair(chunks_dir, num)
        en_l, pl_l = nonzero_lines(en), nonzero_lines(pl)
        L += [f"## Chunk {num}", "", "| | Przed naprawą | Po naprawie |", "|---|---|---|",
              f"| Linie EN | {en_l} | {en_l} |",
              f"| Linie PL | — | {pl_l} |",
              f"| Znaki PL | — | {len(pl.strip())} |",
              "", "**Co poprawiono:** _wpisz tutaj opis poprawki (np. ucięcie o X linii, ...)_", "",
              "---", ""]
    Path(report_path).write_text("\n".join(L), encoding="utf-8")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cmd = args[0]
    if cmd == "detect":
        if len(args) < 2:
            print(__doc__); return 2
        return cmd_detect(args[1])
    if cmd == "verify":
        if len(args) < 2:
            print(__doc__); return 2
        return cmd_verify(args[1])
    if cmd == "stitch":
        if len(args) < 2:
            print(__doc__); return 2
        report = None
        if "--report" in args:
            report = args[args.index("--report") + 1]
        return cmd_stitch(args[1], report)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())