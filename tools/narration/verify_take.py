#!/usr/bin/env python3
"""Transcribe narration WAVs with a Gemini model (google-genai SDK), giving it no script, and word-diff the result
against the exact text of the clip.

The transcription prompt asks for every sound from the first to the last, including any instructions or preamble,
because a TTS model can read its own style direction aloud; a transcriber that is shown the script tends to drop
such extra speech silently. The check assists listening; it does not replace it.

Usage:
  GENAI_API_KEY=... python3 tools/narration/verify_take.py --manifest <manifest.json> <clip_id> <file.wav> [<file.wav> ...]
Writes <file>.transcript.json next to each WAV (script and heard word counts, exact_match, the differences and the
transcript). Prints MATCH or DIFF per file. Exit status 1 if any file differs or returns no text.

Environment: GENAI_API_KEY (or GEMINI_API_KEY); optional GENAI_BASE_URL and GENAI_AUTH_HEADER as in
generate_takes.py; TRANSCRIBE_MODEL picks the model; OTHELLO_MANIFEST can replace --manifest.
"""
import argparse, difflib, json, os, pathlib, re, sys

PROMPT = ("Transcribe every spoken word in this audio verbatim from the very first sound to the last, including any "
          "instructions, preamble, or meta-commentary that precede or follow the story text. Output only the "
          "transcription; write numbers as spoken words.")
# How numerals in the reference text are spoken, so a correct reading is not counted as a difference.
SPOKEN = {"1603": "sixteen oh three"}


def make_client():
    key = os.environ.get("GENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("set GENAI_API_KEY (or GEMINI_API_KEY)")
    from google import genai
    from google.genai import types
    base, header = os.environ.get("GENAI_BASE_URL"), os.environ.get("GENAI_AUTH_HEADER")
    if not base and not header:
        return genai.Client(api_key=key), types
    opts = {"base_url": base} if base else {}
    if header:
        opts["headers"] = {header: key}
    return genai.Client(api_key="unused" if header else key, http_options=types.HttpOptions(**opts)), types


def words(t):
    t = t.replace("—", " ").replace("’", "'")
    for num, said in SPOKEN.items():
        t = t.replace(num, said)
    return ["oh" if w == "o" else w for w in re.findall(r"[a-z']+", t.lower())]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=os.environ.get("OTHELLO_MANIFEST"), help="recording manifest (or OTHELLO_MANIFEST)")
    ap.add_argument("--model", default=os.environ.get("TRANSCRIBE_MODEL", "gemini-3.5-flash"))
    ap.add_argument("--spoken", action="append", default=[], metavar="NUM=WORDS", help='extra numeral readings, e.g. 1604="sixteen oh four"')
    ap.add_argument("clip_id")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    if not a.manifest:
        ap.error("--manifest is required (or set OTHELLO_MANIFEST)")
    for s in a.spoken:
        k, _, v = s.partition("="); SPOKEN[k] = v.strip('"')
    scenes = json.loads(pathlib.Path(a.manifest).read_text())["scenes"]
    exact = next((s["spoken_text_exact"] for s in scenes if s["clip_id"] == a.clip_id), None)
    if exact is None:
        sys.exit(f"unknown clip_id {a.clip_id}")
    c, types = make_client()
    bad = 0
    for f in a.files:
        r = c.models.generate_content(model=a.model, contents=[
            types.Part.from_bytes(data=pathlib.Path(f).read_bytes(), mime_type="audio/wav"), PROMPT])
        heard = (r.text or "").strip()
        if not heard:
            bad += 1
            print(f"NOTEXT {f}  transcription returned no text (finish_reason={r.candidates[0].finish_reason if r.candidates else None}); re-run")
            continue
        x, y = words(exact), words(heard)
        ops = [o for o in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes() if o[0] != "equal"]
        diffs = [{"op": o, "script": " ".join(x[i1:i2]), "heard": " ".join(y[j1:j2])} for o, i1, i2, j1, j2 in ops]
        rep = {"file": pathlib.Path(f).name, "clip_id": a.clip_id, "transcribe_model": a.model, "script_words": len(x),
               "heard_words": len(y), "exact_match": not diffs, "differences": diffs, "transcript": heard}
        pathlib.Path(f).with_suffix(".transcript.json").write_text(json.dumps(rep, indent=2) + "\n")
        bad += bool(diffs)
        print(f"{'MATCH' if not diffs else 'DIFF '} {f}  script={len(x)} heard={len(y)}")
        for d in diffs[:8]:
            print(f"      {d['op']:7s} script='{d['script'][:70]}'  heard='{d['heard'][:110]}'")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
