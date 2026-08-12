#!/usr/bin/env python3
"""Classify every page of a PDF into a cost tier before you spend anything on it.

Digitising a pile of handwritten notebooks, the expensive step is reading pages —
whether that means your own eyes or a large model. Most pages don't need it. A page
whose text already extracts cleanly needs nothing; a pasted screenshot is handled
accurately by a cheap local OCR pass; a blank page needs nothing at all.

Sorting pages into those buckets first cut one real job from 587 pages to 411. See
FINDINGS.md.

Three signals, all cheap:

  gn        the PDF's own text layer, via `pdfpages` (no OCR fallback — that matters,
            see below)
  vi        a local OCR pass over the rendered page, supplied as JSON
  validity  share of alphabetic tokens that are real dictionary words

Clean printed text scores high on validity in `gn`. Handwriting recognition does not:
it garbles into non-words, which is exactly what makes it unusable as-is. A pasted
screenshot shows up as a large `vi` with high validity against a near-empty `gn`,
because a notes app that indexes pen strokes cannot see inside an image.

  usage:  tier_pages.py <pdf> [--ocr ocr.jsonl]

`--ocr` expects one JSON object per line, each with a `path` ending `-pNNN.png` and a
`text` field — the shape any batch OCR runner can emit. Without it, pages are tiered on
the embedded layer alone and nothing is ever classified as a screenshot.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lexicon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

BLANK_MAX = 25       # below this a page carries nothing but stroke noise
SOURCE_MIN = 200     # a real printed page is not 40 characters long
SOURCE_VALID = 0.65
SHOT_DELTA = 250     # OCR beating the embedded layer by this much means an image
SHOT_VALID = 0.50


# Inflected forms included: a page of clean printed prose is full of participles and
# plurals, and the system word list has none of them.
VOCAB = lexicon.load()


def validity(text):
    """Share of alphabetic tokens that are real words.

    Garbled handwriting recognition is mostly non-words, which is the whole
    distinction being drawn here. Under five tokens there is nothing to judge.
    """
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", text)]
    if len(toks) < 5:
        return 0.0
    return sum(t in VOCAB for t in toks) / len(toks)


def embedded_text(pdf):
    """Per-page text from the PDF's own layer, via the pdfpages helper.

    Deliberately not a library with an OCR fallback: the question being asked is
    whether the *file* contains text, and a fallback answers a different question
    while looking like it answered this one.
    """
    binary = os.path.join(HERE, "pdfpages")
    if not os.path.exists(binary):
        sys.exit(f"build it first:  swiftc -O {os.path.join(HERE, 'pdfpages.swift')} "
                 f"-o {binary}")
    out = subprocess.run([binary, pdf], capture_output=True, check=True)
    doc = json.loads(out.stdout.decode("utf-8", "ignore").splitlines()[0])
    return {p["page"]: p["text"] for p in doc["pages"]}


def ocr_text(path):
    """Per-page OCR text, keyed by the page number in each record's filename."""
    out = {}
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            m = re.search(r"-p(\d+)\.\w+$", rec.get("path", ""))
            if m:
                out[int(m.group(1))] = rec.get("text", "")
    return out


def tier(gn, vi):
    gn, vi = gn or "", vi or ""
    if max(len(gn), len(vi)) < BLANK_MAX:
        return "blank"
    if len(gn) >= SOURCE_MIN and validity(gn) >= SOURCE_VALID:
        return "source"
    if len(vi) - len(gn) >= SHOT_DELTA and validity(vi) >= SHOT_VALID:
        return "screenshot"
    return "read"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    pdf = args[0]
    ocr_path = None
    if "--ocr" in sys.argv:
        ocr_path = sys.argv[sys.argv.index("--ocr") + 1]

    gn = embedded_text(pdf)
    vi = ocr_text(ocr_path) if ocr_path else {}

    counts, per_page = {}, {}
    for page in sorted(gn):
        t = tier(gn.get(page, ""), vi.get(page, ""))
        per_page[page] = t
        counts[t] = counts.get(t, 0) + 1

    for page in sorted(per_page):
        print(f"  p{page:<4} {per_page[page]}")
    print()
    for t in ("source", "screenshot", "blank", "read"):
        if counts.get(t):
            print(f"  {t:<11} {counts[t]:>4}")
    print(f"  {'TOTAL':<11} {len(per_page):>4}")
    if not ocr_path:
        print("\n  (no --ocr given: nothing can be classified as a screenshot)")


if __name__ == "__main__":
    main()
