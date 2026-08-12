"""A dictionary that knows about inflected forms.

macOS ships `/usr/share/dict/words` (Webster's Second), which lists **base forms only**:
`exist` but not `existing`, `customer` but not `customers`. That gap is not academic. Two
tools here decide whether a token is an ordinary English word, and without inflections
they both misjudge exactly the tokens that matter most:

  * `tier_pages.py` scores a page by the share of its tokens that are real words. A page
    of clean printed prose is full of participles and plurals, so its score comes out
    lower than it should and the page risks being classified as garbled handwriting.
  * `name_filter.py` looks for tokens *close to* a real word as evidence of a mangled
    word. `EXISING` is a garbling of `existing` — but with `existing` absent from the
    dictionary there is nothing for it to be close to, and it survives as a "name".

So the vocabulary is expanded once, here, with the regular English endings. This is
deliberately crude: no irregular verbs, no stemmer, no dependency. It closes the gap
that actually bites without pretending to be a morphology engine.
"""
import os
import sys

WORDS = "/usr/share/dict/words"


def load(path=WORDS, inflect=True):
    """The dictionary as a set of lowercase words, optionally with regular inflections."""
    if not os.path.exists(path):
        sys.exit(f"no dictionary at {path}; this needs one "
                 "(macOS ships it; on Debian install `wamerican`)")
    with open(path, encoding="utf-8", errors="ignore") as fh:
        base = {w.strip().lower() for w in fh if w.strip()}
    if not inflect:
        return base

    out = set(base)
    for w in base:
        if len(w) < 3:
            continue
        out.add(w + "s")
        out.add(w + "ed")
        out.add(w + "ing")
        if w.endswith(("s", "x", "z", "ch", "sh")):
            out.add(w + "es")
        if w.endswith("e"):
            out.add(w[:-1] + "ing")
            out.add(w + "d")
        if w.endswith("y") and len(w) > 3 and w[-2] not in "aeiou":
            out.add(w[:-1] + "ies")
            out.add(w[:-1] + "ied")
    return out
