# Findings

Seven things I learned building the film. None has been tested with students. The numbers are my own measurements,
in [data/](data/), and the research I cite is listed at the end.

## 1. Stills or motion (unresolved)

I used held paintings rather than generated video, on the idea that a still picture leaves time to read it. Mayer and
colleagues found that static diagrams with printed text did as well as narrated animation or better: better on 4 of 8
comparisons, the same on the rest. In the animated version I measured, a narrator figure was on screen for about half
the runtime, and only 2 of the 11 shots showing it matched what was being said.

Against: across 26 studies, animation beat still pictures on average (Höffler & Leutner 2007). On my own per-shot test
the animated version matched its narration for more of its screen time than my stills did, 51% to 41%. And Mayer's
studies were about physical systems, not literature.

To settle it: the same script and voice over stills and over realistic video, compared on first-try answers to the
same checks.

## 2. Don't cut the script

When I cut the script from 434 words to 299 and sped the voice up to fit a shorter film, it lost its style. Reading
every word at a natural pace kept the style, and splitting the film into parts dealt with the length. What actually
made it long was the voice model: one wouldn't go faster than about 140 words a minute however I directed it, and
another read all 434 words in 2:54.

Against: a faster read is a different voice. One of three AI judges thought the quick read sounded "far too young",
and nobody outside the project has compared the two.

To settle it: people rate the two reads side by side, with a recall test after each.

## 3. Paintings for the story, plates for the structure

I checked every shot for whether the picture showed what the narration was saying at that moment. My paintings did
for 12 of 22 lines. All 10 they missed were structural: definitions, lists, the setting, the ranks. Labelled plates on
those 10 fixed every one.

Against: two visual styles can feel like two films. Plates also put text on screen for half the runtime, and a plate
that teaches a fact gives away the answer to the next question, so the player blurs the film while a question is up.
And I judged the plates myself, having made them.

To settle it: test recall of the structural facts after watching, with plates and without.

## 4. Gate every check

If a student can skip a check, it's decoration. The player sends any seek back to the first unanswered question (in
testing, a jump to 200 s landed back at 47.05 s), won't play while a question is open, and unlocks parts in order. In a
study of recorded lectures, short tests between segments cut mind-wandering from about 40% to 19% (Szpunar et al.
2013).

Against: when in-video quizzes are optional, most viewers answer them anyway (74% in Kovacs 2016), so forcing them may
add little, and may push some students to guess. And the lectures in Szpunar's study carried on whatever the answers; they didn't gate on them.

To settle it: gated against optional checks. The gain in first-try answers has to be worth the minutes the gate adds.

## 5. Keep students' words, don't mark them

I tested an AI marker from an existing reading lesson with 63 realistic Grade 9 answers that I wrote. It got 58
right. The 5 it got wrong were all where a student's wording drifted from the rubric's: it held back 3 right answers,
gave a wrong answer credit on one criterion, and passed a wrong paragraph. About one call in ten didn't come back within 40 seconds. So
the player saves what students write, shows it back to them and never scores it; a multiple-choice question decides
whether the film carries on.

Against: the marker handled the hard cases well, spotting all 10 known misreadings and all 3 answers that tried to
talk it into a pass. A second marker, in another lesson, accepted 14 and then 15 of 15 right answers and let none of
the 28 wrong or partial ones through. In a larger study, a large language model agreed with human markers almost as well as humans agree with
each other (kappa 0.70 against 0.75; Henkel et al. 2024).

To settle it: compare the marker with teachers on real answers, against a bar agreed in advance, and use a
multiple-choice question wherever it falls short.

## 6. Check narration twice, blind

One voice model read its own style instructions aloud at the start of all four of its takes: 21 to 31 seconds of them
before the script began. A transcription that hadn't been given the script caught one of the four takes. Whisper, run locally
with no prompt, caught all four. In the final narration the blind check also heard "ancient" for "ensign" in one take
(the play's own word for the rank), and that take was redone before anyone listened to it.

Against: a transcript can't hear tone or pace. A listening AI judge picked out all four bad takes in three of four
passes, though in one of those it also accused two clean ones. And transcription makes its own mistakes: every take of
the first scene came back with "lies" for "lie". Every flag still needs someone to listen.

To settle it: run both checks on every take of a unit and count what each catches on its own.

## 7. Context during the reading, not before it

I split the script into 26 points and checked each against the Act 1 reading texts. Only 6 are
needed before the play's first line: the setting and who is who, 35 seconds of narration. Another 11 could go in as
notes at the line that first needs them, and 9 just frame the unit. Without the 11, the opening would run about 1:48
instead of 2:54, going by the caption times.

Against: the script is fixed, so moving a line needs its author's agreement. Background knowledge is worth having for
its own sake, and learning the names of the key parts before an explanation helps people follow it (Mayer, Mathias &
Wetzell 2002), which argues for at least the names up front. The full play also needs some points earlier than the
abridged texts do: Venice and the Cyprus wars both come up in 1.1.

To settle it: Act 1 comprehension, with the same checks after reading, for 35 seconds up front with the 11 points
given at their lines, against all 26 up front.

## What kept going wrong

Three of my checks passed things they should have caught, because each leaned on what it expected to find. A
transcriber that returned only the script's words passed takes with up to half a minute of extra speech at the start.
A fidelity score worked out from a recogniser's transcript put a word-perfect film at 98.4%. A frame check that matched
file names passed a repaint whose picture had changed. Each problem only showed up when I checked against something
that didn't assume the answer.

## Open questions

- Does gating help a week later, or only in the moment?
- Do students feel the stops as help or as interruption?
- What does a finished minute cost, in hours and compute?
- Who reads what students write, and what do they learn from it?
- Would any of this hold for a modern novel?

## Research cited

- Mayer, R. E., Hegarty, M., Mayer, S. & Campbell, J. (2005). When static media promote active learning: annotated illustrations versus narrated animations in multimedia instruction. *Journal of Experimental Psychology: Applied*, 11(4), 256–265. https://doi.org/10.1037/1076-898X.11.4.256
- Höffler, T. N. & Leutner, D. (2007). Instructional animation versus static pictures: a meta-analysis. *Learning and Instruction*, 17(6), 722–738. https://doi.org/10.1016/j.learninstruc.2007.09.013
- Szpunar, K. K., Khan, N. Y. & Schacter, D. L. (2013). Interpolated memory tests reduce mind wandering and improve learning of online lectures. *PNAS*, 110(16), 6313–6317. https://doi.org/10.1073/pnas.1221764110 (open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699/)
- Kovacs, G. (2016). Effects of in-video quizzes on MOOC lecture viewing. *Proceedings of the Third ACM Conference on Learning @ Scale*. https://doi.org/10.1145/2876034.2876041 (author copy: https://hci.stanford.edu/publications/2016/invideo/invideo-las2016.pdf)
- Henkel, O., Boxer, A., Hills, L. & Roberts, B. (2024). Can large language models make the grade? An empirical study evaluating LLMs ability to mark short answer questions in K-12 education. https://arxiv.org/abs/2405.02985
- Mayer, R. E., Mathias, A. & Wetzell, K. (2002). Fostering understanding of multimedia messages through pre-training: evidence for a two-stage theory of mental model construction. *Journal of Experimental Psychology: Applied*, 8(3), 147–154. https://doi.org/10.1037/1076-898X.8.3.147
