# Naming

A name says where a thing sits, not what happened to it. Counts, durations, voices, models and verdicts go in the
`README.md` or `QA.md` beside the thing. Every name should read correctly to someone who has never seen the project.

## Rules

1. **Case.** kebab-case for project folders, folders, files, branches, skills and workflows. Python files are
   snake_case, so they can be imported. Only docs use capitals: the doc names below, and the guides in `kit/docs/`.
2. **Domain first.** Every folder, tool, template, skill and workflow belongs to one domain, in pipeline order:
   `sources`, `script`, `narration`, `score`, `art`, `plates`, `film`, `checks`, `player`; with `review` (judging
   finished work), `feedback`, `library` and `tools` alongside, and `video` for the pipeline as a whole.
3. **Versions are folders called `vNN`**, two digits: `film/v07/`. Never put a description in a version name
   (`film-v5-long-final-paintings`); write it in that folder's `README.md`.
4. **One-off events are dated folders**, `YYYY-MM-DD-slug`: `narration/auditions/2026-11-02-two-voices/`.
5. **No `current`, `final`, `new` or `latest` folders.** The domain's `README.md` says which version is current.
6. **Don't repeat the folder in the file name.** Inside `film/v07/` the storyboard is `storyboard.json`. A file that
   leaves the project carries the unit's name instead: `othello-opening-poster.jpg`.
7. **Docs are named by what they hold:**
   - `README.md`: what is here, how to use it, which version is current
   - `QA.md`: what was checked and the results
   - `DECISIONS.md`: dated decisions, each with its reason
   - `METHODS.md`: how each measure was taken, and what it cannot show
   - `FINDINGS.md`: the claims, each with its evidence, the strongest counter-argument and the test that would settle
     it
   - `*.json`: data
8. **Tools are `tools/<domain>/<verb>_<object>.py`**, or `<verb>-<object>.js`: `tools/narration/verify_take.py`. A tool
   with subcommands is named for its object: `tools/library/library.py`.
9. **Templates are `kit/templates/<domain>/<artifact>.example.<ext>`**: `kit/templates/film/storyboard.example.json`.
10. **Skills are `uvk-<domain>-<verb>`** (uvk: unit video kit), with the verbs `make`, `audit`, `compare` and `sweep`:
    `uvk-narration-make`. A workflow has the name of the skill it fans out.
11. **One findings document per project, readable in five minutes.** It holds the few claims the project stands
    behind, numbered 1 to n, each with its evidence, the strongest counter-argument and the test that would settle it;
    the numbers stay in data files beside it. More claims are not more value.
12. **Git.** Branches are `<domain>-<topic>`: `film-v08-plates`. Commits are `<domain>[ vNN]: <what changed>`:
    `film v07: engraved finish`. No tool-attribution trailers.
13. **No people in names.** No file, folder, key, tag or branch carries a person's name: name it by its subject
    (`review/2026-10-07-three-films/animated/`). Nothing in a project or this repository is a note addressed to a
    person; a draft for someone is written in the conversation, not committed.
14. **Project folders are `<unit>-<asset>`**, as this repository is `othello-unit-video`.

## Names fixed elsewhere

These names stay as they are:

- Claude Code looks for `CLAUDE.md` and `.claude/skills/<name>/SKILL.md`.
- The renderer writes `Othello-opening-NARRATED.mp4` and `.vtt`, which `tools/player/build_parts.py` looks up, and
  the player's media are `Othello-opening-full.mp4` and `Othello-opening-part-N.mp4`. The library writes
  `CATALOG.md`.
- Two tools keep the names they had before these rules: `tools/film/render-narrated.js` and `tools/player/serve.js`.
- Clip and check ids are snake_case, as in the tools' examples (`vo_01`, `check_gate`), and the files named after
  them keep the id as it is: `vo_01.wav`, `alignment/vo_01.words.json`, `media/questions/check_gate-ask.m4a`.

Everything else follows the rules above.
