# Troubleshooting

What stops the tools, and what went wrong in this build and what to do instead. The rules are in
[STANDARDS.md](STANDARDS.md); each tool documents its inputs at the top of its file.

## When a tool stops

| message | do this |
|---|---|
| `set GENAI_API_KEY (or GEMINI_API_KEY)` | export the key in the shell that runs the tool; never put it in a file |
| `anchor phrase not found in script` | the phrase must occur in that scene's `spoken_text_exact` exactly, punctuation and curly quotes included |
| `anchor phrase is ambiguous` | lengthen the phrase until it occurs exactly once in its scene |
| `alignment script_text differs from recording manifest` | the alignment was made from another version of the script: verify the takes again, then re-run `tools/narration/align_words.py --all` |
| `missing narration` or `missing alignment` | `--narration` is the takes folder and `--alignment` its `alignment/` folder; generate or align the missing clip |
| `art not found` | give an absolute `art_path`, put the file in the `--art-dir` folder, or point the shot at it with `--art-map` |
| `cue sheet scene N mismatch` | the cue sheet lists the scenes in manifest order, each with its scene's `clip_id` |
| `the cue plan needs N cue-sheet anchors` | `tools/score/fit-score.js` needs at least 4, 3, 3, 2, 3, 2, 3 and 3 anchors in scenes 1 to 8: add phrases to the cue sheet |
| `the palette has 8 scenes, the manifest N` | the score sketch is written for eight scenes: for fewer, write the cue sheet by hand (`kit/templates/score/cue-sheet.example.json`); more than eight need a change to `tools/score/fit-score.js` first (`uvk-film-make`) |
| `unknown arg` from the renderer | it has no such flag: lead-ins, tails and bold words are set with `OTHELLO_LEAD_IN`, `OTHELLO_TAIL` and `OTHELLO_BOLD` |
| `QA needs a timeline from a full render` | render without `--stage` first, then run `--stage qa` |
| `the final-mix transcription needs --manifest` | pass `--manifest` to `--stage qa`, or `--no-transcribe` to skip that check |
| `part N ... > 120s` from `build_parts.py` | a part runs at most `--max` seconds (default 120): move a scene into another part |
| `a checklist holds at most 4 items` (or a rank ladder 3 rungs, a glossary 8 words) | split the content over two plates |
| `Chrome or Chromium not found: set CHROME_BIN` | install Chrome or Chromium, or set `CHROME_BIN` to its binary |

## What went wrong in this build

| what happened | do this |
|---|---|
| Video seeking reset to 0 under `python3 -m http.server` | serve the player with `tools/player/serve.js`, which answers HTTP Range requests |
| `tools/player/build_parts.py` run without `--player-dir` writes into this repository's `player/` | always pass `--player-dir <project>/player` |
| Question audio started from code can be blocked by autoplay rules | the page plays a silent clip on the first tap or key press so that later question audio may play, and turns "Hear again" into "Hear the question" when it is still blocked; test with sound |
| A take read its style direction aloud and still passed a word diff when the transcriber was given the script | verify with `tools/narration/verify_take.py`, which gives no script, and with `tools/narration/align_words.py --no-prompt`, which reports extra heard speech; run both |
| Whisper given the script as its prompt skipped half a clip after a quotation (matched 0.46) | align that clip with `--no-prompt` and keep the alignment that matches more words |
| Whisper looped a phrase over music and repeated a line in closing silence | words heard after the last script word are reported as extra speech and never timed; drop them from comparisons and record what was dropped |
| Sentences run together, so the aligner snapped a sentence start to the wrong silence | when the silence cross-check reports a large onset error, check those sentence times by ear before rejecting the take |
| One speech model would not read faster than about 140 words a minute, whatever the direction | try another model with the same voice before anything else: another read the same script at 158 without time-stretching |
| A pause cap saved far less than planned | `tools/narration/tighten_clips.py` removes only the part of a pause above its cap, and breaths sit above the silence floor: measure what it saves first, and pass `--tempo 1.0`, since its default lifts the tempo |
| A blind judge reversed its ranking between two shuffles of the same takes | read every pass and its raw reply in `judgments.json`, report splits as they fell, and choose by ear |
| The image model drew a border into a painting | check every edge and regenerate |
| A repaint added an embracing couple to an empty bedchamber and put out its last candle, and the frame check passed it | compare every finished painting with its source by eye; the frame check confirms the file, not the picture |
| A repaint can shift what a plate crops | re-measure every `crop` and `face` position a plate takes from the finished painting |
| A generated map got the geography wrong | draw maps from Natural Earth data with `tools/plates/build_plates.py`, never with an image model |
| zsh turned `$n:layout` into a modifier and `$fc[$i]` into a character index | build ffmpeg filtergraphs in Python, not in the shell |
| A contact sheet built with an `fps` filter dropped tiles | confirm every cut with a direct frame grab (`ffmpeg -ss`) |
| Scene detection at a threshold of 0.25 found 8 of a film's 35 transitions | mark soft transitions from scene-score peaks of 0.10 or more and frame-difference spikes, and confirm each by eye |
| Plates built on another machine came out different | build every plate of a film on one machine: the fonts fall back from Big Caslon and Hoefler Text to Libre Caslon, Georgia or the browser's serif |
| A film that reads its script exactly scored 98.4% when fidelity was computed on a recogniser's transcript | score fidelity on each film's own script; the recogniser only confirms the audio |
| The test browser kept restarting during a browser test | another session was using it: test in a fresh, isolated profile, and stop if the browser is in use |
