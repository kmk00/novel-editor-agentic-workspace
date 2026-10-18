#!/usr/bin/env python3
"""
resolve_speakers_llm.py — assist `ln-speaker-resolution` on large PDF-derived
books where every dialogue line is `???`.

For each `???: [...]` line it asks the local Ollama model who is speaking,
using the surrounding context and the per-series cast manifest. A resolution is
accepted ONLY when the model is confident AND the answer maps to a cast entry
via its aliases AND the cited evidence actually appears in the context window.
Everything else stays `???` (the skill's 100%-certainty rule).

Output keeps every line byte-identical except the `???:` speaker label, so it
passes `tools/resolve_names.py --check`.

Usage:
  python3 tools/resolve_speakers_llm.py <chapter.txt> [--cast characters.yaml]
      [--out FILE] [--model NAME] [--context N] [--limit N] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "huihui_ai/gemma-4-abliterated:26b"

DIALOGUE_RE = re.compile(r"^(\s*)([^:\[\]]+?)(\s*):\s*\[(.*)\](\s*)$")

# An explicit attribution needs a speech verb near the name.
SPEECH_VERB_RE = re.compile(
    r"\b(said|says|say|replied|replies|asked|asks|answered|answers|responded|"
    r"mumbled|mumbles|muttered|mutters|murmured|murmurs|whispered|whispers|"
    r"shouted|shouts|yelled|yells|called|calls|continued|continues|added|adds|"
    r"began to speak|begins to speak|began speaking|began talking|"
    r"retorted|retorts|complained|complains|sighed|sighs|"
    r"exclaimed|exclaims|remarked|remarks|noted|notes|snapped|snaps|"
    r"declared|declares|admitted|admits|agreed|agrees|warned|warns|"
    r"teased|teases|joked|jokes|chuckled|chuckles|laughed|laughs|"
    r"insisted|insists|repeated|repeats|went on|cut in|chimed in)\b",
    re.IGNORECASE,
)


def has_attribution(text: str, canonical: str, alias_map: dict[str, str]) -> bool:
    """True if a *narration* line names `canonical` (or an alias, not in
    possessive form) next to a speech verb."""
    if not text or DIALOGUE_RE.match(text):
        return False
    if not SPEECH_VERB_RE.search(text):
        return False
    variants = {canonical} | {a for a, c in alias_map.items() if c == canonical}
    for v in variants:
        # reject possessives (Yakishio's grandmother) and partial words
        if re.search(r"(?<![\w'’])" + re.escape(v) + r"(?![\w'’])", text, re.IGNORECASE):
            return True
    return False

SCHEMA = {
    "type": "object",
    "properties": {
        "speaker": {"type": "string"},
        "evidence": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "low"]},
    },
    "required": ["speaker", "evidence", "confidence"],
}

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "certain": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["certain", "reason"],
}

VERIFY_SYSTEM = """You audit a proposed speaker attribution in a light novel.

You get the CAST, the CONTEXT (the TARGET line marked `>>>`) and a PROPOSED \
speaker. Decide whether it is CERTAIN that the proposed character speaks the \
TARGET line.

Be strict. Answer `certain: false` when:
- the proposed speaker was the previous speaker and the target is a reply from \
someone else (dialogue usually alternates),
- the proposed character is only mentioned, described, looked at, or addressed \
in the target line,
- the target is narration, an internal thought, or a text/chat message,
- the context is ambiguous or you are relying on tone/guesswork.

Only `certain: true` when the context explicitly shows that character speaking \
(a speech-verb attribution) or replying in an unambiguous exchange.

Return ONLY JSON matching the schema."""

SYSTEM = """You resolve anonymous speaker labels (`???`) in a light-novel chapter.

You get a CAST list (canonical names + aliases + voice register), a CONTEXT window, \
and one TARGET dialogue line marked `>>>`.

Rules:
- Answer with a canonical cast name ONLY when the context explicitly attributes the \
line with a speech verb: narration like "X said/replied/asked/mumbled/...", a \
narration sentence naming X as the one who spoke, or a character addressing X by \
name in the immediately adjacent line.
- A name merely mentioned nearby (described, looked at, reacted) is NOT evidence.
- If the speaker is only inferable from tone, alternation, or general knowledge, \
answer `UNKNOWN` with confidence `low`.
- `evidence` must be a short verbatim quote from the context that contains the \
speech verb and the name (or "none" when UNKNOWN).
- Never invent a name that is not in the CAST.

Return ONLY JSON matching the schema."""


def call_ollama(model: str, messages: list[dict], timeout: int = 300,
                schema: dict | None = None) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": schema or SCHEMA,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return json.loads(data.get("message", {}).get("content", ""))


def load_cast(cast_path: Path) -> tuple[list[str], dict[str, str]]:
    """Return (canonical names, alias_lower -> canonical)."""
    names: list[str] = []
    alias_map: dict[str, str] = {}
    current = None
    for line in cast_path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^  ([A-Za-z][\w'\-]*)\s*:\s*$", line)
        if m:
            current = m.group(1)
            names.append(current)
            alias_map[current.lower()] = current
            continue
        m = re.match(r"^\s+aliases\s*:\s*\[(.*?)\]\s*$", line)
        if m and current:
            for a in m.group(1).split(","):
                a = a.strip().strip('"').strip("'")
                if a:
                    alias_map[a.lower()] = current
    return names, alias_map


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapter")
    ap.add_argument("--cast", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--context", type=int, default=5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    src = Path(args.chapter)
    out_path = Path(args.out) if args.out else src.with_name(src.stem + "-resolved.txt")
    cache_path = out_path.with_suffix(".speaker-cache.json")
    vcache_path = out_path.with_suffix(".speaker-verify-cache.json")
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except json.JSONDecodeError:
        cache = {}
    try:
        vcache = json.loads(vcache_path.read_text(encoding="utf-8")) if vcache_path.exists() else {}
    except json.JSONDecodeError:
        vcache = {}

    cast_path = Path(args.cast) if args.cast else src.parent / "characters.yaml"
    names, alias_map = load_cast(cast_path)
    cast_block = "\n".join(f"- {n}" for n in names)

    lines = src.read_text(encoding="utf-8").split("\n")
    out_lines: list[str] = []
    stats = {"resolved": 0, "left": 0, "rejected": 0, "cached": 0, "errors": 0}
    for idx, line in enumerate(lines):
        m = DIALOGUE_RE.match(line)
        if not m or m.group(2).strip() != "???":
            out_lines.append(line)
            continue
        if args.limit and stats["resolved"] >= args.limit:
            out_lines.append(line)
            stats["left"] += 1
            continue

        key = str(idx)
        if key in cache:
            answer = cache[key]
            stats["cached"] += 1
        else:
            before = [l.strip() for l in lines[max(0, idx - args.context):idx] if l.strip()]
            after = [l.strip() for l in lines[idx + 1: idx + 1 + args.context] if l.strip()]
            ctx = "\n".join([f"   {l}" for l in before] +
                            [f">>> {line.strip()}"] +
                            [f"   {l}" for l in after])
            user = (f"CAST:\n{cast_block}\n\nCONTEXT:\n{ctx}\n\n"
                    f"Who speaks the TARGET line? Answer JSON.")
            try:
                answer = call_ollama(args.model, [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ])
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                answer = {"speaker": "UNKNOWN", "evidence": str(exc), "confidence": "low"}
                stats["errors"] += 1
            cache[key] = answer
            if stats["resolved"] % 25 == 0:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

        speaker = (answer.get("speaker") or "").strip()
        evidence = (answer.get("evidence") or "").strip()
        confidence = (answer.get("confidence") or "").strip().lower()
        canonical = alias_map.get(speaker.lower())

        window = "\n".join(lines[max(0, idx - args.context): idx + 1 + args.context])
        # explicit attribution must come from the model's own cited evidence,
        # which must be verbatim in the context window (anti-hallucination).
        ev_norm = " ".join(evidence.split()).lower()
        target_norm = " ".join(line.split()).lower()
        evidence_in_window = bool(ev_norm) and ev_norm in " ".join(window.split()).lower()
        evidence_not_target = bool(ev_norm) and ev_norm not in target_norm
        # an explicit name+speech-verb attribution in the window is the
        # strongest signal; otherwise require the name to be present in the
        # window and the cited evidence to be real (verified separately).
        window_lines = lines[max(0, idx - args.context): idx + 1 + args.context]
        attribution_ok = bool(canonical) and any(
            has_attribution(l, canonical, alias_map) for l in window_lines)
        name_in_window = bool(canonical) and any(
            re.search(r"(?<![\w'’])" + re.escape(v) + r"(?![\w'’])", l, re.IGNORECASE)
            for l in window_lines
            for v in ({canonical} | {a for a, c in alias_map.items() if c == canonical}))
        evidence_ok = bool(canonical) and evidence_in_window and evidence_not_target \
            and (attribution_ok or name_in_window)

        if canonical and confidence == "high" and evidence_ok:
            vkey = str(idx)
            if vkey in vcache:
                verdict = vcache[vkey]
            else:
                before = [l.strip() for l in lines[max(0, idx - args.context):idx] if l.strip()]
                after = [l.strip() for l in lines[idx + 1: idx + 1 + args.context] if l.strip()]
                ctx = "\n".join([f"   {l}" for l in before] +
                                [f">>> {line.strip()}"] +
                                [f"   {l}" for l in after])
                vuser = (f"CAST:\n{cast_block}\n\nCONTEXT:\n{ctx}\n\n"
                         f"PROPOSED SPEAKER: {canonical}\nIs it certain?")
                try:
                    verdict = call_ollama(args.model, [
                        {"role": "system", "content": VERIFY_SYSTEM},
                        {"role": "user", "content": vuser},
                    ], schema=VERIFY_SCHEMA)
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
                    verdict = {"certain": False, "reason": "error"}
                vcache[vkey] = verdict
                if len(vcache) % 25 == 0:
                    vcache_path.write_text(json.dumps(vcache, ensure_ascii=False),
                                           encoding="utf-8")
            if verdict.get("certain") is True:
                out_lines.append(line.replace("???", canonical, 1))
                stats["resolved"] += 1
                if args.verbose:
                    print(f"  line {idx+1}: ??? -> {canonical}  ({evidence[:60]})")
            else:
                out_lines.append(line)
                stats["rejected"] += 1
        else:
            out_lines.append(line)
            stats["left"] += 1

    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    vcache_path.write_text(json.dumps(vcache, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"resolved: {stats['resolved']} | left ???: {stats['left']} | "
          f"rejected by verifier: {stats['rejected']} | from cache: {stats['cached']} | "
          f"errors: {stats['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
