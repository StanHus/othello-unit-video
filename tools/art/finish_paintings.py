#!/usr/bin/env python3
"""Repaint existing paintings in one shared finish (finish B: engraved line and watercolour wash) through the Gemini
image API (gemini-3-pro-image-preview, 2K 16:9), image to image, keeping composition, figures and lighting.

  GENAI_API_KEY=... python3 tools/art/finish_paintings.py --out <dir> painting1.png painting2.jpg ...
  GENAI_API_KEY=... python3 tools/art/finish_paintings.py --out <dir> --inputs list.txt [--force]
--inputs is a text file with one image path per line. Outputs <out>/<stem>.jpg and <out>/manifest.json (model,
finish prompt, and per image the source file name, sha256 and time). Existing outputs are skipped unless --force.

The prompt asks the model to change only the finish, but image-to-image can still change content: in one of 18
repaints the model added two figures and put out the remaining candle flame. Compare every output with its source
by eye before use; a check that only confirms which file is used will not catch it.

Environment: GENAI_API_KEY (or GEMINI_API_KEY); optional GENAI_BASE_URL (default: the public Gemini API) and
GENAI_AUTH_HEADER (default x-goog-api-key). No key or endpoint is written to any output.
"""
import argparse, base64, concurrent.futures as cf, hashlib, json, os, pathlib, sys, time, requests

MODEL = os.environ.get("IMAGE_MODEL", "gemini-3-pro-image-preview")
BASE = os.environ.get("GENAI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
HEADER = os.environ.get("GENAI_AUTH_HEADER", "x-goog-api-key")
KEEP = ("Repaint this exact image. Keep EVERYTHING the same: composition, framing, every figure and their pose, faces, costumes and "
        "colours of costume, architecture, objects and lighting direction. Change ONLY the painterly finish, as follows. ")
FINISH_B = ("Finish: a nineteenth-century engraved book illustration with a watercolour wash. Fine ink line work with cross-hatching for shadow, "
            "laid over transparent washes in a limited palette of sepia, indigo, oxblood and muted brass, on warm off-white laid paper with visible "
            "paper texture. Flat, quiet lighting, no gradients that look digital, no glow, no gloss. It should look printed in an old illustrated "
            "edition of the play.")
PROMPT = KEEP + FINISH_B + " No text, no border, no watermark."


def part(p):
    return {"inline_data": {"mime_type": "image/png" if p.suffix == ".png" else "image/jpeg", "data": base64.b64encode(p.read_bytes()).decode()}}


def call(key, parts):
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}}}
    for attempt in range(4):
        r = requests.post(f"{BASE}/v1beta/models/{MODEL}:generateContent", headers={HEADER: key, "Content-Type": "application/json"}, json=body, timeout=600)
        if r.status_code == 429: time.sleep(20 * (attempt + 1)); continue
        if not r.ok: raise RuntimeError(f"HTTP {r.status_code} {r.text[:160]}")
        cand = r.json().get("candidates", [{}])[0]
        img = next((p for p in cand.get("content", {}).get("parts", []) if "inlineData" in p), None)
        if not img: raise RuntimeError(f"no image (finish={cand.get('finishReason')})")
        return base64.b64decode(img["inlineData"]["data"])
    raise RuntimeError("429 x4")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", help="source paintings")
    ap.add_argument("--inputs", help="text file with one source path per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    key = os.environ.get("GENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or sys.exit("set GENAI_API_KEY (or GEMINI_API_KEY)")
    srcs = [pathlib.Path(p) for p in a.images]
    if a.inputs:
        srcs += [pathlib.Path(l.strip()) for l in pathlib.Path(a.inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
    if not srcs:
        ap.error("give source images or --inputs")
    fin = pathlib.Path(a.out); fin.mkdir(parents=True, exist_ok=True)
    jobs = [(fin / (p.stem + ".jpg"), p) for p in srcs if a.force or not (fin / (p.stem + ".jpg")).exists()]
    man_path = fin / "manifest.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else {"model": MODEL, "finish_prompt": PROMPT, "images": {}}

    def run(job):
        out, src = job
        t = time.time()
        try:
            data = call(key, [part(src), {"text": PROMPT}])
        except Exception as e:
            return out, src, f"FAIL {e}", time.time() - t, None
        out.write_bytes(data)
        return out, src, "ok", time.time() - t, hashlib.sha256(data).hexdigest()

    fails = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for out, src, status, secs, sha in ex.map(run, jobs):
            print(f"{status:8s} {secs:5.1f}s {out.name}", flush=True)
            if status == "ok":
                man["images"][out.name] = {"source": src.name, "sha256": sha, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
                man_path.write_text(json.dumps(man, indent=1) + "\n")
            else:
                fails += 1
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
