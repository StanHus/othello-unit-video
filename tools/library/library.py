#!/usr/bin/env python3
r"""Library: a catalogue of a project folder's documents and media, with curated cards, topic pages and search.

  python3 tools/library/library.py build --root <project> --out <project>/library \
      [--curation <dir>] [--include <path> ...] [--skip <pattern> ...]
  python3 tools/library/library.py list-uncurated --out <project>/library
  python3 tools/library/library.py check --out <project>/library [--strict]
  python3 tools/library/library.py search --out <project>/library <term> [<term> ...] [--limit 15]

build reads --root (or only the --include paths inside it) and writes into --out, nowhere else:
  catalog.json  every item: id, path, title, kind, status, author, date, tags, summary, supersedes and
                superseded_by, bytes, sha256, words, and the card that curates it, if any
  CATALOG.md    the items grouped by kind
  topics/       one page per tag, by status and newest first, and an index (README.md)
  text/         the extracted text of each document, which search reads
A rebuild rewrites these and deletes only files the previous build wrote. Documents (.md .txt .qmd .csv .json
.vtt .html .htm .pdf .docx, and the file lists of .zip and .tar archives) get one item each; media (images, audio,
video, fonts) get one item per folder. PDF text needs pdftotext (poppler) on PATH; without it the item says so.

Cards hold the curated metadata: JSON files in --curation (default <out>/curation), each mapping a path relative
to --root (a media folder ends in "/") to {title, author, date (YYYY-MM-DD), kind, status, supersedes (paths),
summary, tags}. Files whose names start with "_" are not cards: _topic-intros.json maps a tag to a paragraph for
its page, and _vocabulary.json ({"kinds": [...], "tags": [...]}) replaces the default kinds and tags listed below.
An item without a card date shows its file time, marked "(file)".

Not catalogued: hidden files and folders, node_modules, __pycache__, the --out and --curation folders, render
scratch (frames, qa-segments, qa-whisper and their TEST- copies, fitted-test), and the per-clip and per-run data
the tools write (*.transcript.json, *.words.json, judgments.json, narration-manifest.json, art-manifest.json,
the manifest.json of tools/art/finish_paintings.py, narrated-timeline.json and qa-results.json with their TEST-
copies, fitted-cue-sheet.json, web-copies.json). Any other manifest.json, such as a recording manifest, is
catalogued. --skip adds a file or folder name, or a glob on the path relative to --root.

check exits 1 on a supersedes link to a path not in the catalogue, an unknown kind, tag or status, or a card that
matches no catalogued path; --strict also fails while any item has no card.
"""
import argparse, fnmatch, hashlib, html, json, os, pathlib, re, shutil, subprocess, sys, tarfile, textwrap, zipfile
from datetime import datetime, timezone

DOC_EXT = {".md", ".txt", ".qmd", ".csv", ".json", ".vtt", ".html", ".htm", ".pdf", ".docx"}
ARCHIVES = (".zip", ".tar", ".tar.gz", ".tgz")
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".wav", ".mp3", ".m4a", ".flac", ".mp4", ".mov",
             ".webm", ".woff", ".woff2", ".ttf", ".otf"}
SKIP_DIRS = {"node_modules", "__pycache__", "fitted-test"} | {
    tag + name for tag in ("", "TEST-") for name in ("frames", "qa-segments", "qa-whisper")}
SKIP_FILES = ["*.transcript.json", "*.words.json", "judgments.json", "narration-manifest.json", "art-manifest.json",
              "*narrated-timeline.json", "*qa-results.json", "fitted-cue-sheet.json", "web-copies.json"]
KINDS = ["brief", "script", "source-text", "feedback", "notes", "decision", "design", "research", "data", "qa",
         "transcript", "tool", "deliverable", "reference", "archive", "asset-collection"]
TAGS = ["script", "narration", "score", "art", "plates", "film", "checks", "player", "review", "research",
        "feedback", "decisions", "standards", "qa"]
STATUSES = ["current", "superseded", "historical", "reference"]


def rel(root, p):
    return p.relative_to(root).as_posix()


def doc_id(path):
    return "L" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def day(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def as_list(v):
    return [] if v is None else [v] if isinstance(v, str) else list(v)


def count(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def finish_manifest(p):
    """True for the manifest.json that tools/art/finish_paintings.py writes beside the finished paintings; a recording
    manifest, also named manifest.json, is a document and is catalogued."""
    if p.name != "manifest.json":
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and "finish_prompt" in data and isinstance(data.get("images"), dict)


def in_scope(path, scope):
    """True when path lies under one of the catalogued paths (an empty scope is the whole root)."""
    return not scope or any(path == s or path.startswith(s.rstrip("/") + "/") for s in scope)


def walk(root, bases, skips, avoid):
    """Documents, and media files by folder, under each base; skips what the module docstring lists."""
    docs, media, seen = [], {}, set()

    def matches(patterns, name, relpath):
        return any(fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(relpath, pat) for pat in patterns)

    def skip_dir(d):
        return (d.name.startswith(".") or d.name in SKIP_DIRS or d.resolve() in avoid
                or matches(skips, d.name, rel(root, d)))

    def skip_file(p):
        return (p.name.startswith(".") or any(fnmatch.fnmatchcase(p.name, pat) for pat in SKIP_FILES)
                or finish_manifest(p) or matches(skips, p.name, rel(root, p)))

    def add(p):
        if p in seen:
            return
        seen.add(p)
        if p.suffix.lower() in MEDIA_EXT:
            media.setdefault(rel(root, p.parent), []).append(p)
        elif p.suffix.lower() in DOC_EXT or p.name.lower().endswith(ARCHIVES):
            docs.append(p)

    for base in bases:
        if base.is_file():
            add(base)           # a file named with --include is taken as it is
            continue
        for d, dirs, files in os.walk(base):
            here = pathlib.Path(d)
            dirs[:] = sorted(x for x in dirs if not skip_dir(here / x))
            for f in sorted(files):
                if not skip_file(here / f):
                    add(here / f)
    return sorted(docs), media


def extract(p):
    """The plain text of a document, and a note when it could not be read."""
    name, ext = p.name.lower(), p.suffix.lower()
    try:
        if ext == ".pdf":
            if not shutil.which("pdftotext"):
                return "", "no text: pdftotext is not on PATH"
            r = subprocess.run(["pdftotext", "-q", "-layout", str(p), "-"], capture_output=True,
                               encoding="utf-8", errors="ignore", timeout=120)
            return r.stdout, None if r.returncode == 0 else f"no text: pdftotext exited {r.returncode}"
        if ext == ".docx":
            with zipfile.ZipFile(p) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            xml = re.sub(r"</w:p>|<w:br\s*/>", "\n", xml).replace("<w:tab/>", "\t")
            return html.unescape(re.sub(r"<[^>]+>", "", xml)), None
        if ext in (".html", ".htm"):
            raw = p.read_text(encoding="utf-8", errors="ignore")
            raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
            raw = re.sub(r"data:[^\"')\s]{200,}", " ", raw)
            return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip(), None
        if name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                return "\n".join(z.namelist()), None
        if name.endswith(ARCHIVES):
            with tarfile.open(p) as t:
                return "\n".join(t.getnames()), None
        return p.read_text(encoding="utf-8", errors="ignore"), None
    except Exception as e:
        return "", f"no text: extraction failed ({type(e).__name__})"


def guess_title(p, text):
    ext = p.suffix.lower()
    if ext in (".html", ".htm"):
        m = re.search(r"(?is)<title[^>]*>(.*?)</title>", p.read_text(encoding="utf-8", errors="ignore"))
        if m and m.group(1).strip():
            return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:120]
    elif ext in (".md", ".qmd"):
        m = re.search(r"^#\s+\**(.+?)\**\s*$", text, re.M)
        if m:
            return re.sub(r"[*_`]", "", m.group(1)).strip()[:120]
    name = p.name
    for suffix in ARCHIVES + (p.suffix,):
        if suffix and name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.replace("_", " ").replace("-", " ")[:120]


def load_cards(folder):
    """Cards by path, topic intros and vocabulary from the curation folder, which may not exist."""
    cards, intros, vocab = {}, {}, {}
    if not folder.is_dir():
        return cards, intros, vocab
    for f in sorted(folder.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.exit(f"{f.name}: not valid JSON ({e})")
        if not isinstance(data, dict):
            sys.exit(f"{f.name}: must hold one JSON object")
        if f.name == "_topic-intros.json":
            intros = data
        elif f.name == "_vocabulary.json":
            vocab = data
        elif not f.name.startswith("_"):
            for path, card in data.items():
                if not isinstance(card, dict):
                    sys.exit(f"{f.name}: the card for {path} must be a JSON object")
                cards[path] = {**cards.get(path, {}), **card, "_card": f.name}
    return cards, intros, vocab


def card_fields(c, file_day):
    """The curated part of an item; without a card date, the file's own date, marked as such."""
    return {"title": c.get("title"), "kind": c.get("kind"), "status": c.get("status"), "author": c.get("author"),
            "date": c.get("date") or file_day, "date_is_file_time": not c.get("date"),
            "supersedes": as_list(c.get("supersedes")), "superseded_by": [], "tags": as_list(c.get("tags")),
            "summary": c.get("summary"), "card": c.get("_card"), "curated": bool(c)}


def load_catalog(out):
    f = out / "catalog.json"
    if not f.is_file():
        sys.exit(f"no catalog.json in {out}; run build first")
    return json.loads(f.read_text(encoding="utf-8"))


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def shown_date(x):
    return (x["date"] or "") + (" (file)" if x["date"] and x["date_is_file_time"] else "")


def write_pages(out, items, kinds, tags, intros):
    """CATALOG.md and the topic pages; returns the paths written, relative to out."""
    order = {k: i for i, k in enumerate(kinds)}
    groups = {}
    for x in items:
        groups.setdefault(x["kind"] or ("no kind" if x["curated"] else "uncurated"), []).append(x)
    lines = ["# Catalog", "",
             "Built by `tools/library/library.py`. Do not edit this file: edit the cards and build again.", "",
             f"{count(len(items), 'item')}. Status: **current** is the version to use, **superseded** has been "
             "replaced (see its successor), **historical** is kept as evidence, **reference** is outside material. "
             "A date marked (file) is the file's time, not the document's.", ""]
    for k in sorted(groups, key=lambda k: (order.get(k, len(order)), k)):
        lines += [f"## {k}", "", "| id | title | status | date | path |", "|---|---|---|---|---|"]
        lines += [f"| {x['id']} | {esc(x['title'])} | {x['status'] or ''} | {shown_date(x)} | `{esc(x['path'])}` |"
                  for x in groups[k]]
        lines.append("")
    (out / "CATALOG.md").write_text("\n".join(lines), encoding="utf-8")
    written = ["CATALOG.md", "topics/README.md"]
    tdir = out / "topics"
    tdir.mkdir(exist_ok=True)
    index = ["# Topics", "", "| topic | items | current |", "|---|---|---|"]
    for t in tags:
        xs = [x for x in items if t in x["tags"]]
        if not xs:
            continue
        index.append(f"| [{t}]({t}.md) | {len(xs)} | {sum(x['status'] == 'current' for x in xs)} |")
        page = [f"# {t}", ""] + ([intros[t], ""] if intros.get(t) else [])
        other = sorted({x["status"] for x in xs if x["status"] and x["status"] not in STATUSES})
        for status in STATUSES + other + [None]:
            ys = sorted((x for x in xs if x["status"] == status), key=lambda x: (x["date"] or "", x["path"]),
                        reverse=True)
            if not ys:
                continue
            page += [f"## {status or 'no status'}", ""]
            for x in ys:
                line = f"- **{esc(x['title'])}** · {shown_date(x)} · `{x['path']}`"
                if x["summary"]:
                    line += f"  \n  {esc(x['summary'])}"
                if x["superseded_by"]:
                    line += "  \n  Superseded by " + ", ".join(f"`{s}`" for s in x["superseded_by"])
                page.append(line)
            page.append("")
        (tdir / f"{t}.md").write_text("\n".join(page), encoding="utf-8")
        written.append(f"topics/{t}.md")
    if len(index) == 4:
        index = ["# Topics", "", "No item has a tag yet."]
    (tdir / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return written


def build(a):
    root, out = pathlib.Path(a.root).resolve(), pathlib.Path(a.out).resolve()
    curation = pathlib.Path(a.curation).resolve() if a.curation else out / "curation"
    if not root.is_dir():
        sys.exit(f"--root {a.root} is not a folder")
    if out == root:
        sys.exit("--out must not be the --root folder itself; use a folder such as <root>/library")
    bases = []
    for inc in a.include:
        p = (root / inc).resolve()
        if not p.is_relative_to(root):
            sys.exit(f"--include {inc} is outside --root")
        if not p.exists():
            sys.exit(f"--include {inc} does not exist")
        if p.is_relative_to(out) or p.is_relative_to(curation):
            sys.exit(f"--include {inc} is inside --out or --curation")
        bases.append(p)
    scope = [] if not bases or root in bases else sorted(rel(root, b) for b in bases)
    cards, intros, vocab = load_cards(curation)
    kinds, tags = list(vocab.get("kinds", KINDS)), list(vocab.get("tags", TAGS))
    for t in tags:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", t):
            sys.exit(f"_vocabulary.json: tag {t!r} must use only lower-case letters, digits and hyphens")
    prev = json.loads((out / "catalog.json").read_text(encoding="utf-8")) if (out / "catalog.json").is_file() else {}

    docs, media = walk(root, bases or [root], a.skip, {out, curation})
    (out / "text").mkdir(parents=True, exist_ok=True)
    items, written = [], []
    for p in docs:
        r, st = rel(root, p), p.stat()
        i, (text, note) = doc_id(r), extract(p)
        (out / "text" / f"{i}.txt").write_text(text, encoding="utf-8")
        written.append(f"text/{i}.txt")
        item = {"id": i, "path": r, **card_fields(cards.get(r, {}), day(st.st_mtime)), "bytes": st.st_size,
                "sha256": sha256(p), "words": len(text.split()), "text": f"text/{i}.txt"}
        item["title"] = item["title"] or guess_title(p, text)
        if note:
            item["extraction"] = note
        items.append(item)
    for folder, files in sorted(media.items()):
        r = "./" if folder == "." else folder + "/"
        stats = [f.stat() for f in files]
        item = {"id": doc_id(r), "path": r, **card_fields(cards.get(r, {}), day(max(s.st_mtime for s in stats))),
                "bytes": sum(s.st_size for s in stats), "files": len(files), "sha256": None, "words": 0, "text": None}
        exts = ", ".join(sorted({f.suffix.lower().lstrip(".") for f in files}))
        item["title"] = item["title"] or f"Media in {r}: {count(len(files), 'file')} ({exts})"
        item["kind"] = item["kind"] or ("asset-collection" if "asset-collection" in kinds else None)
        items.append(item)
    items.sort(key=lambda x: x["path"])
    if len({x["id"] for x in items}) != len(items):
        sys.exit("two paths share an id; rename one of them")
    by_path = {x["path"]: x for x in items}
    for x in items:
        for s in x["supersedes"]:
            if s in by_path:
                by_path[s]["superseded_by"].append(x["path"])
    unmatched = sorted(k for k in cards if k not in by_path and in_scope(k, scope))

    written += write_pages(out, items, kinds, tags, intros)
    catalog = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "scope": scope or ["."],
               "vocabulary": {"kinds": kinds, "tags": tags, "statuses": STATUSES}, "cards_unmatched": unmatched,
               "written": sorted(written), "items": items}
    (out / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in sorted(set(prev.get("written", [])) - set(written)):     # only what the previous build wrote
        q = (out / f).resolve()
        if q.is_relative_to(out) and q.is_file():
            q.unlink()

    curated = sum(x["curated"] for x in items)
    print(f"catalog: {count(len(items), 'item')} ({count(len(docs), 'document')}, "
          f"{count(len(media), 'media folder')}), {curated} curated, {len(items) - curated} uncurated")
    no_text = sum("extraction" in x for x in items)
    if no_text:
        print(f"{count(no_text, 'document')} without extracted text (see 'extraction' in catalog.json)")
    if unmatched:
        print(f"{count(len(unmatched), 'card')} matching no catalogued path; run check")
    print(f"wrote {a.out}")


def check(a):
    cat = load_catalog(pathlib.Path(a.out).resolve())
    items, voc = cat["items"], cat.get("vocabulary", {})
    scope = [s for s in cat.get("scope", []) if s != "."]
    kinds, tags, statuses = voc.get("kinds", KINDS), voc.get("tags", TAGS), voc.get("statuses", STATUSES)
    paths = {x["path"] for x in items}
    uncurated = [x for x in items if not x["curated"]]
    broken = [f"{x['path']}: supersedes {s}, which is not in the catalogue"
              for x in items for s in x["supersedes"] if s not in paths and in_scope(s, scope)]
    unknown = ([f"{x['path']}: unknown kind {x['kind']!r}" for x in items if x["kind"] and x["kind"] not in kinds]
               + [f"{x['path']}: unknown tag {t!r}" for x in items for t in x["tags"] if t not in tags]
               + [f"{x['path']}: unknown status {x['status']!r}"
                  for x in items if x["status"] and x["status"] not in statuses])
    unmatched = [f"{k}: a card for a media folder; its path must end in '/'" if k + "/" in paths
                 else f"{k}: a card for a path that is not catalogued (moved, deleted or skipped)"
                 for k in cat.get("cards_unmatched", [])]
    print(f"{count(len(items), 'item')}, {len(uncurated)} uncurated, {len(broken)} broken supersedes, "
          f"{len(unknown)} unknown kinds, tags or statuses, "
          f"{count(len(unmatched), 'card')} matching no catalogued path")
    problems = broken + unknown + unmatched
    for line in problems[:20]:
        print("  " + line)
    if len(problems) > 20:
        print(f"  and {len(problems) - 20} more")
    sys.exit(1 if problems or (a.strict and uncurated) else 0)


def list_uncurated(a):
    for x in load_catalog(pathlib.Path(a.out).resolve())["items"]:
        if not x["curated"]:
            print(x["path"])


def search(a):
    out = pathlib.Path(a.out).resolve()
    terms, res = [t.lower() for t in a.terms], []
    for x in load_catalog(out)["items"]:
        meta = " ".join([x["title"] or "", x["summary"] or "", " ".join(x["tags"]), x["path"]]).lower()
        body = ""
        if x.get("text"):
            f = (out / x["text"]).resolve()
            if f.is_relative_to(out) and f.is_file():
                body = f.read_text(encoding="utf-8", errors="ignore").lower()
        if not all(t in meta or t in body for t in terms):
            continue
        score = sum(meta.count(t) * 8 + min(body.count(t), 40) for t in terms) + (5 if x["status"] == "current" else 0)
        i = body.find(terms[0])
        snip = re.sub(r"\s+", " ", body[max(0, i - 80): i + 160]).strip() if i >= 0 else ""
        res.append((score, x, snip))
    for score, x, snip in sorted(res, key=lambda r: (-r[0], r[1]["path"]))[: a.limit]:
        print(f"{x['id']}  [{x['status'] or '-'}] {x['title']}\n        {x['path']}"
              + (f"\n        ... {snip} ..." if snip else ""))
    if not res:
        print("no matches")


def main():
    def listed(label, words):
        return textwrap.fill(f"{label}: " + ", ".join(words), 116, subsequent_indent="  ")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join([listed("default kinds", KINDS), listed("default tags", TAGS),
                                                   listed("statuses", STATUSES)]))
    sub = ap.add_subparsers(dest="command", required=True, metavar="{build,list-uncurated,check,search}")
    b = sub.add_parser("build", help="extract text and rebuild catalog.json, CATALOG.md and the topic pages")
    b.add_argument("--root", required=True, help="the folder to catalogue")
    b.add_argument("--out", required=True, help="the library folder to write")
    b.add_argument("--curation", help="the folder of cards (default <out>/curation)")
    b.add_argument("--include", action="append", default=[], metavar="PATH",
                   help="catalogue only this path inside --root (repeatable)")
    b.add_argument("--skip", action="append", default=[], metavar="PATTERN",
                   help="also skip this file or folder name, or this glob on the path relative to --root (repeatable)")
    u = sub.add_parser("list-uncurated", help="print the path of every item that has no card")
    u.add_argument("--out", required=True, help="the library folder")
    c = sub.add_parser("check", help="report broken supersedes, unknown kinds, tags and statuses, and unmatched cards")
    c.add_argument("--out", required=True, help="the library folder")
    c.add_argument("--strict", action="store_true", help="also fail while any item has no card")
    s = sub.add_parser("search", help="rank items by the terms in their title, summary, tags, path and text")
    s.add_argument("--out", required=True, help="the library folder")
    s.add_argument("--limit", type=int, default=15, help="results to show (default 15)")
    s.add_argument("terms", nargs="+")
    a = ap.parse_args()
    {"build": build, "list-uncurated": list_uncurated, "check": check, "search": search}[a.command](a)


if __name__ == "__main__":
    main()
