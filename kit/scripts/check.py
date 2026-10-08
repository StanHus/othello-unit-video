#!/usr/bin/env python3
"""Check the kit against the repository it lives in. Exit 1 on any failure.

- skills: every .claude/skills/<name>/SKILL.md has YAML front matter whose name is its folder and whose description
  says when to use it; kit/README.md lists exactly the skills and workflows there are;
- workflows: every .claude/workflows/<name>.js begins with `export const meta = {...}`, a pure literal named after
  the file whose phases declare every phase the script uses; no clock or randomness (they break resume); valid
  JavaScript for the workflow runtime, where agent, parallel, pipeline, phase and log are globals;
- paths, flags and arguments: every repository path (tools/, kit/, .claude/, research/, assets/) that a skill,
  workflow, doc or template names exists. Every flag written after a tool, in a command or in running text, is one
  that tool reads (a Python tool's from its --help, a Node tool's from its argument parser), and a tool with
  subcommands is given one. A full command, in a code block or a template's "command", also gives the tool's
  required flags, a value for each flag that takes one, and as many positional arguments as the tool takes;
- every uvk- name is a skill or a workflow that exists;
- links: every relative link in every Markdown file resolves, #anchors included;
- templates: every JSON file parses, and the sample manifest, storyboard, cue sheet and checks agree with each other
  the way the tools require;
- Python: every tool and script compiles;
- secrets: no key-shaped string or e-mail address in any text file.

  python3 kit/scripts/check.py        (or kit/scripts/check.sh, from anywhere)
It reads the repository, runs each Python tool's --help from a temporary folder, and writes only temporary files
outside the repository.
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".local", ".venv", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".mjs", ".json", ".txt", ".sh", ".html", ".css", ".csv", ".vtt", ".yml", ".yaml"}
fails = []


def fail(msg):
    fails.append(msg)


def rel(p):
    return p.relative_to(ROOT).as_posix()


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def files(*suffixes):
    out = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts) and p.suffix in suffixes:
            out.append(p)
    return out


# ---------- skills ----------
SKILLS = ROOT / ".claude" / "skills"
skills = []
for d in sorted(x for x in SKILLS.iterdir() if x.is_dir()) if SKILLS.is_dir() else []:
    s = d / "SKILL.md"
    if not s.exists():
        fail(f"{rel(d)}: no SKILL.md")
        continue
    m = re.match(r"^---\n(.*?)\n---\n", read(s), re.S)
    if not m:
        fail(f"{rel(s)}: no YAML front matter")
        continue
    fm = dict(re.findall(r"^([A-Za-z][\w-]*):[ \t]*(.*)$", m.group(1), re.M))
    if fm.get("name") != d.name:
        fail(f"{rel(s)}: front matter name {fm.get('name')!r} is not the folder name {d.name!r}")
    desc = fm.get("description", "").strip()
    if len(desc) < 60:
        fail(f"{rel(s)}: description too short to say when to use the skill")
    for key, value in fm.items():
        plain = value.strip()
        if plain[:1] not in ("'", '"') and (": " in plain or " #" in plain or plain[:1] in "&*!|>%@`{[,"):
            fail(f"{rel(s)}: front matter {key} needs quoting to be valid YAML")
    skills.append(d.name)
if not skills:
    fail(".claude/skills: no skills found")

# ---------- workflows ----------
WORKFLOWS = ROOT / ".claude" / "workflows"
workflows = []


def js_literal(src):
    """Parse a JavaScript object literal made only of literals (strings, numbers, true, false, null, arrays,
    objects with plain or quoted keys, trailing commas, comments). Raises ValueError on anything else."""
    i, n = 0, len(src)

    def skip():
        nonlocal i
        while i < n:
            if src[i].isspace():
                i += 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j + 1
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                if j < 0:
                    raise ValueError("unclosed comment")
                i = j + 2
            else:
                return

    def string():
        nonlocal i
        q = src[i]
        i += 1
        out = []
        while i < n and src[i] != q:
            c = src[i]
            if c == "\n":
                raise ValueError("line break inside a string")
            if c == "\\":
                i += 1
                e = src[i]
                if e == "u":
                    out.append(chr(int(src[i + 1:i + 5], 16)))
                    i += 4
                else:
                    out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}.get(e, e))
            else:
                out.append(c)
            i += 1
        if i >= n:
            raise ValueError("unclosed string")
        i += 1
        return "".join(out)

    def value():
        nonlocal i
        skip()
        if i >= n:
            raise ValueError("unexpected end")
        c = src[i]
        if c == "{":
            i += 1
            obj = {}
            while True:
                skip()
                if src[i] == "}":
                    i += 1
                    return obj
                if src[i] in "'\"":
                    key = string()
                else:
                    m = re.compile(r"[A-Za-z_$][\w$]*").match(src, i)
                    if not m:
                        raise ValueError(f"bad key at {src[i:i + 20]!r}")
                    key, i = m.group(0), m.end()
                skip()
                if src[i] != ":":
                    raise ValueError(f"expected ':' after {key!r}")
                i += 1
                obj[key] = value()
                skip()
                if src[i] == ",":
                    i += 1
                elif src[i] != "}":
                    raise ValueError(f"expected ',' or '}}' after {key!r}")
        if c == "[":
            i += 1
            arr = []
            while True:
                skip()
                if src[i] == "]":
                    i += 1
                    return arr
                arr.append(value())
                skip()
                if src[i] == ",":
                    i += 1
                elif src[i] != "]":
                    raise ValueError("expected ',' or ']'")
        if c in "'\"":
            return string()
        m = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?").match(src, i)
        if m:
            i = m.end()
            return json.loads(m.group(0))
        for word, v in (("true", True), ("false", False), ("null", None)):
            if src.startswith(word, i) and not re.match(r"[\w$]", src[i + len(word):i + len(word) + 1]):
                i += len(word)
                return v
        raise ValueError(f"not a literal at {src[i:i + 30]!r}")

    result = value()
    skip()
    if i != n:
        raise ValueError(f"text after the literal: {src[i:i + 30]!r}")
    return result


HEAD = "export const meta = "
for w in sorted(WORKFLOWS.glob("*.js")) if WORKFLOWS.is_dir() else []:
    t = read(w)
    workflows.append(w.stem)
    if not t.startswith(HEAD + "{"):
        fail(f"{rel(w)}: must begin with `export const meta = {{`")
        continue
    end = t.find("\n}\n")
    if end < 0:
        fail(f"{rel(w)}: the meta object must end with a line holding only '}}'")
        continue
    meta_src, body = t[len(HEAD):end + 2], t[end + 3:]
    try:
        meta = js_literal(meta_src)
    except (ValueError, IndexError) as e:
        fail(f"{rel(w)}: meta is not a pure literal ({e})")
        continue
    if meta.get("name") != w.stem:
        fail(f"{rel(w)}: meta.name {meta.get('name')!r} is not the file name {w.stem!r}")
    if not str(meta.get("description", "")).strip():
        fail(f"{rel(w)}: meta.description is empty")
    phases = meta.get("phases") or []
    titles = {p.get("title") for p in phases if isinstance(p, dict)}
    if not phases or None in titles:
        fail(f"{rel(w)}: meta.phases must list objects with a title")
    for title in re.findall(r"\bphase\(\s*['\"]([^'\"]+)['\"]\s*\)", body):
        if title not in titles:
            fail(f"{rel(w)}: phase('{title}') is not declared in meta.phases")
    for title in re.findall(r"\bphase:\s*['\"]([^'\"]+)['\"]", body):
        if title not in titles:
            fail(f"{rel(w)}: agent phase '{title}' is not declared in meta.phases")
    if re.search(r"Date\.now\(|Math\.random\(|new Date\(\)", t):
        fail(f"{rel(w)}: uses the clock or randomness, which breaks resume")
    if re.search(r":\s*(?:string|number|boolean)(?:\[\])?\s*[,;)=]|\binterface\s+\w+\s*\{", body):
        fail(f"{rel(w)}: looks like TypeScript; the runtime runs JavaScript")
    with tempfile.TemporaryDirectory() as td:
        wrapped = pathlib.Path(td) / (w.stem + ".mjs")
        wrapped.write_text(t[:end + 2] + "\nexport default async function run(args, agent, parallel, pipeline, phase, log, "
                           "workflow, budget) {\n" + body + "\n}\n", encoding="utf-8")
        r = subprocess.run(["node", "--check", str(wrapped)], capture_output=True, text=True)
        if r.returncode:
            err = [x for x in r.stderr.strip().splitlines() if x.strip()]
            fail(f"{rel(w)}: not valid JavaScript: {err[-1] if err else 'syntax error'}")
if not workflows:
    fail(".claude/workflows: no workflows found")

# kit/README.md lists exactly the skills and workflows there are
front = ROOT / "kit" / "README.md"
if front.exists():
    ft = read(front)
    for section, have in (("Skills", skills), ("Workflows", workflows)):
        m = re.search(rf"^## {section}\n(.*?)(?=^## |\Z)", ft, re.S | re.M)
        listed = re.findall(r"^\|\s*`(uvk-[a-z-]+)`\s*\|", m.group(1), re.M) if m else []
        if sorted(listed) != sorted(have):
            fail(f"kit/README.md: the {section} table lists {sorted(listed)}, but there are {sorted(have)}")
else:
    fail("kit/README.md is missing")

# ---------- paths, flags and uvk- names ----------
PATH_RE = re.compile(r"(?<![\w/$.<>-])((?:tools|kit|\.claude|research|assets)/[A-Za-z0-9_./-]*)")
CMD_RE = re.compile(r"\b(?:python3|node)(?:\s+-[A-Za-z]+)*\s+(tools/[\w./-]+\.(?:py|js))")
MENTION_RE = re.compile(r"(?<![\w./$-])((?:[\w-]+/)*[\w-]+\.(?:py|js))(?![\w/-])")
FLAG_RE = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")
NAME_RE = re.compile(r"(?<![\w-])(uvk-[a-z]+(?:-[a-z]+)+)(?![\w-])")
FENCED_RE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n(.*?)^[ \t]*\1[ \t]*$", re.S | re.M)
INLINE_RE = re.compile(r"`((?:[^`\n]|\n(?![ \t]*\n))+?)`")
SENTENCE_END_RE = re.compile(r"\.(?:\s|$)|;\s|\n")
NODE_FLAG_RE = re.compile(r"""(?:\ba\s*===\s*|\b(?:opt|arg|rawArg)\(\s*)['"](--[a-z][a-z0-9-]*)['"]""")
OPERATORS = {"&&", "||", "|", ";", "&", ">", ">>", "<"}
TOOLS = sorted(rel(p) for p in (ROOT / "tools").rglob("*") if p.is_file() and p.suffix in (".py", ".js"))
interfaces, notes = {}, []
commands = 0


def resolve(mention):
    """The tool a mention names: a path under tools/, or a file name (with folders) that only one tool ends with."""
    if mention in TOOLS:
        return mention
    if mention.startswith("tools/"):
        return None  # reported as a missing path
    hits = [t for t in TOOLS if t.endswith("/" + mention)]
    return hits[0] if len(hits) == 1 else None


def help_text(tool, sub):
    env = {k: v for k, v in os.environ.items() if k not in ("GENAI_API_KEY", "GEMINI_API_KEY", "GENAI_BASE_URL",
                                                             "GENAI_AUTH_HEADER")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory() as td:
        try:
            r = subprocess.run([sys.executable, str(ROOT / tool), *([sub] if sub else []), "--help"], cwd=td, env=env,
                               capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return None
    return r.stdout if r.returncode == 0 and "usage:" in r.stdout else None


def parse_help(text, sub):
    """Flags (name -> 0, 1, '*' or '+' values), required flags, the number of positional arguments (min, max) and the
    subcommands, from argparse's --help."""
    m = re.search(r"^usage: (.*?)(?=\n[ \t]*\n|\Z)", text, re.S | re.M)
    words = (m.group(1).split() if m else [])[2 if sub else 1:]
    elems, cur, depth = [], [], 0
    for w in words:
        cur.append(w)
        depth += w.count("[") - w.count("]")
        if depth <= 0:
            elems.append(" ".join(cur))
            cur, depth = [], 0
    required, subs, low, high, i = set(), [], 0, 0, 0
    while i < len(elems):
        e = elems[i]
        if e.startswith("["):
            inner = e[1:-1].strip()
            if inner.endswith("..."):
                high = float("inf")
            elif not inner.startswith("-"):
                high += 1
        elif e.startswith("{"):
            subs = e.strip("{}").split(",")
        elif e.startswith("-"):
            required.add(e)
            if i + 1 < len(elems) and re.fullmatch(r"[A-Z][A-Z0-9_=-]*", elems[i + 1]):
                i += 1
        elif e != "...":
            low, high = low + 1, high + 1
        i += 1
    flags, section = {}, False
    for line in text.splitlines():
        if re.match(r"^(optional arguments|options):\s*$", line):
            section = True
            continue
        if section and line and not line.startswith(" "):
            section = False
        o = re.match(r"^  (-\S.*?)(?:\s{2,}\S.*)?$", line) if section else None
        forms = [form.split() for form in o.group(1).split(", ")] if o else []
        metas = [meta for _, *meta in forms if meta]
        meta = metas[-1] if metas else []       # newer argparse prints the metavar once: -o, --out OUT
        for name, *_ in forms:
            flags[name] = (0 if not meta else "*" if meta[0].startswith("[")
                           else "+" if len(meta) > 1 and meta[1].startswith("[") else len(meta))
    return {"flags": flags, "required": required, "positional": (low, high), "subs": subs, "full": True}


def interface(tool, sub=None):
    """What a tool reads: a Python tool's from its --help, a Node tool's from its argument parser."""
    if (tool, sub) not in interfaces:
        src = read(ROOT / tool)
        iface = None
        if tool.endswith(".js"):
            iface = {"flags": {f: None for f in NODE_FLAG_RE.findall(src)}, "required": set(), "positional": None,
                     "subs": [], "full": False}
        else:
            text = help_text(tool, sub)
            if text:
                iface = parse_help(text, sub)
            else:
                notes.append(f"{tool}{' ' + sub if sub else ''} --help failed here, so its flags were checked against "
                             "its source only")
                iface = {"flags": {f: None for f in re.findall(r"""['"](--[a-z][a-z0-9-]*)['"=]""", src)},
                         "required": set(), "positional": None, "subs": [], "full": False}
        interfaces[(tool, sub)] = iface
    return interfaces[(tool, sub)]


def check_flags(where, tool, flags, first_word=""):
    """A mention in prose or a prompt: every flag after it is one the tool reads."""
    global commands
    iface = interface(tool)
    if not iface or not flags:
        return
    commands += 1
    if iface["subs"]:
        if first_word not in iface["subs"]:
            fail(f"{where}: {tool} needs a subcommand ({', '.join(iface['subs'])}) before {flags[0]}")
            return
        iface = interface(tool, first_word) or iface
    label = f"{tool} {first_word}" if interface(tool)["subs"] else tool
    for flag in flags:
        if flag != "--help" and flag not in iface["flags"]:
            fail(f"{where}: {label} has no flag {flag}")


def check_command(where, tool, rest):
    """A full command in a code block or a template: its flags, their values, its required flags and its positional
    arguments must be what the tool reads."""
    global commands
    try:
        tokens = shlex.split(rest, comments=True)
    except ValueError as e:
        fail(f"{where}: the command for {tool} cannot be read ({e})")
        return
    words = []
    for w in tokens:
        if w in OPERATORS:
            break
        if words and words[-1].count("<") > words[-1].count(">"):
            words[-1] += " " + w     # a <placeholder with spaces>
        else:
            words.append(w)
    iface = interface(tool)
    if not iface or "--help" in words:
        return
    commands += 1
    label = tool
    if iface["subs"]:
        if not words or words[0] not in iface["subs"]:
            fail(f"{where}: {tool} needs a subcommand ({', '.join(iface['subs'])})")
            return
        label = f"{tool} {words[0]}"
        iface, words = interface(tool, words[0]), words[1:]
        if not iface:
            return
    seen, positional, i = set(), [], 0
    while i < len(words):
        w = words[i]
        i += 1
        if w == "...":
            continue
        if w.startswith("["):
            while i < len(words) and not words[i - 1].endswith("]"):
                i += 1           # an optional [<placeholder> ...]
            continue
        if not w.startswith("-") or w == "-":
            positional.append(w)
            continue
        name, eq, _ = w.partition("=")
        if name not in iface["flags"]:
            fail(f"{where}: {label} has no flag {name}")
            continue
        seen.add(name)
        arity = iface["flags"][name]
        if eq or arity == 0:
            continue
        if arity is None:        # a Node flag: the next word is its value unless it is another flag
            i += 1 if i < len(words) and not words[i].startswith("-") else 0
            continue
        if arity in ("*", "+"):
            while i < len(words) and not words[i].startswith("-"):
                i += 1
            continue
        if i + arity > len(words) or any(x.startswith("-") for x in words[i:i + arity]):
            fail(f"{where}: {label} {name} needs a value")
        i += arity
    if not iface["full"]:
        return
    for name in sorted(iface["required"] - seen):
        fail(f"{where}: {label} needs {name}")
    low, high = iface["positional"]
    if len(positional) < low:
        fail(f"{where}: {label} needs {low} positional argument(s), the command gives {len(positional)}")
    elif len(positional) > high:
        fail(f"{where}: {label} takes {'no' if high == 0 else 'at most ' + str(int(high))} positional argument(s), "
             f"the command gives {len(positional)}: {' '.join(positional)}")


def check_mentions(where, text):
    """Every tool named in running text, with the flags written after it up to the end of the sentence."""
    found = [(m, resolve(m.group(1))) for m in MENTION_RE.finditer(text)]
    found = [(m, tool) for m, tool in found if tool]
    for k, (m, tool) in enumerate(found):
        stop = SENTENCE_END_RE.search(text, m.end())
        end = min(stop.start() if stop else len(text), found[k + 1][0].start() if k + 1 < len(found) else len(text))
        after = text[m.end():end]
        first = re.match(r"\s*([a-z][\w-]*)", after)
        check_flags(where, tool, FLAG_RE.findall(after), first.group(1) if first else "")


def js_strings(src):
    """The string literals of a JavaScript file, with literals joined by + merged and each ${...} replaced by VALUE;
    a template literal inside an interpolation comes out as a string of its own."""
    out = []

    def literal(i):
        q, i, parts = src[i], i + 1, []
        while i < len(src) and src[i] != q:
            if src[i] == "\\" and i + 1 < len(src):
                parts.append("\n" if src[i + 1] == "n" else src[i + 1])
                i += 2
            elif q == "`" and src.startswith("${", i):
                i = expression(i + 2)
                parts.append("VALUE")
            else:
                parts.append(src[i])
                i += 1
        return "".join(parts), i + 1

    def expression(i):
        depth = 1
        while i < len(src) and depth:
            if src[i] in "'\"`":
                s, i = literal(i)
                out.append(s)
                continue
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        return i

    i = 0
    while i < len(src):
        if src.startswith("//", i):
            i = src.find("\n", i) if src.find("\n", i) >= 0 else len(src)
        elif src[i] in "'\"`":
            s, i = literal(i)
            while True:          # 'a' + 'b' is one string
                j = i
                while j < len(src) and src[j].isspace():
                    j += 1
                if j < len(src) and src[j] == "+":
                    j += 1
                    while j < len(src) and src[j].isspace():
                        j += 1
                    if j < len(src) and src[j] in "'\"`":
                        more, i = literal(j)
                        s += more
                        continue
                break
            out.append(s)
        else:
            i += 1
    return out


def json_strings(value, key=None):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from json_strings(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from json_strings(v, key)
    elif isinstance(value, str):
        yield key, value


def strict_lines(where, text):
    for m in CMD_RE.finditer(text):
        tool = m.group(1)
        if (ROOT / tool).exists():
            check_command(where, tool, text[m.end():])


scanned = [*files(".md"), *sorted(WORKFLOWS.glob("*.js")), *sorted((ROOT / "kit" / "templates").rglob("*.json"))]
known = set(skills) | set(workflows)
for f in scanned:
    t = read(f)
    where = rel(f)
    for m in PATH_RE.finditer(t):
        p, after = m.group(1), t[m.end():m.end() + 1]
        if after and after in "<{$*[…":
            continue
        p = p.rstrip(".,:;)")
        if p and not (ROOT / p).exists():
            fail(f"{where}: names {p}, which is not in the repository")
    if f.suffix == ".md":
        prose = t
        for block in FENCED_RE.finditer(t):
            for line in re.sub(r"\\\n[ \t]*", " ", block.group(2)).splitlines():
                strict_lines(where, line)
        prose = FENCED_RE.sub("", t)
        for span in INLINE_RE.finditer(prose):
            code = span.group(1).replace("\n", " ")
            if CMD_RE.search(code):
                strict_lines(where, code)
            else:
                check_mentions(where, code)
        prose = INLINE_RE.sub("", prose)
        for m in CMD_RE.finditer(prose):
            if (ROOT / m.group(1)).exists():
                rest = re.split(r"[\n|;&#`'\")]", prose[m.end():], maxsplit=1)[0]
                check_flags(where, m.group(1), FLAG_RE.findall(rest))
    elif f.suffix == ".js":
        for s in js_strings(t):
            check_mentions(where, s)
    else:
        try:
            data = json.loads(t)
        except ValueError:
            data = None      # reported with the templates
        for key, s in json_strings(data):
            if key == "command":
                strict_lines(where, s)
            else:
                check_mentions(where, s)
    if f.suffix in (".md", ".js") or "templates" in f.parts:
        for name in sorted(set(NAME_RE.findall(t))):
            if name not in known:
                fail(f"{where}: names {name}, which is neither a skill nor a workflow")

# ---------- links in every Markdown file ----------
FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.S | re.M)
LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(<?([^)\s>]+)>?(?:\s+[\"'][^\"'\n]*[\"'])?\)")
anchors_of = {}


def anchors(md):
    if md not in anchors_of:
        seen, out = {}, set()
        for line in FENCE_RE.sub("", read(md)).splitlines():
            h = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
            if not h:
                continue
            s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h.group(1)).lower()
            s = re.sub(r"[^\w\- ]", "", s).replace(" ", "-")
            k = seen.get(s, 0)
            seen[s] = k + 1
            out.add(s if k == 0 else f"{s}-{k}")
        anchors_of[md] = out
    return anchors_of[md]


for md in files(".md"):
    text = FENCE_RE.sub("", read(md))
    text = re.sub(r"`[^`\n]*`", lambda m: m.group(0) if "](" not in m.group(0) else "", text)
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            continue
        path, _, frag = target.partition("#")
        dest = (md.parent / urllib.parse.unquote(path)).resolve() if path else md
        try:
            dest.relative_to(ROOT)
        except ValueError:
            fail(f"{rel(md)}: link {target} leaves the repository")
            continue
        if not dest.exists():
            fail(f"{rel(md)}: link {target} does not resolve")
        elif frag and dest.suffix == ".md" and frag not in anchors(dest):
            fail(f"{rel(md)}: link {target} names no heading in {rel(dest)}")

# ---------- templates ----------
TEMPLATES = ROOT / "kit" / "templates"
loaded = {}
for f in sorted(TEMPLATES.rglob("*.json")) if TEMPLATES.is_dir() else []:
    try:
        loaded[rel(f)] = json.loads(read(f))
    except ValueError as e:
        fail(f"{rel(f)}: not valid JSON ({e})")
for f in [ROOT / "tools/plates/plates.example.json", *sorted((ROOT / "player/sample").glob("*.json"))]:
    if f.exists():
        try:
            json.loads(read(f))
        except ValueError as e:
            fail(f"{rel(f)}: not valid JSON ({e})")


def tpl(name):
    key = f"kit/templates/{name}"
    if key not in loaded:
        fail(f"{key}: missing or unreadable")
    return loaded.get(key)


manifest, board, cues, checks, measures = (tpl(x) for x in (
    "script/manifest.example.json", "film/storyboard.example.json", "score/cue-sheet.example.json",
    "checks/checks.example.json", "review/measures.example.json"))
if manifest:
    scenes = manifest.get("scenes", [])
    text = {s.get("scene_number"): s.get("spoken_text_exact", "") for s in scenes}
    if [s.get("scene_number") for s in scenes] != list(range(1, len(scenes) + 1)):
        fail("kit/templates/script/manifest.example.json: scene_number must run 1, 2, 3 ... in order")
    if len({s.get("clip_id") for s in scenes}) != len(scenes):
        fail("kit/templates/script/manifest.example.json: every clip_id must be unique")
    for p in manifest.get("parts", []):
        if not p.get("scenes") or any(n not in text for n in p["scenes"]):
            fail(f"kit/templates/script/manifest.example.json: part {p.get('part')} names a scene that does not exist")

    def once(phrase, n, where):
        hits = text.get(n, "").count(phrase) if phrase else 0
        if hits != 1:
            fail(f"{where}: {phrase!r} occurs {hits} times in scene {n}; the renderer needs exactly one")

    if board:
        by_name = {}
        for s in board.get("shots", []):
            if s.get("scene") not in text:
                fail(f"kit/templates/film/storyboard.example.json: shot {s.get('shot')} is in no scene of the manifest")
                continue
            once(s.get("spoken_anchor"), s["scene"], "kit/templates/film/storyboard.example.json")
            by_name.setdefault(pathlib.PurePath(s.get("art_path", "")).name, set()).add(s.get("art_path"))
        for name, paths in by_name.items():
            if len(paths) > 1:
                fail(f"kit/templates/film/storyboard.example.json: {sorted(paths)} share the file name {name}")
    if cues:
        fit = read(ROOT / "tools/score/fit-score.js") if (ROOT / "tools/score/fit-score.js").exists() else ""
        m = re.search(r"NEEDED_ANCHORS\s*=\s*\[([\d,\s]+)\]", fit)
        needed = [int(x) for x in m.group(1).split(",")] if m else []
        for k, cs in enumerate(cues.get("scenes", [])):
            n = k + 1
            if k >= len(scenes) or cs.get("clip_id") != scenes[k].get("clip_id"):
                fail(f"kit/templates/score/cue-sheet.example.json: entry {n} is not scene {n} of the manifest")
                continue
            phrases = [a.get("phrase") for a in cs.get("spoken_anchors", [])]
            for phrase in phrases:
                once(phrase, n, "kit/templates/score/cue-sheet.example.json")
            if k < len(needed) and len(phrases) < needed[k]:
                fail(f"kit/templates/score/cue-sheet.example.json: scene {n} has {len(phrases)} anchors; "
                     f"tools/score/fit-score.js needs {needed[k]}")
            if [text[n].find(p) for p in phrases] != sorted(text[n].find(p) for p in phrases):
                fail(f"kit/templates/score/cue-sheet.example.json: scene {n}'s anchors are not in spoken order")
    if checks:
        where = "kit/templates/checks/checks.example.json"
        ids = [c.get("id") for c in checks.get("checks", [])]
        if len(set(ids)) != len(ids):
            fail(f"{where}: every check id must be unique")
        for c in checks.get("checks", []):
            cid, steps = c.get("id"), c.get("steps", [])
            if c.get("afterScene") not in text:
                fail(f"{where}: {cid} follows a scene that is not in the manifest")
            if c.get("corner") not in ("bl", "br"):
                fail(f"{where}: {cid} corner must be bl or br")
            for k in ("say", "ask", "correct"):
                if not c.get(k):
                    fail(f"{where}: {cid} has no {k}")
            kinds = [s.get("kind") for s in steps]
            if not kinds or kinds[-1] != "choice":
                fail(f"{where}: {cid} must end on a choice, the only step that shows Continue")
            for j, kind in enumerate(kinds):
                if kind not in ("choice", "own_words", "probe"):
                    fail(f"{where}: {cid} has an unknown step kind {kind!r}")
                if kind == "probe" and (j == 0 or kinds[j - 1] != "own_words"):
                    fail(f"{where}: {cid}'s probe must follow an own_words step")
            for s in steps:
                if s.get("kind") == "choice":
                    opts, fb, ans = s.get("options", []), s.get("feedback", []), s.get("answer")
                    if not 2 <= len(opts) <= 4 or len(fb) != len(opts) or not isinstance(ans, int) or not 0 <= ans < len(opts):
                        fail(f"{where}: {cid} needs two to four options, one feedback each and an answer index in range")
    if measures:
        m = re.search(r"--reference-words (\d+)", measures.get("command", ""))
        words = sum(len(s.get("spoken_text_exact", "").split()) for s in scenes)
        if not m or int(m.group(1)) != words:
            fail(f"kit/templates/review/measures.example.json: --reference-words must be {words}, "
                 "the word count of the sample manifest")

# ---------- Python compiles ----------
for f in [*sorted((ROOT / "tools").rglob("*.py")), *sorted((ROOT / "kit" / "scripts").glob("*.py"))]:
    try:
        compile(read(f), str(f), "exec")
    except SyntaxError as e:
        fail(f"{rel(f)}: line {e.lineno}: {e.msg}")

# ---------- key-shaped strings and e-mail addresses ----------
SECRETS = [
    ("a Google API key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("an API key", r"\bsk-[A-Za-z0-9_\-]{20,}"),
    ("a GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"),
    ("a Slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("an AWS key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("a private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("a bearer token", r"\bBearer\s+[A-Za-z0-9._~+/=-]{30,}"),
    ("a JSON web token", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("a key assigned in the clear", r"(?i)\b\w*(?:api_?key|secret|token|passw(?:or)?d)\w*\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+]{24,}"),
    ("an e-mail address", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
]
for f in files(*TEXT_SUFFIXES):
    t = read(f)
    for what, pattern in SECRETS:
        if re.search(pattern, t):
            fail(f"{rel(f)}: contains what looks like {what}")

print(f"{len(skills)} skills, {len(workflows)} workflows; {len(scanned)} files checked for paths, with {commands} tool "
      f"commands and mentions checked for flags and arguments; {len(files('.md'))} Markdown files checked for links; "
      f"{len(loaded)} templates")
for note in notes:
    print("note:", note)
if fails:
    print(f"{len(fails)} problem(s):")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("kit check passed")
