---
name: uvk-narration-make
description: Generate, verify and time unit-video narration and the spoken check lines with a Gemini TTS model, one take per scene. Use when recording or re-recording narration, choosing a voice or model, checking a take, aligning words for cuts and captions, or fitting a length cap without cutting a word.
---

# Narration: generate, verify, align

Commands run from the repository root. `<manifest>` is the project's recording manifest and `<takes>` its takes
folder, `<project>/narration/takes/vNN`. The key comes from the environment (`GENAI_API_KEY` or `GEMINI_API_KEY`).

## Audition, then choose by ear

Before generating every clip, read one passage with a few models or voices, one folder per take:

```
python3 tools/narration/generate_takes.py --manifest <manifest> --only <clip_id> --model <model> --voice <voice> \
  --out <project>/narration/auditions/<YYYY-MM-DD-slug>/<model>-<voice>
python3 tools/narration/judge_takes.py --takes <project>/narration/auditions/<YYYY-MM-DD-slug> --clip <clip_id> \
  --reference <manifest> --out <project>/narration/auditions/<YYYY-MM-DD-slug>/judgments.json
```

Each judge model hears every seed's shuffle under letter labels, so no judge sees a model or voice name. Give
`--rubric` your own brief and criteria, starting from `kit/templates/narration/rubric.example.json`, to judge the
register you want. Read every pass, not only the Borda total: in one audition the same judge reversed its ranking
between two shuffles of the same takes. Report splits as they fell, for example "two of three judges preferred the
brisker read; one heard it as far too young". The judges assist a listen; they never replace it.

## Generate

```
# every clip
python3 tools/narration/generate_takes.py --manifest <manifest> --out <takes> --model <model> --voice <voice> \
  --style "<direction>. Do not add or change any words. The text to read is: "
# one clip again
python3 tools/narration/generate_takes.py --manifest <manifest> --out <takes> --model <model> --voice <voice> \
  --style "<direction>. Do not add or change any words. The text to read is: " --only <clip_id> --force
```

- The direction sets the register only, and ends as the tool's default does: no added or changed words, then
  "The text to read is: ".
- One folder per model, voice and direction, and the same `--model`, `--voice` and `--style` on every run into it.
  The tool records them once for the whole folder and skips any clip whose text has not changed, whatever the voice,
  so a new voice in an old folder leaves old takes under a new label.
- Never run two generators into one folder: each rewrites `narration-manifest.json` and drops the other's clips.
- The spoken check lines (each question, its confirmation, any follow-up) go through the same tools, from a line
  manifest of their own (`uvk-checks-make`), so the words shown are the words heard.

## Verify every take twice

```
python3 tools/narration/verify_take.py --manifest <manifest> <clip_id> <takes>/<clip_id>.wav
python3 tools/narration/align_words.py --manifest <manifest> --no-prompt <clip_id> <takes>/<clip_id>.wav
```

The first transcribes the take with no script, from the first sound, word-diffs it against `spoken_text_exact`,
writes `<clip_id>.transcript.json` beside it and exits 1 on any difference. The second runs Whisper locally with no
prompt and prints the matched share and any speech the script does not hold. Run both: one model read its direction
aloud before the script in all four of its takes (21 to 31 s each); the blind transcription flagged one and passed
three, and Whisper caught all four.

Accept a take when the blind check matches word for word, or differs only by recogniser noise seen before (number
words, "Moor" heard as "more", "Roderigo" as "Rodrigo", "lie" as "lies"), and Whisper hears no extra speech. Give
`--spoken 1604="sixteen oh four"` for each numeral in the script, so a right reading is not counted as a difference.

Anything else is a real fault: regenerate the clip and verify it again. Faults met here: the direction read aloud,
half of a 17-word line dropped, and "ancient" heard for "ensign". Check short lines as strictly as long ones. Then
listen: both checks assist listening; neither replaces it.

## Time every word

```
python3 tools/narration/align_words.py --manifest <manifest> --narration <takes> --all
```

This writes `<takes>/alignment/<clip_id>.words.json` for every clip: the script's own tokens with measured times,
which the cuts, captions and score use. Whisper is given the script as a prompt, which helps with names but once
skipped half a clip after a quotation (matched 0.46). This project accepted clips at 0.93 matched or higher, where
the misses were digits and name spellings. For a clip below that, align it with no prompt and keep whichever file
matches more words as `<clip_id>.words.json`:

```
python3 tools/narration/align_words.py --manifest <manifest> --no-prompt <clip_id> <takes>/<clip_id>.wav \
  -o <takes>/alignment/<clip_id>.no-prompt.json
```

If neither reaches 0.93, read the unmatched words it prints, and accept the take only when every one is explained,
such as a digit or a name spelling. When a voice runs two sentences together, the silence cross-check reports a
large onset error: check those sentence times by ear before rejecting the take.

## Pace and length

- Measure words a minute over the speech span, first to last aligned word, not over the file: a take that reads its
  direction aloud looks slower than it is.
- The film runs the sum of the speech spans plus each scene's lead-in and tail. The render plan (`uvk-film-make`)
  gives the exact length before anything is rendered.
- Meet a length cap by changing the model or splitting the film into parts, never by cutting words or stretching a
  take. Try another model with the same voice first: one model read this script at about 140 words a minute whatever
  the direction; another reached 158 without time-stretching.
- `tools/narration/tighten_clips.py` caps long pauses, but its default tempo lift (1.18) is a time-stretch: always
  pass `--tempo 1.0`, and measure what the cap saves before planning around it. It removes only the part of a pause
  above the cap, and breaths sit above the silence floor. Verify and align the new folder afterwards.
  ```
  python3 tools/narration/tighten_clips.py <takes> <new takes folder> --tempo 1.0 --max-pause 0.3
  ```
