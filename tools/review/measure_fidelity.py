#!/usr/bin/env python3
"""Script fidelity of narrated films against one reference script (comparison rubric, row 1).

Each film's script text (what its narration was generated from) is compared word by word, in order, against the
reference script: fidelity = reference words found in order / reference words. Optionally a no-prompt Whisper word
list per film is compared with that film's own script, to confirm the audio reads it; recogniser errors (numerals,
names) then show up as Whisper differences, not as script changes. Score fidelity on the scripts, not on ASR output.

  python3 -I tools/review/measure_fidelity.py --reference script.txt \
      --film stills=stills-script.txt --film animated=animated-script.txt \
      [--whisper stills=stills-words.json ...] [--out fidelity.json] [--diffs]

Inputs: plain .txt, or .json in one of three shapes: {"scenes": [{"spoken_text_exact": ...}]} (a recording
manifest), {"segments": [{"narration"|"text": ...}]}, or {"text": ...}. A Whisper word list is
{"words": [{"w": word, "s": start, "e": end}, ...]}.
By default the output holds counts and percentages only. --diffs adds the word-level differences: they quote the
scripts, so keep them local when the scripts are not yours to publish.
"""
import argparse, difflib, json, pathlib, re, sys


def norm(t):
    t = t.lower().replace("’", "'").replace("—", " ").replace("–", " to ").replace("1603", "sixteen oh three")
    return ["oh" if w == "o" else w for w in re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", t)]


def read_text(path):
    p = pathlib.Path(path)
    if p.suffix != ".json":
        return p.read_text()
    d = json.loads(p.read_text())
    if "scenes" in d:
        return " ".join(s["spoken_text_exact"] for s in d["scenes"])
    if "segments" in d:
        return " ".join(s.get("narration") or s.get("text") or "" for s in d["segments"])
    if "text" in d:
        return d["text"]
    sys.exit(f"{p}: no scenes, segments or text")


def matched(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(x.size for x in sm.get_matching_blocks()), sm


def diffs(a, b, sm):
    return [f"{op}: {' '.join(a[i1:i2]) or '-'} -> {' '.join(b[j1:j2]) or '-'}" for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]


def pairs(items, flag):
    out = {}
    for it in items:
        name, sep, path = it.partition("=")
        if not sep:
            sys.exit(f"{flag} wants name=path, got {it!r}")
        out[name] = path
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--film", action="append", default=[], metavar="NAME=PATH", required=True)
    ap.add_argument("--whisper", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--out", default="fidelity.json")
    ap.add_argument("--diffs", action="store_true", help="also write word-level differences (local use)")
    a = ap.parse_args()
    ref = norm(read_text(a.reference))
    whisper = pairs(a.whisper, "--whisper")
    result = {"reference_words": len(ref), "films": {}}
    for name, path in pairs(a.film, "--film").items():
        h = norm(read_text(path))
        same, sm = matched(ref, h)
        row = {"script_words": len(h), "reference_words_in_order": same, "fidelity_pct": round(100 * same / len(ref), 1)}
        if a.diffs:
            row["differences_vs_reference"] = diffs(ref, h, sm)
        if name in whisper:
            heard = norm(" ".join(w["w"] for w in json.loads(pathlib.Path(whisper[name]).read_text())["words"]))
            agree, sm2 = matched(h, heard)
            row.update({"whisper_words": len(heard), "whisper_agrees": agree, "whisper_agree_pct": round(100 * agree / len(h), 1)})
            if a.diffs:
                row["whisper_differences"] = diffs(h, heard, sm2)
        result["films"][name] = row
    pathlib.Path(a.out).write_text(json.dumps(result, indent=1) + "\n")
    for name, r in result["films"].items():
        line = f"{name:12s} script {r['script_words']} words; {r['reference_words_in_order']}/{len(ref)} of the reference in order = {r['fidelity_pct']}%"
        if "whisper_agrees" in r:
            line += f"; Whisper agrees on {r['whisper_agrees']}/{r['script_words']} ({r['whisper_agree_pct']}%)"
        print(line)


if __name__ == "__main__":
    main()
