# Findings: seven claims, untested

The claims came from building seven versions of the film, comparing it with two other productions of the same
script, and testing an AI answer marker. None has been tested with students. Read them as design hypotheses: each
gives the evidence, the strongest counter-argument and the test that would settle it. Numbers are this project's own
measurements ([`data/`](data/)); outside research is cited at the end.

## 1. Stills beat generated motion for a literature film: a held picture leaves detail to read (disputed)

**Evidence.** In four experiments, static diagrams with printed text matched or beat narrated animation: better on 4
of 8 retention and transfer comparisons, and no different on the rest (Mayer et al. 2005). In the animated version
measured here, an on-screen narrator figure filled 48% of the runtime, and only 2 of the 11 shots that showed it
carried their line, against 23 of the 25 shots without it.

**Against.** Across 26 studies, animation beat still pictures on average (d = 0.37), and by more when it was
realistic, video-based (d = 0.76) (Höffler & Leutner 2007). On this project's own per-shot test the animated version
carried its line for more of its screen time (51%) than the stills did (41%). Mayer's experiments explained physical
systems, not literature. Every painting was repainted in an engraved finish to reduce the generated look of the
paintings; whether it does was not measured.

**Why it stays disputed.** No test has compared stills with realistic video on learning, and none here measured how
credible either format looks.

**Test.** Stills against realistic video, with the same script and voice; first-try accuracy on the same checks.

## 2. The script is fixed: re-read it or split it, never cut lines or speed up the voice

**Evidence.** Cutting the 434-word script to 299 words and speeding the voice 1.2× (v4, 2:00) was judged by the author
to lose the film's style. Keeping every word at natural pace and splitting the film into parts (v5: 4:31, or 1:08,
1:31 and 1:52) kept it. The length problem turned out to be the voice: one speech model could not read this script
faster than about 140 words a minute whatever the direction, while another read it at 158, fitting all 434 words in
2:54 (v7). The animated version, kept whole at 128 words a minute, ran 3:28, over three minutes.

**Against.** A new read is a new voice. Of three blind AI judges, two preferred the brisker read of one passage, and
one heard it as "far too young". No person outside the project has compared the two reads.

**Test.** The natural and the brisk read rated side by side by people, with recall after each.

## 3. Every line gets the picture its job needs: paintings for story, labelled plates for structure

**Evidence.** Share of screen time whose picture carries its line, on one rubric: the 3D version 98%, the animated
version 51%, the stills 41%. The 12 of the stills' 22 lines that carried all show concrete events. All 10 lines that
did not carry were structural: definitions, lists, the setting and the ranks. Labelled plates on those 10 lines alone
made all 22 carry (v6).

**Against.** Two styles can read as two films. With plates, text is on screen for 51% of the runtime (in the 3D
version 95%, with up to 27 items in one frame). A plate that teaches a fact also answers the next check about it, so
the player has to blur the film while a question is on screen. The plates were rated by one non-blind rater, who built
them.

**Test.** Structural facts recalled after viewing, with plates and without.

## 4. A check you can skip is decoration: gate every path, seeking included, even if learners would rather skip

**Evidence.** The player sends every seek back to the first open check: in the v5 browser test a jump to 200 s
landed at 47.05 s, and the film went on only after a right answer. Play is refused while a question is on screen, and
later parts unlock only in order. In recorded online lectures, short tests between segments cut mind-wandering to 19%
of probes, against 39% and 41% in two groups without them; they also tripled note-taking and raised final-test scores
to 90%, against 76% and 68% (Szpunar et al. 2013).

**Against.** Where in-video quizzes were optional, 74% of viewers who started a video answered its quiz, while only
66% watched it to the end (Kovacs 2016). If most learners answer anyway, a forced gate may add little and may invite
guessing. The lecture in Szpunar's study went on whatever the answers; it did not gate on them.

**Test.** Gated against optional checks. The gain in first-try accuracy must pay for the minutes the gate adds, given
that 74% answered optional quizzes anyway.

## 5. Keep the student's own words, never mark them, and let a recognition question decide whether the film goes on

**Evidence.** Given 63 realistic Grade 9 answers, an AI marker in an existing reading lesson gave the exact verdict on
58. Its five misses fall where a student's wording drifts from the rubric's. It held back 3 of the 22 answers that
should have completed their check, two of them right paraphrases. It credited a wrong answer on one criterion, and it
passed one wrong paragraph. 9 of its 91 calls, about one in ten, got no response within 40 s. A later run repeated
three of the five misses. The film's player keeps own-words answers, shows them back and never scores them; a
multiple-choice step decides whether the film goes on.

**Against.** The same marker recognised 10 of 10 known misreadings and marked 3 of 3 prompt injections off-task. A
second marker, in a 3D lesson build, accepted 14, then 15, of 15 right answers in two runs and kept all 28 wrong or
partial ones from passing. A large language model marking short answers in science and history (ages 5 to 16) agreed
with human markers at kappa 0.70, against 0.75 between humans (Henkel et al. 2024).

**Test.** The marker's agreement with teachers on real answers, against a bar set in advance; below the bar, a
recognition question replaces the marker. Here it matched 58 of 63 against the test author's labels.

## 6. Never verify a narration take against its own script: transcribe it blind, and run a second recogniser

**Evidence.** One speech model read its style instruction (57 words; 76 in a slower-paced variant) aloud at the start
of all 4 of its takes of the first scene (21 to 31 s each, before the script began). A multimodal transcription given
no hint of the script flagged 1 of those takes (230 words heard against 90 scripted) and passed the other 3. A second
recogniser (Whisper, run locally with no prompt) caught all four, and heard no instruction in any of the other
model's six takes. In the final narration the blind check heard "ancient" for "ensign" (the play's own word for the
rank) in one take, which was regenerated before anyone listened.

**Against.** Transcripts cannot hear tone or pace: the "far too young" verdict on the brisk read came from a listening
judge, not a recogniser. A listening AI judge may also catch what the transcriber misses: in three of four passes the
judges named all four takes that read their instruction, though one of those passes also accused two clean takes. And
blind transcription raises false alarms of its own: all 10 takes of the first scene, from both models and all three
voices, were heard with "lies" for "lie", almost certainly the transcriber's artefact, so each flag still needs a
listen.

**Test.** Both checks on every take of a unit, counting what each alone catches.

## 7. Context belongs in the reading, not in a film before it: front-load only what the first lines need

**Evidence.** The script splits into 26 points. Against the abridged Act 1 reading texts, 6 points are needed before
Act 1's first line (35 s of narration: the setting and who is who), 11 could be given in-line where first needed
(67 s), and 9 frame the unit (59 s). Without the 11, the opening would run about 1:48 (caption arithmetic, not a
render). For 18 of the 26 points the reading texts already carry all or part of the point.

**Against.** The script is fixed, a design choice of this project, and a fixed script can only move a line with its
author's agreement. Building background knowledge is also a goal in itself, not only a cost before reading. Learning
the names and characteristics of the key parts before a narrated explanation improves understanding of it
(pre-training; Mayer, Mathias & Wetzell 2002), which argues for front-loading at least the names. Against the full
play some points are needed earlier than the abridged texts suggest: Venice and the Cyprus wars are both named in 1.1.

**Test.** Act 1 comprehension, with the same three checks after reading: 35 s up front with the 11 points fed in at
their lines, against all 26 points up front (161 s).

## Across the claims

- **A check is only as honest as what comes before it.** A plate (claim 3), or any other media shown before a check,
  can answer it before it is asked. Put knowledge-building media after the check it would answer, or hide it while
  the question is on screen.
- **Length was set by the voice, not the script** (2). Word for word, the script runs 2:54 at 158 words a minute.
- **Fixed is not frozen** (2, 7). The script's words cannot be cut, but where they are heard can move; a fixed script
  can only move a line with its author's agreement.
- **Free text fails where real answers live** (5). The marker erred where a student's wording drifted from the
  rubric's. Collect the words; don't mark them.
- **A check that knows what to expect finds it** (6). A transcriber that returned only the expected words passed three
  takes that opened with 21 to 31 s of extra speech. A fidelity score computed on recogniser output put a film that
  reads its script exactly at 98.4%. A frame check that matched file names passed a repaint whose content had changed.
  Verify against independent evidence.
- **Measures fixed each cut, but none measured how credible a format looks; the tests should add that** (1, 3).
- **The tests lean on first-try accuracy**, a proxy for attention at the moment of the check. Durable learning needs
  recall a week later, which none of them measures yet.

**Why it matters.** This is assessment validity applied to the film itself. Integrity first: nothing a student sees
may answer a check before it is asked, nothing a student writes is judged by a marker that misreads real wording, and
nothing in the script is cut to fit a clock. A check that can be passed without the learning it tests rewards
guessing, and tells the teacher a student understands when they don't. The cited research fits that frame: tests
between lecture segments cut mind-wandering (Szpunar et al. 2013), which is why gates may help; static diagrams with
text matched or beat narrated animation (Mayer et al. 2005), which is why held pictures need not cost learning; and
the marker's misses on real student wording (claim 5) are why a recognition question, not free text, should open the
gate.

## Open questions

- Does gating raise recall a week later, or only first-try accuracy?
- Do students feel the stops as help or as interruption, and does that differ by reading confidence?
- What does a finished minute cost with this pipeline, in hours and compute, and after how many films does the
  reusable part pay back?
- Who reads the kept own-words answers, and how do they become teaching data, such as misconception patterns or
  rubric gaps?
- Do claims 2, 3 and 7 hold for a modern novel with no archaic language and little historical context?
- How does integrity first differ from standard assessment-validity frameworks, and what does it add for video?
- How would a test separate the learning effect of stills from the credibility cost of a generated look?
- Should gating differ between required and elective courses, where learners have different reasons to skip?

## Research cited

- Mayer, Hegarty, Mayer & Campbell (2005), *J. Exp. Psychol.: Applied* 11(4). https://doi.org/10.1037/1076-898X.11.4.256
- Höffler & Leutner (2007), *Learning and Instruction* 17(6). https://doi.org/10.1016/j.learninstruc.2007.09.013
- Szpunar, Khan & Schacter (2013), *PNAS* 110(16). https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699/
- Kovacs (2016), *Learning @ Scale*. https://doi.org/10.1145/2876034.2876041
- Henkel, Boxer, Hills & Roberts (2024), arXiv. https://arxiv.org/abs/2405.02985
- Mayer, Mathias & Wetzell (2002), *J. Exp. Psychol.: Applied* 8(3). https://doi.org/10.1037/1076-898X.8.3.147

Full entries are in the root [`README.md`](../README.md#references).
