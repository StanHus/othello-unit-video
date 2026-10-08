#!/usr/bin/env python3
"""Labelled book-style plates for the structural lines of a narration: the lines a painting cannot carry (a line
from one point of the story to another, a checklist, a map, labels for a person, a chain of command, a quotation
with its definition, the shape of a genre, a word list).

Each plate is a still at the film's plate size (1480x808, the picture area inside the book frame that
tools/film/render-narrated.js draws), laid out as HTML and screenshotted by headless Chrome. The tool holds only
layouts: every on-screen word comes from the content file. The rule used in the films: a plate shows only words the
narration speaks while it is on screen; plates.json records them so that can be checked.

  python3 tools/plates/build_plates.py --content tools/plates/plates.example.json --out <dir>
  python3 tools/plates/build_plates.py --content plates.json --out <dir> --only quote     # ids starting "quote"
  python3 tools/plates/build_plates.py --ne ne_50m_land.geojson                           # rebuild the coastline
Writes <out>/plates/<id>.png, <out>/plates.json (id, file, type, base painting, on-screen text, sha256) and
<out>/contact-sheet.jpg.

Content file: {"art": {"<key>": "<image path>"}, "plates": [{"id": ..., "type": ..., ...}]}. Image paths are
relative to the content file (--art-map adds or overrides keys). Plate types and their fields:
  title        background, title, byline, note
  arc          background, start {mark, quote|text, ref}, end {mark, quote|text, ref}, ticks [labels]
  checklist    background, title, items [{label, name, crop | words}], shown = items filled in
  map          places [{name, lon, lat, anchor: right|above, tag, gloss}], route [[lon, lat], ...], regions [{text, lon, lat}]
  caption      background, label, text
  label_card   background, kicker, name, items [{text, gloss}], shown
  rank_ladder  background, title, face_art, rungs [{rank, name, gloss, face}], shown = rungs drawn; rungs + 1 also draws link {text}
  quote        background, quote, ref, steps [{label, text}], definition {term, text}, shown = 1 quote, 2 + steps or definition, 3 + both
  curve        background, kicker, title, peak, fall, causes [up to 2], end, shown = 1 title .. 5 everything
  glossary     background, title, words [up to 8], shown = words filled in
"reveal": [n, ...] builds one plate per value of `shown`, with "-n" appended to the id. Optional "dim" and "blur"
change the background painting's brightness and blur. A crop is {"art": key, "x", "y", "h"}: a square whose top-left
corner is at fractions x of the width and y of the height and whose side is a fraction h of the height (faces in a
rank ladder use the same [x, y, h] form). Text may contain "\\n" for a line break.
The map projection is fixed to the central and eastern Mediterranean; the coastline file (--land) is the Natural Earth 1:50m
land polygons (public domain) projected with the same constants by --ne.
Fonts: Big Caslon and Hoefler Text where installed, else Libre Caslon, Georgia or the browser's serif.
Chrome: CHROME_BIN, else google-chrome / chromium on PATH, else the default macOS install.
"""
import argparse, hashlib, html, json, math, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
W, H = 1480, 808
E = html.escape
ART, SIZE = {}, {}
DISPLAY = "'Big Caslon','Libre Caslon Display','Libre Caslon Text',Georgia,serif"
TEXT = "'Hoefler Text','Libre Caslon Text',Garamond,Georgia,serif"

NOISE = ("data:image/svg+xml;utf8," + "<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'>"
         "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
         "<feColorMatrix values='0 0 0 0 .32  0 0 0 0 .24  0 0 0 0 .14  0 0 0 .85 0'/></filter>"
         "<rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")

CSS = f"""
:root{{--paper:#efe6d2;--paper2:#e5d8bc;--ink:#2a2118;--soft:#5b4a37;--brass:#8a6a2f;--rule:#937044;--ox:#7b2a22;--navy:#1c2a3d}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:var(--navy)}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:center}}
.shade{{position:absolute;inset:0}}
.card{{position:absolute;background:var(--paper);color:var(--ink);border:2px solid var(--rule);
  box-shadow:inset 0 0 0 6px var(--paper),inset 0 0 0 7px rgba(147,112,68,.7),0 18px 46px rgba(0,0,0,.55)}}
.card::after,.page::after{{content:"";position:absolute;inset:0;background:url("{NOISE}");opacity:.11;mix-blend-mode:multiply;pointer-events:none}}
.page{{position:absolute;inset:0;background:var(--paper)}}
.display{{font-family:{DISPLAY};font-weight:500}}
.text{{font-family:{TEXT}}}
.label{{font-family:{TEXT};font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--brass)}}
.quote{{font-family:{TEXT};font-style:italic;color:var(--ox)}}
.ref{{font-family:{TEXT};font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--soft);font-size:22px}}
.gloss{{font-family:{TEXT};font-style:italic;color:var(--soft)}}
.abs{{position:absolute}}
.rule{{height:0;border-top:1.5px solid var(--rule);opacity:.8}}
.label,.ref,text{{font-variant-numeric:lining-nums}}
"""


def chrome_bin():
    for c in [os.environ.get("CHROME_BIN"), shutil.which("google-chrome"), shutil.which("google-chrome-stable"),
              shutil.which("chromium"), shutil.which("chromium-browser"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("Chrome or Chromium not found: set CHROME_BIN")


def br(t):
    """Escape text and turn \\n into line breaks; the recorded text uses spaces."""
    return E(t).replace("\n", "<br>")


def flat(t):
    return " ".join(t.split())


def quoted(t):
    return f"“{t}”"


def url(key):
    return ART[key].as_uri()


def bg(key, bright=1.0, blur=0):
    f = f"brightness({bright}) saturate(.92)" + (f" blur({blur}px)" if blur else "")
    scale = "transform:scale(1.03);" if blur else ""
    return f'<div class="bg" style="background-image:url({url(key)});filter:{f};{scale}"></div>'


def crop(key, fx, fy, fh, box_w, box_h=None):
    """CSS background showing a square crop of painting `key`: top-left at fractions (fx, fy), side fh * height."""
    box_h = box_h or box_w
    sw, sh = SIZE[key]
    x0, y0, side = fx * sw, fy * sh, fh * sh
    s = box_w / side
    return (f"background-image:url({url(key)});background-size:{sw*s:.1f}px {sh*s:.1f}px;"
            f"background-position:{-x0*s:.1f}px {-y0*s:.1f}px;background-repeat:no-repeat")


def page(body, title):
    return f'<!doctype html><html><head><meta charset="utf-8"><title>{E(title)}</title><style>{CSS}</style></head><body>{body}</body></html>'


def back(p, bright, blur=0):
    return bg(p["background"], p.get("dim", bright), p.get("blur", blur))


# ---------------------------------------------------------------- plate types
def title(p):
    body = back(p, 1.0) + f'''
<div class="card" style="left:84px;top:250px;width:540px;height:300px;padding:46px 50px">
  <div class="display" style="font-size:108px;line-height:1">{br(p["title"])}</div>
  <div class="rule" style="margin:22px 0 18px;width:120px"></div>
  <div class="label" style="font-size:24px;letter-spacing:.12em;color:var(--ink)">{br(p.get("byline", ""))}</div>
  <div class="gloss" style="font-size:31px;margin-top:8px">{br(p.get("note", ""))}</div>
</div>'''
    return body, [flat(x) for x in (p["title"], p.get("byline"), p.get("note")) if x]


def arc(p):
    st, en, ticks, texts = p["start"], p["end"], "", []
    x0, x1 = 104, 1252
    n = len(p.get("ticks", []))
    for i, lab in enumerate(p.get("ticks", [])):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        ticks += f'<line x1="{x:.1f}" y1="48" x2="{x:.1f}" y2="68" stroke="#937044" stroke-width="2.5"/>'
        ticks += f'<text x="{x:.1f}" y="34" text-anchor="middle" font-family="{TEXT}" font-weight="600" font-size="20" letter-spacing="3" fill="#8a6a2f">{E(lab.upper())}</text>'
        texts.append(lab)

    def end_block(e, align):
        if "quote" in e:
            main, rec = f'<div class="quote" style="font-size:34px;line-height:1.18">&ldquo;{br(e["quote"])}&rdquo;</div>', quoted(flat(e["quote"]))
        else:
            main, rec = f'<div class="text" style="font-size:34px;line-height:1.18">{br(e["text"])}</div>', flat(e["text"])
        ref = f'<div class="ref" style="margin-top:10px">{E(e["ref"])}</div>' if e.get("ref") else ""
        side = "left:36px;width:640px" if align == "left" else "right:36px;width:560px;text-align:right"
        return f'<div class="abs" style="{side};top:108px">{main}{ref}</div>', [rec] + ([e["ref"]] if e.get("ref") else [])

    a_html, a_txt = end_block(st, "left")
    b_html, b_txt = end_block(en, "right")
    body = back(p, .72) + f'''
<div class="shade" style="background:linear-gradient(180deg,rgba(10,16,26,0) 38%,rgba(10,16,26,.72) 100%)"></div>
<div class="card" style="left:60px;top:534px;width:1360px;height:244px">
  <svg class="abs" style="left:0;top:0" width="1360" height="120" viewBox="0 0 1360 120">
    <defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0 0L10 5L0 10z" fill="#937044"/></marker></defs>
    <line x1="104" y1="58" x2="1252" y2="58" stroke="#937044" stroke-width="3" marker-end="url(#arr)"/>{ticks}
    <circle cx="66" cy="58" r="31" fill="#8a6a2f"/><text x="66" y="72" text-anchor="middle" font-family="{DISPLAY}" font-size="42" fill="#efe6d2">{E(st.get("mark", ""))}</text>
    <circle cx="1294" cy="58" r="31" fill="#7b2a22"/><text x="1294" y="72" text-anchor="middle" font-family="{DISPLAY}" font-size="42" fill="#efe6d2">{E(en.get("mark", ""))}</text>
  </svg>
  {a_html}
  {b_html}
</div>'''
    marks = [m for m in (st.get("mark"), en.get("mark")) if m]
    return body, marks + a_txt + b_txt + texts


NUMBERS = ["One", "Two", "Three", "Four", "Five"]


def checklist(p):
    items, shown = p["items"], p.get("shown", len(p["items"]))
    if len(items) > 4:
        sys.exit(f"{p['id']}: a checklist holds at most 4 items")
    labels = [it.get("label", NUMBERS[i]) for i, it in enumerate(items)]
    cards, texts = "", [p["title"]] + labels
    x_start = (W - (len(items) * 300 + (len(items) - 1) * 44)) // 2
    for i, it in enumerate(items):
        x = x_start + i * 344
        if i < shown:
            if "crop" in it:
                c = it["crop"]
                pic = f'<div class="abs" style="left:18px;top:56px;width:264px;height:264px;{crop(c["art"], c["x"], c["y"], c["h"], 264)};box-shadow:inset 0 0 0 1px rgba(42,33,24,.35)"></div>'
            else:
                words = "".join(f"<div>{E(w)}</div>" for w in it.get("words", [])); texts += it.get("words", [])
                pic = (f'<div class="abs quote" style="left:18px;top:56px;width:264px;height:264px;background:var(--paper2);'
                       f'font-size:23px;line-height:30px;text-align:center;padding-top:12px;color:var(--ink)">{words}</div>')
            name_html = f'<div class="abs display" style="left:14px;right:14px;top:336px;font-size:36px;line-height:1.08;text-align:center">{br(it["name"])}</div>'
            texts.append(flat(it["name"]))
        else:
            pic = ('<div class="abs" style="left:18px;top:56px;width:264px;height:264px;background:var(--paper2);border:1.5px dashed rgba(147,112,68,.7)">'
                   f'<div class="display" style="font-size:120px;line-height:264px;text-align:center;color:rgba(138,106,47,.32)">{i+1}</div></div>')
            name_html = ""
        cards += (f'<div class="card" style="left:{x}px;top:176px;width:300px;height:440px">'
                  f'<div class="abs label" style="left:0;right:0;top:20px;text-align:center;font-size:19px">{E(labels[i])}</div>'
                  f'{pic}{name_html}</div>')
    body = back(p, .40, 2) + f'''
<div class="abs display" style="left:0;right:0;top:74px;text-align:center;font-size:56px;color:#efe6d2;text-shadow:0 2px 14px rgba(0,0,0,.6)">{br(p["title"])}</div>
{cards}'''
    return body, texts


def P(lon, lat):
    """Map projection shared with build_land(): equirectangular at 39.5 N, 37 degrees of longitude across 1400 px."""
    k = 1400 / (37 * math.cos(math.radians(39.5)))
    return 40 + (lon - 3.5) * math.cos(math.radians(39.5)) * k, 40 + (46.75 - lat) * k


def map_plate(p, land_d):
    grat = ""
    for lon in range(5, 41, 5):
        x, _ = P(lon, 40)
        grat += f'<line x1="{x:.1f}" y1="40" x2="{x:.1f}" y2="768" stroke="#b9a37a" stroke-width=".8" stroke-opacity=".55"/>'
    for lat in range(35, 47, 5):
        _, y = P(10, lat)
        grat += f'<line x1="40" y1="{y:.1f}" x2="1440" y2="{y:.1f}" stroke="#b9a37a" stroke-width=".8" stroke-opacity=".55"/>'
    rings = "".join(f'<use href="#land" fill="none" stroke="#7f949b" stroke-width="{w}" stroke-opacity="{.6 - i*.08:.2f}"/>'
                    f'<use href="#land" fill="none" stroke="#cdd6d3" stroke-width="{w-1.7}"/>' for i, w in enumerate([34, 27, 20, 13, 6]))
    route, texts, labels = "", [], ""
    if p.get("route"):
        pts = [P(*q) for q in p["route"]]
        d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
        for i in range(1, len(pts)):   # Catmull-Rom to cubic Bezier
            p0, p1 = pts[max(i - 2, 0)], pts[i - 1]
            p2, p3 = pts[i], pts[min(i + 1, len(pts) - 1)]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        route = f'<path d="{d}" fill="none" stroke="#7b2a22" stroke-width="4" stroke-dasharray="14 9" stroke-linecap="round" marker-end="url(#rarr)"/>'
    for r in p.get("regions", []):
        x, y = P(r["lon"], r["lat"])
        labels += f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="{TEXT}" font-weight="600" font-size="30" letter-spacing="9" fill="#8a6a2f">{E(r["text"])}</text>'
        texts.append(r["text"])
    for pl in p.get("places", []):
        x, y = P(pl["lon"], pl["lat"])
        labels += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="none" stroke="#7b2a22" stroke-width="2.5"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#7b2a22"/>')
        tag, gloss = pl.get("tag"), pl.get("gloss")
        if pl.get("anchor", "right") == "right":
            spans = f'<tspan font-family="{DISPLAY}" font-size="44" fill="#2a2118">{E(pl["name"])}</tspan>'
            if tag:
                spans += f'<tspan dx="22" dy="-2" font-family="{TEXT}" font-weight="600" font-size="24" letter-spacing="4" fill="#7b2a22">{E(tag.upper())}</tspan>'
            if gloss:
                spans += f'<tspan dx="22" font-family="{TEXT}" font-style="italic" font-size="30" fill="#5b4a37">{E(gloss)}</tspan>'
            labels += f'<text x="{x+24:.1f}" y="{y+14:.1f}">{spans}</text>'
        else:
            labels += f'<text x="{x:.1f}" y="{y-26:.1f}" text-anchor="middle" font-family="{DISPLAY}" font-size="40" fill="#2a2118">{E(pl["name"])}</text>'
            if tag:
                labels += f'<text x="{x:.1f}" y="{y+48:.1f}" text-anchor="middle" font-family="{TEXT}" font-weight="600" font-size="24" letter-spacing="4" fill="#7b2a22">{E(tag.upper())}</text>'
            if gloss:
                labels += f'<text x="{x:.1f}" y="{y+82:.1f}" text-anchor="middle" font-family="{TEXT}" font-style="italic" font-size="28" fill="#5b4a37">{E(gloss)}</text>'
        texts += [t for t in (pl["name"], tag, gloss) if t]
    svg = f'''<svg class="abs" style="left:0;top:0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <clipPath id="clip"><rect x="40" y="40" width="1400" height="728"/></clipPath>
    <path id="land" d="{land_d}"/>
    <pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(40)"><line x1="0" y1="0" x2="0" y2="7" stroke="#bfa97f" stroke-width="1.1"/></pattern>
    <marker id="rarr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#7b2a22"/></marker>
  </defs>
  <g clip-path="url(#clip)">
    <rect x="40" y="40" width="1400" height="728" fill="#cdd6d3"/>
    {rings}
    <use href="#land" fill="#ebdcb6"/>
    <use href="#land" fill="url(#hatch)" fill-opacity=".38"/>
    <use href="#land" fill="none" stroke="#3a2e22" stroke-width="1.6"/>
    {grat}
    {route}
  </g>
  <rect x="40" y="40" width="1400" height="728" fill="none" stroke="#937044" stroke-width="2.5"/>
  <rect x="30" y="30" width="1420" height="748" fill="none" stroke="#937044" stroke-width="1"/>
  {labels}
</svg>'''
    return '<div class="page"></div>' + svg, texts


def caption(p):
    body = back(p, 1.0) + f'''
<div class="card" style="left:846px;top:604px;width:576px;height:150px;padding:28px 38px">
  <div class="label" style="font-size:20px">{br(p["label"])}</div>
  <div class="quote" style="font-size:40px;margin-top:10px;color:var(--ink)">{br(p["text"])}</div>
</div>'''
    return body, [flat(p["label"]), flat(p["text"])]


def label_card(p):
    rows, texts = "", [p["kicker"], p["name"]]
    for i, it in enumerate(p["items"][:p.get("shown", len(p["items"]))]):
        rows += f'<div class="display" style="font-size:42px;line-height:1.15;margin-top:{26 if i else 6}px">{br(it["text"])}</div>'
        texts.append(flat(it["text"]))
        if it.get("gloss"):
            rows += f'<div class="gloss" style="font-size:28px;margin-top:4px">{br(it["gloss"])}</div>'; texts.append(flat(it["gloss"]))
    body = back(p, 1.0) + f'''
<div class="shade" style="background:linear-gradient(90deg,rgba(10,14,22,0) 0%,rgba(10,14,22,0) 41%,rgba(10,14,22,.78) 53%,rgba(10,14,22,.86) 100%)"></div>
<div class="card" style="left:790px;top:132px;width:640px;height:520px;padding:44px 48px">
  <div class="label" style="font-size:20px">{br(p["kicker"])}</div>
  <div class="display" style="font-size:84px;line-height:1;margin-top:10px">{br(p["name"])}</div>
  <div class="rule" style="margin:20px 0 8px;width:120px"></div>{rows}</div>'''
    return body, texts


def rank_ladder(p):
    rungs = p["rungs"]
    if len(rungs) > 3:
        sys.exit(f"{p['id']}: a rank ladder holds at most 3 rungs")
    shown = p.get("shown", len(rungs))
    html_r, texts = "", [p["title"]]
    face_art = p.get("face_art", p["background"])
    for i, r in enumerate(rungs[:shown]):
        y = 96 + i * 222
        fx, fy, fh = r["face"]
        html_r += (f'<div class="abs" style="left:26px;top:{y}px;width:150px;height:150px;border-radius:50%;{crop(face_art, fx, fy, fh, 150)};'
                   f'box-shadow:0 0 0 3px #937044,0 0 0 7px var(--paper),0 0 0 8px rgba(147,112,68,.7)"></div>'
                   f'<div class="abs" style="left:196px;top:{y+30}px;width:190px">'
                   f'<div class="label" style="font-size:19px">{E(r["rank"])}</div>'
                   f'<div class="display" style="font-size:46px;line-height:1.05;margin-top:4px">{E(r["name"])}</div>'
                   + (f'<div class="gloss" style="font-size:24px;margin-top:2px">{E(r["gloss"])}</div>' if r.get("gloss") else "") + '</div>')
        texts += [r["rank"], r["name"]] + ([r["gloss"]] if r.get("gloss") else [])
        if i:
            html_r += f'<div class="abs" style="left:100px;top:{y-66}px;width:2px;height:58px;background:#937044"></div>'
    if p.get("link") and shown > len(rungs) and len(rungs) >= 2:
        n = len(rungs)
        y_from, y_to = 96 + (n - 1) * 222 + 60, 96 + (n - 2) * 222 + 48
        html_r += ('<svg class="abs" style="left:0;top:0" width="440" height="740"><defs><marker id="ox" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="#7b2a22"/></marker></defs>'
                   f'<path d="M402 {y_from} C 430 {y_from-70}, 430 {y_to+66}, 402 {y_to}" fill="none" stroke="#7b2a22" stroke-width="3" stroke-dasharray="9 7" marker-end="url(#ox)"/></svg>'
                   f'<div class="abs quote" style="left:196px;top:{96 + (n - 1) * 222 + 150}px;width:210px;font-size:25px;line-height:1.1">{br(p["link"]["text"])}</div>')
        texts.append(flat(p["link"]["text"]))
    body = back(p, .86) + f'''
<div class="shade" style="background:linear-gradient(90deg,rgba(10,14,22,0) 0%,rgba(10,14,22,0) 62%,rgba(10,14,22,.7) 72%,rgba(10,14,22,.8) 100%)"></div>
<div class="card" style="left:1008px;top:34px;width:442px;height:740px">
  <div class="abs label" style="left:0;right:0;top:34px;text-align:center;font-size:19px">{E(p["title"])}</div>''' + html_r + '</div>'
    return body, texts


def quote(p):
    shown, steps, defn = p.get("shown", 3), p.get("steps"), p.get("definition")
    texts = [quoted(p["quote"]), p["ref"]]
    quote_h, defn_top, extra = (190, 462, "") if steps else (226, 360, "")
    if steps and shown >= 2:
        rows = "".join(f'<div style="display:flex;gap:18px;align-items:baseline{";margin-top:6px" if i else ""}"><span class="label" style="font-size:20px;width:130px">{E(s["label"])}</span><span class="text" style="font-size:34px">{E(s["text"])}</span></div>'
                       for i, s in enumerate(steps[:2]))
        extra = f'''
<div class="card" style="left:810px;top:312px;width:620px;height:126px;padding:22px 48px">{rows}</div>'''
        for s in steps[:2]:
            texts += [s["label"], s["text"]]
    if defn and shown >= (3 if steps else 2):
        extra += f'''
<div class="card" style="left:810px;top:{defn_top}px;width:620px;height:214px;padding:36px 48px">
  <div class="label" style="font-size:21px">{E(defn["term"])}</div>
  <div class="text" style="font-size:38px;line-height:1.2;margin-top:12px">{br(defn["text"])}</div>
</div>'''
        texts += [defn["term"], flat(defn["text"])]
    body = back(p, .64) + f'''
<div class="shade" style="background:linear-gradient(90deg,rgba(10,14,22,0) 0%,rgba(10,14,22,0) 48%,rgba(10,14,22,.6) 60%,rgba(10,14,22,.7) 100%)"></div>
<div class="card" style="left:810px;top:96px;width:620px;height:{quote_h}px;padding:{38 if steps else 46}px 48px">
  <div class="quote" style="font-size:{p.get("size", 54)}px;line-height:1.05;white-space:nowrap">&ldquo;{E(p["quote"])}&rdquo;</div>
  <div class="ref" style="margin-top:{16 if steps else 22}px">{E(p["ref"])}</div>
</div>''' + extra
    return body, texts


def curve(p):
    shown, causes = p.get("shown", 5), p.get("causes", [])[:2]
    svg, texts = "", [p["kicker"], p["title"]]
    if shown >= 2:
        svg += ('<path d="M64 560 C 150 330, 230 236, 300 236 C 380 236, 470 350, 596 584" fill="none" stroke="#937044" stroke-width="4" marker-end="url(#ta)"/>'
                '<circle cx="300" cy="236" r="10" fill="#8a6a2f"/>'
                f'<text x="300" y="206" text-anchor="middle" font-family="{DISPLAY}" font-size="36" fill="#2a2118">{E(p["peak"])}</text>'
                f'<text x="508" y="372" font-family="{TEXT}" font-style="italic" font-size="32" fill="#5b4a37">{E(p["fall"])}</text>')
        texts += [p["peak"], p["fall"]]
    for k, (cause, (ty, ay, ax0, ax1, ay1)) in enumerate(zip(causes, [(410, 400, 436, 470, 392), (462, 452, 446, 492, 440)])):
        if shown >= 3 + k:
            svg += (f'<text x="292" y="{ty}" text-anchor="middle" font-family="{TEXT}" font-style="italic" font-size="29" fill="#7b2a22">{E(cause)}</text>'
                    f'<path d="M{ax0} {ay} L {ax1} {ay1}" stroke="#7b2a22" stroke-width="2.5" marker-end="url(#tb)"/>')
            texts.append(cause)
    if shown >= 5 and p.get("end"):
        svg += ('<circle cx="600" cy="592" r="9" fill="#2a2118"/>'
                f'<text x="612" y="640" text-anchor="end" font-family="{DISPLAY}" font-size="34" fill="#2a2118">{E(p["end"])}</text>')
        texts.append(p["end"])
    body = back(p, .8) + f'''
<div class="shade" style="background:linear-gradient(90deg,rgba(10,14,22,.78) 0%,rgba(10,14,22,.7) 46%,rgba(10,14,22,0) 58%)"></div>
<div class="card" style="left:56px;top:46px;width:680px;height:716px">
  <div class="abs label" style="left:52px;top:44px;font-size:20px">{E(p["kicker"])}</div>
  <div class="abs display" style="left:50px;top:74px;font-size:72px">{E(p["title"])}</div>
  <svg class="abs" style="left:0;top:0" width="680" height="716" viewBox="0 0 680 716">
    <defs><marker id="ta" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="#937044"/></marker>
    <marker id="tb" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#7b2a22"/></marker></defs>''' + svg + '</svg></div>'
    return body, texts


def glossary(p):
    words, n = p["words"], p.get("shown", len(p["words"]))
    if len(words) > 8:
        sys.exit(f"{p['id']}: a glossary holds at most 8 words")
    slots, texts = "", [p["title"]] + [str(i + 1) for i in range(len(words))]
    for i, w in enumerate(words):
        col, row = divmod(i, 4)
        x, y = 150 + col * 470, 196 + row * 118
        word = f'<span class="display" style="font-size:56px;color:var(--ink)">{E(w)}</span>' if i < n else \
               '<span class="abs" style="left:52px;top:52px;width:330px;border-top:1.5px dotted rgba(147,112,68,.55)"></span>'
        slots += (f'<div class="abs" style="left:{x}px;top:{y}px;width:420px;height:90px">'
                  f'<span class="label" style="display:inline-block;width:52px;font-size:22px">{i+1}</span>{word}</div>')
        if i < n:
            texts.append(w)
    body = back(p, .36, 2) + f'''
<div class="card" style="left:170px;top:44px;width:1140px;height:720px">
  <div class="abs display" style="left:0;right:0;top:56px;text-align:center;font-size:58px">{br(p["title"])}</div>
  <div class="abs rule" style="left:470px;width:200px;top:146px"></div>
  {slots}
</div>'''
    return body, texts


BUILDERS = {"title": title, "arc": arc, "checklist": checklist, "caption": caption, "label_card": label_card,
            "rank_ladder": rank_ladder, "quote": quote, "curve": curve, "glossary": glossary}


# ---------------------------------------------------------------- map data
def build_land(ne_path):
    k = 1400 / (37 * math.cos(math.radians(39.5)))
    c = math.cos(math.radians(39.5))
    proj = lambda lon, lat: (40 + (lon - 3.5) * c * k, 40 + (46.75 - lat) * k)
    gj = json.loads(pathlib.Path(ne_path).read_text())
    parts = []
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            for ring in poly:
                lons = [q[0] for q in ring]; lats = [q[1] for q in ring]
                if max(lons) < 0 or min(lons) > 44 or max(lats) < 28 or min(lats) > 50:
                    continue
                pts, last = [], None
                for lon, lat in ring:
                    x, y = proj(lon, lat)
                    if last and abs(x - last[0]) + abs(y - last[1]) < 1.2:
                        continue
                    pts.append((x, y)); last = (x, y)
                if len(pts) >= 3:
                    parts.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    return " ".join(parts)


def expand(plates):
    """One spec per plate to draw; "reveal" lists expand to one plate per value of `shown`."""
    out = []
    for p in plates:
        if p.get("reveal"):
            for n in p["reveal"]:
                q = dict(p); q.pop("reveal"); q["shown"] = n; q["id"] = f'{p["id"]}-{n}'; out.append(q)
        else:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", help="plates content JSON")
    ap.add_argument("--art-map", help="JSON {key: image path} adding to or overriding the content file's art")
    ap.add_argument("--out", help="output folder")
    ap.add_argument("--only", help="build only plates whose id starts with this")
    ap.add_argument("--land", default=str(ROOT / "assets/map-land-path.txt"), help="projected coastline (SVG path data)")
    ap.add_argument("--ne", help="Natural Earth 1:50m land GeoJSON: rebuild --land from it first")
    a = ap.parse_args()
    land_file = pathlib.Path(a.land)
    if a.ne:
        land_file.write_text(build_land(a.ne) + "\n"); print("coastline", land_file)
        if not a.content:
            return
    if not a.content or not a.out:
        ap.error("--content and --out are required")
    content_path = pathlib.Path(a.content).resolve()
    content = json.loads(content_path.read_text())
    art = {k: (content_path.parent / v) for k, v in content.get("art", {}).items()}
    if a.art_map:
        amp = pathlib.Path(a.art_map).resolve()
        art.update({k: (amp.parent / v) for k, v in json.loads(amp.read_text()).items()})
    from PIL import Image
    for k, v in art.items():
        ART[k] = v.resolve()
        with Image.open(ART[k]) as im:
            SIZE[k] = im.size
    specs = [p for p in expand(content["plates"]) if not a.only or p["id"].startswith(a.only)]
    land_d = land_file.read_text().strip() if any(p["type"] == "map" for p in specs) else ""
    out = pathlib.Path(a.out); plates_dir = out / "plates"; plates_dir.mkdir(parents=True, exist_ok=True)
    man_path = out / "plates.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else {"plates": {}}
    chrome = chrome_bin()
    with tempfile.TemporaryDirectory() as td:
        for p in specs:
            if p["type"] == "map":
                body, texts = map_plate(p, land_d)
            elif p["type"] in BUILDERS:
                body, texts = BUILDERS[p["type"]](p)
            else:
                sys.exit(f'{p["id"]}: unknown plate type {p["type"]}')
            hp = pathlib.Path(td) / f'{p["id"]}.html'; hp.write_text(page(body, p["id"]))
            png = plates_dir / f'{p["id"]}.png'
            r = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                                f"--window-size={W},{H}", f"--screenshot={png}", "--allow-file-access-from-files", hp.as_uri()],
                               capture_output=True, text=True, timeout=120)
            if not png.exists():
                sys.exit(f'{p["id"]}: chrome failed: {r.stderr[-400:]}')
            man["plates"][p["id"]] = {"file": f"plates/{png.name}", "type": p["type"],
                                      "base_painting": ART[p["background"]].name if p.get("background") else "engraved map (Natural Earth 1:50m land, public domain)",
                                      "on_screen_text": texts, "sha256": hashlib.sha256(png.read_bytes()).hexdigest()}
            print("plate", p["id"], flush=True)
    man_path.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    files = [out / man["plates"][p["id"]]["file"] for p in expand(content["plates"]) if p["id"] in man["plates"]]
    cols = 6
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for f in files: args += ["-i", str(f)]
    fc = "".join(f"[{i}]scale=370:202[s{i}];" for i in range(len(files)))
    lay = "|".join(f"{(i % cols) * 370}_{(i // cols) * 202}" for i in range(len(files)))
    if len(files) > 1:
        fc += "".join(f"[s{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout={lay}:fill=black"
        subprocess.run(args + ["-filter_complex", fc, "-q:v", "3", str(out / "contact-sheet.jpg")], check=True)
        print("contact sheet", out / "contact-sheet.jpg", len(files), "plates")


if __name__ == "__main__":
    main()
