#!/usr/bin/env python3
"""Generate one narration take per scene with Gemini TTS (google-genai SDK), with provenance.

Source of truth: a recording manifest (`--manifest` or OTHELLO_MANIFEST) whose scenes carry `clip_id`,
`scene_number` and `spoken_text_exact`. The text is never rewritten here. Output: one WAV per clip_id plus
<out>/narration-manifest.json with the model, voice, style prompt, word count, measured duration and a sha256 of
the exact text for every clip, so later steps can tell a stale take from a current one.

Some TTS models return a complete RIFF WAV, others raw 24 kHz 16-bit mono PCM; both are written as WAV.

Usage:
  GENAI_API_KEY=... python3 tools/narration/generate_takes.py --manifest <manifest.json> --out <dir>
  GENAI_API_KEY=... python3 tools/narration/generate_takes.py --manifest <manifest.json> --out <dir> --only vo_intro_01 --force
  TTS_MODEL=gemini-3.1-flash-tts-preview TTS_VOICE=Gacrux python3 tools/narration/generate_takes.py ...

Environment: GENAI_API_KEY (or GEMINI_API_KEY) is the key. GENAI_BASE_URL is optional (unset = the public Gemini
API); GENAI_AUTH_HEADER optionally names the header a proxy expects the key in. The endpoint is never written to
any output.

Before generating every clip, audition one passage with a few voices and choose by listening. After every take,
run tools/narration/verify_take.py (a no-hint transcription and word diff); regenerate any clip that differs.
"""
import argparse, hashlib, json, os, pathlib, sys, time, wave

RATE, WIDTH = 24000, 2
DEFAULT_STYLE = (
    "Read the following as one off-screen storyteller for a mature, illustrated-book film: epic, atmospheric, "
    "theatrical and quietly ominous, with a measured pace and every word clear. Give proper names and quotations "
    "a little space. Do not act out characters, do not imitate any actor, and do not add or change any words. "
    "The text to read is: ")


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


def write_wav(path, data):
    if data[:4] == b"RIFF":          # already a complete WAV: do not wrap it again
        path.write_bytes(data)
        return
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(WIDTH); w.setframerate(RATE); w.writeframes(data)


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=os.environ.get("OTHELLO_MANIFEST"), help="recording manifest (or OTHELLO_MANIFEST)")
    ap.add_argument("--out", default=os.environ.get("TTS_OUTDIR"), help="output folder for the takes (or TTS_OUTDIR)")
    ap.add_argument("--only", action="append", help="clip_id to generate (repeatable)")
    ap.add_argument("--force", action="store_true", help="regenerate even when the take matches the current text")
    ap.add_argument("--model", default=os.environ.get("TTS_MODEL", "gemini-3.1-flash-tts-preview"))
    ap.add_argument("--voice", default=os.environ.get("TTS_VOICE", "Gacrux"), help="a prebuilt voice name")
    ap.add_argument("--style", default=os.environ.get("TTS_STYLE", DEFAULT_STYLE), help="direction prepended to the text")
    args = ap.parse_args()
    if not args.manifest or not args.out:
        ap.error("--manifest and --out are required (or set OTHELLO_MANIFEST and TTS_OUTDIR)")

    manifest = pathlib.Path(args.manifest).resolve()
    outdir = pathlib.Path(args.out)
    client, types = make_client()
    src = json.loads(manifest.read_text())
    outdir.mkdir(parents=True, exist_ok=True)
    prov_path = outdir / "narration-manifest.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {"clips": {}}
    prov.update({"model": args.model, "voice": args.voice, "style": args.style,
                 "source_manifest": manifest.name, "schema_version": src.get("schema_version")})

    made = skipped = failed = 0
    for scene in src["scenes"]:
        cid, text = scene["clip_id"], scene["spoken_text_exact"]
        if args.only and cid not in args.only:
            continue
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        out = outdir / f"{cid}.wav"
        if out.exists() and not args.force and prov["clips"].get(cid, {}).get("text_sha256") == text_hash:
            skipped += 1; print(f"skip {cid} (up to date, {duration(out):.2f}s)"); continue
        t = time.time()
        try:
            r = client.models.generate_content(
                model=args.model, contents=args.style + text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=args.voice)))))
            part = r.candidates[0].content.parts[0]
            if part.inline_data is None:
                raise RuntimeError(f"no audio part (finish_reason={r.candidates[0].finish_reason}); "
                                   "if the text was refused, bisect per sentence and reword rather than retrying blind")
            write_wav(out, part.inline_data.data)
            dur = duration(out)
            prov["clips"][cid] = {"file": out.name, "scene_number": scene.get("scene_number"), "words": len(text.split()),
                                  "duration_seconds": round(dur, 3), "text_sha256": text_hash,
                                  "mime_type": part.inline_data.mime_type, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            made += 1; print(f"ok   {cid} {dur:6.2f}s {time.time()-t:5.1f}s wall")
        except Exception as e:
            failed += 1; print(f"FAIL {cid}: {type(e).__name__}: {str(e)[:300]}")
        prov_path.write_text(json.dumps(prov, indent=2) + "\n")
    print(f"made={made} skipped={skipped} failed={failed} -> {outdir}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
