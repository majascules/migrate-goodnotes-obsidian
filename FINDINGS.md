# Getting graphic notes into a text system

> GoodNotes' notes are fundamentally graphic, hand-drawn, hand-written. They are a
> different beast than the neat data of Obsidian. Importing it required extraction but
> also understanding. Recognition to get content yes (and the handwriting recognition
> latent in GoodNotes is atrocious), but also vision to analyze the pages that weren't
> fundamentally text, and then fusion: describe what we saw so it would be searchable.
> **If it can't be found in Obsidian, it's basically non-extant. Dead.**

Findability is the test. Not fidelity, not character counts — whether the thing turns up
when you search for it two years later. And that reframes the whole job, because the
pages in the greatest danger are the ones with the least text on them.

Take one page from these notebooks: a competitor-monitoring user journey. Six actors
drawn as circles, labelled flows between them, three personas down the left margin, and
the unresolved design problems written around the edges — aggregation, security silos,
integration. It is a complete piece of thinking. Its extractable text is a handful of
stranded words.

No OCR failed on that page. There was nothing on it to fail at. Perfect recognition of
every stroke would have left it exactly as dead. What made it findable was a paragraph
saying **what the page is**: a journey that closes a loop, with the real thinking in the
margins. That paragraph is not transcription. It is description, and it is the only thing
that gets a drawing into a search index.

So the job has three layers:

| layer | cost | what it serves |
|---|---|---|
| **Extract** | seconds | pages that were already text |
| **Read** | expensive | handwriting the recognisers garble |
| **Describe** | expensive | drawings — nothing else reaches them |

Findings 1–4 below establish exactly how far extraction gets you, because you should
spend the expensive layers only where the cheap one has failed. Findings 5 and 6 are
about the expensive layers themselves.

Every number came off ten notebooks exported both ways, and can be reproduced with the
tools in `tools/`.

Method throughout: text is pulled with `pdfpages`, a ~40-line PDFKit wrapper that has
**no OCR fallback**. That is the whole point of it. Every convenient extraction library
quietly falls back to OCR when a page has no text layer, which answers a completely
different question — *can this page be read* rather than *does this file contain text* —
while looking like it answered yours.

---

## 1. The two exports are not interchangeable

One notebook, 8 pages, exported both ways:

| export | extractable text |
|---|---|
| Flattened + Handwriting Recognition | **1,394 chars** across 7 of 8 pages |
| Editable + PDF Data | **0 chars**, 0 pages |

The editable export contains no recoverable text at all. Not less — none.

The structure explains it. Counting raw PDF markers in each file:

| marker | editable | flattened |
|---|---:|---:|
| `/Ink` annotations | **2,586** | 0 |
| `/ToUnicode` maps | 0 | **6** |
| `/Font` references | 7 | **1,160** |
| TrueType fonts | 1 | **191** |

The editable export keeps your handwriting as live vector ink you can still edit in the
app. The flattened export burns the strokes into the page and adds an invisible text
layer holding the recognition result. Only the second is searchable outside GoodNotes.

## 2. Flattening costs you nothing

The obvious worry is that flattening destroys the underlying document — most of these
notebooks were built on imported PDFs, so the page background *is* a source document.

It doesn't. A notebook built on a 94-page typed PDF:

| | characters |
|---|---:|
| source PDF, extracted from inside the notebook bundle | 114,494 |
| flattened export | **114,494** |
| editable export | 114,406 |

A source document's own text layer survives both exports intact. Flattening only *adds*
the recognition layer.

**So: extract from the flattened export. Keep the editable one as an archive** — it
round-trips back into GoodNotes with annotations still live, which is worth having, but
there is nothing in it to mine.

## 3. Two engines, reading two different things

The word "OCR" hides the finding. GoodNotes does not run OCR. It runs **handwriting
recognition over stroke data** — the pen's path as you drew it — which is a different
input entirely from an image of the page.

|  | reads | good at | blind to |
|---|---|---|---|
| **handwriting recognition** (GoodNotes) | pen strokes | cursive and proper nouns, *relative to OCR* | anything that isn't a stroke |
| **OCR** (a Vision pass) | the rendered image | printed text, pasted screenshots | nothing — but it *sees* a diagram without understanding it |

The practical consequence, for anyone who has wondered why GoodNotes search misses
things:

**The recognition covers pen strokes only. Text inside a pasted screenshot is invisible
to it** — and always has been, in the app's own search as much as in the export.

Across one 182-page notebook, comparing the embedded recognition against a local OCR
pass over rendered pages:

| | characters |
|---|---:|
| embedded recognition | 55,620 |
| local OCR of the same pages | 60,218 |

Read as totals, that looks like a wash. The distribution is the finding:

| page | embedded | OCR |
|---|---:|---:|
| a pasted spreadsheet | 107 | **3,340** |
| a pasted profile page | 1 | **2,450** |

Going the other way, on dense handwriting the embedded layer beats OCR by 200–300 chars
per page and is noticeably better on proper nouns. That is consistent with it having the
pen's path rather than a picture of the result — though I have not reverse-engineered the
engine, and this is inference from behaviour, not from its internals.

**Neither is sufficient alone.** If your notebooks contain pasted screenshots — mine were
full of them — the app's own search has never seen that text, and neither will anything
you build on the export.

### And neither of them is what read the pages

Both engines were compared against a third option on the same page: **Claude**, reading
the rendered page image directly.

"Recognition" gets used for all of this, so here is who actually did what:

| job | done by |
|---|---|
| Handwriting recognition over stroke data | GoodNotes, in the app, at export time |
| OCR over rendered pages | Apple's Vision framework, locally — `tools/ocr` |
| Reading handwriting that a person could read and neither engine could | Claude, from the page image |
| Describing what a drawing *is* | Claude, from the page image |
| Confirming uncertain readings against the page | me |
| Blessing recurring proper nouns, once each | me |
| Deciding what got filed and what was held back | me |

The first two are in this repo. The middle two are not code and cannot be. The last three
are the reason the middle two can be trusted at all.

On one page carrying a company name, a person's full name and two internal acronyms, both
engines garbled **every proper noun on it**. Claude's read got them right, and I checked
three of them word for word against the page image. That check is why this is a result
rather than an impression.

Two rows that carry nothing identifying, reproduced exactly:

| on the page | GoodNotes | Vision | Claude |
|---|---|---|---|
| Renumeration | `Rummation` | `Piration` | Renumeration |
| Beta / Socialize NO. | `Beta/Souilize No` | `Muta/Saulize NO .` | Beta / Socialize NO. |

The proper nouns themselves can't be printed here — they are a real company and a real
person — but that is also the finding: **proper nouns are exactly where both engines
failed, and proper nouns are what you search for.**

Beyond the words, both engines emit flat text, including one line of `iiiiiiiiiiiiiiii-`.
Claude's read carried the page's structure: what sat in the top right, what was centred,
what was underlined. Neither engine is built to report that, and on a diagram the
structure is most of the meaning.

**What this does not establish.** One page, three phrases checked by hand. It is not a
rate, and no corpus-wide comparison was run — by the time the question mattered, the whole
corpus was already being read this way. Take it as evidence of *where* the engines fail,
proper nouns and structure, rather than how often.

## 4. Tier your pages before you spend anything on them

The expensive step in digitising handwriting is reading pages. Most pages don't need it.

Classifying every page first — using the two cheap signals above plus a dictionary-validity
score — sorted 587 pages into:

| tier | pages | what it needs |
|---|---:|---|
| source | 105 | nothing; text already extracts cleanly |
| screenshot | 32 | the cheap local OCR pass, which reads them accurately |
| blank | 39 | nothing |
| **needs reading** | **411** | the expensive path |

That is a 30% cut before any expensive work starts, and the classification itself costs
seconds. `tools/tier_pages.py` implements it.

The thresholds in that script are tuned to my handwriting and my notebooks. They are
constants at the top of the file for exactly that reason.

## 5. A garbled word is not a name

Recognised handwriting is unusable as-is, but it is very useful as *evidence*. In
particular you can mine it for the proper nouns that recur — product names, people,
acronyms — get a human to confirm them once, and then apply them everywhere. Proper nouns
are where every recogniser fails hardest and where a wrong reading does the most damage,
because a garbled product name reads as fact.

The obvious filter is a dictionary: drop real words, keep the rest. It does not work.
OCR mangles ordinary words *out* of the dictionary, and they drown the real names:

```
Custoner   Produt   Seach   Strugth   Featur   Reportng
```

The signal that does work: **a token within one or two characters of a common word is a
mangled word, not a name.** Measured over my corpus:

| | best similarity to a dictionary word |
|---|---|
| garbled ordinary words | 0.875 – 0.941 |
| real product names | 0.706 – 0.857 |

They separate, but the margin is **0.018 wide** — thin enough that the threshold is a
tuning knob, not a constant of nature. `tools/name_filter.py` sets it at 0.87 and says so.

Two traps found the hard way, both preserved as comments in that file:

- **Don't exempt ALL-CAPS tokens.** I did, reasoning that capitals were a deliberate mark
  rather than a sentence start. People write headings in capitals. The exemption flooded
  the candidate list with `SEARCH`, `PROJECT`, `USER`, `REPORT` and buried every real name.
- **The system dictionary has no inflections.** macOS ships Webster's Second, which lists
  base forms only — `exist` but not `existing`, `customer` but not `customers`. Without
  inflected forms, `EXISING` has no `existing` to be close to, and a whole class of
  garbling survives as false "names". `tools/lexicon.py` closes that gap.

## 6. Description, not transcription — and it has to be checkable

Findings 1–5 are all about extraction. They end at a wall: a page that was never text
cannot be extracted into existence. Roughly a third of these notebooks were diagrams,
wireframes, flows and drawings. Extraction returns almost nothing from them, and the
nothing it returns is not a bug to be fixed.

What works is writing a short paragraph at the top of the page saying **what the page
is** — its subject, its shape, and where the actual thinking sits on it. Not what marks
are present; what they amount to.

That paragraph does three things nothing else does:

- **It names the artefact.** "A user-journey map for a competitor-monitoring service"
  is what someone searches for. No label on the page says that.
- **It captures the shape of the argument.** That the flow *closes a loop*, that seven
  pages are seven states of one toolbar, that nineteen pages are a single specification
  rather than nineteen sketches. Structure is invisible to per-page extraction by
  construction.
- **It supplies vocabulary.** A page of arrows contributes nearly no searchable words.
  A description contributes a paragraph of them, in the language you would actually
  search in.

### The catch, and the discipline it forces

Description is interpretation. Transcription can be checked against the page mark by
mark; description asserts what marks *mean*, and can be confidently wrong in a way that
looks exactly like being right.

So the rule that makes it safe: **the page image travels with the description, and every
uncertain reading carries a pointer to where on the page it came from.** In this
migration that meant 411 page images embedded beside their text, and a citation format
that resolves — best guess, marked as a guess, plus a position on the page. Any sentence
can be checked against its source in one click.

Two consequences worth stating plainly:

- If the images are not reachable from the notes, description is unverifiable and you are
  trusting an assertion. Keep them adjacent, not merely archived somewhere.
- The description layer is not code and this repo does not contain it. `tier_pages.py`
  decides *which* pages need a reader; it cannot be the reader. What is transferable is
  the method and the discipline, not a program you run.

### Where the effort actually went

| tier | pages | what happened to them |
|---|---:|---|
| source | 105 | extracted, free |
| screenshot | 32 | local OCR, free |
| blank | 39 | nothing |
| needs reading | 411 | read and, where they were drawings, described |

The three cheap tiers cover 30% of the corpus for essentially nothing. The remaining 70%
is where a graphic notebook actually lives, and no amount of better OCR would have
changed that ratio.


---

## Reproducing this

```bash
swiftc -O tools/pdfpages.swift -o tools/pdfpages
swiftc -O tools/render.swift   -o tools/render

tools/pdfpages "MyNotebook (flattened).pdf" | python3 -m json.tool | head -40
tools/pdfpages "MyNotebook (editable).pdf"  | python3 -m json.tool | head -40
```

If the second one reports `totalChars: 0` while the first reports thousands, you have
reproduced finding 1 on your own notebooks.

For finding 3 you need an OCR pass over rendered pages:

```bash
swiftc -O tools/render.swift -o tools/render
swiftc -O tools/ocr.swift    -o tools/ocr

tools/render "MyNotebook (flattened).pdf" ./pages 1.6
tools/ocr ./pages/*.png > pages-ocr.jsonl
python3 tools/tier_pages.py "MyNotebook (flattened).pdf" --ocr pages-ocr.jsonl
```

`tools/ocr` is a Vision pass, which is local and free on macOS. Any OCR that emits one
JSON object per image will do instead; it only has to be good at printed text.

Finding 6 has nothing to run. Take the page your extraction returned least from, look at
it, and write one paragraph saying what it is. Then search your vault for the words in
that paragraph, and note that none of them were previously there.

## What this does not tell you

- Only GoodNotes 5 was tested, on macOS, mid-2026. Later versions may differ.
- That GoodNotes uses stroke-based recognition is inferred from behaviour — total
  blindness to pasted images, superiority on cursive — not from inspecting the engine.
- Recognition quality is specific to a person's handwriting. Mine is bad.
- Every threshold here is empirical, from one corpus of ten notebooks.
- Finding 6 is a method, not a measurement. It is the part I am most confident about and
  the part with the least hard evidence behind it — no controlled comparison was run
  between described and undescribed pages, because the whole corpus got described.
