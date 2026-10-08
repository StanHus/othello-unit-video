# Methods

Six methods and the player's tests, each with its procedure, where its numbers are and what it cannot show. The
aggregate results are in [`data/`](data/); what each claim rests on is in [`FINDINGS.md`](FINDINGS.md).

Three rules held across all of them:

1. **Measured, not estimated.** Every cut, caption and music move is placed from measured word times. A render with
   estimated times is labelled as one.
2. **No answer before the attempt.** Nothing a student sees or hears may give an answer before the first attempt.
   Checks sit after the scene they ask about, and the film is blurred while a question is on screen.
3. **The script is read as written.** No word is cut, added or reordered, and the caption text equals the script.

## 1. Per-shot test

**Question.** For each cut: does the picture show what the line being spoken is about?

- *carries*: the picture shows what the line is about;
- *partly*: it shows some of it;
- *competes*: the picture is about something else.

**Procedure.** One frame per shot (its midpoint) is judged against the words spoken while the shot is on screen, with
notes on any motion. Verdicts are counted by shot and weighted by screen time. When a narrator figure talks to camera,
the shot counts as *partly* if the line is about the student's task or the film's framing, and as *competes* if it is
about a character or a concept.

**Shot boundaries.** Scene detection finds hard cuts but not soft transitions. In the animated version, ffmpeg scene
detection at a threshold of 0.25 found only 8 of its 35 transitions; 17 were three-frame crossfades and 10 were
dissolves. Boundaries were therefore marked from scene-score peaks of 0.10 or more and frame-difference spikes, each
confirmed with a mix-ratio curve on 96×54 grey frames, with the boundary at the 50% point of the mix. All 27 soft
transitions fell within −0.62 to +0.41 s of a caption cue, so they follow the narration.

**Screen density.** Text items per frame count the names and labels on screen, not captions. Edge density is the
share of pixels on an edge (ffmpeg `edgedetect`) in one frame per shot, scaled to 640×360 and cropped to the same band
(6 to 78% of the height) so that captions and player controls are left out of every film alike.

**Why.** Pictures that show something other than the line, or show everything at once, cost the processing the line
needs (Mayer & Moreno 2003). The test asks where a student should look during each line; a picture with no clear
subject spreads attention over all of it.

**Limits.** One non-blind rater, who also built the plates. It is a design judgement against the line, not eye
tracking.

Results: [`data/per-shot-test.csv`](data/per-shot-test.csv). Tool: `tools/review/measure_screen.py`.

## 2. Comparison rubric

Three productions of the same 434-word script: this project's stills film (v5), an animated version and a 3D version
built in code. The rubric was written before the other two were measured, and every row was checked the same way on
each film.

| # | row | how it is checked |
|---|---|---|
| 1 | script fidelity | words heard against the script: the share of script words spoken, in order |
| 2 | coverage of the opening's knowledge areas | each knowledge area the script covers, looked for in what is spoken |
| 3 | an opening, teaching and return structure | a judgement on the narration: how it opens, what it teaches, how it closes |
| 4 | checks that gate playback | how many; whether playback waits for an answer; whether a seek can pass an open check |
| 5 | pictures that teach structure (maps, hierarchies, timelines) | which structural lines have such a picture on screen while they are read |
| 6 | share of screen time whose picture carries its line | the per-shot test: carries, partly, competes, by count and by screen time (method 1) |
| 7 | length and words per minute | runtime, speech span, words per minute |
| 8 | visual density per frame | text items per frame; share of edge pixels |
| 9 | look and motion | production style and how the pictures move (a judgement) |
| 10 | the narrator's role | who narrates, who asks, whether a narrator figure is on screen |

**A correction made during the pass.** Fidelity is scored on each film's script, with a recogniser only confirming
that the audio reads it. Scored on recogniser output instead, one film came out at 98.4% purely from recogniser
errors (number words, a name spelling, "Moor" heard as "more").

**Limits.** Rows 3, 5, 6, 9 and 10 rest on judgements by one rater. Nothing here measures how students watch or learn.

Results: [`data/comparison.csv`](data/comparison.csv). Tools: `tools/review/measure_fidelity.py`,
`tools/review/measure_screen.py`.

## 3. Narration verification

Each clip is generated with a provenance record: model, voice, direction, a hash of the exact text and the measured
duration. Every take then goes through two independent checks.

**Blind transcription.** A multimodal model transcribes the take without being given the script. The prompt asks for
every sound from the very first to the last, including any instruction or preamble, with numbers written as words.
The transcript is word-diffed against the script, and its word count and the take's duration are compared with other
takes of the same text. Any difference is either regenerated or matched to a known transcriber artefact.

**A second recogniser.** Whisper (large-v3-turbo, run locally) gives word timestamps. Its words are mapped onto the
script's own tokens with a sequence diff, and each onset that falls inside a measured silence (−45 dBFS for 0.2 s) is
moved to the end of it. Every clip must match a high share of its tokens: at least 0.948 per clip in v3 and 0.93 in
v7, where the misses were digits and name spellings.

**Failure modes met in this build.**

- One speech model read its style instruction aloud at the start of all 4 of its takes (21 to 31 s each). The no-hint
  transcription flagged 1 and passed 3; whether the prompt above catches all four has not been re-tested. The second
  recogniser (Whisper, no prompt) caught all four, and found none in six clean takes.
- Durations that include a spoken instruction overstate how slowly a model reads. The leaking model's takes looked
  slower than the other model's, but their script spans were 36 to 41 s against 43 to 45 s.
- Giving the recogniser the script as its initial prompt biased decoding: once it skipped half a clip after a
  quotation (0.46 matched). A no-prompt fallback is kept, and the better alignment wins.
- Over music or silence the recogniser loops phrases, so words after the last script word are dropped and logged.
- Where the voice runs two sentences together, alignment can snap to the wrong silence; sentence times are then
  checked by hand against silence detection.
- One model dropped half of a 17-word check line, so short lines get the same check.
- Stable false alarms: "lie" heard as "lies" in every take of the first scene, "Roderigo" as "Rodrigo", "Moor" as
  "more", and number words.

**Auditions.** Takes of one passage are judged blind by AI judges: each pass shuffles the takes with its own seed and
relabels them, the judge scores each take on a written rubric (the tool's default: intelligibility, pacing,
naturalness, register and exact words), and the rankings are combined by Borda count. The judges are a filter, not a
verdict: in one audition the same judge model reversed its ranking between two shuffles. In the first audition the
judges named all four takes that read their instruction aloud in three of four passes, and one of those passes also
accused two clean takes. A voice is chosen by listening.

Results: [`data/tts-auditions.json`](data/tts-auditions.json). Tools: `tools/narration/generate_takes.py`,
`verify_take.py`, `align_words.py`, `judge_takes.py`.

## 4. Timing, captions and mix

- **Cuts** land at the measured start of their anchor phrase, 0.12 s early, rounded to a frame.
- **Captions** start at the first aligned word minus 0.05 s and end at the last word plus 0.3 s, clipped to the next
  cue. The joined caption text must equal the script.
- **Onset check** (v1). For the 37 cues that follow a pause of 0.5 s or more, the aligned first-word time was compared
  with the speech onset measured on the voice-only stem: median error 0.000 s, signed mean −0.035 s, 36 of 37 within
  0.25 s. The worst, −0.769 s, was where the voice ran two sentences together.
- **Recogniser on the final mix** (v1). It matched 464 of 473 tokens. Its word starts ran a median 0.325 s ahead of
  the caption starts (signed mean +0.26 s); the onset check shows that this is the recogniser's own early bias over
  music, not late captions.
- **Mix.** The music sits 10 LU under the voice and is ducked a further 8 dB from a voice-activity envelope (−42 dBFS,
  20 ms windows, gaps under 0.9 s merged; attack 0.35 s, hold 0.25 s, release 1.2 s). Delivery target: −16 LUFS
  integrated, true peak at most −1 dBTP. Voice over ducked music is measured per scene during speech: 14.0 to 19.4 dB
  in v7.
- **Final-mix transcription.** Each scene is cut from the finished mix and transcribed blind. In v7, 6 of 8 scenes
  came back exact; the rest were digits, one dropped word that a second pass and the second recogniser both heard,
  and one name spelling.
- **Frame check.** One frame is grabbed at each cut and matched to the planned picture file. That confirms which file
  sits at a cut, not what the picture shows.

**Limits.** The v7 mix measured −0.9 dBTP true peak, 0.1 dB over its target. A repainted picture whose content had
changed (an embracing couple added to an empty bedchamber, its last lit candle put out) passed the frame check and
reached the final film's opening. No person outside the project has listened to the mix.

Results: [`data/versions.csv`](data/versions.csv), [`data/final-film-qa.json`](data/final-film-qa.json).

## 5. Context mapping

**Question.** How much of the film's context must come before reading Act 1, and how much could be given at the line
that first needs it?

- **Points.** The script (not included) is split along the final film's 51 caption cues into 26 points, one per piece
  of knowledge or framing move. Each cue belongs to exactly one point.
- **Times.** A point runs from the start of its first cue to the end of its last. Pauses, the lead-in and the tail
  belong to no point (13.784 s in v7).
- **First needed.** The first line of the Act 1 reading text, in scene order (1.1, 1.2, 1.3), whose sense depends on
  the point. Notes and glossaries give context rather than need it, so they do not count.
- **Classes.** *Before reading*: a student cannot follow 1.1 without it. *Could be fed in*: first needed at a later
  line, where a short note could carry it. *Framing*: it frames the unit and is not needed to follow the reading.
- **Check.** Each play line cited as the first need was matched exactly against the reading texts.

**Why.** Pre-training on the names and characteristics of key parts helps learners understand a later narrated
explanation (Mayer, Mathias & Wetzell 2002). The map asks which of those parts the first lines of the play actually
need.

**Limits.** "First needed" is relative to the abridged Act 1 reading texts (not included). Against the full play some
points are needed earlier: Venice and the Cyprus wars are both named in 1.1. The 107.664 s (about 1:48) for the film
without the could-be-fed-in points is arithmetic on caption times, not a render.

Results: [`data/context-map-totals.json`](data/context-map-totals.json).

## 6. Testing an AI marker with realistic answers

**Test set.** 63 synthetic answers in Grade 9 student voice, written for the seven checks that an existing
reading lesson on 1.1 marks:

| group | answers | what they are |
|---|---|---|
| should complete their check | 22 | right answers in plain, informal, slang, misspelled and non-native wording, two buried in a long answer, one full paragraph |
| partial | 13 | part of the answer, or an incomplete paragraph |
| wrong | 10 | wrong person, wrong rank, a line that is not evidence, a vague or restated answer |
| known misreadings | 10 | each built on a known misreading of the passage |
| arguable | 5 | some criteria arguable, and left out of the score |
| prompt injection | 3 | instructions to the marker inside the answer |

Expected labels follow each rubric.

**Protocol.** Realistic Grade 9 answers were sent one by one to each marker's own endpoint, and each verdict was
compared with the expected mark. Repeated answers were sent three times to test stability (ten of them here). Calls
with no response in 40 s were sent again.

**Scores.** Exact verdict (every scored criterion right); criterion-level agreement; false passes (a wrong answer that
would complete the check); false holds (a right answer held back); known misreadings recognised; injections marked
off-task; the same verdict on repeated runs; response time; and replies, by length and by whether they hand over a
missing answer (a keyword heuristic flags candidates, which are then read).

**Misses sent again.** A later run repeated three of the five misses.

**A second marker.** A separate set of 48 answers on the reading checks of a 3D lesson build, sent to its own
marker in two runs 7 minutes apart, scored for right answers accepted, wrong or partial answers kept from passing, and
repeated answers given the same verdict.

**Not published.** The rubrics, the test set keyed to them and the raw responses belong with the lesson builds they
were written for, so only aggregates are here.

**Limits.** The labels are the test author's reading of each rubric, not a teacher's, and the answers are synthetic.
Only the marker was tested, not the rest of the lesson around it, and no student took part.

Results: [`data/marker-test.json`](data/marker-test.json).

## Player gating tests

Automated browser tests (isolated profile, media muted, audio checked by source rather than by ear):

- a seek past an unanswered check is clamped to it (v5: a jump to 200 s landed at 47.05 s); once a check is done,
  seeks up to the next open check are allowed;
- play is refused while a question is on screen; the film is blurred and the captions hidden;
- a wrong option shows its own feedback and no Continue; a right one gives Continue;
- free-text answers: gibberish strings and a two-word answer were refused without a reply, and a real sentence was
  saved and shown back;
- finished checks, attempts and position survive a reload;
- the frame and controls fit a 1440×823 screen, and at 390×844 the check becomes a bottom sheet with no sideways
  scroll;
- in parts mode, later parts unlock only in order and play on automatically.

Media seeking needs a server with HTTP Range support. Audio started from code outside a click can be blocked by a
browser's autoplay rules, so the player unlocks its voice channel on the first click.

**Not tested.** A person watching at full speed with sound; browsers other than one Chromium-based browser; a screen
reader; every check of the final version (the code paths are shared).

## Method references

- Mayer, R. E. & Moreno, R. (2003). Nine ways to reduce cognitive load in multimedia learning. *Educational
  Psychologist*, 38(1), 43–52. https://doi.org/10.1207/S15326985EP3801_6
- Mayer, R. E., Mathias, A. & Wetzell, K. (2002). Fostering understanding of multimedia messages through pre-training.
  *Journal of Experimental Psychology: Applied*, 8(3), 147–154. https://doi.org/10.1037/1076-898X.8.3.147
