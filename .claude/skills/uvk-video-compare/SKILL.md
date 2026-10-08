---
name: uvk-video-compare
description: Compare several productions of the same script, such as a stills film, an animated version and a 3D version built in code, on one rubric fixed in advance, with every measure taken the same way, including script fidelity, the per-shot test, pace, screen density, gated checks and the narrator's role. Use when choosing between approaches, or when someone claims one film is better.
---

# Compare films

Commands run from the repository root. `<project>` is the project folder, outside this repository; `<manifest>` the
reference script; `<review>` the comparison folder, `<project>/review/<YYYY-MM-DD-slug>`, with one subfolder per film
(`stills/`, `animated/`, `3d/`).

## Fix the rubric first

Copy `kit/templates/review/rubric.example.md` to `<review>/rubric.md` and settle every row, and how each is checked,
before measuring anything. The rows used here (`research/METHODS.md`, method 2): script fidelity; coverage of the
opening's knowledge areas; how it opens, teaches and closes; checks that gate playback; pictures that teach
structure; the per-shot test; length and words per minute; visual density per frame; look and motion; the narrator's
role.

## Capture each film

- **A video file.** Probe it, find every shot boundary, grab one frame per shot at its midpoint, and transcribe it.
  Scene detection finds hard cuts and misses soft ones: in the animated version measured here, a threshold of 0.25
  found 8 of its 35 transitions. Mark soft transitions from scene-score peaks of 0.10 or more and frame-difference
  spikes, and confirm each by eye.
- **A live build** (HTML or 3D in a browser). Record the text its narration is generated from, the chapter times, the
  on-screen text each second and the checks: how many, whether playback waits for an answer, whether a seek can pass
  an open check. Never submit answers to a build you do not own: record its gating by watching what it does.

Save into each film's folder (`kit/templates/review/fidelity.example.json` and
`kit/templates/review/measures.example.json` lay these inputs out for three films):

- `script.txt`: the script its narration was generated from. If a film has none, say so and leave its fidelity
  unscored: scored on a transcript, recogniser errors count as script changes.
- `whisper-noprompt.json`: Whisper with no prompt and the same settings for every film (the command below), its
  words flattened to `{"words": [{"w", "s", "e"}]}`. Drop the words heard after the last script word, because Whisper
  loops phrases over music and silence, and note what was dropped.
- `shots.json`: `{"shots": [{"n", "start", "end", "frame", "text_items"}]}`, with `frame` relative to the film's folder
  and `text_items` the names and labels on screen, not captions.
- `verdicts.json`: the per-shot test (`uvk-film-audit`), judged the same way for every film.
- `notes.md`: how the film was captured, its checks, narrator and music, and what could not be captured.

```
whisper <audio> --model large-v3-turbo --word_timestamps True --output_format json --language en --fp16 False \
  --output_dir <review>/<film>
```

## Measure the same way

```
python3 -I tools/review/measure_fidelity.py --reference <manifest> --out <review>/fidelity.json \
  --film stills=<review>/stills/script.txt --whisper stills=<review>/stills/whisper-noprompt.json \
  --film animated=<review>/animated/script.txt --whisper animated=<review>/animated/whisper-noprompt.json \
  --film 3d=<review>/3d/script.txt --whisper 3d=<review>/3d/whisper-noprompt.json
python3 -I tools/review/measure_screen.py --dir <review> --reference-words <words> --out <review>/measures.json
```

- Score fidelity on each film's script; Whisper only confirms that the audio reads it. Scored on recogniser output,
  one film here came out at 98.4% purely from recogniser errors.
- `--reference-words` is the reference script's word count (434 in this repository's comparison).
  `--first-word <word>`, in lower case, adds the time a word is first heard, such as a key term.
- `--diffs` adds the word-level differences, which quote the scripts: keep them local when a script is not yours to
  publish.

## Write it up

`<review>/README.md`: one table, the rubric rows by film; then at most five findings, each with its numbers, the
strongest counter-argument and the test that would settle it (the shape of `research/FINDINGS.md`); then corrections
to earlier claims; then what was not checked. Quote exactly and attribute exactly: a document's account of what
someone said is not their words. Describe other productions by what they are ("an animated version", "a 3D version
built in code"), and publish only your own measurements of them, never their frames, transcripts, scripts or rubrics.

The `uvk-video-compare` workflow captures and judges each film in parallel, scores the rubric from the saved files,
has three refuters try to break every claim, and writes up only the claims that survive.
