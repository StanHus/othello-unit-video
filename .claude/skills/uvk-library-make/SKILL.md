---
name: uvk-library-make
description: Catalogue a unit-video project's documents, sources, decisions and media with curated cards and topic pages, so nothing is lost between sessions and the current version of anything can be found. Use after adding documents, feedback, analyses or media to a project, at the record stage, or when asked to collate a project's materials into a library.
---

# Library

`tools/library/library.py` walks a project folder and writes a catalogue into the folder you name, and nowhere else:
`catalog.json`, `CATALOG.md` (items by kind), `topics/` (one page per tag, newest first) and `text/` (extracted text,
for search). Every document gets an item; media get one item per folder. What you decide about an item lives on its
card; everything else is derived, so rebuilding is always safe. The library belongs to the project: keep it in the
project folder, not in this repository.

```
python3 tools/library/library.py build --root <project> --out <project>/library
python3 tools/library/library.py list-uncurated --out <project>/library
python3 tools/library/library.py check --out <project>/library --strict
python3 tools/library/library.py search --out <project>/library <term> [<term> ...]
```

`list-uncurated` prints the items with no card yet. `check` fails on a `supersedes` path that is not catalogued, an
unknown kind, tag or status, or a card that matches no catalogued path; `--strict` also fails while any item has no
card. `--help` lists what is never catalogued: hidden folders, render scratch and the per-clip data the tools write. Add
`--skip <pattern>` to leave out more, or `--include <path>` to catalogue part of a project.

## Cards

Cards are JSON files in `<project>/library/curation/`, each mapping a path relative to the project to its card. A
media folder's path ends in `/`.

- `title`, `author` (`this project` for your own work) and `date` (`YYYY-MM-DD`, the document's own date; without
  one the catalogue shows the file's time and marks it).
- `kind` and `tags` from the lists `--help` prints. A `_vocabulary.json` in the same folder replaces them, and a
  `_topic-intros.json` gives each topic page an opening paragraph.
- `status`: `current` (the version to use), `superseded` (replaced), `historical` (kept as evidence) or `reference`
  (outside material).
- `supersedes`: the paths it replaces. Mark each replaced card `superseded`.
- `summary`: the finding, not the topic. "Labelled plates on the 10 structural lines made all 22 lines carry", not
  "plate results".

## Sources

Feedback, reviews, comments, call notes and briefs go into `<project>/sources/` verbatim, one dated file each. Keep
them read-only (`chmod a-w`): unlock the folder only to add a file, then lock it again. Put any context note below the
verbatim text, never inside it, and never address a note to anyone.

## Record

At the end of a version: build, card every item until `list-uncurated` prints nothing, and pass `check --strict`.
Then write each claim the work supports with its evidence, the strongest counter-argument and the test that would
settle it, in the shape of `research/FINDINGS.md`, citing the paths it rests on.
