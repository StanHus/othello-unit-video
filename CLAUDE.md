# CLAUDE.md

This repository holds a study (`README.md`, `research/`), the tools that built its film (`tools/`), the player
(`player/`) and a kit of skills and workflows that run them (`kit/`, `.claude/`). Projects live outside the
repository: run every command from the repository root, pass the project's paths to the tools by flag, and never
write into the repository during a project run.

- Start with the `uvk-video-make` skill. It names the skill for each stage.
- Follow `kit/docs/STANDARDS.md`. The claim behind each rule is in `research/FINDINGS.md`.
- Name new files and folders by `kit/docs/NAMING.md`; the project layout is `kit/docs/PROJECT-LAYOUT.md`.
- `tools/` is the source of truth: read a tool's `--help` or usage header before writing a command for it, and never
  invent a flag.
- Keys come from the environment (`GENAI_API_KEY` or `GEMINI_API_KEY`). Never write a key into a file, a commit or a
  log.
- Nothing leaves the project without explicit approval: draft it, don't send it, and never write into someone else's
  environment or files.
- Run `kit/scripts/check.sh` before committing. Commit messages follow `kit/docs/NAMING.md`, with no tool-attribution
  trailers. Don't push unless asked.
