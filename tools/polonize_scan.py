#!/usr/bin/env python3
"""Scan a text file for candidate proper nouns (capitalized tokens) with counts.

Usage: scan.py <input.txt> [> candidates.txt]
Heuristic: words starting with an uppercase letter that are NOT at a sentence
start and are not known common words. Also catches ALL-CAPS tokens and tokens
with internal apostrophes/hyphens (O'Brien, Jean-Luc).
"""
import re
import sys
from collections import Counter

COMMON = {
    "I", "A", "An", "The", "But", "And", "Or", "Not", "No", "Yes", "It", "He",
    "She", "They", "We", "You", "His", "Her", "Their", "My", "Your", "Our",
    "This", "That", "These", "Those", "There", "Then", "When", "What", "Who",
    "Why", "How", "Where", "If", "In", "On", "At", "To", "Of", "For", "With",
    "From", "By", "As", "Was", "Were", "Is", "Are", "Be", "Been", "Had", "Has",
    "Have", "Do", "Does", "Did", "Will", "Would", "Could", "Should", "Can",
    "May", "Might", "Must", "Shall", "So", "Such", "One", "Two", "All", "Any",
    "Each", "Every", "Some", "Most", "More", "Less", "Now", "Here", "Just",
    "Even", "Still", "Also", "Once", "After", "Before", "While", "Because",
    "Chapter", "Interlude", "Epilogue", "Prologue", "Afterword",
}

TOKEN_RE = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż'’\-]*[a-ząćęłńóśźż]\b")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    counts = Counter()
    sentence_start = set()
    for sent in re.split(r"[.!?…]\s+", text):
        m = re.match(r"\s*([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż'’\-]*)", sent)
        if m:
            sentence_start.add(m.group(1))
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0)
        if tok in COMMON:
            continue
        counts[tok] += 1
    # candidates: not typical sentence-initial words, or appear 2+ times
    out = []
    for tok, c in counts.most_common():
        if c >= 2 or tok not in sentence_start:
            out.append((tok, c))
    for tok, c in sorted(out, key=lambda x: (-x[1], x[0])):
        print(f"{tok}\t{c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
