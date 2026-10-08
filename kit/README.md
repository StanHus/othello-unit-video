# Kit

The steps that made the Othello film, as Claude Code skills and workflows. They call the scripts in
[`tools/`](../tools/) and build the player in [`player/`](../player/); their rules come from the claims in
[`research/FINDINGS.md`](../research/FINDINGS.md).

## Use

Open Claude Code at the repository root. It picks up the skills and workflows in `.claude/` and the rules in
[`CLAUDE.md`](../CLAUDE.md). Keep each project outside the repository, starting from the manifest template:

```
mkdir -p <project>/sources <project>/script/v01
cp kit/templates/script/manifest.example.json <project>/script/v01/manifest.json
```

Then ask for `uvk-video-make` (or type `/uvk-video-make`). It goes through the stages in order and names the skill
for each. Commands run from the repository root and get the project's paths by flag, so a project run writes nothing
into the repository. A workflow is the multi-agent version of the skill with the same name; its arguments are listed
at the top of its file. Nothing in the kit sends or publishes anything.

## Skills

| skill | use it to |
|---|---|
| `uvk-video-make` | run the pipeline in order |
| `uvk-narration-make` | audition voices, generate one take per scene, verify every take twice, time every word |
| `uvk-art-make` | brief, generate and finish the paintings, and check each one by eye |
| `uvk-plates-make` | build labelled plates for what a painting can't show: a map, the ranks, a quotation, a word list |
| `uvk-film-make` | cut the stills to spoken anchors, fit the score, then render, caption and check the film |
| `uvk-checks-make` | write the gated checks, record their spoken lines, build the player and test it in a browser |
| `uvk-film-audit` | run the per-shot test: does each picture show what the line being spoken is about |
| `uvk-video-compare` | compare productions of one script on a rubric fixed in advance |
| `uvk-feedback-sweep` | check open feedback against the build and sort what is left |
| `uvk-library-make` | catalogue a project's documents and media |

## Workflows

| workflow | does |
|---|---|
| `uvk-video-make` | the pipeline, from the script check to the film's QA, with agents |
| `uvk-video-compare` | measures each film in parallel, scores the rubric, then tries to break each claim |
| `uvk-film-audit` | two judges per shot, and a third when they disagree |
| `uvk-feedback-sweep` | one reader per source, items merged and checked against the build, then a pass for what was missed |

## Also here

- [`docs/`](docs/): [the stages](docs/PIPELINE.md), [the rules](docs/STANDARDS.md),
  [known problems](docs/TROUBLESHOOTING.md), [the project layout](docs/PROJECT-LAYOUT.md) and [naming](docs/NAMING.md).
- [`templates/`](templates/): starting files for the script manifest, the narration rubric, the painting briefs, the
  cue sheet, the storyboard, the checks and the comparison. The manifest, storyboard, cue sheet and checks make one
  two-scene sample, which the check script tests against each other.
- [`scripts/`](scripts/): `check.sh` checks the skills, the workflows, the tool commands they name, links, templates
  and key-shaped strings; `smoke.sh` runs every tool's `--help` or syntax check, offline. Run `kit/scripts/check.sh`
  before every commit.

Requirements and keys are in [`tools/README.md`](../tools/README.md#requirements).
