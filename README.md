# migrate-goodnotes-obsidian

I had 10 years of handwritten notebooks, annotated PDFs, and whiteboard sessions in GoodNotes. And I needed that information findable in Obsidian. A simple export > import failed miserably.  This project is a best-effort attempt to ingest GoodNotes materials and make them a searchable archive inside of your Obsidian. One or more GoodNotes export(s) are put into your Obsidian vault, with some shepherding from you, and provides stats to help you understand what was done. This is a migration, not a sync tool.

GoodNotes' notes are fundamentally graphic, hand-drawn, hand-written. E.g. A flow diagram for a process: a page of drawn circles and arrows can be exported and imported but still be lost, because there was little text to extract. Making GoodNotes accessible in Obsidian requires extraction AND understanding.

Recognition to get content yes (and the handwriting recognition latent in GoodNotes is atrocious), but also machine-vision to analyze the graphical content, and then fusion: take the original text, the handwriting, the images, and describe the page in a way that makes it findable.

The rule is: **If it can't be found in Obsidian, it's basically non-extant. Lost.** "Findability" + fidelity became the test. The pages that most need help are the ones with the least text on them. 

Three different things can read a page, and conflating them is the mistake that costs you:

- **Handwriting recognition** — what GoodNotes runs. It works from the **strokes**: the
  pen's path, recorded as you draw. It is marginal at cursive, and it ignores text inside
  images and screenshots entirely, because it never looks at pixels.

- **OCR** — what a Vision pass runs. It works from the **rendered image**. That is why it
  reads pasted screenshots cleanly and why it is worse than GoodNotes at your actual
  handwriting.

- **A multimodal read** — **Claude**, looking at the page image the way a person would.
  This is what actually transcribed the hard pages here and wrote their descriptions. On
  a page where both engines garbled every proper noun, it got them all right and I checked
  three word for word. It is also the only one of the three that can say what a drawing
  *is*. One page, three phrases verified — evidence about *where* the engines fail, not a
  rate. The comparison is in [FINDINGS.md](FINDINGS.md), finding 3.

The first two are not better or worse versions of each other. They read different things,
and a page can easily contain both. The third is what you reach for when both have
failed, which on a graphic notebook is most of the time.

Full numbers, method, and the case for layer 3: **[FINDINGS.md](FINDINGS.md)**.

So the job has three layers, and only the first two are what people mean by "getting
notes out":

1. **Extract** — cheap, mechanical, and it only ever serves pages that were already text
2. **Read** — expensive, and it recovers handwriting the recognisers garble
3. **Describe** — the only step that makes a *drawing* findable, and the one nothing
   off-the-shelf does

The tools here do layer 1, decide how much of layer 2 you actually have to pay for, and
write the result into your vault. Layers 2 and 3 themselves are not code and this repo
does not pretend otherwise: reading a page, and saying what it is, are things a person or
a model does. What the tools can tell you is exactly how much is left for them.

## Tools

| | |
|---|---|
| `tools/pdfpages.swift` | Per-page text from a PDF's own layer. **No OCR fallback, by design.** |
| `tools/render.swift` | Render PDF pages to PNG at a chosen scale. |
| `tools/ocr.swift` | Vision OCR over those PNGs, in the shape `tier_pages.py` reads. |
| `tools/tier_pages.py` | Sort pages into *source / screenshot / blank / needs-reading* before spending anything on them. |
| `tools/name_filter.py` | Separate real proper nouns from words the recognisers garbled. |
| `tools/lexicon.py` | The system dictionary, plus the inflected forms it is missing. |
| `tools/ingest.py` | Write a tiered export into an Obsidian vault. Dry run by default. |

`tier_pages.py` is the one that matters most in practice: it decides which pages need a
reader at all. On this corpus it cut 587 pages to 411, in seconds, as the migration ran.
The current version gives 417 on the same pages, after a threshold was recalibrated; the
reason is in [FINDINGS.md](FINDINGS.md), finding 4, and it is worth reading. It cannot *be*
the reader. That's layers 2 and 3.

A worked page, end to end — what each engine returned, what the tiering decided, and the
description that made it findable: **[EXAMPLE.md](EXAMPLE.md)**.

### No OCR Fallback when the text-layer is absent

Every convenient PDF-text library falls back to OCR when a page has no text layer. That
answers *can this page be read* — a different question from *does this file contain
text*, which is the one you are asking when comparing two exports. `pdfpages` reports an
image-only page as zero characters, which is the true answer.

This is not a position against OCR; `tools/ocr` is right there in the table. It is what
makes that tool useful. The screenshot test compares the file's own text against the
image's, and a comparison needs two things measured differently. If `pdfpages` quietly fell
back to OCR, both numbers would be the same and no page could ever be identified as a
screenshot.

## Getting the exports

Export the **flattened** copy. That is what every tool here reads.

Export the **editable** copy too if you want one you can still edit in GoodNotes years from
now. It is insurance, not a step: nothing in `tools/` reads it. You cannot get both
properties in one file, because choosing `PDF Data` + `Editable` removes the
`Enable Handwriting Recognition` option entirely.

| export | what it is for |
|---|---|
| **Flattened**, with `Enable Handwriting Recognition` on | the working copy. Carries the recognition as a text layer. Extract from this one |
| **Editable** + `PDF Data` | the archive. Round-trips back into GoodNotes with live ink. A source PDF's own text survives in it, but nothing the flattened copy doesn't also have |

Why export for a recognition layer that is this bad? Because it is not there to be read.
It is there to be measured: it is one of the two cheap signals `tier_pages.py` sorts pages
by, and it is the raw material `name_filter.py` mines for proper nouns. Bad text that is
consistently bad is a usable instrument.

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

## Into the vault

`ingest.py` runs the cheap pass end to end and writes one note per notebook.

    python3 tools/ingest.py ~/MyVault "MyNotebook.pdf"           # dry run
    python3 tools/ingest.py ~/MyVault "MyNotebook.pdf" --write

Pages that extracted cleanly arrive as text. Pasted screenshots arrive as their OCR.
Everything else arrives as the page image under a *Not yet read* marker — which is
most of a graphic notebook, and is the honest state of it. Nothing here transcribes
or describes; that is the expensive layer, and it is not code.

It writes by appending and never truncates, skips notes it has already written so
re-running is safe, and refuses to touch a note of the same name that it did not
write. `--exclude` keeps named pages out of the vault entirely, which real notebooks
turn out to need.

## Caveats

Every threshold here is empirical, tuned against one corpus of ten notebooks and one
person's handwriting. They are constants at the top of each file, with the measurements
that produced them written down beside them. Expect to retune.

Tested on GoodNotes 5, macOS, mid-2026. The page reads were done with Claude in the same
period; model behaviour moves, and that result should be expected to move with it.

## Licence

MIT — © 2026 Esmaeil Khaksari. See [LICENSE](LICENSE).
