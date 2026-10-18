#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inline emotion tagging for audiobook TTS via a LOCAL open-source LLM (Ollama).

Produces the canonical `Name: [<<tag>> speech]` format (see the
`ln-emotion-tagging` skill). The tag is ALWAYS in English and is a short
performance direction (delivery + audible traits [+ "as if ..."]), never a bare
emotion label like `<<fear>>`.

Pipeline per dialogue line:
  1. a light structured analysis by the local LLM (emotion, intensity, volume,
     pacing, texture, intent) + a proposed tag,
  2. deterministic validation (English only, <=1 comma, no banned sound-effect
     words, sane length) with an automatic fallback renderer if the model tag
     is invalid,
  3. text normalisation (leading/trailing dashes, stutters, terminal punctuation).

The LLM never edits the spoken text — only the tag is inserted.

Usage:
    python3 tools/emotion_tagger.py <chapter.txt> [--out FILE] [--model NAME]
                                    [--cast characters.yaml] [--context N]
                                    [--limit N] [--keep-stutters]

After writing the output run the mandatory gate:
    python3 tools/check_coverage.py <chapter.txt> <out>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_coverage import (  # noqa: E402
    DIALOGUE_RE,
    LEADING_DASH_RE,
    NON_WORD_RE,
    TRAILING_DASH_RE,
    is_banned,
    normalize_stutters,
)

OLLAMA_URL = "http://localhost:11434/api/chat"
# Best locally available model (26B gemma-4 abliterated) with reasoning disabled.
# Reasoning-capable models (gemma-4, qwen3) return EMPTY JSON while thinking, which
# forces the fallback renderer — always send "think": false for them.
DEFAULT_MODEL = "huihui_ai/gemma-4-abliterated:26b"

# ── structured output schema ------------------------------------------------
SCHEMA = {
    "type": "object",
    "properties": {
        "tag": {"type": "string"},
        "emotion": {"type": "string", "enum": [
            "neutral", "joy", "sadness", "anger", "fear", "surprise",
            "disgust", "embarrassment", "affection", "contempt",
            "determination", "confusion", "relief", "pain", "concern",
            "amusement", "pride", "nervousness", "sarcasm", "mockery",
            "exasperation", "resignation", "urgency", "doubt", "warmth"]},
        "intensity": {"type": "integer", "minimum": 1, "maximum": 5},
        "volume": {"type": "string", "enum": ["whisper", "soft", "normal", "raised", "loud", "shout"]},
        "pacing": {"type": "string", "enum": ["slow", "measured", "normal", "quick", "rushed", "halting"]},
        "texture": {"type": "string"},
        "intent": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["tag", "emotion", "volume", "pacing", "confidence"],
}

SYSTEM_PROMPT = """\
You are an audiobook voice director. For one spoken line you return a SHORT \
ENGLISH performance-direction tag describing HOW the line is delivered — never \
who the character is, never a bare emotion label.

The tag follows: delivery verb/adverb + concrete audible traits (volume, pacing, \
texture) + optional motivation.

HARD RULES:
- Write the tag in English ONLY. Never use any other language.
- One fragment, roughly 8-20 words, starting with a capital letter.
- At most ONE comma in the whole tag (usually only before an "as if ..." clause).
- Never use sound-effect or body-noise words: breath, breathing, sigh, gasp, \
pant, wheeze, moan, groan, sob, whimper, wail, sputter, choke, strangl(e), \
bark, growl, snarl, hiss, purr, howl, bleat.
- At most ONE texture word (e.g. strained, flat, warm, sharp, trembling).
- Do NOT mention the character's name or identity in the tag.
- If the speech text contains a written stutter (e.g. "A-are", "W-with"), \
begin the tag with "Stuttering" and keep it short: delivery + volume only, \
no "as if" clause. NEVER use the word "Stuttering" if the speech does not \
actually contain a written stutter.
- If the speech is a cut-off word/fragment (e.g. "Wha", "Stu-"), use an \
ultra-short plain tag (4-8 words), no "as if" clause.
- Infer from the line's content and punctuation, the character's register, and \
the surrounding context. Punctuation hints: "!?" shock, "..." hesitation or \
gloom, a dash interruption.

Good examples:
  <<Asking with sharp concern, brisk and pressing>>
  <<Saying it dryly and exasperated, holding her back>>
  <<Exclaiming brightly and eager, pushing for agreement>>
  <<Whispering very quietly and tensely, as if afraid of being overheard>>
  <<Snapping back sharply and loudly, as if fed up with the argument>>

Bad examples (never produce):
  <<fear>>  <<Angry>>  <<Nervously>>  <<Breath catching in a sigh>>

Return ONLY a JSON object matching the provided schema. The "tag" field is the \
English direction; the other fields are your short internal analysis."""


# ── Ollama call --------------------------------------------------------------
def call_ollama(model: str, messages: list[dict], timeout: int = 300,
                think: bool = False) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": SCHEMA,
        "think": think,
        "options": {"temperature": 0.3, "num_predict": 300},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data.get("message", {}).get("content", "")
    return json.loads(content)


# ── validation & fallback ---------------------------------------------------
PL_DIACRITICS_RE = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


def validate_tag(tag: str) -> str:
    """Return an error description, or '' when the tag is valid."""
    t = (tag or "").strip()
    if not t:
        return "empty"
    if PL_DIACRITICS_RE.search(t):
        return "not English (Polish characters)"
    if "<<" in t or ">>" in t or "\n" in t:
        return "contains tag delimiters"
    if t.count(",") > 1:
        return "more than one comma"
    words = re.findall(r"[A-Za-z']+", t)
    if len(words) < 4:
        return "too short (abstract label)"
    if len(words) > 24:
        return "too long"
    if not t[:1].isupper():
        return "does not start with a capital letter"
    banned = is_banned(t)
    if banned:
        return f"banned sound-effect word {banned!r}"
    if re.search(r"[^A-Za-z ,'\-]", t):
        return "contains unsafe characters"
    return ""


_EMO_ADV = {
    "fear": "frightened", "anger": "angrily", "joy": "happily",
    "sadness": "sadly", "surprise": "in surprise", "disgust": "with disgust",
    "embarrassment": "flustered", "affection": "warmly", "contempt": "with contempt",
    "determination": "firmly", "confusion": "confused", "relief": "with relief",
    "pain": "through pain", "neutral": "calmly", "concern": "with concern",
    "amusement": "amused", "pride": "proudly", "nervousness": "nervously",
    "sarcasm": "sarcastically", "mockery": "mockingly", "exasperation": "with exasperation",
    "resignation": "with resignation", "urgency": "urgently", "doubt": "doubtfully",
    "warmth": "warmly",
}
_VOL_ADV = {
    "whisper": "almost inaudibly", "soft": "softly", "normal": "at an even volume",
    "raised": "loudly", "loud": "very loudly", "shout": "shouting",
}
_PAC_ADV = {
    "slow": "slowly", "measured": "deliberately", "normal": "evenly",
    "quick": "quickly", "rushed": "rushing the words", "halting": "in a broken rhythm",
}
# short stutter-safe fragments
_VOL_W = {"whisper": "whispered", "soft": "soft", "normal": "steady",
          "raised": "raised", "loud": "loud", "shout": "shouted"}
_PAC_W = {"slow": "slow", "measured": "measured", "normal": "steady",
          "quick": "quick", "rushed": "rushed", "halting": "halting"}


def render_fallback(analysis: dict, intent_ok: bool = True) -> str:
    emo = str(analysis.get("emotion", "neutral")).lower()
    vol = str(analysis.get("volume", "normal")).lower()
    pac = str(analysis.get("pacing", "normal")).lower()
    if vol in ("loud", "shout"):
        lead = "Raising the voice"
    elif vol in ("whisper", "soft"):
        lead = "Saying it quietly"
    else:
        lead = "Saying it"
    mods = []
    if emo != "neutral":
        mods.append(_EMO_ADV.get(emo, "calmly"))
    p = _PAC_ADV.get(pac)
    if p and p != "evenly":
        mods.append(p)
    # join modifiers with "and" (never commas) so the tag has room for
    # exactly one comma before an optional "as if ..." clause
    tag = lead + (" " + " and ".join(mods) if mods else "")
    intent = str(analysis.get("intent", "")).strip().rstrip(".")
    if intent_ok and intent and len(intent.split()) <= 8 and not is_banned(intent) \
            and not PL_DIACRITICS_RE.search(intent):
        tag += f", as if {intent}"
    return tag


def render_stutter_tag(analysis: dict) -> str:
    vol = _VOL_W.get(str(analysis.get("volume", "normal")).lower(), "steady")
    pac = _PAC_W.get(str(analysis.get("pacing", "normal")).lower(), "steady")
    return f"Stuttering, {vol} and {pac}"


# ── per-line analysis --------------------------------------------------------
def build_messages(name: str, speech: str, before: list[str], after: list[str],
                   register: str | None, stutter: bool) -> list[dict]:
    ctx_before = "\n".join(f"- {b}" for b in before[-4:]) or "(none)"
    ctx_after = "\n".join(f"- {a}" for a in after[:3]) or "(none)"
    reg = f"\nCHARACTER REGISTER: {register}" if register else ""
    stut = "\nNOTE: the speech contains a written stutter." if stutter else ""
    user = (
        f"CHARACTER: {name}{reg}\n"
        f"SPEECH: {speech}{stut}\n\n"
        f"CONTEXT BEFORE:\n{ctx_before}\n\n"
        f"CONTEXT AFTER:\n{ctx_after}\n\n"
        "Return the JSON analysis with the English tag. Reply with JSON only."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def analyze_line(model, name, speech, before, after, register, stutter, verbose=False, cache=None,
                 think=False):
    """Return (tag, analysis, attempts, fallback_used)."""
    key = f"{name}\u241f{speech}"
    if cache is not None and key in cache:
        c = cache[key]
        return c["tag"], c.get("analysis", {}), c.get("attempts", 1), c.get("fallback", False)
    messages = build_messages(name, speech, before, after, register, stutter)
    last_err = ""
    analysis: dict = {}
    for attempt in range(1, 4):
        try:
            analysis = call_ollama(model, messages, think=think)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_err = f"ollama error: {exc}"
            if verbose:
                print(f"    ! {last_err}", file=sys.stderr)
            continue

        if stutter:
            tag = render_stutter_tag(analysis)
            if verbose:
                print(f"    stutter -> {tag}", file=sys.stderr)
            return tag, analysis, attempt, False

        tag = str(analysis.get("tag", "")).strip()
        err = validate_tag(tag)
        # a model-invented "Stuttering" on a line without one is a real error
        if not err and tag.lower().startswith("stuttering"):
            err = "Stuttering used on a line without a written stutter"
        if not err:
            if cache is not None:
                cache[key] = {"tag": tag, "analysis": analysis, "attempts": attempt, "fallback": False}
            return tag, analysis, attempt, False
        last_err = err
        if verbose:
            print(f"    ! invalid tag ({err}): {tag!r}", file=sys.stderr)
        # tell the model what was wrong and retry
        messages = messages + [
            {"role": "assistant", "content": json.dumps(analysis, ensure_ascii=False)},
            {"role": "user", "content":
                f"That tag was rejected: {err}. Rewrite it as a valid short English "
                "performance direction (8-20 words, at most one comma, no sound-effect words). "
                "Return JSON only."},
        ]

    fb = render_fallback(analysis)
    if verbose:
        print(f"    fallback -> {fb}  ({last_err})", file=sys.stderr)
    if cache is not None:
        cache[key] = {"tag": fb, "analysis": analysis, "attempts": 3, "fallback": True}
    return fb, analysis, 3, True


# ── text normalisation -------------------------------------------------------
def transform_speech(speech: str, normalize_stutter: bool = True) -> str:
    s = LEADING_DASH_RE.sub("", speech).strip()
    stripped = TRAILING_DASH_RE.sub("", s).rstrip()
    if stripped:
        s = stripped
    if normalize_stutter:
        s = normalize_stutters(s)
    if s and s[-1] not in ".!?…":
        s = s.rstrip() + "…"
    return s


# ── cast lookup --------------------------------------------------------------
def load_registers(cast_path: Path | None) -> dict[str, str]:
    """Very small characters.yaml reader: returns {name: register}."""
    if not cast_path or not cast_path.exists():
        return {}
    regs: dict[str, str] = {}
    current = None
    for line in cast_path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^  ([A-Za-z][\w'\-]*)\s*:\s*$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^\s+register\s*:\s*(.+?)\s*$", line)
        if m and current:
            regs[current] = m.group(1).strip().strip('"').strip("'")
    return regs


# ── main ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapter")
    ap.add_argument("--out")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--cast", help="characters.yaml for character registers")
    ap.add_argument("--context", type=int, default=3, help="context lines before/after")
    ap.add_argument("--limit", type=int, help="tag only the first N dialogue lines (test)")
    ap.add_argument("--keep-stutters", action="store_true",
                    help="do not normalise written stutters in the text")
    ap.add_argument("--think", action="store_true",
                    help="allow model reasoning (default off; reasoning models otherwise return empty JSON)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    src = Path(args.chapter)
    out_path = Path(args.out) if args.out else src.with_name(src.stem + "-tagged.txt")
    cache_path = out_path.with_suffix(".cache.json")
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except json.JSONDecodeError:
        cache = {}
    lines = src.read_text(encoding="utf-8").split("\n")

    registers = load_registers(Path(args.cast) if args.cast else
                               src.parent / "characters.yaml")
    registers_lc = {k.lower(): v for k, v in registers.items()}

    out_lines: list[str] = []
    stats = {"tagged": 0, "narration": 0, "removed": 0, "fallback": 0,
             "stutters": 0, "analysis": []}

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # symbol-only narration filler -> delete
        if stripped and not NON_WORD_RE.search(stripped):
            stats["removed"] += 1
            continue

        m = DIALOGUE_RE.match(line)
        if not m:
            out_lines.append(line)
            if stripped:
                stats["narration"] += 1
            continue

        indent, name, sp1, speech, suffix = m.groups()

        # dash-only / empty dialogue -> delete
        if not TRAILING_DASH_RE.sub("", LEADING_DASH_RE.sub("", speech)).strip():
            stats["removed"] += 1
            continue

        if args.limit and stats["tagged"] >= args.limit:
            out_lines.append(line)
            stats["narration"] += 1 if stripped else 0
            continue

        before = [l.strip() for l in lines[max(0, idx - args.context):idx] if l.strip()]
        after = [l.strip() for l in lines[idx + 1: idx + 1 + args.context] if l.strip()]
        register = registers_lc.get(name.strip().lower())

        stutter = (not args.keep_stutters) and (normalize_stutters(speech) != speech)
        if stutter:
            stats["stutters"] += 1

        tag, analysis, attempts, fb = analyze_line(
            args.model, name.strip(), speech, before, after, register, stutter,
            verbose=args.verbose, cache=cache, think=args.think)
        if fb:
            stats["fallback"] += 1

        new_speech = transform_speech(speech, normalize_stutter=not args.keep_stutters)
        out_lines.append(f"{indent}{name.strip()}: [<<{tag}>> {new_speech}]{suffix}")

        stats["tagged"] += 1
        stats["analysis"].append((name.strip(), tag, attempts, fb))
        print(f"  [{stats['tagged']:>3}] {name.strip()}: <<{tag}>>", file=sys.stderr)
        # crash-safe: persist the cache periodically so a long run can resume
        if stats["tagged"] % 10 == 0:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=0),
                                  encoding="utf-8")

    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")

    # ── summary table ──
    print()
    print(f"✅ Zapisano: {out_path}")
    print(f"   model: {args.model} | ctx: ±{args.context} | "
          f"tagów: {stats['tagged']} | narracja: {stats['narration']} | "
          f"usunięte (nieczytelne): {stats['removed']} | "
          f"fallback: {stats['fallback']} | stutter: {stats['stutters']}")
    print()
    print("| # | Postać | Tag (EN) | Prób | Fallback |")
    print("|---|--------|----------|------|----------|")
    for i, (name, tag, attempts, fb) in enumerate(stats["analysis"], 1):
        print(f"| {i} | {name} | `<<{tag}>>` | {attempts} | {'tak' if fb else '—'} |")
    print()
    print(f"Bramka: python3 tools/check_coverage.py {src} {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
