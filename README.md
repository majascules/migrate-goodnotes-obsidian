# migrate-goodnotes-obsidian

Getting ten years of handwritten notebooks out of GoodNotes and into Obsidian, and what
that turns out to require.

> GoodNotes' notes are fundamentally graphic, hand-drawn, hand-written. They are a
> different beast than the neat data of Obsidian. Importing it required extraction but
> also understanding. Recognition to get content yes (and the handwriting recognition
> latent in GoodNotes is atrocious), but also vision to analyze the pages that weren't
> fundamentally text, and then fusion: describe what we saw so it would be searchable.
> **If it can't be found in Obsidian, it's basically non-extant. Dead.**

That last line is the whole problem. Findability is the test, not fidelity — and the
pages that most need help are the ones with the least text on them. A page of circles and
arrows can be extracted perfectly and still be dead, because there was never anything on
it to extract.

Two different engines are in play, and conflating them is the mistake that costs you:

- **Handwriting recognition** — what GoodNotes runs. It works from the **strokes**: the
  pen's path, recorded as you draw. That is why it is good at cursive and why it cannot
  see a single word inside a pasted screenshot. It never looks at pixels.
- **OCR** — what a Vision pass runs. It works from the **rendered image**. That is why it
  reads pasted screenshots cleanly and why it is worse than GoodNotes at your actual
  handwriting.

Neither is a better version of the other. They read different things, and a page can
easily contain both.

So the job has three layers, and only the first two are what people mean by "getting
notes out":

1. **Extract** — cheap, mechanical, and it only ever serves pages that were already text
2. **Read** — expensive, and it recovers handwriting the recognisers garble
3. **Describe** — the only step that makes a *drawing* findable, and the one nothing
   off-the-shelf does

This repo holds the measurements behind layers 1 and 2 — how far extraction actually gets
you, exactly — and the tools used to take them. Layer 3 isn't code and can't be; it's a
method, written up in [FINDINGS.md](FINDINGS.md).

## What the measurements showed

Ten notebooks, exported both ways GoodNotes offers, then measured:

- the **editable** export contains **zero** extractable text — handwriting stays as 2,586
  live ink annotations with no text layer at all
- the **flattened** export carries the recognition as an invisible text layer, and does
  **not** damage a source PDF's own text (114,494 chars in, 114,494 out)
- GoodNotes' recognition covers **pen strokes only** — text inside a pasted screenshot is
  invisible to it, and always has been

That third one is where the argument turns. The failure isn't quality, it's category.
Stroke-based recognition is blind to images by construction, and image-based OCR is
blind to nothing *and* useless on a diagram — because a diagram's meaning was never
written down on it. An engine that read every stroke perfectly would still leave a
hand-drawn user-journey map unfindable, since *describing* is not something either kind
of recognition does.

Full numbers, method, and the case for layer 3: **[FINDINGS.md](FINDINGS.md)**.

## Tools

| | |
|---|---|
| `tools/pdfpages.swift` | Per-page text from a PDF's own layer. **No OCR fallback, by design.** |
| `tools/render.swift` | Render PDF pages to PNG at a chosen scale. |
| `tools/ocr.swift` | Vision OCR over those PNGs, in the shape `tier_pages.py` reads. |
| `tools/tier_pages.py` | Sort pages into *source / screenshot / blank / needs-reading* before spending anything on them. |
| `tools/name_filter.py` | Separate real proper nouns from words the recognisers garbled. |
| `tools/lexicon.py` | The system dictionary, plus the inflected forms it is missing. |

`tier_pages.py` is the one that matters most in practice: it decides which pages need a
reader at all. On this corpus it cut 587 pages to 411, in seconds. It cannot *be* the
reader — that's layer 3.

### Why no OCR fallback

Every convenient PDF-text library falls back to OCR when a page has no text layer. That
answers *can this page be read* — a different question from *does this file contain
text*, which is the one you are asking when comparing two exports. `pdfpages` reports an
image-only page as zero characters, which is the true answer.

## Getting the exports

Export each notebook **twice**. GoodNotes 5 makes the two useful options mutually
exclusive: choosing `PDF Data` + `Editable` removes the `Enable Handwriting Recognition`
option entirely, so no single export gives you both.

| export | what it is for |
|---|---|
| **Flattened**, with `Enable Handwriting Recognition` on | the working copy. Carries the recognition as a text layer. Extract from this one |
| **Editable** + `PDF Data` | the archive. Round-trips back into GoodNotes with live ink, but there is nothing in it to mine |

Leave **`Include Page Background` on** for both. If your notebooks are built on imported
PDFs, turning it off exports your handwriting floating on blank pages and silently
discards the source document — which is the thing finding 2 says you get to keep.

## Use

```bash
swiftc -O tools/pdfpages.swift -o tools/pdfpages
swiftc -O tools/render.swift   -o tools/render
swiftc -O tools/ocr.swift      -o tools/ocr

# does this export carry any text at all?
tools/pdfpages "MyNotebook.pdf"

# render pages for the OCR pass, at 1.6x
tools/render "MyNotebook.pdf" ./pages 1.6

# OCR them
tools/ocr ./pages/*.png > pages-ocr.jsonl

# which pages actually need expensive handling?
python3 tools/tier_pages.py "MyNotebook.pdf" --ocr pages-ocr.jsonl

# see the name filter's three outcomes on a worked sample
python3 tools/name_filter.py --demo
```

Nothing to install. The Swift tools use PDFKit and Vision, both already on the machine;
the Python tools are standard library plus `/usr/share/dict/words`. No third-party
dependencies, and no package manager involved at any step.

### This is a macOS toolkit

Not incidentally, but structurally. `pdfpages` and `render` are PDFKit, `ocr` is Vision,
and `tier_pages.py` shells out to the compiled `pdfpages`. Only `name_filter.py` and
`lexicon.py` stand alone. There is no portable version of this and I have not tried to
pretend otherwise.

Vision is the reason the OCR step costs nothing here. If you are porting this, that is
the piece to replace, and the section below says what it actually has to be good at.

### What the OCR pass is for

Printed text inside pasted screenshots. Not handwriting.

This surprises people, so it is worth being explicit. `tier_pages.py` calls a page a
screenshot only when the OCR text is both much longer than the PDF's own text layer
*and* mostly real dictionary words. Garbled handwriting fails that second test by
construction, which is the point — an engine that tried harder on handwriting would make
this worse, by inflating the length comparison without adding real words.

So the bar is ordinary printed-text OCR, which is a solved problem. The detector is also
tolerant: on a test page where Vision mangled three lines outright, the page still
classified correctly, because enough of the rest came back as real words.

`tools/ocr` emits one JSON object per line, with a `path` ending `-pNN.png` and a `text`
field. Any other engine works if you reshape its output to match:

```json
{"path": "pages/MyNotebook-p01.png", "text": "text found on page 1"}
{"path": "pages/MyNotebook-p02.png", "text": ""}
```

Without `--ocr`, `tier_pages.py` still runs, but it tiers on the embedded layer alone and
nothing is ever classified as a screenshot. An image-only page then reads as `blank`,
which means finding 3, the one the argument turns on, is the finding you cannot
reproduce.

## Caveats

Every threshold here is empirical, tuned against one corpus of ten notebooks and one
person's handwriting. They are constants at the top of each file, with the measurements
that produced them written down beside them. Expect to retune.

Tested on GoodNotes 5, macOS, mid-2026.

## Licence

MIT — © 2026 Esmaeil Khaksari. See [LICENSE](LICENSE).
