# Kit

Claude Code skills and workflows that make a narrated unit-opening film with gated checks: a fixed script read word
for word in one synthetic voice, over held paintings and labelled plates, with captions and an original score, in a
player that stops at checks a student must answer before the film goes on. The kit was condensed from building the
Othello opening in this repository. The skills run the tools in [`tools/`](../tools/) and the player in
[`player/`](../player/); the rules they follow rest on the claims in [`research/FINDINGS.md`](../research/FINDINGS.md).

## Use it with Claude Code

1. Open Claude Code at the root of this repository. It finds the skills in `.claude/skills/` and the workflows in
   `.claude/workflows/`, and reads the rules in [`CLAUDE.md`](../CLAUDE.md).
2. Make the project folder outside the repository and start the script manifest from its template:
   ```
   mkdir -p <project>/sources <project>/script/v01
   cp kit/templates/script/manifest.example.json <project>/script/v01/manifest.json
   ```
3. Ask for the `uvk-video-make` skill, or type `/uvk-video-make`. It names the skill for each stage. Every command
   runs from the repository root with the project's paths passed by flag, so nothing in a project run writes into the
   repository.

A workflow is the multi-agent version of the skill with the same name. Ask Claude Code to run it by name, with the
arguments listed at the top of its file, giving files and folders as absolute paths; with `repo` set to this
repository's path, it refuses a project or output folder inside the repository. Nothing in the kit sends or
publishes anything: sharing a review copy waits for explicit approval.

## Skills

| skill | use it to |
|---|---|
| `uvk-video-make` | run the whole pipeline in order, and find the skill for each stage |
| `uvk-narration-make` | audition voices, generate one take per scene, verify every take twice and time every word |
| `uvk-art-make` | brief, generate and finish the paintings in one style, and check every one by eye |
| `uvk-plates-make` | build labelled plates for the lines a painting cannot carry: a map, the ranks, a quotation, a word list |
| `uvk-film-make` | cut the stills to spoken anchors, fit the score, render and caption the film, and run its QA |
| `uvk-checks-make` | write the gated checks, record their spoken lines, build the player and test its gating in a browser |
| `uvk-film-audit` | run the per-shot test: does each picture show what the line being spoken is about |
| `uvk-video-compare` | compare productions of the same script on one rubric fixed in advance, every measure taken the same way |
| `uvk-feedback-sweep` | check every open piece of feedback against the build, and sort what is left |
| `uvk-library-make` | catalogue a project's documents and media with curated cards, so nothing is lost between sessions |

## Workflows

| workflow | does |
|---|---|
| `uvk-video-make` | the script check, verified narration, paintings and plates, the render and its QA, the shot audit and the QA record |
| `uvk-video-compare` | captures and judges each film in parallel, scores the rubric, has three refuters try to break every claim, and writes up the claims that survive |
| `uvk-film-audit` | two independent judges per shot, a story lens and a structure lens, a third when they split, and the totals |
| `uvk-feedback-sweep` | one reader per source, repeated items merged, every item checked against the build and sorted, then a critic for what was missed |

## Docs

| doc | holds |
|---|---|
| [`docs/PIPELINE.md`](docs/PIPELINE.md) | the stages in order: the skill, what each reads and writes, and the check that ends it |
| [`docs/STANDARDS.md`](docs/STANDARDS.md) | the rules, and the claim behind each one that rests on a claim |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | what stops the tools, and what went wrong in this build and what to do instead |
| [`docs/PROJECT-LAYOUT.md`](docs/PROJECT-LAYOUT.md) | the project folder the skills use, and the flag each path is given to |
| [`docs/NAMING.md`](docs/NAMING.md) | how files, folders, versions, skills and commits are named |

## Templates

| template | holds | read by |
|---|---|---|
| [`script/manifest.example.json`](templates/script/manifest.example.json) | the script as scenes and parts | `--manifest` of the narration, score and film tools; `tools/player/build_parts.py --parts` |
| [`narration/rubric.example.json`](templates/narration/rubric.example.json) | the judges' brief and criteria for an audition | `tools/narration/judge_takes.py --rubric` |
| [`art/briefs.example.json`](templates/art/briefs.example.json) | the style, the character bible and one brief per painting | `tools/art/generate_paintings.py --briefs` |
| [`score/cue-sheet.example.json`](templates/score/cue-sheet.example.json) | the phrases the music moves on, per scene | `tools/film/render-narrated.js --cue-sheet` |
| [`film/storyboard.example.json`](templates/film/storyboard.example.json) | one shot per picture change, each on a spoken anchor | `tools/film/render-narrated.js --storyboard` |
| [`checks/checks.example.json`](templates/checks/checks.example.json) | gated checks in the player's format | `tools/player/build_parts.py --checks` |
| [`review/rubric.example.md`](templates/review/rubric.example.md) | a comparison rubric, fixed before anything is measured | the comparison (`uvk-video-compare`) |
| [`review/fidelity.example.json`](templates/review/fidelity.example.json) | the folder and the command for script fidelity | `tools/review/measure_fidelity.py`, by flag |
| [`review/measures.example.json`](templates/review/measures.example.json) | the files in each film's folder and the command for the screen measures | `tools/review/measure_screen.py`, by flag |

The manifest, storyboard, cue sheet and checks templates fit together: two sample scenes with their anchors and two
checks, which `kit/scripts/check.sh` tests against each other. The plates' example content is
[`tools/plates/plates.example.json`](../tools/plates/plates.example.json), and the briefs behind this repository's
paintings are [`assets/painting-briefs.json`](../assets/painting-briefs.json).

## Scripts

```
kit/scripts/check.sh    # skills, workflows, the tool paths, flags and arguments they name, links, templates,
                        # key-shaped strings
kit/scripts/smoke.sh    # offline and without keys: every tool's --help or syntax, the example plates if Chrome is installed
```

Both run from anywhere, exit 1 on any failure and write nothing into the repository. Run `kit/scripts/check.sh`
before every commit.

## Requirements

ffmpeg, Node, the Python packages in `tools/requirements.txt`, and Chrome or Chromium for the plates:
[`tools/README.md`](../tools/README.md#requirements). The model-calling tools read their key from the environment:
[keys and endpoints](../tools/README.md#keys-and-endpoints).
