# Standards

The rules every skill follows. Where a rule rests on one of the seven claims in
[`research/FINDINGS.md`](../../research/FINDINGS.md), it names the claim; the evidence, the strongest
counter-argument and the test that would settle each claim are there. The claims are untested with students: they
are design hypotheses, and a rule changes when its test says so.

## Script and length

1. The script is fixed, a design choice of this project: never cut, paraphrase, add to or reorder its words. (claim 2)
2. Meet a length limit by changing the model or splitting the film into parts, never by cutting lines or
   time-stretching a take. (claim 2)
3. Score fidelity on each film's script, not on a recogniser's transcript: recogniser errors are not script changes.
4. Captions are the script: they are built from `spoken_text_exact`, never from a transcript.

## Narration

5. Verify every take twice: a transcription given no script, then a second recogniser with no prompt. (claim 6)
6. Regenerate until both agree, or until every difference is a recogniser error seen before; then listen. (claim 6)
7. Check short lines, the spoken check lines among them, as strictly as long ones.
8. Choose the voice and model by measured pace and blind judging, then by ear. The judges assist; they never decide.
9. One folder per model, voice and direction, and never two generators running into one folder.

## Timing

10. Every cut, caption and music move sits at a measured word time. A render with estimated times is labelled as one.
11. Words a minute are measured over the speech span, first word to last, not over the file.

## Pictures

12. Run the per-shot test on every line: does the picture show what the line being spoken is about? (claim 3)
13. Paintings for story lines, labelled plates for structural lines: a map, the ranks, a definition, a word list.
    (claim 3)
14. A plate shows only words the narration speaks while it is on screen, and quotes the play word for word with its
    act.scene.line.
15. Bring each plate item in on the phrase that names it, and bold key words in the captions (`OTHELLO_BOLD`).
16. Hold each picture: held stills and hard cuts, no camera moves. (claim 1)
17. Treat a generated look as a matter of the finish, not the format. (claim 1)
18. Compare every generated or repainted image with its brief and its source by eye: a check that confirms which file
    is on screen does not see what the file shows.
19. No legible stray text and no depicted death: show the line, not the act.
20. Count clutter both ways: text items per frame and picture detail. (claim 3)

## Checks

21. Gate every path through the player: playing, seeking, reloading, switching parts. (claim 4)
22. Nothing a student sees or hears may give an answer before the first attempt: put each check after the scene it
    asks about, and blur the film while a check is open. (claim 3)
23. When a check asks for the student's own words, ask before showing any option, keep them unmarked and refuse only
    noise; the film goes on only after a right answer to a recognition question. (claim 5)
24. Never reply to what a student writes, and never send it to a marker. (claim 5)
25. Give the player a new storage tag whenever the timeline changes.

## Working

26. Projects live outside the repository. Pass their paths to the tools by flag, run every command from the
    repository root, and write nothing into the repository during a project run.
27. Nothing leaves the project without explicit approval: draft it, don't send it. Never write into someone else's
    environment or files.
28. Keys come from the environment. Never write one to a file, a commit or a log.
29. Name every file and folder by [NAMING.md](NAMING.md), and keep people's names out of names and notes.
30. Record a claim with its evidence, the strongest counter-argument and the test that would settle it.
