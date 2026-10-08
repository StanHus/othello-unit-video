#!/usr/bin/env python3
"""Forced alignment of a narration clip to its EXACT script tokens.

Measured timing comes from local openai-whisper (large-v3-turbo, word_timestamps=True, CPU, no network).
Whisper's words are mapped onto the exact script tokens with difflib on normalised words, so every output
word is the script's own token (captions reproduce the exact script, never the transcript).

  python3 tools/narration/align_words.py --manifest <manifest.json> <clip_id> <wav> [-o out.json]
  python3 tools/narration/align_words.py --manifest <manifest.json> --narration <takes dir> --all
        # every clip in <takes dir>/narration-manifest.json -> <takes dir>/alignment/<clip_id>.words.json

Timing rules (downstream tools rely on these):
- A script token joined by an em dash ("word—word") is split into sub-words for matching; the token spans
  from its first sub-word's start to its last sub-word's end.
- A run of script tokens whisper heard differently ("1603," vs "sixteen oh three") takes the time span of the
  whisper words it replaced, shared out by character length; matched=false.
- Script tokens whisper did not hear at all get a zero-width time at the gap between neighbours; matched=false.
- Times are clamped monotonic non-decreasing and within [0, duration_seconds].
- Word onsets that fall inside a detected silence are snapped to the end of that silence.

By default the exact script is given to whisper as its initial prompt. That helps with names but biases decoding:
on one clip it skipped half the speech after a quotation (matched 0.46). Re-run such a clip with --no-prompt
(or ALIGN_NO_PROMPT=1) and keep whichever alignment matches more words. Words whisper reports after the last
script word (it can loop phrases over music or silence) are reported as extra_heard_* and never timed.

Run with a Python environment that has openai-whisper installed (pip install openai-whisper); ffmpeg must be on PATH.
OTHELLO_MANIFEST and OTHELLO_NARRATION can replace --manifest and --narration.
"""
import os, argparse, difflib, json, pathlib, re, statistics, subprocess, sys, wave

MANIFEST = None   # set in main()
MODEL_NAME = "large-v3-turbo"
_model = None

DASHES = re.compile(r"[—–-]")
CLOSERS = "”’\"')"


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"[^a-z0-9]", "", s)


def script_for(clip_id):
    for s in json.loads(MANIFEST.read_text())["scenes"]:
        if s["clip_id"] == clip_id:
            return s["spoken_text_exact"]
    sys.exit(f"unknown clip_id {clip_id}")


def duration_of(wav):
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def model():
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model(MODEL_NAME, device="cpu")
    return _model


def whisper_words(wav, prompt):
    import whisper
    r = model().transcribe(str(wav), language="en", word_timestamps=True, initial_prompt=(None if os.environ.get('ALIGN_NO_PROMPT') else prompt),
                           condition_on_previous_text=False, temperature=0.0, fp16=False)
    out = []
    for seg in r["segments"]:
        for w in seg.get("words", []):
            for part in DASHES.split(w["word"].strip()):
                n = norm(part)
                if n:
                    out.append({"norm": n, "raw": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])})
    return out, getattr(whisper, "__version__", "?")


def silences(wav):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                        "silencedetect=noise=-40dB:d=0.25", "-f", "null", "-"], capture_output=True, text=True)
    s = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", p.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", p.stderr)]
    return list(zip(s, e))


def align(clip_id, wav):
    wav = pathlib.Path(wav).resolve()
    text = script_for(clip_id)
    dur = duration_of(wav)
    tokens = text.split(" ")
    # sub-words: (token index, norm)
    subs = []
    for ti, tok in enumerate(tokens):
        parts = [norm(p) for p in DASHES.split(tok)]
        parts = [p for p in parts if p] or [norm(tok) or tok.lower()]
        for p in parts:
            subs.append((ti, p))
    heard, wver = whisper_words(wav, text)
    a = [p for _, p in subs]
    b = [h["norm"] for h in heard]
    st = [None] * len(subs); en = [None] * len(subs); ok = [False] * len(subs)
    extra = []  # heard words that are not in the script (added commentary, read-aloud instructions, repeats)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            extra.extend(heard[j1:j2])
        if op == "equal":
            for k in range(i2 - i1):
                st[i1 + k], en[i1 + k], ok[i1 + k] = heard[j1 + k]["start"], heard[j1 + k]["end"], True
        elif op == "replace":
            s0, s1 = heard[j1]["start"], heard[j2 - 1]["end"]
            lens = [max(len(x), 1) for x in a[i1:i2]]; tot = sum(lens); acc = 0
            for k, L in enumerate(lens):
                st[i1 + k] = s0 + (s1 - s0) * acc / tot
                acc += L
                en[i1 + k] = s0 + (s1 - s0) * acc / tot
        # "delete": filled below; "insert" (extra heard words): ignored
    # fill gaps (delete runs) with zero-width time between neighbours
    for k in range(len(subs)):
        if st[k] is None:
            prev = next((en[j] for j in range(k - 1, -1, -1) if en[j] is not None), 0.0)
            st[k] = en[k] = prev
    # monotonic clamp
    last = 0.0
    for k in range(len(subs)):
        st[k] = min(max(st[k], last), dur)
        en[k] = min(max(en[k], st[k]), dur)
        last = st[k]
    # Measured refinement: whisper puts word onsets inside the preceding pause. Snap a start that lies inside a
    # detected silence to that silence's end (true onset) and an end inside a silence to its start.
    gaps = silences(wav)
    raw_starts = list(st)
    snapped = 0
    for k in range(len(subs)):
        for g0, g1 in gaps:
            if g0 <= st[k] < g1 and en[k] > g1:
                st[k] = g1; snapped += 1
            if g0 < en[k] < g1 and st[k] < g0:
                en[k] = g0
    # zero-width words (whisper collapsed timestamps) get a floor: up to the next onset, max 0.3 s
    for k in range(len(subs)):
        if en[k] <= st[k]:
            nxt = st[k + 1] if k + 1 < len(subs) else dur
            en[k] = min(max(nxt, st[k]), st[k] + 0.3)
    words = []
    for ti, tok in enumerate(tokens):
        ks = [k for k, (t, _) in enumerate(subs) if t == ti]
        words.append({"i": ti, "text": tok, "norm": norm(tok), "start": round(st[ks[0]], 3),
                      "end": round(max(en[k] for k in ks), 3), "matched": all(ok[k] for k in ks)})
    for k in range(1, len(words)):  # token-level monotonic guard
        words[k]["start"] = max(words[k]["start"], words[k - 1]["start"])
        words[k]["end"] = max(words[k]["end"], words[k]["start"])
    sentences, first = [], 0
    for k, w in enumerate(words):
        if w["text"].rstrip(CLOSERS).endswith((".", "?", "!")) or k == len(words) - 1:
            sentences.append({"text": " ".join(x["text"] for x in words[first:k + 1]),
                              "start": words[first]["start"], "end": words[k]["end"], "word_range": [first, k]})
            first = k + 1
    ends = [g1 for _, g1 in gaps]
    sub_first = {t: k for k, (t, _) in reversed(list(enumerate(subs)))}
    raw = [min(abs(raw_starts[sub_first[s["word_range"][0]]] - g) for g in ends) for s in sentences[1:]] if ends else []
    fin = [min(abs(s["start"] - g) for g in ends) for s in sentences[1:]] if ends else []
    xc = (f"{len(sentences) - 1} sentence starts vs {len(gaps)} silences (-40dB, d=0.25). Raw whisper onset error: "
          f"median {statistics.median(raw):.3f}s, max {max(raw):.3f}s. After snapping {snapped} onsets to silence ends: "
          f"median {statistics.median(fin):.3f}s, max {max(fin):.3f}s, {sum(e <= 0.1 for e in fin)}/{len(fin)} within 0.1s") if raw else "no silence gaps found"
    unmatched = [w["text"] for w in words if not w["matched"]]
    rel = wav.name
    return {
        "clip_id": clip_id, "file": rel, "duration_seconds": round(dur, 3),
        "method": f"openai-whisper {wver} {MODEL_NAME} word_timestamps (cpu, temp 0, {'no initial_prompt' if os.environ.get('ALIGN_NO_PROMPT') else 'exact script as initial_prompt'}) + difflib map onto exact script tokens",
        "script_text": text, "words": words, "sentences": sentences,
        "quality": {"matched_ratio": round(sum(w["matched"] for w in words) / len(words), 4),
                    "unmatched_tokens": unmatched, "silence_crosscheck": xc,
                    "extra_heard_words": len(extra),
                    # >8 words/s inside the span cannot be real speech: a whisper repetition/hallucination artifact
                    "extra_heard_plausible": bool(extra) and len(extra) / max(extra[-1]["end"] - extra[0]["start"], 0.05) <= 8,
                    "extra_heard_text": " ".join(h["raw"] for h in extra)[:400],
                    "extra_heard_span": [round(extra[0]["start"], 2), round(extra[-1]["end"], 2)] if extra else None},
    }


def show(r):
    q = r["quality"]
    print(f"{r['clip_id']}  {r['file']}  dur={r['duration_seconds']}s  words={len(r['words'])}  matched={q['matched_ratio']}  unmatched={q['unmatched_tokens']}")
    print(f"  {q['silence_crosscheck']}")
    if q["extra_heard_words"]:
        tag = "EXTRA SPEECH not in script" if q["extra_heard_plausible"] else "whisper artifact (implausible density, ignore)"
        print(f"  {tag}: {q['extra_heard_words']} words at {q['extra_heard_span']}s: {q['extra_heard_text'][:160]!r}")
    for w in r["words"][:5] + [None] + r["words"][-5:]:
        print("   ..." if w is None else f"   {w['i']:3d} {w['start']:7.3f} {w['end']:7.3f} {'ok ' if w['matched'] else 'INT'} {w['text']}")


def main():
    global MANIFEST
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip_id", nargs="?"); ap.add_argument("wav", nargs="?")
    ap.add_argument("-o", "--out"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--manifest", default=os.environ.get("OTHELLO_MANIFEST"), help="recording manifest (or OTHELLO_MANIFEST)")
    ap.add_argument("--narration", default=os.environ.get("OTHELLO_NARRATION"), help="takes folder with narration-manifest.json, for --all")
    ap.add_argument("--no-prompt", action="store_true", help="do not give whisper the script as initial_prompt")
    args = ap.parse_args()
    if not args.manifest:
        ap.error("--manifest is required (or set OTHELLO_MANIFEST)")
    MANIFEST = pathlib.Path(args.manifest).resolve()
    if args.no_prompt:
        os.environ["ALIGN_NO_PROMPT"] = "1"
    jobs = []
    if args.all:
        if not args.narration:
            ap.error("--all needs --narration <takes dir> (or OTHELLO_NARRATION)")
        narr = pathlib.Path(args.narration)
        m = json.loads((narr / "narration-manifest.json").read_text())
        for cid, c in sorted(m["clips"].items()):
            jobs.append((cid, narr / c["file"], narr / "alignment" / f"{cid}.words.json"))
    elif args.clip_id and args.wav:
        jobs.append((args.clip_id, args.wav, pathlib.Path(args.out) if args.out else None))
    else:
        ap.error("give <clip_id> <wav> or --all")
    for cid, wav, out in jobs:
        r = align(cid, wav)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        show(r)
    return jobs


if __name__ == "__main__":
    main()
