---
name: uvk-video-make
description: Run the whole unit-video pipeline in order, from a fixed script to a verified, captioned film with gated checks. Use when starting or resuming a unit video, when asked "what's next" on one, or before changing any stage, to know which skill handles it.
---

# Unit video: the pipeline

A unit video opens a unit on a text. It reads a fixed script word for word in one synthetic voice, over held
paintings and labelled plates, with captions and an original score, and stops at checks a student must answer before
it goes on. The script is fixed, a design choice of this project; the work is voice, pictures, checks and timing.
Stages, inputs and the check that ends each one are in `kit/docs/PIPELINE.md`; the rules are in
`kit/docs/STANDARDS.md`.

## Set up

```
cd <this repository>                # every command runs from the repository root
pip install -r tools/requirements.txt
export GENAI_API_KEY=<key>          # or GEMINI_API_KEY; GENAI_BASE_URL and GENAI_AUTH_HEADER only for a proxy
mkdir -p <project>/sources <project>/script/v01   # outside this repository: kit/docs/PROJECT-LAYOUT.md
cp kit/templates/script/manifest.example.json <project>/script/v01/manifest.json
```

ffmpeg, Node 18+ and Chrome or Chromium are needed as well (`tools/README.md`). Every tool takes the manifest and the
project's folders by flag (`--manifest`, `--out` and the like): nothing is written into this repository during a
project run. Always pass the output flag. Several tools write into the current folder without it, and
`tools/player/build_parts.py` into this repository's own `player/`.

## Order

1. **Script.** Copy the script into the manifest: one scene per clip, `spoken_text_exact` verbatim, and a `parts`
   list, which the player needs. For a film not cut into parts, give one part holding every scene, and give
   `tools/player/build_parts.py` a `--max` at least the film's length. Save the script as received as plain text in
   `<project>/sources/script.txt`, then prove the manifest against it:
   ```
   python3 tools/review/measure_fidelity.py --reference <project>/sources/script.txt \
     --film manifest=<project>/script/v01/manifest.json --out <project>/script/v01/fidelity.json
   ```
   Go on only at 100% with the manifest's word count equal to the reference's. Fidelity counts the reference's words
   found in order, so an added word shows only in the count; `--diffs` lists the differences.
2. **Narration** → `uvk-narration-make`: every take verified twice, every word timed.
3. **Paintings** → `uvk-art-make`, for the story lines.
4. **Plates** → `uvk-plates-make`, for the structural lines: a map, the ranks, a quotation and its definition, a word
   list, the title.
5. **Storyboard, score and render** → `uvk-film-make`.
6. **Checks** → `uvk-checks-make`.
7. **Audit** → `uvk-film-audit`. Every picture should carry its line, and a second judge, not the builder, decides.
8. **Share a review copy** only with explicit approval, and never into someone else's environment or files.
9. **Record.** Catalogue the project with `uvk-library-make`, and write each claim with its evidence, the strongest
   counter-argument and the test that would settle it, in the shape of `research/FINDINGS.md`.

When feedback arrives, run `uvk-feedback-sweep` before changing anything. To set the film beside other productions of
the same script, run `uvk-video-compare`. The workflow `uvk-video-make` runs stages 1 to 4 with agents, renders
stage 5 from the storyboard and cue sheet you have written, runs stage 7 and writes the QA record; the checks stay a
separate step.

## Never

- Cut, paraphrase or reorder the script, or time-stretch a take to fit a limit: change the model or split the film.
- Label an estimated time as measured.
- Show or play anything that answers a check before the student's first attempt.
- Send or publish anything without explicit approval, or write into someone else's environment or files at all.
- Write a key into a file, a commit or a log.
