#!/usr/bin/env python3
"""Write a tiered GoodNotes export into an Obsidian vault, append-only.

This is the step between the measurements and an actual migration. It runs the whole
cheap pass — render, OCR, tier — and writes one note per notebook, with the text that
could be recovered mechanically and, for everything else, the page image plus an
explicit marker that the page is not yet searchable.

It does not transcribe and it does not describe. Those are the expensive layers and
they are not code (see FINDINGS.md, finding 6). What this does is get every page that
*can* be made findable without judgment into the vault, and stage the rest so the
expensive pass has somewhere to land.

Safety, because this writes into someone's notes:

  * Dry run is the default. Nothing is written without `--write`.
  * Writes are appends. Never a truncate, never a rewrite, never a delete.
  * A note this tool already wrote is skipped, so re-running is safe.
  * A note it did *not* write is reported and left alone, never appended to. A name
    collision with your own note is a situation to look at, not to guess about.
  * `--exclude` keeps named pages out of the vault entirely. Real notebooks contain
    material you read and then decide not to file, and that decision has to survive
    into the tool rather than being something you clean up afterwards.

Usage:
  ingest.py <vault> <flattened.pdf> [<flattened.pdf>...] [options]

  --write               actually write (default is a dry run)
  --dest <folder>       vault subfolder for notes        (default: GoodNotes)
  --attachments <folder>  vault subfolder for images     (default: GoodNotes/images)
  --scale <n>           render scale                     (default: 1.6)
  --exclude <file>      lines of `Stem:page` or `Stem:first-last` to omit
  --all-images          embed an image on every page, not just unread ones
  --png                 keep PNG images instead of converting to JPEG
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_pages  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Every note this tool writes carries this line. It is how a re-run knows what it
# already did, and how it tells its own notes apart from yours.
MARKER = "<!-- ingested-by: migrate-goodnotes-obsidian | source: {stem} -->"

# JPEG q80 rather than PNG for the vault copies. Grey pen on cream carries no
# artefacts worth the extra size, and a page-image set for a real corpus runs to
# most of a gigabyte in a sync-backed vault. `--png` opts out.
JPEG_QUALITY = 80


def tool(name):
    """Path to a built Swift helper, with the build line if it is missing."""
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        sys.exit(f"build it first:  swiftc -O {path}.swift -o {path}")
    return path


def parse_exclusions(path):
    """`Stem:page` or `Stem:first-last` per line; blanks and `#` comments ignored."""
    out = set()
    if not path:
        return out
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = re.match(r"^(.+?):(\d+)(?:-(\d+))?$", line)
            if not m:
                sys.exit(f"{path}:{lineno}: expected `Stem:page` or `Stem:first-last`, got {line!r}")
            stem, first, last = m.group(1).strip(), int(m.group(2)), m.group(3)
            for page in range(first, int(last) + 1 if last else first + 1):
                out.add((stem, page))
    return out


def render(pdf, outdir, scale):
    """Render every page to PNG. Returns {page number: path}."""
    subprocess.run([tool("render"), pdf, outdir, str(scale)],
                   check=True, capture_output=True)
    pages = {}
    for name in os.listdir(outdir):
        m = re.search(r"-p(\d+)\.png$", name)
        if m:
            pages[int(m.group(1))] = os.path.join(outdir, name)
    return pages


def ocr(paths, outfile):
    """OCR the rendered pages into the jsonl shape tier_pages reads."""
    if not paths:
        return {}
    with open(outfile, "w", encoding="utf-8") as fh:
        subprocess.run([tool("ocr")] + paths, check=True, stdout=fh)
    return tier_pages.ocr_text(outfile)


def to_jpeg(src, dest):
    """PNG to JPEG via sips, which ships with macOS like everything else here."""
    subprocess.run(["sips", "-s", "format", "jpeg",
                    "-s", "formatOptions", str(JPEG_QUALITY),
                    src, "--out", dest], check=True, capture_output=True)


# `tier_pages` calls the expensive tier "read", meaning it is the one that needs a
# reader. In a note that heading would say the opposite of what it means.
TIER_LABEL = {"source": "extracted", "screenshot": "screenshot",
              "blank": "blank", "read": "needs reading"}


def page_section(page, tier, text, image):
    """One page's markdown. The unread pages are the ones that need the image."""
    head = f"### p{page:02d} — {TIER_LABEL[tier]}"
    if tier == "blank":
        return None
    body = []
    if image:
        body.append(f"![[{image}]]")
    if tier in ("source", "screenshot") and text.strip():
        body.append(text.strip())
    if tier == "read":
        body.append("> [!todo] Not yet read\n"
                    "> Nothing on this page is searchable yet. Extraction recovered "
                    "little or nothing from it, which is the expected result for "
                    "handwriting and drawings rather than a failure.")
    return head + "\n\n" + "\n\n".join(body) + "\n"


def build_note(stem, per_page, gn, vi, images, excluded):
    """The whole note for one notebook, plus the counts to report."""
    counts = {"source": 0, "screenshot": 0, "blank": 0, "read": 0, "excluded": 0}
    sections = []
    for page in sorted(per_page):
        if (stem, page) in excluded:
            counts["excluded"] += 1
            continue
        tier = per_page[page]
        counts[tier] += 1
        text = vi.get(page, "") if tier == "screenshot" else gn.get(page, "")
        section = page_section(page, tier, text, images.get(page))
        if section:
            sections.append(section)

    # Every page lands somewhere or the note is wrong. Silent page loss is the one
    # failure this cannot be allowed to have — a page that vanishes here is a page
    # nobody will ever go looking for.
    assert sum(counts.values()) == len(per_page), (counts, len(per_page))

    summary = (f"{counts['source']} extracted, {counts['screenshot']} from screenshots, "
               f"{counts['read']} awaiting a read, {counts['blank']} blank")
    if counts["excluded"]:
        summary += f", {counts['excluded']} excluded"

    header = (f"---\nsource: {stem}\ntype: goodnotes-import\n---\n\n"
              f"# {stem}\n\n{MARKER.format(stem=stem)}\n\n"
              f"{len(per_page)} page{'s' if len(per_page) != 1 else ''}: {summary}.\n\n")
    if counts["read"]:
        header += ("Pages marked *Not yet read* carry no searchable text. That is what "
                   "extraction cannot reach, and what a read has to supply.\n\n")
    return header + "\n".join(sections), counts


def note_status(path, stem):
    """`new`, `ours` (already ingested), or `theirs` (someone else's note)."""
    if not os.path.exists(path):
        return "new"
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return "ours" if MARKER.format(stem=stem) in fh.read() else "theirs"


def main():
    # Before argparse, so the docstring is what you get from `--help` or from no
    # arguments at all. argparse would otherwise answer with its own usage line and
    # the reasoning above would never be read.
    if len(sys.argv) < 3 or "-h" in sys.argv or "--help" in sys.argv:
        sys.exit(__doc__)

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("vault")
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dest", default="GoodNotes")
    ap.add_argument("--attachments", default="GoodNotes/images")
    ap.add_argument("--scale", type=float, default=1.6)
    ap.add_argument("--exclude")
    ap.add_argument("--all-images", action="store_true")
    ap.add_argument("--png", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.vault):
        sys.exit(f"no vault at {args.vault}")
    excluded = parse_exclusions(args.exclude)
    notes_dir = os.path.join(args.vault, args.dest)
    img_dir = os.path.join(args.vault, args.attachments)
    ext = "png" if args.png else "jpg"

    planned, skipped = [], []
    for pdf in args.pdfs:
        stem = os.path.splitext(os.path.basename(pdf))[0]
        note_path = os.path.join(notes_dir, f"{stem}.md")
        status = note_status(note_path, stem)
        if status != "new":
            skipped.append((stem, status))
            continue

        with tempfile.TemporaryDirectory() as tmp:
            rendered = render(pdf, os.path.join(tmp, "pages"), args.scale)
            vi = ocr(sorted(rendered.values()), os.path.join(tmp, "ocr.jsonl"))
            gn = tier_pages.embedded_text(pdf)
            per_page = {p: tier_pages.tier(gn.get(p, ""), vi.get(p, "")) for p in sorted(gn)}

            images = {}
            for page, tier in per_page.items():
                if (stem, page) in excluded:
                    continue
                if tier == "blank" or (tier != "read" and not args.all_images):
                    continue
                if page not in rendered:
                    continue
                name = f"{stem}-p{page:02d}.{ext}"
                images[page] = name
                if args.write:
                    os.makedirs(img_dir, exist_ok=True)
                    dest = os.path.join(img_dir, name)
                    if args.png:
                        shutil.copy2(rendered[page], dest)
                    else:
                        to_jpeg(rendered[page], dest)

            body, counts = build_note(stem, per_page, gn, vi, images, excluded)

        # Nothing left after blanks and exclusions. An empty note is worse than no
        # note: it is a search result that wastes the one click it costs to open.
        if counts["blank"] + counts["excluded"] == len(per_page):
            skipped.append((stem, "empty"))
            continue

        planned.append((stem, note_path, body, counts, len(images)))
        if args.write:
            os.makedirs(notes_dir, exist_ok=True)
            # Append, never truncate: creates the file when absent and cannot
            # destroy what it never read.
            with open(note_path, "a", encoding="utf-8") as fh:
                fh.write(body)

    reasons = {
        "ours": "already ingested",
        "empty": "nothing to write — every page blank or excluded",
        "theirs": ("a note of that name exists and this tool did not write it — "
                   "left alone; rename one of them"),
    }
    for stem, status in skipped:
        print(f"  skip  {stem:<28} {reasons[status]}")
    for stem, path, _body, counts, n_img in planned:
        print(f"  {'wrote' if args.write else 'would write'}  {stem:<24} "
              f"{counts['source']} src / {counts['screenshot']} shot / "
              f"{counts['read']} unread / {counts['blank']} blank"
              + (f" / {counts['excluded']} excluded" if counts["excluded"] else "")
              + f", {n_img} images")
    if planned and not args.write:
        print(f"\n  dry run. {len(planned)} note(s) not written. Add --write.")


if __name__ == "__main__":
    main()
