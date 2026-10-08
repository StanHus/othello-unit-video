#!/usr/bin/env python3
"""Blind, shuffled comparison of TTS takes of one passage by audio-capable LLM judges.

Every take folder under --takes holds <clip>.wav for the same clip. Each judging pass shuffles the takes with its
own seed, labels them A, B, C... in that order, sends the reference text, the rubric and the audio, and asks for
per-take scores and a ranking as JSON. Labels are mapped back to folder names, so no judge sees a model or voice
name. The passes are combined with a Borda count (n points for first place, n-1 for second, ...) and the mean
"overall" score. The same judge can reverse its ranking between seeds: read the per-pass rankings, not only the
total. The judges assist a human listen; they do not replace it.

Usage:
  GENAI_API_KEY=... python3 tools/narration/judge_takes.py --takes <auditions dir> --clip vo_intro_01 \
      --reference passage.txt [--rubric rubric.json] [--models m1,m2] [--seeds 1,2] [--out judgments.json]

  --reference  a .txt file with the exact passage, or a recording manifest (.json) to look --clip up in
  --rubric     optional JSON: {"brief": "...", "criteria": {"name": "what a 10 means", ...}}; the default asks for
               intelligibility, pacing, naturalness, register and exact words
Writes the raw judgments (with each pass's order, labels and reply) to --out and prints the aggregate table.

Environment: GENAI_API_KEY (or GEMINI_API_KEY); optional GENAI_BASE_URL and GENAI_AUTH_HEADER as in
generate_takes.py.
"""
import argparse, json, os, pathlib, random, re, string, sys

DEFAULT_RUBRIC = {
    "brief": ("You are a dialogue editor choosing the narration take for a short educational film for students aged "
              "14 to 15. Judge only what you hear."),
    "criteria": {
        "intelligibility": "every word is clear at normal listening volume",
        "pacing": "the pace suits the passage; pauses help meaning and none drag",
        "naturalness": "no robotic prosody, glitches, clipped words or audio artefacts",
        "register": "the delivery suits the passage without exaggeration or character voices",
    },
}


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


def reference_text(path, clip):
    p = pathlib.Path(path)
    if p.suffix == ".json":
        scenes = json.loads(p.read_text())["scenes"]
        hit = next((s["spoken_text_exact"] for s in scenes if s["clip_id"] == clip), None)
        if hit is None:
            sys.exit(f"{clip} not in {p.name}")
        return hit
    return p.read_text().strip()


def ask(client, types, model, takes_dir, clip, order, seed, text, rubric):
    labels = {t: string.ascii_uppercase[i] for i, t in enumerate(order)}
    keys = list(rubric["criteria"])
    crit = "\n".join(f"- {k} (1-10): {v}" for k, v in rubric["criteria"].items())
    schema = ("{\"takes\": {\"<label>\": {" + ",".join(f"\"{k}\":1-10" for k in keys) +
              ",\"exact_words\":true/false,\"word_issues\":\"...\",\"artifacts\":\"...\",\"overall\":1-10,\"one_line\":\"...\"}}, "
              "\"ranking\": [labels best first], \"why_winner\": \"...\"}")
    parts = [rubric["brief"] + "\n\nScore each take on:\n" + crit +
             "\n- exact_words: true only if the take reads the exact script with no added, dropped or changed words."
             "\n\nEXACT SCRIPT:\n" + text + f"\n\nYou will hear {len(order)} takes of this script, labelled in order."]
    for t in order:
        parts += [f"TAKE {labels[t]}:", types.Part.from_bytes(data=(takes_dir / t / f"{clip}.wav").read_bytes(), mime_type="audio/wav")]
    parts.append("Listen to every take fully. Return ONLY JSON: " + schema)
    r = client.models.generate_content(model=model, contents=parts,
                                       config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"))
    raw = (r.text or "").strip()
    d = json.loads(re.sub(r"^```(?:json)?|```$", "", raw).strip())
    inv = {v: k for k, v in labels.items()}
    valid = "".join(labels.values())

    def lab(k):   # accept "A", "Take A", "TAKE A:" and the like
        m = re.search(rf"(?:^|[^A-Za-z])([{valid}])(?:$|[^A-Za-z])", " " + str(k) + " ")
        return m.group(1) if m else None
    takes = {lab(k): v for k, v in d.get("takes", {}).items() if lab(k)}
    ranking = [lab(x) for x in d.get("ranking", []) if lab(x)]
    return {"model": model, "seed": seed, "order": order, "labels": labels,
            "takes": {inv[k]: v for k, v in takes.items() if k in inv},
            "ranking": [inv[x] for x in ranking if x in inv], "why_winner": d.get("why_winner"), "raw": raw}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--takes", required=True, help="folder with one subfolder per take")
    ap.add_argument("--clip", required=True, help="clip id; each take folder holds <clip>.wav")
    ap.add_argument("--reference", required=True, help=".txt passage or recording manifest .json")
    ap.add_argument("--rubric", help="rubric JSON (see the docstring)")
    ap.add_argument("--models", default=os.environ.get("JUDGE_MODELS", "gemini-3.1-pro-preview,gemini-3.8-flash"))
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--out", default="judgments.json")
    a = ap.parse_args()
    takes_dir = pathlib.Path(a.takes)
    takes = sorted(p.parent.name for p in takes_dir.glob(f"*/{a.clip}.wav"))
    if len(takes) < 2:
        sys.exit(f"need at least two take folders with {a.clip}.wav under {takes_dir}")
    if len(takes) > 26:
        sys.exit("at most 26 takes per comparison")
    rubric = json.loads(pathlib.Path(a.rubric).read_text()) if a.rubric else DEFAULT_RUBRIC
    text = reference_text(a.reference, a.clip)
    client, types = make_client()
    out = []
    for model in [m.strip() for m in a.models.split(",") if m.strip()]:
        for seed in [int(s) for s in a.seeds.split(",")]:
            order = takes[:]; random.Random(seed).shuffle(order)
            try:
                out.append(ask(client, types, model, takes_dir, a.clip, order, seed, text, rubric))
                print("ok", model, seed, out[-1]["ranking"][:3], flush=True)
            except Exception as e:
                print("FAIL", model, seed, type(e).__name__, str(e)[:200], flush=True)
    pathlib.Path(a.out).write_text(json.dumps({"clip": a.clip, "takes": takes, "rubric": rubric, "passes": out}, indent=2) + "\n")
    overall = {t: [] for t in takes}
    borda = {t: 0 for t in takes}
    for j in out:
        for t, v in j["takes"].items():
            if isinstance(v, dict) and isinstance(v.get("overall"), (int, float)):
                overall[t].append(v["overall"])
        for i, t in enumerate(j["ranking"]):
            borda[t] += len(takes) - i
    print("\n%-44s %-13s %-6s %s" % ("take", "mean overall", "borda", "first places"))
    for t in sorted(takes, key=lambda t: -borda[t]):
        firsts = sum(1 for j in out if j["ranking"][:1] == [t])
        mean = sum(overall[t]) / len(overall[t]) if overall[t] else float("nan")
        print("%-44s %-13.2f %-6d %d/%d" % (t, mean, borda[t], firsts, len(out)))


if __name__ == "__main__":
    main()
