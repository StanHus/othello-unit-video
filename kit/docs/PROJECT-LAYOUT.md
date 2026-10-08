# Project layout

A project is a folder outside this repository, named by [NAMING.md](NAMING.md). The tools assume no layout: every
path goes in by flag, every command runs from the repository root, and nothing in a project run writes into the
repository. This is the layout the skills use; `<project>` below is the project folder.

| path in `<project>` | what | given to |
|---|---|---|
| `README.md` | what the project is and which version of each part is current | |
| `sources/` | documents as received, the script among them as `script.txt`, verbatim, dated and read-only | `measure_fidelity.py --reference` |
| `script/vNN/manifest.json` | the recording manifest: scenes and parts (`kit/templates/script/manifest.example.json`) | `--manifest` of the narration, score and film tools; `build_parts.py --parts` |
| `narration/auditions/YYYY-MM-DD-slug/` | one folder per audition take (`<model>-<voice>/`), and `judgments.json` | `generate_takes.py --out`; `judge_takes.py --takes` |
| `narration/takes/vNN/` | one WAV per scene, `narration-manifest.json`, `<clip_id>.transcript.json` | `generate_takes.py --out`; `align_words.py --narration`; `render-narrated.js --narration` |
| `narration/takes/vNN/alignment/` | `<clip_id>.words.json` for every clip, written by `align_words.py --all` | `render-narrated.js --alignment` |
| `art/briefs.json`, `art/refs/` | the briefs and the reference paintings they name | `generate_paintings.py --briefs`, `--refs-dir` |
| `art/` | the generated paintings and `art-manifest.json` | `generate_paintings.py --out`; `render-narrated.js --art-dir` while the set is unfinished |
| `art/finished/` | the finished paintings and their `manifest.json` | `finish_paintings.py --out`; `render-narrated.js --art-dir` |
| `score/anchors.json` | per scene, the phrases the music moves on (eight-scene films) | `generate-score.js --anchors` |
| `score/sketch/` | the score sketch: stems and `bed-demo.m4a` | `generate-score.js --out` |
| `score/cue-sheets/vNN.json` | the cue sheet (`kit/templates/score/cue-sheet.example.json`) | `generate-score.js --cue-sheet`; `render-narrated.js --cue-sheet` |
| `film/README.md` | which film version is current | |
| `film/vNN/plate-content.json` | the plates' layouts and words (`tools/plates/plates.example.json`) | `build_plates.py --content` |
| `film/vNN/` | `storyboard.json`; `plates/`, `plates.json` and `contact-sheet.jpg` from the plates; `shots.json`, `verdicts.json` and `measures.json` from the audit | `build_plates.py --out`; `render-narrated.js --storyboard`; `measure_screen.py --dir <project>/film --films vNN` |
| `film/vNN/render/` | the timeline, film, captions, stems, `frames/`, `qa-results.json`, `QA.md`, `parts/`, and the fitted score in `fitted/` | `render-narrated.js --out` (`--fitted` defaults to `<out>/fitted`); `build_parts.py --film-dir` |
| `checks/checks.json` | the gated checks (`kit/templates/checks/checks.example.json`) | `build_parts.py --checks` |
| `checks/lines.json`, `checks/lines/` | the spoken check lines as a recording manifest, and their takes | `generate_takes.py --manifest`, `--out`; `verify_take.py --manifest` |
| `player/` | a copy of this repository's `player/index.html`; `media/`, with the spoken check lines and the film files `build_parts.py` writes; `content/`, the check data it writes; `QA.md` | `build_parts.py --player-dir`; `serve.js 8780 <project>/player` |
| `review/YYYY-MM-DD-slug/` | a comparison: `rubric.md`, one folder per film, `fidelity.json`, `measures.json`, `README.md` | `measure_fidelity.py --out`; `measure_screen.py --dir` |
| `library/` | the catalogue, with its cards in `library/curation/` | `library.py build --root <project> --out <project>/library` |
| `FINDINGS.md` | the claims the project stands behind, in the shape of `research/FINDINGS.md` | |

Every tool is under `tools/`, by domain: `tools/narration/`, `tools/art/`, `tools/plates/`, `tools/score/`,
`tools/film/`, `tools/player/`, `tools/review/` and `tools/library/`.

## Settings without a flag

- `OTHELLO_LEAD_IN` and `OTHELLO_TAIL`: seconds of near-silence before each scene's first word and after its last, as
  JSON lists with one number per scene. The renderer's defaults are written for eight scenes; set both for any other
  count, with a longer tail where a check follows.
- `OTHELLO_BOLD`: a JSON list of words or phrases the captions bold wherever they are said.
- `IMAGE_MODEL`: the image model of `generate_paintings.py` and `finish_paintings.py`.
- `TRANSCRIBE_MODEL`: the transcription model of the renderer's QA, which runs `verify_take.py` without `--model`.
- `GENAI_API_KEY` (or `GEMINI_API_KEY`) is the key; `GENAI_BASE_URL` and `GENAI_AUTH_HEADER` only route through a proxy.
- `CHROME_BIN` names the Chrome or Chromium binary for the plates.

The other model settings are defaults for flags: `TTS_MODEL`, `TTS_VOICE` and `TTS_STYLE` for
`generate_takes.py --model`, `--voice` and `--style`, `TRANSCRIBE_MODEL` for `verify_take.py --model`, and
`JUDGE_MODELS` for `judge_takes.py --models`. The tools also read `OTHELLO_MANIFEST`, `OTHELLO_STORYBOARD`,
`OTHELLO_CUESHEET`, `OTHELLO_NARRATION`, `OTHELLO_S8_IMPACT`, `TTS_OUTDIR` and `ALIGN_NO_PROMPT` in place of their
flags. The skills pass flags instead, so every setting a run used is in its command.
