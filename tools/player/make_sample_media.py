#!/usr/bin/env python3
"""Build sample media so the player can be tried without a real film.

Makes a silent 24 s render from three published images (8 s each), a caption file, a poster and chime sounds in
place of recorded questions, then runs build_parts.py with player/sample/checks.json and player/sample/parts.json.

  python3 tools/player/make_sample_media.py [--player-dir player] [--assets assets]
Writes <player-dir>/media/ (full film, two parts, captions, poster, sample-audio/) and regenerates
<player-dir>/content/checks.js and checks-parts.js. Needs ffmpeg and ffprobe on PATH.
"""
import argparse, json, math, pathlib, struct, subprocess, sys, tempfile, wave

HERE = pathlib.Path(__file__).resolve().parent
SCENES = [("paintings/venice-establishing.jpg", "Sample caption: Venice."),
          ("example-plate-quotation.jpg", "Sample caption: a street at night."),
          ("paintings/cyprus-dawn.jpg", "Sample caption: Cyprus.")]
SECONDS = 8


def chime(path, notes, dur=0.9, rate=24000):
    """A soft bell-like chime (sine partials with an exponential decay), mono 16-bit WAV."""
    frames = []
    for i in range(int(dur * rate)):
        t = i / rate
        v = sum(math.exp(-4.0 * max(0.0, t - k * 0.18)) * math.sin(2 * math.pi * f * (t - k * 0.18)) * (t >= k * 0.18)
                for k, f in enumerate(notes))
        frames.append(struct.pack("<h", int(max(-1, min(1, 0.22 * v)) * 32767)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"".join(frames))


def ts(t):
    return f"00:00:{t:06.3f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--player-dir", default=str(HERE.parents[1] / "player"))
    ap.add_argument("--assets", default=str(HERE.parents[1] / "assets"))
    a = ap.parse_args()
    player, assets = pathlib.Path(a.player_dir), pathlib.Path(a.assets)
    audio = player / "media" / "sample-audio"; audio.mkdir(parents=True, exist_ok=True)
    chime(audio / "ask.wav", [659.25, 523.25]); chime(audio / "correct.wav", [523.25, 659.25, 783.99], 1.2); chime(audio / "probe.wav", [587.33])
    with tempfile.TemporaryDirectory() as td:
        render = pathlib.Path(td)
        clips = []
        for i, (img, _) in enumerate(SCENES):
            src = assets / img
            if not src.exists():
                sys.exit(f"missing {src}")
            clip = render / f"scene-{i + 1}.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "24", "-i", str(src),
                            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(SECONDS),
                            "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-r", "24", "-c:a", "aac", "-b:a", "64k", str(clip)], check=True)
            clips.append(clip)
        lst = render / "list.ffconcat"
        lst.write_text("ffconcat version 1.0\n" + "".join(f"file '{c}'\n" for c in clips))
        film = render / "Othello-opening-NARRATED.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(film)], check=True)
        cues = "".join(f"{i + 1}\n{ts(i * SECONDS + 0.5)} --> {ts((i + 1) * SECONDS - 0.5)}\n{cap}\n\n" for i, (_, cap) in enumerate(SCENES))
        (render / "Othello-opening-NARRATED.vtt").write_text("WEBVTT\n\n" + cues)
        timeline = {"status": "sample render: silent stills, no narration",
                    "scenes": [{"scene": i + 1, "start_seconds": i * SECONDS, "end_seconds": (i + 1) * SECONDS} for i in range(len(SCENES))]}
        (render / "narrated-timeline.json").write_text(json.dumps(timeline, indent=1) + "\n")
        poster = render / "poster.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(assets / SCENES[0][0]), "-vf", "scale=1280:-2", "-q:v", "4", str(poster)], check=True)
        subprocess.run([sys.executable, str(HERE / "build_parts.py"), "--film-dir", str(render), "--parts", str(player / "sample/parts.json"),
                        "--checks", str(player / "sample/checks.json"), "--player-dir", str(player), "--poster", str(poster), "--storage-tag", "sample",
                        "--title", "Othello \u00b7 Sample opening", "--subtitle", "Sample media: three silent stills and sample checks"], check=True)
    print("sample media in", player / "media")


if __name__ == "__main__":
    main()
