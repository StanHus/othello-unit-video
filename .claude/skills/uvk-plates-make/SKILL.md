---
name: uvk-plates-make
description: Build labelled book plates for the lines a painting cannot carry (a title, an arc, a checklist, a map, a caption, a label card, a rank ladder, a quotation with steps and a definition, a rise-and-fall curve or a word list), rendered as stills by headless Chrome. Use when the shot audit shows structural lines competing with their picture, or when a line teaches a structure rather than an event.
---

# Plates

Paintings carry story and fail where the script turns structural: definitions, lists, the setting, the ranks. A
plate is a printed inlay in the book: cream paper, a brass rule, a serif display face, quotations in oxblood, the
painting dimmed behind it. In this project paintings alone carried 12 of 22 lines; plates on the 10 structural lines
made all 22 carry.

## Build

`tools/plates/build_plates.py` holds only layouts: every word on a plate comes from a content file.
`tools/plates/plates.example.json` has one plate of every type over the paintings in `assets/paintings/`. Build it
once to see them:

```
python3 tools/plates/build_plates.py --content tools/plates/plates.example.json --out <scratch folder>
```

Then write the project's content file, with image paths relative to it, and build:

```
python3 tools/plates/build_plates.py --content <project>/film/vNN/plate-content.json --out <project>/film/vNN
python3 tools/plates/build_plates.py --content <project>/film/vNN/plate-content.json --out <project>/film/vNN \
  --only <prefix>                                       # only the plates whose id starts with it
```

The tool writes `plates/<id>.png`, `plates.json` (each plate's type, base painting, on-screen words and sha256) and
`contact-sheet.jpg`. `--art-map <file>`, a JSON file of `{"<key>": "<image path>"}` with paths relative to that file,
swaps the paintings behind the plates, for example for their finished versions, without editing the content file.
Plates are 1480×808, the picture area inside the renderer's book frame, so their text is never rescaled. Chrome comes
from `CHROME_BIN`, else from the PATH or the default macOS install.

| a line that | type |
|---|---|
| names the work | `title` |
| runs from one point of the story to another | `arc` |
| lists up to four things to know | `checklist` |
| places the story | `map` |
| states one fact | `caption` |
| says who someone is | `label_card` |
| ranks up to three people | `rank_ladder` |
| quotes the play, with steps and a definition | `quote` |
| gives the shape of a genre: rise, fall and their causes | `curve` |
| gives up to eight words | `glossary` |

The fields of each type are in the tool's help: `python3 tools/plates/build_plates.py --help`.

## Build up in steps

`"reveal": [n, ...]` makes one plate per state, with `-n` added to the id. Give each state its own storyboard shot,
anchored to the phrase that brings its item in (`uvk-film-make`).

## Rules

- One plate per structural line, built up in steps, every step anchored to a spoken phrase.
- A plate shows only words the narration speaks while it is on screen, and quotations word for word with their
  act.scene.line. Check `on_screen_text` in `plates.json` against the script. Labels are keywords, not sentences.
- A quote plate carries the quotation, its steps and a one-line definition.
- Count the text. With plates, this project's film had text on screen for 51% of its runtime; a 3D version of the
  same script had text on screen for 95%, with up to 27 items in one frame. A plate that prints everything competes
  like a busy painting. `tools/review/measure_screen.py` gives the median and maximum text items per frame (`uvk-film-audit`).
- Draw maps from data, never with an image model. The coastline is Natural Earth 1:50m land, public domain
  (`assets/map-land-path.txt`), and the projection is fixed to the central and eastern Mediterranean. A map of
  anywhere else needs the projection in `P()` and `build_land()` changed in a copy of the tool kept in the project,
  and the coastline rebuilt there with `--ne <ne_50m_land.geojson> --land <project>/<coastline>.txt`; pass the same
  `--land` on every build with the copy, since its default resolves beside the copy. Never rebuild it over
  `assets/map-land-path.txt`, the default `--land`.
- Check the contact sheet, then every plate at full size, for clipping, overlaps and lines crossing labels.
- `crop` and `face` positions are fractions of the painting: re-measure them after a repaint.
- Build every plate of one film on one machine: the fonts fall back from Big Caslon and Hoefler Text to Libre Caslon,
  Georgia or the browser's serif.
- A plate that teaches a fact answers the next check about it. Put it after that check, or make sure the player blurs
  the film while the check is open (`uvk-checks-make`).
