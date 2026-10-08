#!/usr/bin/env python3
"""Generate scene paintings with an image model (gemini-3-pro-image-preview) through the Gemini image API, using
existing paintings as style and character references.

Each brief names its reference paintings (`refs`, file stems looked up in --refs-dir), the play characters it shows
(`chars`, described once in the briefs file's character bible so faces and costumes stay the same across images)
and a `subject`. The prompt is: style + character descriptions + subject. See assets/painting-briefs.json.

  GENAI_API_KEY=... python3 tools/art/generate_paintings.py --briefs assets/painting-briefs.json --refs-dir <dir> --out <dir>
  GENAI_API_KEY=... python3 tools/art/generate_paintings.py ... --only venice-senate secret-wedding --force
Writes <out>/<file> (JPEG, 2K, 16:9) and <out>/art-manifest.json (model, refs, characters, full prompt, sha256).

Environment: GENAI_API_KEY (or GEMINI_API_KEY) is the key. GENAI_BASE_URL is optional (default: the public Gemini
API); GENAI_AUTH_HEADER is the header the key is sent in (default x-goog-api-key). No key or endpoint is written
to any output. Review every image by eye before use: character identity, style, no text, nothing the brief excludes.
"""
import argparse, base64, concurrent.futures as cf, hashlib, json, os, pathlib, sys, time, requests

MODEL = os.environ.get("IMAGE_MODEL", "gemini-3-pro-image-preview")
BASE = os.environ.get("GENAI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
HEADER = os.environ.get("GENAI_AUTH_HEADER", "x-goog-api-key")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def ref_part(refs_dir, stem):
    for ext in MIME:
        p = refs_dir / f"{stem}{ext}"
        if p.exists():
            return {"inline_data": {"mime_type": MIME[ext], "data": base64.b64encode(p.read_bytes()).decode()}}
    sys.exit(f"reference painting {stem}.(png|jpg) not found in {refs_dir}")


def gen(key, brief, style, bible, refs_dir, out_dir, force):
    out = out_dir / brief["file"]
    if out.exists() and not force:
        return brief["id"], "skip", out.name, 0
    parts = [ref_part(refs_dir, r) for r in brief["refs"]]
    text = style + "\n\nCharacters (keep identity exactly as in the references): " + " ".join(bible[c] for c in brief["chars"]) + "\n\nSubject: " + brief["subject"]
    parts.append({"text": text})
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}}}
    t = time.time()
    for attempt in range(3):
        r = requests.post(f"{BASE}/v1beta/models/{MODEL}:generateContent", headers={HEADER: key, "Content-Type": "application/json"}, json=body, timeout=600)
        if r.status_code == 429: time.sleep(20 * (attempt + 1)); continue
        if not r.ok: return brief["id"], f"HTTP {r.status_code} {r.text[:120]}", out.name, time.time() - t
        cand = r.json().get("candidates", [{}])[0]
        img = next((p for p in cand.get("content", {}).get("parts", []) if "inlineData" in p), None)
        if not img: return brief["id"], f"no image (finish={cand.get('finishReason')})", out.name, time.time() - t
        data = base64.b64decode(img["inlineData"]["data"]); out.write_bytes(data)
        return brief["id"], "ok", out.name, time.time() - t, hashlib.sha256(data).hexdigest(), text
    return brief["id"], "429 x3", out.name, time.time() - t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--briefs", required=True, help="JSON with style, bible and paintings[] (id, file, refs, chars, subject)")
    ap.add_argument("--refs-dir", required=True, help="folder holding the reference paintings named in refs")
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--only", nargs="*", help="painting ids to generate")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    key = os.environ.get("GENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or sys.exit("set GENAI_API_KEY (or GEMINI_API_KEY)")
    b = json.loads(pathlib.Path(a.briefs).read_text())
    briefs = [s for s in b["paintings"] if "subject" in s and (not a.only or s["id"] in a.only)]
    refs_dir, out_dir = pathlib.Path(a.refs_dir), pathlib.Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    mpath = out_dir / "art-manifest.json"
    man = json.loads(mpath.read_text()) if mpath.exists() else {"model": MODEL, "paintings": {}}
    fails = 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for res in ex.map(lambda s: gen(key, s, b["style"], b["bible"], refs_dir, out_dir, a.force), briefs):
            pid, status, name = res[0], res[1], res[2]
            print(f"{pid:28s} {status:8s} {name} {res[3]:5.1f}s", flush=True)
            if status == "ok":
                s = next(x for x in briefs if x["id"] == pid)
                man["paintings"][pid] = {"file": name, "refs": s["refs"], "chars": s["chars"], "sha256": res[4], "prompt": res[5], "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
                mpath.write_text(json.dumps(man, indent=2) + "\n")
            elif status != "skip": fails += 1
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
