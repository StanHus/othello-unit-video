---
name: uvk-art-make
description: Brief, generate and finish the paintings for a unit video in one consistent illustrated-book style with an image model, then check every one by eye. Use when a story line needs a picture, when characters must stay the same across shots, or when the paintings have a generated look.
---

# Paintings

Paintings carry the story lines, the ones about concrete events. A line that teaches a structure (a definition, a
list, the setting, the ranks) gets a plate instead (`uvk-plates-make`): in this project paintings alone carried 12 of
22 lines, and all 10 misses were structural.

## Brief

Start `<project>/art/briefs.json` from `kit/templates/art/briefs.example.json`; `assets/painting-briefs.json` is the
full set behind this repository's paintings.

- `style`: one paragraph for every painting. Include "No text, lettering, speech balloons, borders, logos or
  watermarks." and what must never be shown, such as gore or a depicted death.
- `bible`: one description per character (age, face, hair, costume), sent with every painting that shows them, so
  each stays the same person.
- `paintings`: per painting an `id`, a `file`, the `chars` it shows, its `refs` (reference paintings, by file stem
  in `--refs-dir`) and a `subject`.

The prompt is the style, then the bible entries of the characters shown, then the subject. Brief each painting to
show what its line is about and, where the line allows, an inference a student can find: in
`assets/paintings/honest-iago.jpg`, Iago's far hand is clenched behind his back as Othello hands Desdemona into his
care.

## Generate

```
python3 tools/art/generate_paintings.py --briefs <project>/art/briefs.json \
  --refs-dir <project>/art/refs --out <project>/art                        # every painting not yet on disk
python3 tools/art/generate_paintings.py --briefs <project>/art/briefs.json \
  --refs-dir <project>/art/refs --out <project>/art --only <id> [<id> ...] --force
```

Outputs are 2K 16:9 JPEGs and `art-manifest.json` (model, references, characters, full prompt, sha256). References
set the style and the faces: the first painting of a new style can go without them (`"refs": []`); after that, send
one or two that fix the style and, for a character who recurs, one that shows them.

## Finish

A generated look is a matter of the finish, not the format. Repaint image to image in one engraved
line-and-watercolour finish that keeps the composition:

```
python3 tools/art/finish_paintings.py --out <project>/art/finished <painting> [<painting> ...]
python3 tools/art/finish_paintings.py --out <project>/art/finished --inputs <list.txt>    # one path per line
```

Each finished painting is saved under its source's name, as a JPEG, in the finish folder, so the film takes the
finished set by pointing `--art-dir` at that folder (`uvk-film-make`).

Settle the finish on two or three paintings beside their originals before repainting a set. In this project's test
an oil finish barely changed the paintings, while the engraved finish changed the surface and kept composition and
faces (`assets/finish-test-comparison.jpg`). Whether it makes a set look less generated was not measured.

## Check every image by eye

- Compare every finished painting with its source. Image to image can change content: in 1 of 18 repaints the model
  added an embracing couple to an empty bedchamber and put out its last lit candle, and the film's frame check passed
  it, because that check confirmed which file was on screen, not what it showed (`assets/drift/`).
- No legible text and no depicted death; faces readable and dignified; every character recognisably the same person
  across paintings.
- Check every edge for a drawn-in border or frame, and regenerate a painting that has one.
- The characters and the object the line needs are in the picture.
- After a repaint, re-measure any crop or face position a plate takes from the painting.
- Give every still a file name that no other painting or plate in the film uses: the renderer frames stills by file
  name.
- Copies that leave the project go through `tools/art/export_web_copies.py --out <folder> <image> [<image> ...]`,
  which resizes them and removes every metadata block (EXIF, XMP, IPTC, ICC, C2PA, comments).
