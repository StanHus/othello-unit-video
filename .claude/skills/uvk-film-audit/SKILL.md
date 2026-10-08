---
name: uvk-film-audit
description: Run the per-shot test on a rendered film, asking for every shot whether its picture shows what the line being spoken is about (carries, partly or competes), with totals by count and by screen time, and measure on-screen text and picture detail. Use after a render and before sharing, when pictures may compete with their lines, or to decide which lines need plates.
---

# Per-shot test

For every shot: does the picture show what the line being spoken is about? The test asks where a student should look
during each line; a picture with no clear subject spreads attention over all of it. Method and limits:
`research/METHODS.md`, method 1. Commands run from the repository root. `<project>` is the project folder, outside
this repository, and `<film>` the version being audited, `<project>/film/vNN`.

## Judge

1. Take one frame per shot. The render's QA (`uvk-film-make`) writes one per cut into `<film>/render/frames/`. For a
   film with motion, grab each shot's midpoint and note the motion.
2. For each shot, write the words spoken while it is on screen (in this pipeline, from its `spoken_anchor` to the
   next shot's), where a student should look, what the picture shows, and a verdict:
   - **carries**: the picture shows what the line is about;
   - **partly**: it shows some of it;
   - **competes**: the picture is about something else.
3. A narrator figure talking to camera is **partly** when the line is about the student's task or the film's framing,
   and **competes** when it is about a character or a concept.
4. Total the verdicts by count and by share of screen time, and fix every line that does not carry: a structural line
   (a definition, a list, a place, the ranks) gets a plate (`uvk-plates-make`); a story line gets a painting that
   shows it (`uvk-art-make`). Paintings alone carried 12 of 22 lines here, and all 10 misses were structural; plates
   on those 10 made 22 of 22 carry.
5. Count clutter both ways: text items per frame (the names and labels on screen, not captions) and picture detail as
   edge density. Plates bring text: with them, text was on screen for 51% of the runtime.

## Measure

`tools/review/measure_screen.py` reads one folder per film, so give it the version's folder. Write `<film>/shots.json`,
one entry per cut with `n`, `start`, `end`, `frame` (relative to `<film>`, such as `render/frames/<file>.jpg`) and
`text_items` (for a plate, the number of items in its `on_screen_text` in `plates.json`; for a painting, 0), and
`<film>/verdicts.json` as `{"verdicts": [{"n", "verdict"}]}`. Then:

```
python3 -I tools/review/measure_screen.py --dir <project>/film --films vNN --reference-words <words> \
  --out <film>/measures.json
```

`--reference-words` is the script's word count (434 for this repository's film). The output gives the verdicts by
count and by share of runtime; the median and maximum text items per frame, and how many frames have any; and the
median, minimum and maximum edge density, measured on a 640x360 copy of each frame cropped to 6 to 78% of its height,
so that captions and controls are left out alike.

## Report

In the film's QA record, `<film>/render/QA.md`: a table with one row per shot (`#`, time, line, where to look,
picture, verdict, fix), then the totals and what they show. Say who judged. A builder judging their own plates is
not enough: ask a second judge, or run the `uvk-film-audit` workflow with the render folder's absolute path as
`render_out` (and `out` to save `verdicts.json`); it gives every shot two independent judges, a story lens and a
structure lens, and a third when they split. Publish only the counts when the script is not yours to publish.
