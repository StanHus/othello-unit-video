# Data

Aggregate results behind [`../FINDINGS.md`](../FINDINGS.md), taken from the project's own measurement records of
6 to 8 October 2026, with other builds anonymised. Numbers only: no script text, no rubric text, no marker replies,
no frames.

| file | what it holds | method |
|---|---|---|
| [`comparison.csv`](comparison.csv) | the three productions of the same script on the comparison rubric: runtime, shots, per-shot verdicts by count and by share of runtime, text and edge density, pace, when the murder is first heard, script fidelity, recogniser agreement, and how the checks are gated | [rubric](../METHODS.md#2-comparison-rubric) |
| [`per-shot-test.csv`](per-shot-test.csv) | per-shot verdicts and on-screen text for the stills film (v5), the hybrid with plates (v6), the animated version split by whether its narrator figure is on screen, and the 3D version | [per-shot test](../METHODS.md#1-per-shot-test) |
| [`versions.csv`](versions.csv) | the seven film versions: script, words, model and voice labels, tempo, duration, cuts, plates, loudness, voice over music, caption cues and parts | [timing and mix](../METHODS.md#4-timing-captions-and-mix) |
| [`tts-auditions.json`](tts-auditions.json) | speech-model auditions: per-take durations, gaps and word checks, the spoken style instruction, blind-judge results and pace | [narration](../METHODS.md#3-narration-verification) |
| [`final-film-qa.json`](final-film-qa.json) | the final film's QA (loudness, voice over music per scene, captions, final-mix transcription counts, parts, check times) and the caption-timing checks made on v1 | [timing and mix](../METHODS.md#4-timing-captions-and-mix) |
| [`marker-test.json`](marker-test.json) | the AI marker test: test-set groups, verdict scores, the five misses described by kind, reply statistics, a later run of the five misses and the second marker's two runs | [marker test](../METHODS.md#6-testing-an-ai-marker-with-realistic-answers) |
| [`context-map-totals.json`](context-map-totals.json) | the Act 1 context map: points and seconds by class and by first scene, and what the reading texts already carry | [context map](../METHODS.md#5-context-mapping) |

## Labels

- `stills_v5`, `hybrid_v6`: this project's films. `animated`: an animated version of the same script, made elsewhere.
  `3d_code`: a 3D version of the same script built in code, made elsewhere.
- Speech models and voices are labelled `A` to `D` and `1` to `3` for brevity, and judges `J1` to `J3` (legend in
  `tts-auditions.json`). The final film uses model `C` with voice `2`.
- `asr_reference_words` is 436: the script's 434 words after numbers are normalised to words.
- Per-shot verdicts: `carries`, `partly`, `competes`. The `*_pct_runtime` columns weight them by screen time.

## Notes

- `v06` uses the same narration, score and timeline as `v05`; its audio was not measured separately, so its loudness
  columns are empty and its duration is that of `v05`.
- The first audition's durations come from the build's record and include any spoken style instruction. The
  `instruction_read_aloud`, `script_starts_s` and `script_span_s` fields come from the second recogniser (Whisper, no
  prompt), which found the instruction at the start of all four takes of model `B` and in none of the six takes of
  model `A`.
- Marker-test counts are against the test author's labels, not a teacher's. `false_pass_of` and `false_hold_of` are
  the answers that should not, and should, complete their check.
- Context-map times are arithmetic on caption cue times, not a render. "First needed" is relative to the abridged Act 1
  reading texts (not included).

Not here: the script, narration audio, films, captions, transcripts, frames of other builds, the rubrics, the test
answers keyed to them and the raw marker responses.
