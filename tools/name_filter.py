#!/usr/bin/env python3
"""Tell a garbled ordinary word apart from a proper noun, in OCR output.

Mining names out of recognised handwriting, the obvious filter is a dictionary: drop
anything that is a real English word, keep the rest. It does not work. OCR mangles
ordinary words *out* of the dictionary — `Custoner`, `Produt`, `Seach`, `Strugth` — and
they then crowd out the actual names you were looking for.

The signal that works: a token one or two characters from a common word is a mangled
word. A name almost never is.

The dictionary must include inflected forms — see `lexicon.py`. Without them this
filter misses a whole class of garbling, since participles and plurals are absent from
the system word list.

Two things this deliberately does not do:

  * It does not apply below length 6. Short tokens carry too little signal, and the
    filter would eat real short names — a four-letter surname sits a hair from an
    ordinary word more often than not.
  * It does not exempt ALL-CAPS tokens. An earlier version did, on the theory that caps
    were a deliberate mark rather than a capitalised sentence start. But people write
    headings in caps, and the exemption flooded the results with SEARCH, PROJECT, USER
    and REPORT while burying every real name.

  usage:  name_filter.py <file.txt>       one token per line, or free text
          name_filter.py --demo
"""
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache

import lexicon

MIN_LEN = 6          # below this, too little signal to judge

# Where "close to a real word" becomes "is a mangled one". Measured, not guessed —
# against the sample in DEMO plus the wider run it came from:
#
#     garbled ordinary words   0.875 – 0.941
#     real product names       0.706 – 0.857
#
# The margin is 0.018 wide, which is thin. Raise this if real product names are being
# eaten; lower it if garbled words are surviving. Both failure modes are visible in
# `--demo`.
SIMILARITY = 0.87

# Inflected forms matter here: the system dictionary lists base forms only, so without
# them `EXISING` has no `existing` to be close to and survives as a false "name".
VOCAB = lexicon.load()

# Dictionary words indexed by (initial, length), so a token only ever compares against
# the few hundred words it could plausibly be a garbling of. OCR mangles the middle of
# a word far more often than it invents a new first letter.
BY_SHAPE = defaultdict(list)
for _w in VOCAB:
    if len(_w) >= 5:
        BY_SHAPE[(_w[0], len(_w))].append(_w)


@lru_cache(maxsize=None)
def mangled_english(token):
    """True if this looks like a garbled ordinary word rather than a name."""
    low = token.lower()
    if len(low) < MIN_LEN:
        return False
    if low.endswith("s") and low[:-1] in VOCAB:
        return True
    for length in (len(low) - 1, len(low), len(low) + 1):
        for cand in BY_SHAPE.get((low[0], length), ()):
            if SequenceMatcher(None, low, cand).ratio() >= SIMILARITY:
                return True
    return False


def is_name_candidate(token):
    """A token worth showing a human as a possible proper noun."""
    low = token.lower()
    if len(token) < 3:
        return False
    if low in VOCAB:
        return False
    return not mangled_english(token)


def classify(token):
    """The same decision as `is_name_candidate`, with the rejection reason kept.

    Three outcomes, not two. The middle one is why `lexicon.py` exists: `Customers`
    is a correctly spelled plural that the raw system dictionary does not list, and
    calling it garbled would be wrong for a different reason than calling it a name.
    """
    if len(token) < 3:
        return "too short"
    if token.lower() in VOCAB:
        return "ordinary word"
    if mangled_english(token):
        return "garbled word"
    return "name candidate"


TOKEN = re.compile(r"\b[A-Z][A-Za-z][A-Za-z'&.\-]{1,18}\b|\b[A-Z]{2,6}\b")

# Every token the raw system dictionary does not list, split by what it actually is.
# All are real OCR output except the product names, which are invented — the originals
# belonged to a former employer. They were chosen to sit in the same similarity band as
# the real ones (0.71–0.86) so the demo still shows a true margin rather than a
# flattering one.
DEMO = [
    # garblings, plus `Customers`: a correct plural that only the inflection fix recovers
    "Custoner", "Produt", "Strugth", "EXISING", "Customers", "Featur", "Reportng",
    # product names, acronyms, and a short name that MIN_LEN protects
    "Verilex", "Quantiva", "Pentavo", "Zylotech", "Coredyne", "Marbex",
    "EMEA", "APAC", "NPL", "Kira",
]


def main():
    if "--demo" in sys.argv:
        width = max(len(t) for t in DEMO)
        for t in DEMO:
            print(f"  {t:<{width}}  {classify(t)}")
        return

    if len(sys.argv) < 2:
        sys.exit(__doc__)

    text = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    seen, keep = set(), []
    for m in TOKEN.finditer(text):
        tok = m.group(0).strip(".-'")
        if tok.lower() in seen:
            continue
        seen.add(tok.lower())
        if is_name_candidate(tok):
            keep.append(tok)
    for t in sorted(keep):
        print(t)
    print(f"\n  {len(keep)} candidates from {len(seen)} distinct tokens",
          file=sys.stderr)


if __name__ == "__main__":
    main()
