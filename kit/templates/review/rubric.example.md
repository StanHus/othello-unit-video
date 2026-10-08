# Comparison rubric

For films of the same script. Fix every row before any film is measured, and check each row the same way on every
film. Copy this file into the comparison folder and adapt the rows to the unit before the first measurement; after
that, change a row only as a dated correction with its reason.

| # | row | how it is checked | measured with |
|---|---|---|---|
| 1 | script fidelity | each film's own script against the fixed script: the share of its words found in order; a no-prompt recogniser only confirms that the audio reads the film's script | `tools/review/measure_fidelity.py` |
| 2 | coverage of the knowledge areas | each knowledge area the script covers, looked for in what is spoken | a reading of each film's script |
| 3 | opening, teaching and return | how the narration opens, what it teaches and how it closes | a judgement |
| 4 | checks that gate playback | how many; whether playback waits for an answer; whether a seek can pass an open check | the player, by hand |
| 5 | pictures that teach structure | which structural lines (a map, a hierarchy, a timeline, a definition) have such a picture on screen while they are read | the frames, by hand |
| 6 | per-shot test | carries, partly or competes, by count and by share of screen time | `uvk-film-audit`, then `tools/review/measure_screen.py` |
| 7 | length and pace | runtime, speech span, words a minute | `tools/review/measure_screen.py` |
| 8 | visual density | text items per frame; share of edge pixels in each frame | `tools/review/measure_screen.py` |
| 9 | look and motion | production style and how the pictures move | a judgement |
| 10 | the narrator's role | who narrates, who asks, whether a narrator figure is on screen | a judgement |

For every judgement row, say who judged and whether they built any of the films. A builder's verdicts need a second
judge.
