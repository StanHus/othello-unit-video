# Tools

The pipeline that turns a fixed script into a narrated, captioned film with gated checks, and the measures used to
compare unit-opening films. Every timing in the film (cuts, captions, music moves) comes from measured speech, never
from an estimate. The script, narration audio and rendered films of the study are not in this repository, so the
narration and film tools need your own inputs; the score, the plates and the player sample run from this repository
alone.

## Requirements

- ffmpeg and ffprobe on PATH; Node 18 or later; Python 3.9 or later (tested on 3.9 and 3.13)
- Python packages: `requests`, `google-genai`, `Pillow`; `openai-whisper` for word alignment and the caption timing
  check (runs on CPU; the films used `large-v3-turbo`)
- Chrome or Chromium for the plates (`CHROME_BIN`, else `google-chrome` / `chromium` on PATH)

## Keys and endpoints

Model-calling tools read the key from `GENAI_API_KEY` (or `GEMINI_API_KEY`). `GENAI_BASE_URL` is optional and
defaults to the public Gemini API; `GENAI_AUTH_HEADER` names the header a proxy expects the key in. No tool writes a
key or an endpoint into its outputs. Models can be changed with `TTS_MODEL`, `TTS_VOICE`, `TTS_STYLE`,
`TRANSCRIBE_MODEL`, `IMAGE_MODEL` and `JUDGE_MODELS`.

## Order of use

1. `narration/generate_takes.py`: one TTS take per scene, with provenance.
2. `narration/verify_take.py`: transcribe each take with no script and word-diff it; regenerate any take that differs.
3. Optional: `narration/judge_takes.py` to compare auditions blind; `narration/tighten_clips.py` to cap pauses.
4. `narration/align_words.py --all`: word times for every clip, mapped onto the exact script tokens.
5. `score/generate-score.js`: the score sketch, and the cue sheet that binds music moves to spoken phrases.
6. `art/generate_paintings.py`, `art/finish_paintings.py`, `plates/build_plates.py`: paintings for story lines,
   labelled plates for structural lines; `art/export_web_copies.py` makes the published copies.
7. `film/render-narrated.js`: timeline, captions, fitted score (through `score/fit-score.js`), ducked mix, picture and QA.
8. `player/build_parts.py`: the film and its parts for the player, with the checks placed at measured scene ends;
   `player/serve.js` to run it.
9. `review/measure_fidelity.py`, `review/measure_screen.py`: comparison measures.
10. Optional: `library/library.py` to catalogue the project's documents and media, with curated cards and topic pages.

## What each tool does

| tool | what it does | inputs | outputs |
|---|---|---|---|
| `narration/generate_takes.py` | Gemini TTS take per scene; skips clips whose text hash matches the last take | recording manifest, `--out`, model, voice, style | `<clip_id>.wav`, `narration-manifest.json` (model, voice, style, words, duration, text sha256) |
| `narration/verify_take.py` | no-hint transcription from the first sound, word diff against the exact text | manifest, clip id, WAVs | `<take>.transcript.json`, MATCH or DIFF; exit 1 on any difference |
| `narration/judge_takes.py` | blind comparison of takes by audio-capable LLM judges: seeded shuffles, letter labels mapped back, Borda count | folder of take folders, clip id, reference text, optional rubric | `judgments.json` with every pass and its raw reply; table of mean score, Borda points, first places |
| `narration/tighten_clips.py` | caps internal pauses (ffmpeg silenceremove) and lifts tempo (atempo), re-measures durations | takes folder with `narration-manifest.json` | tightened WAVs and manifest |
| `narration/align_words.py` | local Whisper word timestamps mapped onto the script's own tokens; onsets inside a silence snapped to its end | manifest, clip and WAV, or `--narration` with `--all` | `<clip_id>.words.json`: words, sentences, matched ratio, extra heard speech, silence cross-check |
| `score/generate-score.js` | original synthesis (sine-table pads, low pulse, air, sparse impacts, bells; seeded PRNG, no samples) | optional manifest, anchor phrases | eight FLAC beds, `bed-demo.m4a`, optional cue sheet; with no manifest it reproduces `assets/score-sketch.m4a` sample for sample |
| `score/fit-score.js` | regenerates each bed at its measured scene length, places every music move at its anchor's measured time, crossfades scenes over 2 s | timeline, alignment, manifest, optional impact phrase | fitted beds, full bed, `fitted-cue-sheet.json` |
| `film/render-narrated.js` | cuts 0.12 s before each anchor word; captions of at most 84 characters on two lines, from first word -0.05 s to last word +0.3 s; music 10 LU under the voice and ducked 8 dB under measured speech; -16 LUFS, true peak at most -1 dBTP; picture in a book-page frame | manifest, storyboard, cue sheet, narration, alignment, art folder | `narrated-timeline.json`, MP4 with captions track, VTT, stems, `qa-results.json` |
| `plates/build_plates.py` | ten plate layouts (title, arc, checklist, map, caption, label card, rank ladder, quotation with steps and definition, rise-and-fall curve, word list), rendered by headless Chrome | content JSON (`plates.example.json`), paintings, coastline | plate PNGs, `plates.json` with every on-screen word, contact sheet |
| `art/generate_paintings.py` | scene paintings from a style prompt, a character bible and a subject, with reference paintings for style and faces | `assets/painting-briefs.json`, reference folder | JPEGs, `art-manifest.json` (refs, full prompt, sha256) |
| `art/finish_paintings.py` | image-to-image repaint in one finish (engraved line and watercolour wash) | source paintings | finished JPEGs, `manifest.json` |
| `art/export_web_copies.py` | published copies: resize, JPEG, every metadata block removed (EXIF, XMP, IPTC, ICC, C2PA, comments) | images | copies and `web-copies.json` (size, bytes, sha256) |
| `player/build_parts.py` | cuts the full film and parts at scene boundaries, splits captions, places each check at scene end -0.3 s | render folder, parts JSON, checks JSON | `player/media/*`, `player/content/checks.js`, `checks-parts.js` |
| `player/make_sample_media.py` | a silent 24 s sample film from three published images, chimes for the questions, then `build_parts.py` | `player/sample/` | sample media and checks for the player |
| `player/serve.js` | static server with HTTP Range support (video seeking fails without it) | port, root folder | |
| `review/measure_fidelity.py` | script fidelity: reference words found in order; optional Whisper agreement per film | reference script, film scripts, optional Whisper word lists | `fidelity.json` (counts; word differences only with `--diffs`) |
| `review/measure_screen.py` | per-shot verdict shares by count and by runtime, text items per frame, edge density, pace, first time a word is heard | film folders with `shots.json` (and `verdicts.json`) | `measures.json` |
| `library/library.py` | catalogue of a project folder: one item per document, with its extracted text (PDFs through `pdftotext` when on PATH), one per media folder; curated cards merged in; `check` flags broken `supersedes` links, unknown kinds, tags and statuses, and cards that match no file; `search` ranks items by terms | `--root` project folder, `--out` library folder, cards in `<out>/curation/*.json` | `catalog.json`, `CATALOG.md`, `topics/`, `text/`, all in `--out` |

## Input formats

- Recording manifest: `{"scenes": [{"scene_number", "clip_id", "title", "spoken_text_exact"}], "parts": [...]}`.
  `spoken_text_exact` is the only source of words: captions are built from it, never from a transcript.
- Storyboard: `{"shots": [{"shot", "scene", "art_path", "visual_caption", "spoken_anchor"}]}`; each
  `spoken_anchor` must occur exactly once in its scene's text.
- Cue sheet: `{"scenes": [{"scene", "clip_id", "spoken_anchors": [{"phrase"}]}]}`; the cue plan in `fit-score.js`
  expects 4, 3, 3, 2, 3, 2, 3 and 3 anchors in scenes 1 to 8.
- Checks: see `../player/README.md`.

## Method notes from the study

- A TTS take can read its style direction aloud and still pass a word diff when the transcriber is given the script:
  it drops the extra speech. `verify_take.py` transcribes with no script, from the first sound. In the study a no-hint
  transcription still passed 3 of the 4 takes that read their direction; Whisper with no prompt
  (`align_words.py --no-prompt`, reported as extra heard speech) caught all four, so run both.
- Run that check on short lines too. One model dropped half of a 17-word line.
- Whisper given the script as its initial prompt handles names better but can skip speech: on one clip it skipped half
  the speech after a quotation (matched 0.46). Re-run with `--no-prompt` and keep the better alignment.
- Whisper can loop a phrase over music or silence. Words heard after the last script word are reported as extra
  speech and never timed.
- When a TTS model runs sentences together with no pause, the nearest silence belongs to another sentence and the
  alignment's silence cross-check reports a large onset error. Check those sentence times by ear before rejecting the take.
- Score script fidelity on each film's script, not on a recogniser transcript, or recogniser errors count as script
  changes. Recurring recogniser errors here: "Moor" heard as "more", "Roderigo" as "Rodrigo", numerals, "lie" as "lies".
- `tighten_clips.py` removes only the part of a pause above its cap, and breaths sit above the silence floor: measure
  what a cap saves before planning around it.
- One TTS model read this script at about 140 words a minute whatever the direction; another reached 158 without
  time-stretching.
- Blind judges of audio changed their ranking between shuffles of the same takes, and returned labels in varied
  forms: keep every pass and its raw reply.
- Image-to-image finishing changed content in 1 of 18 paintings (see `../assets/README.md`). A frame check that
  confirms which file is on screen does not catch that; look at every output.
- Contact sheets built with an `fps` filter can drop tiles. Confirm with direct frame grabs (`ffmpeg -ss`).
