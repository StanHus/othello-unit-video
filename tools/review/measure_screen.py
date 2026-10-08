#!/usr/bin/env python3
"""Same-method screen and pace measures for narrated films (comparison rubric rows 6, 7 and 8).

Per film folder under --dir (default films/; one subfolder per film, each with shots.json):
- the per-shot test by count and by share of runtime (carries / partly / competes);
- on-screen text items per shot frame;
- visual detail per shot frame as edge density: ffmpeg edgedetect on a 640x360 copy of the frame cropped to
  y 6-78 %, so player captions and controls are excluded the same way for every film;
- narration pace and, with --first-word, the time a word is first heard, from a no-prompt Whisper word list.

  python3 -I tools/review/measure_screen.py --reference-words N [--dir films/] [--films a,b,...]
      [--first-word WORD] [--out <dir>/measures.json]

Inputs per film:
  shots.json     {"shots": [...]} or [...]; each shot has n, start, end and either
                 text_items + edge_density_pct (precomputed) or frame (an image path relative to the film folder)
                 and optionally on_screen_text (items separated by | , or ;).
                 A shot may also carry its verdict; otherwise verdicts.json {"verdicts": [{"n", "verdict"}]}.
  whisper-noprompt.json (optional)  {"words": [{"w", "s", "e"}]}. Without it, speech_span_s, words_per_minute
                 and the first-word time are carried over from an existing measures.json, and the film's
                 "speech_source" says so.
words_per_minute = --reference-words (the reference script's word count; every film reads the same script) / speech span.
"""
import argparse, json, pathlib, re, statistics, subprocess, sys


def load(p):
    return json.loads(pathlib.Path(p).read_text())


def shots_of(d):
    s = load(d / "shots.json")
    return s["shots"] if isinstance(s, dict) else s


def verdicts_of(d, shots):
    if all("verdict" in x for x in shots):
        return {x["n"]: x["verdict"] for x in shots}
    return {v["n"]: v["verdict"] for v in load(d / "verdicts.json")["verdicts"]}


def text_items(shot):
    if "text_items" in shot:
        return shot["text_items"]
    t = shot.get("on_screen_text")
    if not t or t.strip().lower() == "none":
        return 0
    if "[in-scene 3D text]" in t:   # annotation that separates captions from text drawn inside the scene
        t = t.split("[in-scene 3D text]", 1)[1].strip()
        return 0 if t in ("", "none") else len([x for x in t.split(" | ") if x.strip()])
    return len([x for x in re.split(r"\s*[|,;]\s*", t) if x.strip()])


def edge_density(frame):
    vf = "scale=640:360,crop=640:259:0:22,edgedetect,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-"
    out = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(frame), "-vf", vf, "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    return round(float(re.findall(r"YAVG=([0-9.]+)", out)[-1]) / 255 * 100, 1)


def edge_of(d, shot):
    if "edge_density_pct" in shot:
        return shot["edge_density_pct"]
    if shot.get("frame") and (d / shot["frame"]).exists():
        return edge_density(d / shot["frame"])
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="films/", help="folder with one subfolder per film (default films/)")
    ap.add_argument("--films", help="comma-separated film folders (default: every subfolder with shots.json)")
    ap.add_argument("--reference-words", type=int, required=True, help="word count of the reference script")
    ap.add_argument("--first-word", help="optional: report when a heard word containing this is first spoken")
    ap.add_argument("--out", help="default <dir>/measures.json")
    a = ap.parse_args()
    here = pathlib.Path(a.dir)
    out_path = pathlib.Path(a.out) if a.out else here / "measures.json"
    names = a.films.split(",") if a.films else sorted(p.parent.name for p in here.glob("*/shots.json"))
    if not names:
        sys.exit(f"no film folders with shots.json under {here}")
    previous = load(out_path) if out_path.exists() else {}
    result = {}
    for name in names:
        d = here / name
        shots = shots_of(d)
        verdict = verdicts_of(d, shots)
        total = shots[-1]["end"] - shots[0]["start"]
        secs = {"carries": 0.0, "partly": 0.0, "competes": 0.0}
        for x in shots:
            secs[verdict[x["n"]]] += x["end"] - x["start"]
        texts = [text_items(x) for x in shots]
        edges = [e for e in (edge_of(d, x) for x in shots) if e is not None]
        row = {
            "runtime_s": round(total, 1), "shots": len(shots), "mean_shot_s": round(total / len(shots), 1),
            "verdict_counts": {k: sum(1 for v in verdict.values() if v == k) for k in secs},
            "verdict_share_of_runtime_pct": {k: round(100 * v / total) for k, v in secs.items()},
            "text_items_per_frame": {"median": statistics.median(texts), "max": max(texts), "frames_with_any": sum(1 for t in texts if t)},
            "edge_density_pct": {"median": statistics.median(edges), "min": min(edges), "max": max(edges)} if edges else None,
        }
        wj = d / "whisper-noprompt.json"
        key = f"{a.first_word}s_first_heard_s" if a.first_word else None
        if wj.exists():
            words = load(wj)["words"]
            span = words[-1]["e"] - words[0]["s"]
            row.update({"speech_span_s": round(span, 1), "words_per_minute": round(a.reference_words / span * 60)})
            if key:
                first = next((w["s"] for w in words if a.first_word in w["w"].lower()), None)
                row[key] = round(first, 1) if first is not None else None
        elif name in previous and "speech_span_s" in previous[name]:
            row.update({k: previous[name][k] for k in ("speech_span_s", "words_per_minute", key) if k and k in previous[name]})
            row["speech_source"] = "carried over from the previous measures.json (the word timings are not in this folder)"
        result[name] = row
    out_path.write_text(json.dumps(result, indent=1) + "\n")
    for name, r in result.items():
        print(name, json.dumps(r))


if __name__ == "__main__":
    main()
