# Othello unit opening: a narrated film with gated checks (Grade 9)

How a short narrated film that opens a Grade 9 unit on Shakespeare's *Othello* was built, checked and measured, and
what the measurements suggest. The film reads a fixed 434-word script word for word in one synthetic voice, over held
paintings and labelled plates, and stops at six checks that a student must answer before it goes on. Seven versions
were built and measured in October 2026. The film was scored against two other productions of the same script on a
rubric fixed in advance, and an AI answer marker in a reading lesson was tested with 63 synthetic but realistic
Grade 9 answers.

No student has used the film. The seven claims below are design hypotheses, each with the test that would settle it.

## Question

How should a short narrated film open a unit on a Shakespeare play when the script is fixed (a design choice of this
project), the voice is synthetic and the film stops for checks? And how can each part be verified before a student
sees it?

1. **Picture.** What should be on screen while each line is read?
2. **Voice.** How fast can a synthetic voice read a fixed script without cutting it, and how do you know it read
   every word?
3. **Checks.** What must a gate block, and should a machine mark a student's own words?
4. **Context.** How much of the play's background belongs before the reading at all?

## What was built

| part | what it is |
|---|---|
| Film (v7) | 2:54 (174.542 s). The 434-word script verbatim at 158 words a minute, with no cuts and no time-stretch. 52 cuts: paintings for the story lines and 35 labelled plates for the structural lines (among them a map, the ranks in order, two definitions and a word list). Captions, and an original synthesised score under the voice. Also cut into three parts of 0:46, 1:01 and 1:07. Not included, because its soundtrack and captions carry the script. |
| Player | Six gated checks. The film goes on only after a right answer, any seek is sent back to the first open check, and the film is blurred while a question is on screen. Free-text answers are saved and never scored; one fixed follow-up asks the student for a reason. [`player/`](player/) holds the engine with sample checks and sample media. |
| Paintings | Scenes of the play made with an image-generation model, then repainted in an engraved finish; no legible text, no depicted death. In [`assets/`](assets/), with one repaint that changed its content kept as a documented example. |
| Score | Original synthesis from a seeded generator (no samples, loops or licensed music), fitted to measured speech. A sketch is in [`assets/`](assets/). |
| Tools | Narration with provenance, blind verification, word alignment, rendering, plates, the player builder, screen measures and a project library, in [`tools/`](tools/). |
| Kit | Claude Code skills and workflows that run these tools in order for a new script, with the rules, templates, project layout and self-checks they follow, in [`kit/`](kit/) and `.claude/`. |

| version | change | words | length |
|---|---|---|---|
| v1 | an earlier script written for the project; 19 cuts over 6 paintings | 470 | 4:44 |
| v2 | the same audio; a painting for each of the 19 cuts | 470 | 4:44 |
| v3 | that script revised; an older-sounding voice | 523 | 5:44 |
| v4 | the fixed script condensed; the voice sped up 1.2×, pauses capped at 0.3 s | 299 | 2:00 |
| v5 | the fixed script verbatim at natural pace (99 words a minute); 22 cuts | 434 | 4:31, or parts of 1:08, 1:31, 1:52 |
| v6 | v5 with labelled plates on its 10 structural lines; 51 cuts | 434 | 4:31 |
| v7 | a faster speech model at 158 words a minute; an engraved finish on every painting; 52 cuts | 434 | 2:54, or parts of 0:46, 1:01, 1:07 |

## Methods

Procedures and limits are in [`research/METHODS.md`](research/METHODS.md).

- **Per-shot test.** For each cut: does the picture show what the line being spoken is about? *Carries*, *partly* or
  *competes*, counted by shot and by share of screen time.
- **Comparison rubric.** Three productions of the same script (this project's stills film, an animated version and a
  3D version built in code) scored on ten rows written before the other two were measured.
- **Narration verification.** Every take is transcribed by a model that is not given the script, then word-diffed
  against it. A second recogniser (Whisper, run locally) times every word and catches what the first misses. Any
  difference is regenerated or explained.
- **Timing from measured speech.** Cuts, captions and music moves sit at measured word times. Captions are checked
  against independent speech onsets, the final mix is transcribed again, and loudness is measured (target −16 LUFS
  integrated, true peak at most −1 dBTP).
- **Context map.** The script split into 26 points, each timed and placed at the first line of Act 1 whose sense
  depends on it.
- **Marker test.** Synthetic Grade 9 answers (right, informal, misspelled, partial, wrong, known misreadings, prompt
  injections) sent one by one to an AI marker and scored for exact verdicts, false passes, false holds, consistency
  and replies.

Three rules held throughout: estimated timing is never labelled as measured, nothing a student sees or hears may
give an answer before the first attempt, and the script is read as written.

## Seven claims (untested)

Evidence, the strongest counter-argument and the deciding test for each are in
[`research/FINDINGS.md`](research/FINDINGS.md); the numbers are in [`research/data/`](research/data/).

| # | claim | key evidence | test that would settle it |
|---|---|---|---|
| 1 | Stills beat generated motion for a literature film: a held picture leaves detail to read. **Disputed.** | Static diagrams with printed text matched or beat narrated animation [1]. Against: animation wins on average (d = 0.37) [2], and the animated version carried its line for more of its screen time than the stills (51% against 41%). | Stills against realistic video, same script and voice; first-try accuracy on the same checks. |
| 2 | The script is fixed, a design choice of this project: re-read it or split it, never cut lines or speed up the voice. | Cut to 299 words and sped up 1.2× (v4), the film was judged by the author to lose its style. One speech model could not read faster than about 140 words a minute; another read all 434 words at 158, in 2:54. | The natural and the brisk read rated side by side by people, with recall after each. |
| 3 | Every line gets the picture its job needs: paintings for story, labelled plates for structure. | Paintings alone carried 12 of 22 lines, and all 10 misses were structural. Plates on those 10 made 22 of 22 carry. | Structural facts recalled after viewing, with plates and without. |
| 4 | A check you can skip is decoration: gate every path, seeking included. | A seek to 200 s lands at the open check at 47.05 s. Quizzes between lecture segments cut mind-wandering from about 40% of probes to 19% [3]. | Gated against optional checks: the accuracy gain must pay for the minutes the gate adds [4]. |
| 5 | Keep the student's own words, never mark them, and let a recognition question decide whether the film goes on. | An AI marker gave the exact verdict on 58 of 63 answers, but held back 3 of the 22 right ones and let one wrong paragraph through. | The marker's agreement with teachers on real answers, against a bar set in advance [5]. |
| 6 | Never verify a narration take against its own script: transcribe it blind, and run a second recogniser. | One speech model read its style instruction aloud at the start of all 4 of its takes (21 to 31 s each). The no-hint transcription flagged 1 and passed 3; a second recogniser (Whisper) caught all four. | Both checks on every take of a unit, counting what each alone catches. |
| 7 | Context belongs in the reading, not in a film before it: front-load only what the first lines need. | Of the script's 26 points, 6 (35 s) are needed before Act 1's first line, and 11 (67 s) could be given at the line that first needs them. | Act 1 comprehension with the same checks: 35 s up front and 11 points fed in, against all 26 points up front (161 s). |

Taken together: a check is only as honest as what comes before it. Nothing a student sees may answer a check before
it is asked, nothing a student writes is judged by a marker that misreads real wording, and nothing in the script is
cut to fit a clock.

## Limitations

- No student has watched any version, so there are no learning, recall or eye-tracking data.
- One non-blind rater, who also built the plates, made the per-shot verdicts. The marker-test labels are the test
  author's reading of each rubric, not a teacher's, and the answers are synthetic.
- Voice choices rest on blind AI judges and the project's own listening; in one audition the same judge reversed its
  ranking between two shuffles of the same takes.
- The context map is relative to the abridged Act 1 reading texts (not included). Against the full play some points
  are needed earlier: Venice and the Cyprus wars are both named in 1.1.
- Frame checks confirmed which file sat at each cut, not what it showed. One engraved repaint added an embracing
  couple to an empty bedchamber and put out its last lit candle; its man does not match the film's Othello. It passed
  into the final film's opening, under the line that names the death.
- The final film's true peak measured −0.9 dBTP, 0.1 dB above its own target.
- One play, one grade, one script and one voice.

## Reproduce with your own script

Requirements: ffmpeg; Node 18+; Python 3.9+ with `requests`, `Pillow`, `google-genai` and `openai-whisper`; Chrome or
Chromium for the plates (`CHROME_BIN`). The speech, transcription, judging and image tools call a hosted model API:
set `GENAI_API_KEY`, and `GENAI_BASE_URL` and `GENAI_AUTH_HEADER` only to route through a proxy. Keys are read from
the environment and never written to any output.

Write the script as a recording manifest: a `scenes` list with `scene_number`, `clip_id`, `title` and
`spoken_text_exact` per clip, and a `parts` list (`part`, `scenes`, `title`), which the player needs; a film that is
not cut into parts has one part holding every scene. Keep it in a project folder outside this repository
(`<project>` below) and run every command from the repository root, so that nothing is written into the repository.
`<manifest>` is the manifest and `<takes>` the narration takes, `<project>/narration/takes/v01`:

```sh
# script: prove the manifest is the script, word for word
python3 tools/review/measure_fidelity.py --reference <project>/sources/script.txt --film manifest=<manifest> \
  --out <project>/script/v01/fidelity.json

# narration: audition by ear (the judges only assist), generate, verify blind twice, time every word
python3 tools/narration/generate_takes.py --manifest <manifest> --only vo_01 --model <model> --voice <voice> \
  --out <project>/narration/auditions/<YYYY-MM-DD-slug>/<model>-<voice>
python3 tools/narration/judge_takes.py --takes <project>/narration/auditions/<YYYY-MM-DD-slug> --clip vo_01 \
  --reference <manifest> --out <project>/narration/auditions/<YYYY-MM-DD-slug>/judgments.json
python3 tools/narration/generate_takes.py --manifest <manifest> --out <takes> --model <model> --voice <voice>
python3 tools/narration/verify_take.py --manifest <manifest> vo_01 <takes>/vo_01.wav
python3 tools/narration/align_words.py --manifest <manifest> --no-prompt vo_01 <takes>/vo_01.wav
python3 tools/narration/align_words.py --manifest <manifest> --narration <takes> --all

# pictures and score: compare every repaint with its source by eye
python3 tools/art/generate_paintings.py --briefs <project>/art/briefs.json --refs-dir <project>/art/refs --out <project>/art
python3 tools/art/finish_paintings.py --out <project>/art/finished <project>/art/*.jpg
python3 tools/plates/build_plates.py --content <project>/film/v01/plate-content.json --out <project>/film/v01
node tools/score/generate-score.js --out <project>/score/sketch --manifest <manifest> \
  --anchors <project>/score/anchors.json --cue-sheet <project>/score/cue-sheets/v01.json

# film, QA and player
node tools/film/render-narrated.js --manifest <manifest> --storyboard <project>/film/v01/storyboard.json \
  --cue-sheet <project>/score/cue-sheets/v01.json --narration <takes> --alignment <takes>/alignment \
  --art-dir <project>/art/finished --out <project>/film/v01/render
node tools/film/render-narrated.js --stage qa --out <project>/film/v01/render --manifest <manifest>
mkdir -p <project>/player && cp player/index.html <project>/player/
python3 tools/player/build_parts.py --film-dir <project>/film/v01/render --parts <manifest> \
  --checks <project>/checks/checks.json --player-dir <project>/player --storage-tag v01
node tools/player/serve.js 8780 <project>/player    # HTTP Range support, so seeking works
```

`python3 tools/player/make_sample_media.py` builds sample media so the player can be tried without a film. Each
tool documents its inputs at the top of the file. The score's cue plan in `tools/score/fit-score.js` is written for an
eight-scene opening. The films in this project cannot be rebuilt from this repository alone, because their script,
narration and check questions are not included.

To run these steps with Claude Code, open it at the repository root and start with the `uvk-video-make` skill:
[`kit/README.md`](kit/README.md) lists the skill for each stage, and the rules, templates and project layout
([`kit/docs/PROJECT-LAYOUT.md`](kit/docs/PROJECT-LAYOUT.md)) they follow.

## What is not included

The unit script, its narration audio, the rendered films and their captions, and the check questions supplied with
the script or drafted from it. The course's own assets: reading texts, lesson designs, characters and artwork. Other
builds of the same lesson: their films, frames, transcripts, rubrics and marker replies. These belong to their owners.
Other builds appear here only through this project's measurements of them, described generically.

## References

1. Mayer, R. E., Hegarty, M., Mayer, S. & Campbell, J. (2005). When static media promote active learning: annotated
   illustrations versus narrated animations in multimedia instruction. *Journal of Experimental Psychology: Applied*,
   11(4), 256–265. https://doi.org/10.1037/1076-898X.11.4.256
2. Höffler, T. N. & Leutner, D. (2007). Instructional animation versus static pictures: a meta-analysis. *Learning and
   Instruction*, 17(6), 722–738. https://doi.org/10.1016/j.learninstruc.2007.09.013
3. Szpunar, K. K., Khan, N. Y. & Schacter, D. L. (2013). Interpolated memory tests reduce mind wandering and improve
   learning of online lectures. *PNAS*, 110(16), 6313–6317. https://doi.org/10.1073/pnas.1221764110 (open access:
   https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699/)
4. Kovacs, G. (2016). Effects of in-video quizzes on MOOC lecture viewing. *Proceedings of the Third ACM Conference on
   Learning @ Scale*. https://doi.org/10.1145/2876034.2876041 (author copy:
   https://hci.stanford.edu/publications/2016/invideo/invideo-las2016.pdf)
5. Henkel, O., Boxer, A., Hills, L. & Roberts, B. (2024). Can large language models make the grade? An empirical study
   evaluating LLMs ability to mark short answer questions in K-12 education. https://arxiv.org/abs/2405.02985
6. Mayer, R. E. & Moreno, R. (2003). Nine ways to reduce cognitive load in multimedia learning. *Educational
   Psychologist*, 38(1), 43–52. https://doi.org/10.1207/S15326985EP3801_6
7. Mayer, R. E., Mathias, A. & Wetzell, K. (2002). Fostering understanding of multimedia messages through pre-training:
   evidence for a two-stage theory of mental model construction. *Journal of Experimental Psychology: Applied*, 8(3),
   147–154. https://doi.org/10.1037/1076-898X.8.3.147

Every other figure was measured in this project.
