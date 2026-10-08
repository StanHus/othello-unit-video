---
name: uvk-checks-make
description: Write a film's gated checks and wire them into the player, so playback stops at each check, a seek is sent back to the first open check, own-words answers are saved and never marked, one fixed follow-up asks for a reason, and a recognition question decides whether the film goes on. Use when adding or changing checks, recording their spoken lines, or testing the player's gating and storage.
---

# Gated checks

The player is `player/index.html`: one page, no build step, no external requests, and nothing in it replies to what
a student writes. Its data format is in `player/README.md`; `player/sample/checks.json` is a working example and
`kit/templates/checks/checks.example.json` a starting file. Commands run from the repository root. `<project>` is the
project folder, outside this repository, and `<manifest>` its recording manifest.

## Write the checks

`<project>/checks/checks.json` holds `{"voice": {"voice": "<voice of the spoken lines>"}, "checks": [...]}`. Each
check has:

- `id`, unique. `afterScene`: the scene it asks about; `tools/player/build_parts.py` sets `at` to that scene's
  measured end minus 0.3 s and `sceneStart` to its start. `corner`: `bl` or `br`, where the card opens.
- `say`: the words of the spoken question, shown under "Show the words". `ask`: its audio. `correct`: the
  confirmation played after the last right answer. Audio paths are relative to the player folder (`media/...`).
- `steps`: `own_words`, then `probe`, then one or more `choice` steps; or choices alone. `own_words` asks for a
  sentence in the student's words (`stem`, and the `prompt` above the text box). `probe` is the one fixed follow-up,
  asking for a reason (`stem`, `prompt`, `audio`). `choice` is the recognition question: `stem`, two to four
  `options` (the page letters them A to D), `answer` (the index of the right option) and one `feedback` per option.
  End on a choice: only a right choice shows Continue.

Rules:

- Own words first, kept and unmarked; then a recognition question decides whether the film goes on. Ask for own words
  before showing any option, so no option can supply the answer.
- Ask only about what the film has already said. Nothing a student sees or hears before the first attempt may give
  the answer, the question's own wording included; the player blurs any plate behind the card.
- Feedback on a wrong option says why it is wrong and points back to the scene without naming the right one. Feedback
  on the right one can quote the play with act.scene, as the sample does.
- Never mark own words, reply to them or send them to a marker. An AI marker tested here gave the exact verdict on 58
  of 63 realistic answers, but held back 3 of the 22 right ones and passed one wrong paragraph (claim 5 in
  `research/FINDINGS.md`).
- Use check questions that come with a script word for word, and keep them out of anything you publish. A question
  you write stays a draft until it is explicitly approved.

## Record the spoken lines

Write a line manifest, `<project>/checks/lines.json`, so the words shown are the words heard: the recording-manifest
format, one scene per spoken line, with `scene_number`, `clip_id` and `spoken_text_exact`. A question's words are its
`say` and a follow-up's are its probe's `stem`; write each confirmation into the line manifest directly, since the
checks file holds only its audio. Generate every line and verify it twice, as narration (`uvk-narration-make`):

```
python3 tools/narration/generate_takes.py --manifest <project>/checks/lines.json --out <project>/checks/lines \
  --model <model> --voice <voice>
python3 tools/narration/verify_take.py --manifest <project>/checks/lines.json <clip_id> \
  <project>/checks/lines/<clip_id>.wav
python3 tools/narration/align_words.py --manifest <project>/checks/lines.json --no-prompt <clip_id> \
  <project>/checks/lines/<clip_id>.wav
```

Check short lines as strictly as long ones: one model dropped half of a 17-word line. Copy each verified take into
`<project>/player/media/questions/`, as WAV or encoded to `.m4a` with ffmpeg, and point `ask`, `correct` and the
follow-up's `audio` at it. Listen to the lines beside the film: they should sit at its level (the film is delivered
at -16 LUFS integrated).

## Build and serve

```
mkdir -p <project>/player && cp player/index.html <project>/player/     # the project keeps its own copy of the page
python3 tools/player/build_parts.py --film-dir <project>/film/vNN/render --parts <manifest> \
  --checks <project>/checks/checks.json --player-dir <project>/player --storage-tag vNN
node tools/player/serve.js 8780 <project>/player                       # HTTP Range, so seeking works
```

`build_parts.py` writes the film and its parts into the player's `media/`, and `content/checks.js` (the full film)
and `content/checks-parts.js` (the parts) into its `content/`. Always pass `--player-dir`: its default is this
repository's `player/`. The parts come from the manifest's `parts` list (`part`, `title`, `scenes`), are cut at scene
boundaries and must each run at most `--max` seconds (default 120). Give every new timeline a new `--storage-tag`;
the answers are stored under it. `--poster`, `--title` and `--subtitle` set the cover image and the page's labels.

## What the player enforces

Keep all of it, and test it again after any change to the page or the checks.

- Playback pauses at each check, and Play is refused while its card is open.
- A seek cannot pass an open check: it is sent back to just before the first one (in the v5 test a jump to 200 s
  landed at 47.05 s). Once a check is done, seeks up to the next open one are allowed.
- While a card is open the film is blurred and dimmed and the captions hide, so a plate or a painting cannot give the
  answer away.
- The question audio plays as the card opens. "Hear again" repeats it, "Show the words" shows `say`, and if the
  browser blocks the audio the button turns into "Hear the question". A silent clip played on the first tap or key
  press keeps later question audio from being blocked.
- "Hear the scene again" closes the card and replays the scene from `sceneStart`.
- Own words and the follow-up are refused only as noise (fewer than four words, a run of repeated letters, too few
  real words), with a fixed prompt and no reply; otherwise they are saved and shown back as "Your words".
- A wrong option shows its own feedback and leaves the others open. A right option gives Next, or on the last step
  Continue and the confirmation audio.
- In parts mode (`?parts`) later parts unlock only after the earlier parts and their checks are done, and the parts
  play on by themselves.
- Attempts, own words and position stay in the browser's localStorage under the configuration's key.

## Test in a browser

Serve the project's player with `tools/player/serve.js` (Python's `http.server` breaks video seeking), in a fresh
browser profile with media muted. Walk every check: the pause at its time, the blur, the question audio, noise and a
two-word answer refused, a sentence saved and shown back, the follow-up, a wrong and a right option, Continue, a seek
past an open check, a reload, `?parts`, and a 390x844 phone width, where the card becomes a bottom sheet. Record each
result in the project's player `QA.md`, as `player/QA.md` does. Use a browser no one else is using. Automated runs
are muted, so a person still has to watch the film with sound.
