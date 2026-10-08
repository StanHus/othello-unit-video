#!/bin/sh
# Offline smoke test of the tools: no keys, no network, nothing written inside the repository.
#   1. every Python tool answers --help;
#   2. every Node tool passes node --check;
#   3. the example plates (tools/plates/plates.example.json) build into a temporary folder, if Chrome is installed;
#   4. nothing inside the repository changed while it ran.
# Usage: kit/scripts/smoke.sh    (from anywhere; exit 1 on any failure)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
for c in python3 node; do
  command -v "$c" >/dev/null 2>&1 || { echo "$c not found on PATH"; exit 1; }
done
TMP=$(mktemp -d "${TMPDIR:-/tmp}/kit-smoke.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT
trap 'exit 130' INT TERM
unset GENAI_API_KEY GEMINI_API_KEY GENAI_BASE_URL GENAI_AUTH_HEADER
export PYTHONDONTWRITEBYTECODE=1
cd "$TMP" || exit 1
: > "$TMP/.start"
fails=0
bad() { echo "  FAIL $*"; fails=$((fails + 1)); }

echo "1. Python tools answer --help"
for f in $(cd "$ROOT" && find tools -name '*.py' | sort); do
  if python3 "$ROOT/$f" --help > "$TMP/out.txt" 2>&1; then echo "  ok   $f"; else bad "$f: $(tail -n 1 "$TMP/out.txt")"; fi
done

echo "2. Node tools parse"
for f in $(cd "$ROOT" && find tools -name '*.js' | sort); do
  if node --check "$ROOT/$f" > "$TMP/out.txt" 2>&1; then echo "  ok   $f"; else bad "$f: $(tail -n 1 "$TMP/out.txt")"; fi
done

echo "3. Example plates"
chrome=""
for c in "${CHROME_BIN:-}" "$(command -v google-chrome 2>/dev/null)" "$(command -v google-chrome-stable 2>/dev/null)" \
  "$(command -v chromium 2>/dev/null)" "$(command -v chromium-browser 2>/dev/null)" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  if [ -n "$c" ] && [ -e "$c" ]; then chrome=$c; break; fi
done
if [ -z "$chrome" ]; then
  echo "  skipped: Chrome or Chromium not found (install one, or set CHROME_BIN, to build the plates)"
elif python3 "$ROOT/tools/plates/build_plates.py" --content "$ROOT/tools/plates/plates.example.json" --out "$TMP/plates" \
  > "$TMP/out.txt" 2>&1; then
  expected=$(python3 -c 'import json, sys; print(sum(len(p.get("reveal") or [0]) for p in json.load(open(sys.argv[1]))["plates"]))' \
    "$ROOT/tools/plates/plates.example.json")
  built=$(find "$TMP/plates/plates" -name '*.png' | wc -l | tr -d ' ')
  if [ "$built" = "$expected" ] && [ -s "$TMP/plates/plates.json" ] && [ -s "$TMP/plates/contact-sheet.jpg" ]; then
    echo "  ok   $built plates, plates.json and contact-sheet.jpg"
  else
    bad "built $built of $expected plates"
  fi
else
  bad "tools/plates/build_plates.py: $(tail -n 1 "$TMP/out.txt")"
fi

echo "4. Nothing written inside the repository"
changed=$(find "$ROOT" -path "$ROOT/.git" -prune -o -newer "$TMP/.start" -print 2>/dev/null)
if [ -n "$changed" ]; then
  bad "changed inside the repository while the test ran:"
  echo "$changed" | sed "s|^$ROOT/*|       |"
else
  echo "  ok"
fi

if [ "$fails" -gt 0 ]; then echo "$fails failure(s)"; exit 1; fi
echo "smoke test passed"
