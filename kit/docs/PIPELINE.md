# The pipeline

Each stage has a skill (sharing has none), what it reads and writes in the project, and the check that ends it. Run
the stages in order: a later stage never repairs an earlier one. Every command runs from the repository root, with
the project's paths passed by flag; the paths below are inside the project ([PROJECT-LAYOUT.md](PROJECT-LAYOUT.md)),
and the rules are in [STANDARDS.md](STANDARDS.md).

| # | stage | skill | reads | writes | done when |
|---|---|---|---|---|---|
| 1 | script | `uvk-video-make` | the script as received, in `sources/` | `script/vNN/manifest.json` | the manifest scores 100% against the script with `tools/review/measure_fidelity.py`, with the same word count |
| 2 | narration | `uvk-narration-make` | the manifest, a voice chosen by ear | `narration/takes/vNN/`: one WAV per scene, `narration-manifest.json`, transcripts, `alignment/` | every take matches on the blind check or differs only by known recogniser errors, Whisper hears no extra speech, every clip is aligned at 0.93 matched or more (below that, only once every unmatched word has been read and explained), and the pace fits the length limit |
| 3 | paintings | `uvk-art-make` | briefs, reference paintings | `art/`, `art/finished/` | every painting compared by eye with its brief and its source: no text, border or depicted death, every character the same person throughout |
| 4 | plates | `uvk-plates-make` | the structural lines | `film/vNN/plates/`, `plates.json`, `contact-sheet.jpg` | every structural line has a plate, every word on a plate is spoken while it shows, and every quotation is verbatim with its act.scene.line |
| 5 | storyboard, score and render | `uvk-film-make` | narration, alignment, paintings, plates | `film/vNN/storyboard.json`, `score/cue-sheets/vNN.json`, `film/vNN/render/` | the plan resolves every anchor; the film is within the length limit; -16 LUFS integrated, true peak at most -1 dBTP; the voice 14 dB or more over the music in every scene; the captions equal the script; the final-mix transcription differs only by known recogniser errors; every frame shows the right picture |
| 6 | checks | `uvk-checks-make` | the checks file, the spoken lines, the render | `checks/`, `player/` | every path gates (play, seek, reload, parts), noise is refused, answers are stored, and every check has been walked in a browser |
| 7 | audit | `uvk-film-audit` | the render's frames and timeline | `film/vNN/shots.json`, `verdicts.json`, `measures.json`; the QA record | every picture carries its line, judged by a second judge, not the builder |
| 8 | share a review copy | none | `player/` | a review copy | only with explicit approval, and never into someone else's environment or files |
| 9 | record | `uvk-library-make` | everything above | `library/`, `FINDINGS.md` | nothing is uncatalogued, and each claim is written with its evidence, the strongest counter-argument and the test that would settle it, in the shape of `research/FINDINGS.md` |

`uvk-feedback-sweep` runs whenever feedback arrives, before anything changes, and `uvk-video-compare` whenever there
are productions of the same script to compare. The `uvk-video-make` workflow runs stages 1 to 4 with agents, renders
stage 5 from the storyboard and cue sheet you have written, runs stage 7 and writes the QA record; the checks stay a
separate step.
