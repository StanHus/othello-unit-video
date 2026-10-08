# Assets

The study's own images and music, published as small copies. Every image is AI-generated, or built from the
AI-generated paintings, and shows the play's characters and places; none carries legible text except the example
plate's quotation. Provenance per file, with the sha256 of each published copy, is in `paintings.json`; the generation
prompts are in `painting-briefs.json`.

## Paintings (`paintings/`, 17 files, 1600 x 893)

How they were made:

1. Six base paintings were generated for the project before this pipeline (their model and prompts were not
   recorded): `venice-establishing`, `venice-love`, `venice-household`, `venice-ranks`, `act1-night-quay`, `cyprus-dawn`.
2. Eleven more (ten in this folder and the bedchamber in `drift/`) were generated with `gemini-3-pro-image-preview`
   by `tools/art/generate_paintings.py`. Each prompt is a shared style paragraph, the descriptions of the characters
   shown (one character bible, so faces and costumes stay the same across images) and a subject, sent with one or
   two base paintings as style and face references. A twelfth, `ottoman-fleet`, came from an early test run of the
   same model; its prompt was not recorded.
3. All eighteen (these seventeen and the bedchamber below) were then repainted in one finish, an engraved line with
   a watercolour wash, image to image with the same model (`tools/art/finish_paintings.py`).

Each painting was checked by eye during production, not by an independent reviewer, against four rules: no legible
text; no death shown; faces readable and dignified; each character recognisably the same person across paintings.
Some banners show illegible marks.

| file | shows | in the play |
|---|---|---|
| `venice-establishing.jpg` | Venice at dusk: canal, domes, gondolas | Act 1 setting |
| `venice-love.jpg` | Othello and Desdemona, hands joined, on a balcony over a canal | Acts 1-2 |
| `venice-household.jpg` | Desdemona with her attendant; an old senator behind them | Act 1 |
| `venice-ranks.jpg` | Othello, Cassio and Iago in a hall; Iago holds the banner | the ranks (1.1) |
| `act1-night-quay.jpg` | Iago and Roderigo on a quay at night | 1.1 |
| `cyprus-dawn.jpg` | Othello on a rampart above the Cyprus fortress | Acts 2-5 setting |
| `venice-senate.jpg` | The Senate in session; Othello before the Duke | 1.3 |
| `ottoman-fleet.jpg` | The Ottoman fleet seen from the Cyprus ramparts | the threat reported in 1.3 |
| `secret-wedding.jpg` | The secret wedding by candlelight | before the play opens |
| `roderigo-pays-iago.jpg` | Roderigo presses a purse into Iago's hand | 1.1 |
| `iago-and-the-masks.jpg` | Iago between carnival masks, reflected upside down in the canal | 1.1 |
| `honest-iago.jpg` | Othello hands Desdemona into Iago's care; Iago's far hand clenched behind his back | 1.3 |
| `rampart-storm.jpg` | Othello alone on a rampart in a night storm | Acts 3-5 |
| `lieutenant-and-ensign.jpg` | Othello gives Cassio a sealed order; Iago holds the banner | the ranks (1.1) |
| `canal-shadow-and-light.jpg` | Iago and Roderigo in shadow; the couple lit across the canal | Acts 1-2 |
| `fortress-gate.jpg` | Othello walking alone into the fortress gate at dusk | Acts 2-5 |
| `couple-and-shadow.jpg` | The couple at first light; a hooded man's shadow across the floor | Acts 1-2 |

## The finish test (`finish-test-comparison.jpg`)

Goal: reduce the glossy look of generated images without changing composition or characters. Three paintings (rows:
the couple, `honest-iago`, `ottoman-fleet`) were each repainted in two finishes, image to image, with the original as
the input (columns: original, A old-master oil, B engraved line and wash).

- A (oil) barely changed them: darker and a little more textured, with the same digital gloss.
- B (engraved line and wash) changed the surface clearly: ink hatching, flat quiet light, paper texture.
  Composition and faces held on all three; `honest-iago` stayed closest to painted.

B was applied to all eighteen paintings. Seventeen kept their composition and content. One did not:

## Content drift in the finish pass (`drift/`)

`bedchamber-original.jpg` matches its brief: an empty bedchamber at night, three candles just out and smoking, the
last one guttering, the strawberry handkerchief on the table, no people. The finished version,
`bedchamber-finish-b.jpg`, added an embracing couple (the man does not match the Othello of the other paintings),
and the smoke and the last flame are gone. The prompt asked for the finish only. The finished painting was used in
a film under the line that names the death, and the film's frame check passed it, because that check confirmed which
file was on screen, not what the file showed. These two files are published only as this example.

## Example plate (`example-plate-quotation.jpg`)

One labelled plate from `tools/plates/build_plates.py` (type `quote`): Iago's "I am not what I am." (1.1.71, Folger
line numbering) on a card over `iago-and-the-masks`. In the films, plates like this carried the structural lines of
the narration (a quotation, a map, the ranks, a word list) while paintings carried the story lines.

## Score sketch (`score-sketch.m4a`)

234 s of original instrumental music, eight beds in sequence, no voice: sine-table pads, a low pulse, filtered air,
sparse low impacts and bells, from a seeded random generator; no samples, loops or third-party music. Rebuild it with
`node tools/score/generate-score.js --out <dir>`: the beds come out sample for sample the same. In the films the beds
were refitted to the measured narration by `tools/score/fit-score.js`.

## Coastline (`map-land-path.txt`)

SVG path data for the plate map: Natural Earth 1:50m land polygons (public domain), clipped to the Mediterranean and
projected by `tools/plates/build_plates.py --ne <ne_50m_land.geojson>`.

## How the copies were made

`tools/art/export_web_copies.py`: paintings resized to 1600 px on the long edge (Lanczos) at JPEG quality 80, the
drift pair at 1000 px, the plate re-encoded from PNG, the comparison sheet copied losslessly. Every metadata block was
removed: EXIF, XMP, IPTC, ICC profiles, embedded C2PA provenance manifests and encoder comments. The score was
remuxed with empty container tags; its audio stream still carries the encoder's version string.
