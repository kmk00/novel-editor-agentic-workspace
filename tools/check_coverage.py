#!/usr/bin/env python3
"""Tagged-chapter coverage check (NOVEL EDITOR).

Verifies that the emotion-tagged file preserves EVERY readable line of the original
chapter: no readable line deleted, no line added, and no dialogue text altered beyond
the allowed transformations:
  - tag insertion right after the opening '[',
  - removal of leading '―' dashes before real speech,
  - removal of trailing '―' dashes with a compensating '…'/'.' appended,
  - a trailing '…'/'.' appended to complete a cut-off line,
  - a written stutter ('A-are', 'W-with') normalized to the full word ('Are', 'With')
    while the hesitation moves into the tag ('<<Stuttering>>').

UNREADABLE lines of the original — dialogue lines whose speech is dashes-only or empty
(`Name: [――――]`) and symbol-only narration filler (`――.`, dot runs, `△▼△▼△▼△`) — are
intentionally ABSENT from the tagged file; the checker skips them and does not count
their absence as deletion.

Additionally checks tag placement, tag-only lines, untouched dash-only /
symbol-only lines, narration purity, end punctuation, and banned
sound-effect words inside tags.

Usage:
    python3 check_coverage.py <original-file> <tagged-file>

Exit codes: 0 = PASS, 1 = FAIL, 2 = usage error.
"""
import re
import sys

DASHES = '―—–‒'
TAG_RE = re.compile(r'<<[^<>]*>>\s*')
DIALOGUE_RE = re.compile(r'^(\s*)([^:\[\]]+)(\s*):\s*\[(.*)\](\s*)$')
LEADING_DASH_RE = re.compile(r'^[' + DASHES + r']+\s*')
TRAILING_DASH_RE = re.compile(r'\s*[' + DASHES + r']+$')
END_PUNCT_RE = re.compile(r'(?:\.|\!|\?|\.\.\.|…|\!{1,2}|\?{1,2})\s*$')
SYMBOL_ONLY_RE = re.compile(r'^[\s' + DASHES + r'・.…‥△▼◆※~〜*\-—–―]*$')
# A line is "dash-only" if it has no letters/digits at all
NON_WORD_RE = re.compile(r'[\w\d]', re.UNICODE)

# Banned sound-effect / vocal-noise words in tags (English + Polish).
# Matching is case-insensitive on lowercase stems.
BANNED_STEMS = [
    # breath / sigh family
    'breath', 'sigh', 'exhal', 'inhal', 'gasp', 'pant', 'wheez', 'huff',
    'westchn', 'wzdych', 'oddech', 'dyszą', 'dysza', 'dysze',
    # vocal-noise family
    'moan', 'groan', 'sob', 'whimper', 'wail', 'sputter', 'choked', 'choking',
    'strangled', 'strangling', 'jęk', 'szloch', 'charcz', 'płacz',
    # animal / onomatopoeia family
    'bark', 'growl', 'snarl', 'hiss', 'purr', 'howl', 'bleat',
    'szczeka', 'warkn', 'sycz', 'wycie', 'beczę',
    # NOTE: 'stutter'/'stammer' are NOT banned: a written stutter ('A-are') is
    # normalized to the full word in the text and the hesitation is directed via
    # a short '<<Stuttering>>' tag (see the emotions skill, rule 7).
]

SAFE_EXCEPTIONS = [
    # words containing banned stems as substrings but perfectly safe
    'wearily', 'sharply', 'crisp', 'whisper', 'whispered', 'whispering',
    'ship', 'equipment', 'history', 'sight', 'slight', 'sunlight', 'insight',
]


def is_banned(tag_text: str) -> str:
    """Return the banned stem found in tag_text, or ''. False positives
    inside SAFE_EXCEPTIONS are ignored (whole-word match on stems like
    'sob'/'bark' is enforced via word-boundary-ish check)."""
    low = tag_text.lower()
    for safe in SAFE_EXCEPTIONS:
        low = low.replace(safe, '#')
    for stem in BANNED_STEMS:
        if stem in low:
            # short stems need a word boundary to avoid false hits
            if len(stem) <= 4:
                if re.search(r'\b' + re.escape(stem), low):
                    return stem
            else:
                return stem
    return ''


def strip_tags(line: str) -> str:
    return TAG_RE.sub('', line)


# A written stutter: single letter (any case), hyphen, then a word of >=2 letters
# whose FIRST letter repeats the letter before the hyphen (case-insensitive).
# Matches 'A-are', 'W-with', 'Z-zaraz' but NOT 'T-shirt', 'e-mail', 'co-op'.
_STUTTER_RE = re.compile(
    r'\b([A-Za-z\u00C0-\u024F])-(?![A-Za-z\u00C0-\u024F]*-)([A-Za-z\u00C0-\u024F]{2,})\b')


def normalize_stutters(text: str) -> str:
    """Collapse written stutters ('A-are' -> 'Are' keeps the second part's case)."""
    def repl(m):
        first, second = m.group(1), m.group(2)
        if second[0].lower() == first.lower():
            if first.isupper() and second[0].islower():
                return second[0].upper() + second[1:]
            return second
        return m.group(0)
    return _STUTTER_RE.sub(repl, text)


def allowed_speech_variants(speech: str):
    """All allowed forms the tagged speech text may take for a given
    original speech text."""
    lead_stripped = LEADING_DASH_RE.sub('', speech)
    trail_stripped = TRAILING_DASH_RE.sub('', lead_stripped).rstrip()
    both_stripped = TRAILING_DASH_RE.sub('', speech).rstrip()
    variants = set()
    for base in (speech, lead_stripped, trail_stripped, both_stripped):
        for b in (base, normalize_stutters(base)):
            variants.add(b)
            variants.add(b + '…')
            variants.add(b + '.')
            variants.add(b + '….')
            variants.add(b + '……')
    return variants


def speech_is_dashes_or_empty(speech: str) -> bool:
    return not NON_WORD_RE.search(speech)


def is_unreadable_orig(line: str) -> bool:
    """True for original lines that the tagging skill DELETES from the
    output: symbol-only narration lines and dash-only/empty dialogue lines."""
    m = DIALOGUE_RE.match(line)
    if m:
        return speech_is_dashes_or_empty(m.group(4))
    if not line.strip():
        return False  # blank lines are kept
    return not NON_WORD_RE.search(line)


def collapse_blanks(lines):
    """Collapse runs of blank lines to a single blank; strip lead/trail."""
    out, prev_blank = [], False
    for l in lines:
        blank = not l.strip()
        if blank and prev_blank:
            continue
        out.append(l)
        prev_blank = blank
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def check(orig_path: str, tagged_path: str):
    with open(orig_path, encoding='utf-8') as f:
        orig_all = f.read().splitlines()
    with open(tagged_path, encoding='utf-8') as f:
        tagged_all = f.read().splitlines()

    n_removed = 0
    orig = []
    for a in orig_all:
        if is_unreadable_orig(a):
            n_removed += 1
        else:
            orig.append(a)
    orig = collapse_blanks(orig)
    tagged = collapse_blanks(tagged_all)

    errors = []
    n_tagged = 0
    n_untouched = 0

    if len(orig) != len(tagged):
        errors.append(
            f"LINE COUNT MISMATCH: readable original={len(orig)}, tagged={len(tagged)} "
            f"(no readable line may ever be deleted or added)")

    for i, (a, b) in enumerate(zip(orig, tagged), 1):
        m_a = DIALOGUE_RE.match(a)
        orig_speech = m_a.group(4) if m_a else None

        if a == b:
            n_untouched += 1
            if orig_speech is not None and not speech_is_dashes_or_empty(orig_speech):
                errors.append(
                    f"line {i}: dialogue line with real speech but NO emotion tag:\n  {b}")
            continue

        has_tag = '<<' in b and '>>' in b
        if not m_a:
            # narration line: must be byte-identical, never tagged
            if has_tag:
                errors.append(
                    f"line {i}: NARRATION line must never be tagged or modified:\n"
                    f"  original: {a}\n  tagged:   {b}")
            else:
                errors.append(
                    f"line {i}: NARRATION line must stay identical:\n"
                    f"  original: {a}\n  tagged:   {b}")
            continue

        # dialogue line
        stripped = strip_tags(b)
        m_b = DIALOGUE_RE.match(stripped)
        new_speech = m_b.group(4) if m_b else None

        # speaker rename: only allowed to resolve an original '???' speaker
        orig_speaker = m_a.group(2).strip()
        if m_b is not None and m_b.group(2).strip() != orig_speaker:
            if orig_speaker != '???':
                errors.append(
                    f"line {i}: SPEAKER RENAME of a known speaker is forbidden "
                    f"(only '???' may be resolved):\n"
                    f"  original: {a}\n  tagged:   {b}")
            elif not m_b.group(2).strip():
                errors.append(
                    f"line {i}: '???' speaker resolved to an EMPTY name:\n  tagged:   {b}")

        if new_speech is None or not matches_allowed(orig_speech, new_speech):
            errors.append(
                f"line {i}: TEXT DOES NOT MATCH any allowed transformation\n"
                f"  original: {a}\n  tagged:   {b}")
            continue

        if speech_is_dashes_or_empty(orig_speech):
            # dash-only / empty lines must have been removed from the output
            errors.append(
                f"line {i}: DASH-ONLY/EMPTY dialogue line must be DELETED "
                f"from the output, not kept or tagged:\n  original: {a}\n  tagged:   {b}")
            continue

        # real-speech dialogue line: tag required
        if not has_tag:
            errors.append(
                f"line {i}: dialogue line changed but NO tag inserted:\n"
                f"  original: {a}\n  tagged:   {b}")
            continue

        if b.count('<<') != 1 or b.count('>>') != 1:
            errors.append(
                f"line {i}: expected exactly ONE tag, found {b.count('<<')}: {b}")
            continue

        if not re.match(r'^\s*[^:\[\]]+\s*:\s*\[<<', b):
            errors.append(
                f"line {i}: tag not placed immediately after the opening '[': {b}")

        tag_m = re.match(r'^\s*[^:\[\]]+\s*:\s*\[(<<[^<>]*>>)\s*(.*)\]\s*$', b)
        if tag_m:
            tag_text = tag_m.group(1)[2:-2]
            speech_text = tag_m.group(2)
            bad = is_banned(tag_text)
            if bad:
                errors.append(
                    f"line {i}: tag contains BANNED sound-effect word '{bad}' "
                    f"(engine renders it as a noise, not speech): {b}")
            if not speech_text.strip():
                errors.append(
                    f"line {i}: TAG-ONLY line (no spoken text after the tag): {b}")
            elif not END_PUNCT_RE.search(speech_text.strip()):
                errors.append(
                    f"line {i}: spoken text does not end with punctuation "
                    f"(. ! ? … !? …): {b}")
        n_tagged += 1

    return errors, len(orig), n_tagged, n_untouched, n_removed


def matches_allowed(orig_speech: str, new_speech: str) -> bool:
    return new_speech in allowed_speech_variants(orig_speech)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: check_coverage.py <original-file> <tagged-file>")
        return 2
    orig_path, tagged_path = sys.argv[1], sys.argv[2]
    errors, total, n_tagged, n_untouched, n_removed = check(orig_path, tagged_path)
    print(f"Coverage check: {tagged_path}")
    print(f"  lines total:         {total} readable")
    print(f"  unreadable removed:  {n_removed} (dash-only/symbol-only, absent from output)")
    print(f"  tagged lines:        {n_tagged}")
    print(f"  untouched lines:     {n_untouched}")
    if errors:
        print(f"\nFAIL — {len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print("\nPASS — every readable line of the original is present, none deleted, "
          "all changes within the allowed set.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
