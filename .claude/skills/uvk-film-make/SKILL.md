---
name: uvk-film-make
description: Cut held paintings and plates to spoken anchors, fit the score to the measured narration, mix, caption with bold key words, render the film and run its QA. Use when assembling or re-rendering a unit film, changing cut points, captions or the mix, or making a new version the current one.
---

# Render the film

Every cut, caption and music move sits at a measured word time, never at an estimate. Commands run from the
repository root. `<project>` is the project folder, outside this repository (`kit/docs/PROJECT-LAYOUT.md`);
`<manifest>` is its recording manifest, `<takes>` the narration takes with their `alignment/` folder
(`uvk-narration-make`), and `<film>` the version being built, `<project>/film/vNN`.

## Storyboard

Write `<film>/storyboard.json` (`kit/templates/film/storyboard.example.json`; the fields are in `tools/README.md`):
one shot per picture change. The first shot of a scene opens it; every later shot cuts 0.12 s before its
`spoken_anchor`, which must occur exactly once in that scene's `spoken_text_exact`. Paintings carry the story lines
(`uvk-art-make`), plates the structural ones (`uvk-plates-make`).

An `art_path` is an absolute path or a file name found in `--art-dir`, whose default is this repository's
`assets/paintings`. Give every picture its own file name: the renderer keeps its framed copies by file name, so two
pictures with one name collide. `--art-map <file>`, a JSON file of `{"<shot>": "<image path>"}` keyed by shot number,
with absolute image paths, sets a shot's picture without editing the storyboard.

## Score cues

The score moves at spoken phrases. Write `<project>/score/anchors.json`, one list of exact phrases per scene, each
occurring once in its scene, and build the cue sheet from it; the tool refuses a phrase its scene does not hold:

```
node tools/score/generate-score.js --out <project>/score/sketch --manifest <manifest> \
  --anchors <project>/score/anchors.json --cue-sheet <project>/score/cue-sheets/vNN.json
```

The score tools are written for an eight-scene opening: the sketch refuses another scene count, and the cue plan in
`tools/score/fit-score.js` needs at least 4, 3, 3, 2, 3, 2, 3 and 3 anchors in scenes 1 to 8 and has no plan beyond
scene 8. For fewer scenes, write the cue sheet by hand in the same format
(`kit/templates/score/cue-sheet.example.json`). More than eight scenes need a change to the tools (`PALETTE` and
`INTENT` in `fit-score.js`), made and checked with `kit/scripts/check.sh` and `kit/scripts/smoke.sh` outside any
project run, never as a step of one.

## Render

```
node tools/film/render-narrated.js --stage plan --manifest <manifest> --storyboard <film>/storyboard.json \
  --cue-sheet <project>/score/cue-sheets/vNN.json --narration <takes> --alignment <takes>/alignment \
  --art-dir <project>/art/finished --out <film>/render
```

`--art-dir` is the finished set (`uvk-art-make`), or `<project>/art` while the paintings are unfinished. The plan
resolves every anchor, writes the timeline and the captions, prints the length and its `warnings`, and renders
nothing; an anchor that is missing or ambiguous stops it. Fix anchors there. Then run the same command without
`--stage` (score, mix and picture), and then the QA:

```
node tools/film/render-narrated.js --stage qa --out <film>/render --manifest <manifest> --whisper large-v3-turbo
```

The QA transcribes each scene of the final mix through the model API (`--no-transcribe` skips that); `--whisper`
adds a local second recogniser that checks the caption timing.

Settings:

- `--impact-phrase "<phrase>"`: the exact phrase in scene 8 after which the score's last low impact falls; without
  it there is none.
- `OTHELLO_LEAD_IN` and `OTHELLO_TAIL`: seconds of near-silence before each scene's first word and after its last,
  as JSON lists with one number per scene. The defaults are for eight scenes; give a longer tail where a check follows.
- `OTHELLO_BOLD`: a JSON list of key words or phrases to bold wherever a caption says them, such as
  `'["Venice", "Cyprus"]'`.
- Export the variables before the plan, so that the plan and the render agree.
- `--test` stamps every output TEST-ONLY. Never ship a test render.

## Accept when

Read `<film>/render/qa-results.json`:

- `duration_check`: the container equals the plan, within any length limit set for the film. If it runs long, split
  it into parts or re-read it with a faster model (`uvk-narration-make`); never cut a line or stretch the voice.
- `loudness_mp4_aac`: about -16 LUFS integrated and a true peak of at most -1 dBTP. Read the number: the final film
  here measured -0.9 dBTP, 0.1 dB over.
- `speech_vs_music`: the voice 14 dB or more over the music in every scene (14.0 to 19.4 dB in the final film here).
- `caption_lines.exact_text` is true and `captions_vs_alignment` shows no error beyond rounding: the captions are the
  script, at the measured times.
- `final_mix_transcription`: each scene exact, or differing only by recogniser noise seen before (number words, name
  spellings, "Moor" heard as "more"). In the final film here 6 of 8 scenes came back exact. Listen to anything else.
- `frames/`: one frame per cut. Open every one and check that the right picture is there and shows what its brief
  says. The frame check confirms the file, not the content: a repaint whose content had changed passed it here.
- With `--whisper`, `captions_vs_whisper`: over music the recogniser's word starts run ahead of the captions (a median
  of 0.325 s on v1). That is the recogniser's bias, not late captions.

Write the results with their numbers, and what was not checked, into `<film>/render/QA.md`.

## The player

The film and its parts go into the player at the checks stage (`uvk-checks-make`, "Build and serve"). Always pass
`tools/player/build_parts.py` the `--player-dir <project>/player`, since its default is this repository's `player/`,
and give every new timeline a new `--storage-tag`, so answers saved against the old one never carry over.

## Versions

Keep every version in its own folder; the project's `film/README.md` says which one is current
(`kit/docs/NAMING.md`). When only the pictures change, reuse the narration, the alignment and the cue sheet, so the
timeline and the mix stay the same: v6 kept v5's narration, score and timeline, and added plates.
