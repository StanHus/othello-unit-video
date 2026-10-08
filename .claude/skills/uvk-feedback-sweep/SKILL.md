---
name: uvk-feedback-sweep
description: Collect every open piece of feedback on a unit video, from written reviews, comments and call notes to the project's own audits and comparisons, check each item against the current build, and sort what is still open into apply now, needs the project's decision, or outside this project's control. Use when asked what feedback is left to apply, before a new version, or when new feedback arrives.
---

# Feedback sweep

## Gather

Read every source in full: written reviews, including their open questions; comments; call notes; and the project's
own audits and comparisons (`uvk-film-audit`, `uvk-video-compare`). Keep each source verbatim in `<project>/sources/`
(`uvk-library-make`). For every item note the exact words, the source and where in it they are, and whether they are
the source's own words or a quotation it reports.

## Check each item against the build

If the current build already does what an item asks, say where (the file, or the version and shot) and set it aside.
Check before claiming: a feature that seems missing may already be in `player/index.html` or `tools/`, and a quoted
line may be the document's own commentary rather than words it reports.

## Sort what is open

- **Apply now:** inside the fixed script, the rules in `kit/docs/STANDARDS.md` and the decisions already made.
- **Needs the project's decision:** it conflicts with a decision already made or with one of those rules; name it. A
  request to time-stretch the voice to save time, for example, conflicts with the rule to split the film or change
  the model instead.
- **Outside this project's control:** it changes what the project does not own, such as the script's words, check
  questions supplied with it, or someone else's files or environment, or it needs an answer no source gives.

## Then

List the groups plainly, each item with its source and where it is. When told to apply them, apply the first group;
apply the second only with explicit approval; for the third, say in the reply what would have to be asked, never in a
note in the repository or the project. Run the sweep again after applying: what was applied should come back as
already done.

The workflow `uvk-feedback-sweep` runs the same sweep with agents: one reader per source, repeated items merged, each
item checked against the build and sorted, then a critic for what was missed. Pass `project` (the project folder),
`sources` (a list of files) and, optionally, `build_summary`; it changes no files.
