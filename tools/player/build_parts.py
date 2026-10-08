#!/usr/bin/env python3
"""Wire a rendered narrated film into the player: the full film plus parts of at most --max seconds, cut at scene
boundaries, with the gated checks placed from measured scene ends.

  python3 tools/player/build_parts.py --film-dir <render dir> --parts parts.json --checks checks.json \
      [--player-dir player] [--poster poster.jpg] [--storage-tag v1] [--max 120] [--title T] [--subtitle S]

--film-dir  holds narrated-timeline.json, Othello-opening-NARRATED.mp4 and .vtt (tools/film/render-narrated.js)
--parts     JSON with "parts": [{"part": 1, "title": "...", "scenes": [1, 2, 3]}, ...] (a recording manifest
            with a "parts" list also works)
--checks    JSON with "checks": [{"id", "afterScene", "corner", "say", "ask", "correct", "steps": [...]}] and an
            optional "voice": {"voice": "<name>"}; see player/README.md for the step schema
Writes <player-dir>/media/Othello-opening-full.{mp4,vtt} and Othello-opening-part-N.{mp4,vtt} (poster as cover
art), <player-dir>/content/checks.js (full film) and checks-parts.js (parts), and <film-dir>/parts/parts.json.
Each check's `at` = end of its scene minus 0.3 s and `sceneStart` = start of its scene, relative to the video.
"""
import argparse, json, pathlib, re, shutil, subprocess

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--film-dir", required=True); ap.add_argument("--parts", required=True); ap.add_argument("--checks", required=True)
ap.add_argument("--player-dir", default="player"); ap.add_argument("--poster", help="poster image, copied to <player-dir>/media/")
ap.add_argument("--storage-tag", default="v1"); ap.add_argument("--max", type=float, default=120.0)
ap.add_argument("--title", help="page title shown by the player"); ap.add_argument("--subtitle", help="line under the title when there is one part")
a = ap.parse_args()
fd = pathlib.Path(a.film_dir); parts_doc = json.loads(pathlib.Path(a.parts).read_text()); tl = json.loads((fd / "narrated-timeline.json").read_text())
checks_doc = json.loads(pathlib.Path(a.checks).read_text()); checks = checks_doc["checks"]
check_voice = checks_doc.get("voice", {}).get("voice", "unrecorded")
scene = {s["scene"]: s for s in tl["scenes"]}
film, vtt = fd / "Othello-opening-NARRATED.mp4", fd / "Othello-opening-NARRATED.vtt"
L = pathlib.Path(a.player_dir); media = L / "media"; media.mkdir(parents=True, exist_ok=True); (L / "content").mkdir(parents=True, exist_ok=True)
out = fd / "parts"; out.mkdir(exist_ok=True)
thumb = None
if a.poster:
    thumb = media / pathlib.Path(a.poster).name
    if pathlib.Path(a.poster).resolve() != thumb.resolve():
        shutil.copy(a.poster, thumb)
poster_rel = f"media/{thumb.name}" if thumb else None


def ts(t):
    h, r = divmod(max(t, 0), 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def cues_of(text):
    found = []
    for blk in re.split(r"\n\s*\n", text.strip()):
        m = re.search(r"(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)[^\n]*\n(.*)", blk, re.S)
        if m: g = m.groups(); found.append((int(g[0]) * 3600 + int(g[1]) * 60 + float(g[2]), int(g[3]) * 3600 + int(g[4]) * 60 + float(g[5]), g[6].strip()))
    return found


CUES = cues_of(vtt.read_text())


def cut(name, scenes, fade_in):
    t0, t1 = scene[scenes[0]]["start_seconds"], scene[scenes[-1]]["end_seconds"]; d = t1 - t0
    mp4, pv = out / f"{name}.mp4", out / f"{name}.vtt"
    pc = [(max(s, t0) - t0, min(e, t1) - t0, x) for s, e, x in CUES if e > t0 + 0.01 and s < t1 - 0.01]
    pv.write_text("WEBVTT\n\n" + "\n\n".join(f"{i+1}\n{ts(s)} --> {ts(e)}\n{x}" for i, (s, e, x) in enumerate(pc)) + "\n")
    af = (f"afade=t=in:st=0:d={fade_in}," if fade_in else "") + f"afade=t=out:st={max(d - 0.45, 0):.3f}:d=0.45"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", str(film), "-i", str(pv)]
    maps = ["-map", "0:v:0", "-map", "0:a:0", "-map", "1:0"]
    cover = []
    if thumb:
        cmd += ["-i", str(thumb)]; maps += ["-map", "2:0"]; cover = ["-c:v:1", "mjpeg", "-disposition:v:1", "attached_pic"]
    subprocess.run(cmd + maps + ["-c:v:0", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "24",
                                 "-c:a", "aac", "-b:a", "160k", "-af", af, "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-disposition:s:0", "default",
                                 *cover, "-movflags", "+faststart", "-t", f"{d:.3f}", str(mp4)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip())
    shutil.copy(mp4, media / mp4.name); shutil.copy(pv, media / pv.name)
    stops = []
    for c in checks:
        n = c["afterScene"]
        if n in scenes:
            s = dict(c); s.update(at=round(scene[n]["end_seconds"] - t0 - 0.3, 3), sceneStart=round(scene[n]["start_seconds"] - t0, 3)); stops.append(s)
    print(f"{name}: scenes {scenes} {t0:.3f}-{t1:.3f} -> {dur:.3f}s, {len(pc)} cues, checks at {[s['at'] for s in stops]}")
    return {"film": f"media/{mp4.name}", "captions": f"media/{pv.name}", "duration": round(dur, 3), "stops": stops}


full = cut("Othello-opening-full", list(range(1, len(scene) + 1)), 0); full.update(part=1, title="The full opening")
parts = []
for p in parts_doc["parts"]:
    r = cut(f"Othello-opening-part-{p['part']}", p["scenes"], 0 if p["part"] == 1 else 0.35); r.update(part=p["part"], title=p["title"])
    assert r["duration"] <= a.max + 0.05, f"part {p['part']} {r['duration']}s > {a.max}s"; parts.append(r)
head = (f"/* Gated checks for the narrated opening (built by tools/player/build_parts.py). Check voice: {check_voice}.\n"
        "   `at` = end of the scene minus 0.3 s, relative to the video. */\n")
labels = {k: v for k, v in (("title", a.title), ("subtitle", a.subtitle)) if v}
(L / "content/checks.js").write_text(head + "window.OTHELLO_FILM_CHECKS = " + json.dumps({**labels, "poster": poster_rel, "storageKey": f"othello-film-checks-{a.storage_tag}-full", "parts": [full]}, indent=2, ensure_ascii=False) + ";\n")
(L / "content/checks-parts.js").write_text(head + "window.OTHELLO_FILM_CHECKS_PARTS = " + json.dumps({**labels, "poster": poster_rel, "storageKey": f"othello-film-checks-{a.storage_tag}-parts", "parts": parts}, indent=2, ensure_ascii=False) + ";\n")
(out / "parts.json").write_text(json.dumps({"full": full, "parts": parts}, indent=2, ensure_ascii=False) + "\n")
