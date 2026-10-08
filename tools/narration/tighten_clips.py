#!/usr/bin/env python3
"""Tighten narration clips for a time cap: cap internal pauses, then a pitch-preserving tempo lift.

  python3 tools/narration/tighten_clips.py <in_dir> <out_dir> --tempo 1.18 --max-pause 0.3
Writes <out_dir>/<clip>.wav + narration-manifest.json (durations re-measured; source provenance kept). ffmpeg silenceremove + atempo.
"""
import argparse, json, pathlib, subprocess, wave

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--tempo", type=float, default=1.18); ap.add_argument("--max-pause", type=float, default=0.3); ap.add_argument("--threshold", default="-42dB")
a = ap.parse_args(); src, dst = pathlib.Path(a.src), pathlib.Path(a.dst); dst.mkdir(parents=True, exist_ok=True)
m = json.loads((src / "narration-manifest.json").read_text())
af = f"silenceremove=stop_periods=-1:stop_duration={a.max_pause}:stop_threshold={a.threshold}:stop_silence={a.max_pause},atempo={a.tempo}"
for cid, c in sorted(m["clips"].items()):
    out = dst / c["file"]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src / c["file"]), "-af", af, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    with wave.open(str(out)) as w: d = w.getnframes() / w.getframerate()
    c["source_duration_seconds"] = c["duration_seconds"]; c["duration_seconds"] = round(d, 3)
    print(f"{cid} {c['source_duration_seconds']:6.2f}s -> {d:6.2f}s")
m["tightened"] = {"from": str(src), "filter": af}
(dst / "narration-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("total", round(sum(c["duration_seconds"] for c in m["clips"].values()), 1), "s")
