#!/bin/sh
# Check the kit: skills, workflows, the tool paths, flags and arguments they name, links, templates and key-shaped
# strings.
# Usage: kit/scripts/check.sh    (from anywhere; exit 1 on any failure)
exec python3 "$(dirname "$0")/check.py" "$@"
