/* Narrated film: picture cuts, captions, fitted score and ducked mix, all timed from MEASURED speech.
 *
 * Inputs (never modified):
 *   --manifest   recording manifest: scenes[] with scene_number, clip_id, title, spoken_text_exact
 *   --storyboard storyboard: shots[] with shot, scene, art_path, visual_caption, spoken_anchor (an exact phrase of the scene)
 *   --cue-sheet  score cue sheet: scenes[] with clip_id and spoken_anchors[] (from tools/score/generate-score.js)
 *   --narration  folder with <clip_id>.wav per scene (+ narration-manifest.json from tools/narration/generate_takes.py)
 *   --alignment  folder with <clip_id>.words.json per scene (tools/narration/align_words.py)
 *   --art-dir    folder the storyboard's art files are looked up in by name (default assets/paintings)
 *   --art-map    optional JSON {"<shot>": "<image path>"} overriding the storyboard's art per shot
 * (OTHELLO_MANIFEST, OTHELLO_STORYBOARD and OTHELLO_CUESHEET can replace the first three.)
 * Outputs in --out:
 *   narrated-timeline.json, Othello-opening-NARRATED.{mp4,vtt}, *-voice-only/-music-only/-full-mix.wav,
 *   qa-results.json; the fitted score goes to --fitted (default <out>/fitted), written by tools/score/fit-score.js.
 *
 * Usage:
 *   node tools/film/render-narrated.js --manifest m.json --storyboard sb.json --cue-sheet cues.json \
 *        --narration takes/ --alignment takes/alignment/ --out render/            # plan + score + mix + picture
 *   node tools/film/render-narrated.js ... --stage plan                           # timeline and captions only
 *   node tools/film/render-narrated.js --stage qa --out render/ [--manifest m.json] [--whisper large-v3-turbo]
 *   node tools/film/render-narrated.js ... --test --scenes 1 --clip vo_intro_01=<wav>
 * --test stamps every output TEST-ONLY; never ship a --test render.
 * Captions: start = first aligned word - 0.05 s, end = last word + 0.3 s, at most 84 characters in two lines.
 * Mix: music 10 LU under the voice, ducked 8 dB under measured speech (attack 0.35 s, hold 0.25 s, release 1.2 s),
 * delivered at -16 LUFS integrated with true peak at most -1 dBTP. --impact-phrase is passed to fit-score.js.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const here = __dirname;
const root = path.resolve(here, '..', '..');
const FPS = 24;
const CUT_LEAD = 0.12;          // cut a few frames before the anchor word (film convention)
const CAPTION_LEAD = 0.05;
const MIN_SHOT = 1.5;
const SR = 48000;

// ---------- shared helpers (also used by tools/score/fit-score.js) ----------
function run(args, opts = {}) {
  const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...args], { encoding: 'utf8', maxBuffer: 1 << 28, ...opts });
  if (r.status !== 0) throw new Error(r.stderr || `ffmpeg exited ${r.status}`);
  return r;
}
function ffprobeDuration(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', file], { encoding: 'utf8' });
  return Number(r.stdout.trim());
}
const normText = s => s.replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"');

/** Character spans of each alignment word inside script_text. Throws if the words do not tile the script. */
function wordSpans(al) {
  let cursor = 0;
  return al.words.map(w => {
    const at = al.script_text.indexOf(w.text, cursor);
    if (at < 0 || al.script_text.slice(cursor, at).trim() !== '') throw new Error(`${al.clip_id}: word ${w.i} "${w.text}" does not tile script_text`);
    cursor = at + w.text.length;
    return [at, cursor];
  });
}

/** Resolve an exact spoken phrase to measured clip-relative times. Fails loudly when absent or ambiguous. */
function resolvePhrase(al, phrase, { occurrence } = {}) {
  const text = al.script_text;
  const hits = [];
  for (let at = text.indexOf(phrase); at >= 0; at = text.indexOf(phrase, at + 1)) hits.push(at);
  if (!hits.length) throw new Error(`${al.clip_id}: anchor phrase not found in script: "${phrase}"`);
  if (hits.length > 1 && occurrence === undefined) throw new Error(`${al.clip_id}: anchor phrase is ambiguous (${hits.length} hits): "${phrase}"`);
  const startChar = hits[occurrence || 0], endChar = startChar + phrase.length;
  const spans = al._spans || (al._spans = wordSpans(al));
  const iFirst = spans.findIndex(([a, b]) => startChar < b);
  let iLast = -1;
  spans.forEach(([a, b], i) => { if (a < endChar) iLast = i; });
  const wf = al.words[iFirst], wl = al.words[iLast];
  const [fa, fb] = spans[iFirst], [la, lb] = spans[iLast];
  // phrase may begin/end inside a token (e.g. "word—word"): interpolate by character position, and say so.
  const startIntra = startChar > fa, endIntra = endChar < lb;
  const start = startIntra ? wf.start + (wf.end - wf.start) * (startChar - fa) / (fb - fa) : wf.start;
  const end = endIntra ? wl.start + (wl.end - wl.start) * (endChar - la) / (lb - la) : wl.end;
  return {
    phrase, start: +start.toFixed(3), end: +end.toFixed(3), word_range: [iFirst, iLast],
    first_word: wf.text, last_word: wl.text,
    anchor_words_matched: al.words.slice(iFirst, iLast + 1).every(w => w.matched !== false),
    start_interpolated_within_token: startIntra, end_interpolated_within_token: endIntra
  };
}

function loadAlignment(dir, clipId, expectedText) {
  const file = path.join(dir, `${clipId}.words.json`);
  if (!fs.existsSync(file)) throw new Error(`missing alignment ${file}`);
  const al = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (al.clip_id !== clipId) throw new Error(`${file}: clip_id ${al.clip_id}`);
  if (al.script_text.trim() !== expectedText.trim()) throw new Error(`${clipId}: alignment script_text differs from recording manifest`);
  if (al.words.length !== expectedText.trim().split(/\s+/).length) throw new Error(`${clipId}: alignment word count differs from script`);
  // words without times (unmatched) get linear interpolation between timed neighbours; counted in al.interpolated
  al.interpolated = 0;
  for (let i = 0; i < al.words.length; i++) {
    const w = al.words[i];
    if (typeof w.start === 'number' && typeof w.end === 'number') continue;
    let a = i - 1; while (a >= 0 && typeof al.words[a].end !== 'number') a--;
    let b = i + 1; while (b < al.words.length && typeof al.words[b].start !== 'number') b++;
    const t0 = a >= 0 ? al.words[a].end : 0, t1 = b < al.words.length ? al.words[b].start : (al.duration_seconds || t0);
    const n = b - a, k = i - a;
    w.start = t0 + (t1 - t0) * (k - 1) / n; w.end = t0 + (t1 - t0) * k / n; w.matched = false; al.interpolated++;
  }
  for (let i = 1; i < al.words.length; i++) {
    if (!(al.words[i].start >= al.words[i - 1].start - 1e-6)) throw new Error(`${clipId}: non-monotonic word starts at ${i}`);
  }
  al._file = path.relative(root, file);
  return al;
}

/** Measured leading/trailing silence of a narration clip (ffmpeg silencedetect, -45 dBFS, 0.2 s). */
function speechBounds(wav) {
  const dur = ffprobeDuration(wav);
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', wav, '-af', 'silencedetect=noise=-45dB:d=0.2', '-f', 'null', '-'], { encoding: 'utf8' });
  const starts = [...r.stderr.matchAll(/silence_start: ([0-9.]+)/g)].map(m => +m[1]);
  const ends = [...r.stderr.matchAll(/silence_end: ([0-9.]+)/g)].map(m => +m[1]);
  let on = 0, off = dur;
  if (starts.length && starts[0] <= 0.01 && ends.length) on = ends[0];
  if (starts.length && starts[starts.length - 1] > on && (ends.length < starts.length || ends[ends.length - 1] >= dur - 0.05)) off = starts[starts.length - 1];
  return { duration: dur, speech_on: +on.toFixed(3), speech_off: +off.toFixed(3) };
}

// ---------- scene plan ----------
// Seconds of near-silence before each scene's first word and after its last (JSON arrays, one value per scene).
const LEAD_IN = process.env.OTHELLO_LEAD_IN ? JSON.parse(process.env.OTHELLO_LEAD_IN) : [2.6, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0];       // scene 1 opens on a breath of near-silence
const TAIL = process.env.OTHELLO_TAIL ? JSON.parse(process.env.OTHELLO_TAIL) : [1.6, 2.2, 1.6, 2.2, 2.2, 1.6, 1.6, 5.0];          // longer where a check follows; the last scene ends on a long silence
const frameRound = t => Math.round(t * FPS) / FPS;
const ts = seconds => {
  const ms = Math.round(seconds * 1000);
  return `${String(Math.floor(ms / 3600000)).padStart(2, '0')}:${String(Math.floor(ms / 60000) % 60).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}.${String(ms % 1000).padStart(3, '0')}`;
};

function captionChunks(tokens) {
  // tokens: [{text, i}] for one or more sentences. Greedy to <=84 chars, prefer breaks after , ; : — or sentence ends.
  const out = [];
  let cur = [];
  const len = arr => arr.map(t => t.text).join(' ').length;
  for (const t of tokens) {
    if (cur.length && len([...cur, t]) > 84) {
      let k = -1;
      for (let j = cur.length - 1; j >= 2; j--) if (/[,;:—.?!]["”’]?$/.test(cur[j].text) || /—/.test(cur[j].text)) { k = j; break; }
      if (k >= 0 && k < cur.length - 1) { out.push(cur.slice(0, k + 1)); cur = cur.slice(k + 1); }
      else { out.push(cur); cur = []; }
    }
    cur.push(t);
  }
  if (cur.length) out.push(cur);
  return out;
}
function twoLines(chunk) {
  const words = chunk.map(t => t.text);
  const full = words.join(' ');
  if (full.length <= 42) return [full];
  let best = null;
  for (let k = 1; k < words.length; k++) {
    const a = words.slice(0, k).join(' '), b = words.slice(k).join(' ');
    const score = Math.max(a.length, b.length) - (/[,;:—.?!]["”’]?$/.test(words[k - 1]) ? 6 : 0);
    if (!best || score < best.score) best = { score, lines: [a, b] };
  }
  return best.lines;
}

function buildPlan(opts) {
  const readJson = f => JSON.parse(fs.readFileSync(f, 'utf8'));
  const manifest = readJson(opts.manifest), storyboard = readJson(opts.storyboard), cueSheet = readJson(opts.cueSheet);
  const narrManifestPath = path.join(opts.narration, 'narration-manifest.json');
  const narrManifest = fs.existsSync(narrManifestPath) ? JSON.parse(fs.readFileSync(narrManifestPath, 'utf8')) : { clips: {} };
  const sceneNums = opts.scenes || manifest.scenes.map(s => s.scene_number);
  let elapsed = 0;
  const scenes = [], shots = [], cues = [], warnings = [];
  for (const n of sceneNums) {
    const ms = manifest.scenes[n - 1];
    const clipId = ms.clip_id;
    const wav = opts.clips[clipId] || path.join(opts.narration, `${clipId}.wav`);
    if (!fs.existsSync(wav)) throw new Error(`missing narration ${wav}`);
    const al = loadAlignment(opts.alignment, clipId, ms.spoken_text_exact);
    const b = speechBounds(wav);
    const firstWord = al.words[0].start, lastWord = al.words[al.words.length - 1].end;
    if (firstWord < b.speech_on - 0.4 || lastWord > b.speech_off + 0.6) warnings.push(`${clipId}: alignment span ${firstWord}-${lastWord}s vs measured speech ${b.speech_on}-${b.speech_off}s`);
    const trimStart = Math.max(0, b.speech_on - 0.15), trimEnd = Math.min(b.duration, b.speech_off + 0.30);
    const lead = LEAD_IN[n - 1], tail = TAIL[n - 1];
    const sceneStart = elapsed;
    const voiceOffset = lead - (b.speech_on - trimStart);                  // scene-relative start of trimmed clip
    const duration = frameRound(lead + (b.speech_off - b.speech_on) + tail);
    const toFilm = t => sceneStart + voiceOffset + (t - trimStart);
    const toScene = t => voiceOffset + (t - trimStart);

    // shots: sorted by spoken anchor position; the first shot opens the scene.
    const sceneShots = storyboard.shots.filter(s => s.scene === n).map(s => ({ s, r: resolvePhrase(al, s.spoken_anchor) }))
      .sort((x, y) => x.r.word_range[0] - y.r.word_range[0] || x.r.start - y.r.start);
    const starts = sceneShots.map((x, j) => j === 0 ? sceneStart : frameRound(toFilm(x.r.start) - CUT_LEAD));
    for (let j = 1; j < starts.length; j++) {
      if (starts[j] - starts[j - 1] < MIN_SHOT) warnings.push(`${clipId}: shot ${sceneShots[j].s.shot} only ${(starts[j] - starts[j - 1]).toFixed(2)}s after previous cut`);
    }
    const sceneEnd = frameRound(sceneStart + duration);
    const timedShots = sceneShots.map((x, j) => ({
      storyboard_shot: x.s.shot, art_path: (opts.artMap && opts.artMap[String(x.s.shot)]) || x.s.art_path, visual_caption: x.s.visual_caption, spoken_anchor: x.s.spoken_anchor,
      art_source: opts.artMap && opts.artMap[String(x.s.shot)] ? 'art-map override' : 'storyboard',
      start_seconds: +starts[j].toFixed(3), end_seconds: +(j + 1 < starts.length ? starts[j + 1] : sceneEnd).toFixed(3),
      cut_rule: j === 0 ? 'opens scene (scene start)' : `anchor start - ${CUT_LEAD}s lead, frame-rounded`,
      anchor_measured: { ...x.r, film_start_seconds: +toFilm(x.r.start).toFixed(3), source: `${al._file} words[${x.r.word_range[0]}..${x.r.word_range[1]}]` }
    }));
    shots.push(...timedShots);

    // music anchors from the cue sheet, measured
    const cs = cueSheet.scenes[n - 1];
    if (cs.clip_id !== clipId) throw new Error(`cue sheet scene ${n} mismatch`);
    const musicAnchors = cs.spoken_anchors.map(a => {
      const r = resolvePhrase(al, a.phrase);
      return { ...r, scene_start_seconds: +toScene(r.start).toFixed(3), scene_end_seconds: +toScene(r.end).toFixed(3), film_start_seconds: +toFilm(r.start).toFixed(3), source: `${al._file} words[${r.word_range[0]}..${r.word_range[1]}]` };
    });

    // captions: sentences -> merge very short neighbours -> chunk -> two lines
    const toks = al.words.map(w => ({ text: w.text, i: w.i }));
    const sentences = [];
    let st = 0;
    toks.forEach((t, i) => { if (/[.?!]["”’]?$/.test(t.text) || i === toks.length - 1) { sentences.push(toks.slice(st, i + 1)); st = i + 1; } });
    const merged = [];
    for (const s of sentences) {
      const prev = merged[merged.length - 1];
      const str = x => x.map(t => t.text).join(' ');
      if (prev && (str(prev).length < 26 || str(s).length < 26) && (str(prev) + ' ' + str(s)).length <= 42) merged[merged.length - 1] = [...prev, ...s];
      else merged.push(s);
    }
    const sceneCues = [];
    for (const s of merged) for (const chunk of captionChunks(s)) {
      const w0 = al.words[chunk[0].i], w1 = al.words[chunk[chunk.length - 1].i];
      sceneCues.push({ lines: twoLines(chunk), word_range: [chunk[0].i, chunk[chunk.length - 1].i], first_word_film: toFilm(w0.start), start: toFilm(w0.start) - CAPTION_LEAD, end: toFilm(w1.end) + 0.3 });
    }
    for (let k = 0; k < sceneCues.length; k++) {
      const c = sceneCues[k];
      c.end = Math.max(c.end, c.start + 1.2);
      if (k + 1 < sceneCues.length) c.end = Math.min(c.end, sceneCues[k + 1].start - 0.04);
      c.end = Math.min(c.end, sceneEnd);
    }
    const capText = sceneCues.flatMap(c => c.lines).join(' ');
    if (capText !== ms.spoken_text_exact.trim().split(/\s+/).join(' ')) throw new Error(`${clipId}: caption text is not the exact script`);
    cues.push(...sceneCues.map(c => ({ ...c, clip_id: clipId })));

    scenes.push({
      scene: n, clip_id: clipId, title: ms.title, spoken_text_exact: ms.spoken_text_exact,
      start_seconds: +sceneStart.toFixed(3), duration_seconds: +duration.toFixed(3), end_seconds: +sceneEnd.toFixed(3),
      lead_in_seconds: lead, tail_seconds: tail,
      voice: {
        file: path.relative(root, wav), clip_duration_seconds: b.duration,
        speech_on_seconds: b.speech_on, speech_off_seconds: b.speech_off, speech_bounds_source: 'ffmpeg silencedetect -45 dBFS 0.2 s on the clip',
        trim_start_seconds: +trimStart.toFixed(3), trim_end_seconds: +trimEnd.toFixed(3),
        scene_offset_seconds: +voiceOffset.toFixed(3), film_offset_seconds: +(sceneStart + voiceOffset).toFixed(3),
        manifest_duration_seconds: (narrManifest.clips[clipId] || {}).duration_seconds ?? null
      },
      alignment: { file: al._file, method: al.method || null, words: al.words.length, matched: al.words.filter(w => w.matched !== false).length, interpolated_untimed_words: al.interpolated || 0 },
      music_anchors: musicAnchors,
      shots: timedShots
    });
    elapsed = sceneEnd;
  }
  return {
    status: opts.test ? 'TEST-ONLY render from temporary data; not a deliverable' : 'narrated: cuts, captions and music moves timed from measured narration',
    generated_at: new Date().toISOString(),
    narration: { model: narrManifest.model || null, voice: narrManifest.voice || null, manifest: path.relative(root, narrManifestPath) },
    fps: FPS, cut_lead_seconds: CUT_LEAD, caption_lead_seconds: CAPTION_LEAD,
    total_seconds: +elapsed.toFixed(3), scenes, captions: cues.map(c => ({ ...c, start: +c.start.toFixed(3), end: +c.end.toFixed(3), first_word_film: +c.first_word_film.toFixed(3) })),
    warnings
  };
}

function writeVtt(plan, file, test) {
  const out = ['WEBVTT', '', `NOTE ${test ? 'TEST-ONLY. ' : ''}Exact script text. Cue times come from measured word alignment of the narration (${plan.narration.voice || 'unknown voice'}, ${plan.narration.model || 'unknown model'}).`, ''];
  // OTHELLO_BOLD='["ensign",...]' bolds those words or phrases wherever a caption line says them; unset = plain captions.
  const bold = process.env.OTHELLO_BOLD ? JSON.parse(process.env.OTHELLO_BOLD) : [];
  const boldRe = bold.length ? new RegExp(`\\b(${bold.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'gi') : null;
  const mark = l => boldRe ? l.replace(boldRe, '<b>$1</b>') : l;
  plan.captions.forEach((c, k) => out.push(String(k + 1), `${ts(c.start)} --> ${ts(c.end)}`, ...c.lines.map(mark), ''));
  fs.writeFileSync(file, out.join('\n'));
}

// ---------- audio ----------
function decodeF32(file, channels) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', file, '-ac', String(channels), '-ar', String(SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
  if (r.status !== 0) throw new Error(String(r.stderr));
  return new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.length / 4);
}
function encodeF32(samples, channels, file, codec = 'pcm_s24le') {
  const tmp = path.join(os.tmpdir(), `othello-${process.pid}-${Math.random().toString(36).slice(2)}.f32`);
  fs.writeFileSync(tmp, Buffer.from(samples.buffer, samples.byteOffset, samples.byteLength));
  run(['-f', 'f32le', '-ar', String(SR), '-ac', String(channels), '-i', tmp, '-c:a', codec, file]);
  fs.unlinkSync(tmp);
}
function loudness(file) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' });
  const tail = r.stderr.slice(r.stderr.lastIndexOf('Summary:'));
  const g = re => { const m = tail.match(re); return m ? +m[1] : null; };
  return { integrated_lufs: g(/I:\s+(-?[0-9.]+) LUFS/), lra_lu: g(/LRA:\s+(-?[0-9.]+) LU/), true_peak_dbtp: g(/Peak:\s+(-?[0-9.]+) dBFS/) };
}
const smooth = x => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };

/** Speech intervals of the voice stem (film time), measured: |x| envelope > -42 dBFS, gaps < 0.9 s merged. */
function speechIntervals(voice) {
  const win = Math.round(SR * 0.02), thr = Math.pow(10, -42 / 20);
  const active = [];
  for (let i = 0; i < voice.length; i += win) {
    let s = 0; const e = Math.min(voice.length, i + win);
    for (let j = i; j < e; j++) s += voice[j] * voice[j];
    active.push(Math.sqrt(s / (e - i)) > thr);
  }
  const iv = [];
  active.forEach((a, k) => {
    const t = k * 0.02;
    if (a) { const last = iv[iv.length - 1]; if (last && t - last[1] < 0.9) last[1] = t + 0.02; else iv.push([t, t + 0.02]); }
  });
  return iv.filter(([a, b]) => b - a > 0.15);
}

function mixAudio(plan, outDir, fitted, test) {
  const total = plan.total_seconds, N = Math.round(total * SR);
  // voice stem: place each trimmed clip at its film offset (mono 48 kHz)
  const voice = new Float32Array(N);
  for (const s of plan.scenes) {
    const clip = decodeF32(path.join(root, s.voice.file), 1);
    const a = Math.round(s.voice.trim_start_seconds * SR), b = Math.min(clip.length, Math.round(s.voice.trim_end_seconds * SR));
    const at = Math.round(s.voice.film_offset_seconds * SR);
    const fadeN = Math.round(0.02 * SR);
    for (let k = a; k < b && at + k - a < N; k++) {
      const edge = Math.min(1, (k - a) / fadeN, (b - k) / fadeN);
      voice[at + k - a] += clip[k] * edge;
    }
  }
  const music = decodeF32(fitted, 2);
  if (Math.abs(music.length / 2 - N) > SR * 0.05) throw new Error(`fitted score length ${music.length / 2 / SR}s != film ${total}s`);
  const tmpV = path.join(os.tmpdir(), `othello-v-${process.pid}.wav`), tmpM = path.join(os.tmpdir(), `othello-m-${process.pid}.wav`);
  encodeF32(voice, 1, tmpV, 'pcm_f32le'); encodeF32(music, 2, tmpM, 'pcm_f32le');
  const vL = loudness(tmpV), mL = loudness(tmpM);
  // balance: undocked music sits MUSIC_REL LU under the voice; ducking adds DUCK_DB under speech.
  const MUSIC_REL = -10, DUCK_DB = -8, ATTACK = 0.35, RELEASE = 1.2, HOLD = 0.25;
  const musicGainDb = (vL.integrated_lufs + MUSIC_REL) - mL.integrated_lufs;
  const iv = speechIntervals(voice);
  const duckDb = new Float32Array(Math.ceil(total * 100) + 1);   // 10 ms control rate
  for (let k = 0; k < duckDb.length; k++) {
    const t = k / 100;
    let d = 0;
    for (const [a, b] of iv) {
      if (t >= a - ATTACK && t <= b + HOLD + RELEASE) {
        const down = smooth((t - (a - ATTACK)) / ATTACK), up = 1 - smooth((t - (b + HOLD)) / RELEASE);
        d = Math.min(d, DUCK_DB * Math.min(down, up));
      }
    }
    duckDb[k] = d;
  }
  const ducked = new Float32Array(music.length);
  for (let i = 0; i < N; i++) {
    const p = i / SR * 100, k = Math.floor(p), f = p - k;
    const db = musicGainDb + (duckDb[k] * (1 - f) + duckDb[Math.min(k + 1, duckDb.length - 1)] * f);
    const g = Math.pow(10, db / 20);
    ducked[2 * i] = music[2 * i] * g; ducked[2 * i + 1] = music[2 * i + 1] * g;
  }
  const mix = new Float32Array(N * 2);
  for (let i = 0; i < N; i++) { mix[2 * i] = voice[i] + ducked[2 * i]; mix[2 * i + 1] = voice[i] + ducked[2 * i + 1]; }
  // delivery target: -16 LUFS integrated, true peak <= -1 dBTP. Gain to target, then a transparent limiter as a guard.
  const TARGET = -16, TP = -1.0;
  const tmpMix = path.join(os.tmpdir(), `othello-mix-${process.pid}.wav`);
  encodeF32(mix, 2, tmpMix, 'pcm_f32le');
  const pre = loudness(tmpMix);
  const gain = TARGET - pre.integrated_lufs;
  const tag = test ? 'TEST-' : '';
  const names = {
    mix: path.join(outDir, `${tag}Othello-opening-NARRATED-full-mix.wav`),
    voice: path.join(outDir, `${tag}Othello-opening-NARRATED-voice-only.wav`),
    music: path.join(outDir, `${tag}Othello-opening-NARRATED-music-only.wav`)
  };
  const limiter = `volume=${gain.toFixed(3)}dB,alimiter=limit=${Math.pow(10, (TP - 0.5) / 20).toFixed(4)}:attack=5:release=80:level=false:asc=true,aresample=${SR}`;
  run(['-i', tmpMix, '-af', limiter, '-c:a', 'pcm_s24le', names.mix]);
  // stems at the same delivery gain so voice + music ≈ mix (pre-limiter)
  run(['-i', tmpV, '-af', `volume=${gain.toFixed(3)}dB`, '-ac', '1', '-c:a', 'pcm_s24le', names.voice]);
  const tmpD = path.join(os.tmpdir(), `othello-d-${process.pid}.wav`);
  encodeF32(ducked, 2, tmpD, 'pcm_f32le');
  run(['-i', tmpD, '-af', `volume=${gain.toFixed(3)}dB`, '-c:a', 'pcm_s24le', names.music]);
  const final = loudness(names.mix);
  for (const f of [tmpV, tmpM, tmpMix, tmpD]) fs.unlinkSync(f);
  return {
    files: Object.fromEntries(Object.entries(names).map(([k, v]) => [k, path.relative(root, v)])),
    balance: { voice_stem_lufs_raw: vL.integrated_lufs, fitted_score_lufs_raw: mL.integrated_lufs, music_relative_to_voice_lu: MUSIC_REL, music_gain_db: +musicGainDb.toFixed(2) },
    ducking: { method: 'gain envelope from measured voice activity (-42 dBFS, 20 ms windows, gaps < 0.9 s merged)', duck_db: DUCK_DB, attack_s: ATTACK, hold_s: HOLD, release_s: RELEASE, speech_intervals: iv.length },
    delivery_target: { integrated_lufs: TARGET, true_peak_dbtp_max: TP, gain_applied_db: +gain.toFixed(2), limiter: 'alimiter guard at TP-0.5 dB' },
    measured_final_mix: final
  };
}

// ---------- picture ----------
function renderPicture(plan, outDir, mixWav, vtt, test, artDir) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'othello-narrated-'));
  // art paths: absolute, or relative to the working directory or the repo root, or else looked up by file name in artDir.
  const resolveArt = p => {
    if (path.isAbsolute(p)) return p;
    for (const c of [path.resolve(p), path.join(root, p)]) if (fs.existsSync(c)) return c;
    const byName = path.join(artDir, path.basename(p));
    if (!fs.existsSync(byName)) throw new Error(`art not found: ${p} (looked in ${artDir})`);
    return byName;
  };
  const images = [...new Set(plan.scenes.flatMap(s => s.shots.map(x => x.art_path)))];
  for (const art of images) {   // the book-page frame: cream page, brass rule, dark inlay, painting inside
    const file = path.basename(art);
    run(['-i', resolveArt(art), '-f', 'lavfi', '-i', 'color=c=0x142239:s=1600x900',
      '-filter_complex', '[0:v]scale=1480:808:force_original_aspect_ratio=increase,crop=1480:808[plate];[1:v]drawbox=x=24:y=16:w=1552:h=868:color=0xeee5d2:t=fill,drawbox=x=48:y=38:w=1504:h=824:color=0x937044:t=2,drawbox=x=59:y=49:w=1482:h=810:color=0x1c2a3d:t=fill[book];[book][plate]overlay=60:50[v]',
      '-map', '[v]', '-frames:v', '1', path.join(temp, file)]);
  }
  const list = ['ffconcat version 1.0'];
  const shots = plan.scenes.flatMap(s => s.shots);
  shots.forEach((shot, i) => {
    const frames = Math.round(shot.end_seconds * FPS) - Math.round(shot.start_seconds * FPS);
    const p = path.join(temp, `shot-${String(i + 1).padStart(2, '0')}.mp4`);
    run(['-loop', '1', '-framerate', String(FPS), '-i', path.join(temp, path.basename(shot.art_path)), '-frames:v', String(frames),
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-an', p]);
    list.push(`file '${p}'`);
  });
  const listPath = path.join(temp, 'shots.ffconcat');
  fs.writeFileSync(listPath, list.join('\n') + '\n');
  const picture = path.join(temp, 'picture.mp4');
  run(['-f', 'concat', '-safe', '0', '-i', listPath, '-c:v', 'copy', '-an', picture]);
  const out = path.join(outDir, `${test ? 'TEST-' : ''}Othello-opening-NARRATED.mp4`);
  run(['-i', picture, '-i', mixWav, '-i', vtt, '-map', '0:v:0', '-map', '1:a:0', '-map', '2:s:0',
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-c:s', 'mov_text',
    '-metadata', `title=Othello illustrated opening - narrated${test ? ' - TEST ONLY' : ''}`,
    '-metadata', `comment=Narration ${plan.narration.voice} / ${plan.narration.model}; cuts and captions timed from measured speech`,
    '-metadata:s:a:0', 'language=eng', '-metadata:s:s:0', 'language=eng', '-metadata:s:s:0', 'title=English (exact script)',
    '-disposition:s:0', 'default', '-t', String(plan.total_seconds), '-movflags', '+faststart', out]);
  fs.rmSync(temp, { recursive: true, force: true });
  return path.relative(root, out);
}


// ---------- QA ----------
const normWord = w => w.toLowerCase().replace(/[\u2018\u2019]/g, "'").replace(/[^a-z0-9']/g, '');
function scriptTokens(plan) {
  return plan.scenes.flatMap(s => s.spoken_text_exact.trim().split(/\s+/).flatMap(t => t.split('\u2014')).map(normWord).filter(Boolean));
}
function lcsMap(a, b) {   // returns index map a->b for equal tokens (longest common subsequence)
  const n = a.length, m = b.length, dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const map = new Array(n).fill(-1); let i = 0, j = 0;
  while (i < n && j < m) { if (a[i] === b[j]) { map[i] = j; i++; j++; } else if (dp[i + 1][j] >= dp[i][j + 1]) i++; else j++; }
  return map;
}
function rmsDb(x, a, b, stride = 1, off = 0) {
  let s = 0, n = 0;
  for (let i = a; i < b; i++) { const v = x[i * stride + off]; s += v * v; n++; }
  return n ? 10 * Math.log10(s / n + 1e-12) : null;
}
function runQa(plan, outDir, test, opts) {
  const tag = test ? 'TEST-' : '';
  const res = { generated_at: new Date().toISOString(), test };
  if (!plan.video || !plan.mix) throw new Error('QA needs a timeline from a full render (plan.video/plan.mix missing): run without --stage first');
  const mp4 = path.join(root, plan.video);
  const pr = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:stream_tags=language,title:stream_disposition=default:format=duration,size', '-of', 'json', mp4], { encoding: 'utf8' });
  res.ffprobe = JSON.parse(pr.stdout);
  res.duration_check = { planned_seconds: plan.total_seconds, container_seconds: +Number(res.ffprobe.format.duration).toFixed(3) };
  res.loudness_master_wav = loudness(path.join(root, plan.mix.files.mix));
  res.loudness_mp4_aac = loudness(mp4);
  // per-scene speech-vs-music level over measured speech
  const voice = decodeF32(path.join(root, plan.mix.files.voice), 1);
  const music = decodeF32(path.join(root, plan.mix.files.music), 1);
  const iv = speechIntervals(voice);
  res.speech_vs_music = plan.scenes.map(s => {
    let vs = 0, ms = 0, n = 0;
    for (const [a, b] of iv) {
      const lo = Math.max(a, s.start_seconds), hi = Math.min(b, s.end_seconds);
      if (hi <= lo) continue;
      for (let i = Math.round(lo * SR); i < Math.round(hi * SR); i++) { vs += voice[i] * voice[i]; ms += music[i] * music[i]; n++; }
    }
    const v = 10 * Math.log10(vs / n + 1e-12), m = 10 * Math.log10(ms / n + 1e-12);
    // music level in pauses (>= 0.9 s between speech intervals inside the scene), 100 ms windows: max-min = pumping indicator
    const pauseDb = [];
    // only gaps BETWEEN speech intervals inside the scene; the designed lead-in and tail are excluded
    const inScene = iv.filter(([a, b]) => a >= s.start_seconds && b <= s.end_seconds);
    for (let k = 0; k + 1 < inScene.length; k++) {
      const lo = inScene[k][1], hi = inScene[k + 1][0];
      if (hi - lo < 0.9) continue;
      for (let t = lo + 0.2; t + 0.1 <= hi - 0.2; t += 0.1) pauseDb.push(rmsDb(music, Math.round(t * SR), Math.round((t + 0.1) * SR)));
    }
    const pauseStats = pauseDb.length ? { windows: pauseDb.length, max_dbfs: +Math.max(...pauseDb).toFixed(1), min_dbfs: +Math.min(...pauseDb).toFixed(1), swing_db: +(Math.max(...pauseDb) - Math.min(...pauseDb)).toFixed(1) } : null;
    return { scene: s.scene, clip_id: s.clip_id, speech_seconds: +(n / SR).toFixed(2), voice_rms_dbfs: +v.toFixed(1), music_rms_dbfs_under_speech: +m.toFixed(1), voice_minus_music_db: +(v - m).toFixed(1), music_in_pauses: pauseStats };
  });
  // captions vs alignment (construction check)
  const vttText = fs.readFileSync(path.join(outDir, `${tag}Othello-opening-NARRATED.vtt`), 'utf8');
  const toSec = x => { const [h, m, s] = x.split(':'); return +h * 3600 + +m * 60 + +s; };
  const vttStarts = [...vttText.matchAll(/(\d\d:\d\d:\d\d\.\d\d\d) --> (\d\d:\d\d:\d\d\.\d\d\d)/g)].map(m => toSec(m[1]));
  const errs = plan.captions.map((c, k) => Math.abs(vttStarts[k] + CAPTION_LEAD - c.first_word_film));
  res.captions_vs_alignment = { cues: vttStarts.length, max_abs_error_seconds: +Math.max(...errs).toFixed(3), note: 'cue start + lead vs aligned first-word time; checks rendering, not alignment accuracy' };
  const lines = vttText.split('\n').filter(l => l && !/-->|^\d+$|^WEBVTT|^NOTE/.test(l)).map(l => l.replace(/<[^>]+>/g, ''));
  res.caption_lines = { count: lines.length, max_chars: Math.max(...lines.map(l => l.length)), exact_text: lines.join(' ') === plan.scenes.map(s => s.spoken_text_exact.trim().split(/\s+/).join(' ')).join(' ') };
  // frames at every cut + 0.5 s
  const fdir = path.join(outDir, `${tag}frames`); fs.mkdirSync(fdir, { recursive: true });
  res.frames = plan.scenes.flatMap(s => s.shots).map((x, k) => {
    const f = path.join(fdir, `cut-${String(k + 1).padStart(2, '0')}-shot${String(x.storyboard_shot).padStart(2, '0')}-${path.basename(x.art_path).replace(/\.(png|jpe?g)$/i, '')}.jpg`);
    run(['-ss', String(x.start_seconds + 0.5), '-i', mp4, '-frames:v', '1', '-vf', 'scale=800:-2', '-q:v', '4', f]);
    return { cut: k + 1, storyboard_shot: x.storyboard_shot, at_seconds: +(x.start_seconds + 0.5).toFixed(3), expected_art: path.basename(x.art_path), frame: path.relative(root, f) };
  });
  // final-mix transcription per scene (tools/narration/verify_take.py, no script given) -> word diff vs exact script
  if (opts.transcribe !== false) {
    if (!opts.manifest) throw new Error('the final-mix transcription needs --manifest (or pass --no-transcribe)');
    const sdir = path.join(outDir, `${tag}qa-segments`); fs.mkdirSync(sdir, { recursive: true });
    const segs = plan.scenes.map(s => {
      const f = path.join(sdir, `${s.clip_id}-final-mix.wav`);
      run(['-ss', String(s.start_seconds), '-t', String(s.duration_seconds + (s.scene < plan.scenes.length ? 0.4 : 0)), '-i', path.join(root, plan.mix.files.mix), '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', f]);
      return [s.clip_id, f];
    });
    res.final_mix_transcription = segs.map(([id, f]) => {
      const r = spawnSync('python3', [path.join(root, 'tools/narration/verify_take.py'), '--manifest', opts.manifest, id, f], { encoding: 'utf8' });
      const j = f.replace(/\.wav$/, '.transcript.json');
      if (!fs.existsSync(j)) return { clip_id: id, error: (r.stderr || '').split('\n').filter(l => !/Warning|warn/.test(l)).slice(-3).join(' ') };
      const t = JSON.parse(fs.readFileSync(j, 'utf8'));
      return { clip_id: id, exact_match: t.exact_match, script_words: t.script_words, heard_words: t.heard_words, differences: t.differences, transcript_file: path.basename(j) };
    });
  }
  // independent timing check: local whisper word timestamps on the full mix vs caption starts
  if (opts.whisper) {
    const wdir = path.join(outDir, `${tag}qa-whisper`); fs.mkdirSync(wdir, { recursive: true });
    const wav = path.join(wdir, 'final-mix-16k.wav');
    run(['-i', path.join(root, plan.mix.files.mix), '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav]);
    const wr = spawnSync(opts.whisperBin || 'whisper', [wav, '--model', opts.whisper, '--word_timestamps', 'True', '--output_format', 'json', '--output_dir', wdir, '--language', 'en', '--fp16', 'False'], { encoding: 'utf8', maxBuffer: 1 << 28 });
    const jf = path.join(wdir, 'final-mix-16k.json');
    if (fs.existsSync(jf)) {
      const hw = JSON.parse(fs.readFileSync(jf, 'utf8')).segments.flatMap(s => s.words || []).flatMap(w => {
        const parts = w.word.split(/[\u2014-]/).map(normWord).filter(Boolean);
        return parts.map(p => ({ w: p, start: w.start, end: w.end }));
      });
      // script tokens with caption membership
      const toks = [];
      plan.scenes.forEach(s => s.spoken_text_exact.trim().split(/\s+/).forEach((t, wi) => t.split('\u2014').map(normWord).filter(Boolean).forEach((p, pi) => toks.push({ w: p, clip_id: s.clip_id, wi, pi }))));
      const map = lcsMap(toks.map(t => t.w), hw.map(h => h.w));
      const capErr = plan.captions.map(c => {
        const k = toks.findIndex(t => t.clip_id === c.clip_id && t.wi === c.word_range[0] && t.pi === 0);
        const j = map[k];
        return j >= 0 ? { cue_start: c.start, first_word: toks[k].w, whisper_start: hw[j].start, error: +(c.start + CAPTION_LEAD - hw[j].start).toFixed(3) } : { cue_start: c.start, first_word: toks[k].w, whisper_start: null };
      });
      const measured = capErr.filter(e => e.whisper_start !== null);
      const abs = measured.map(e => Math.abs(e.error)).sort((a, b) => a - b);
      res.captions_vs_whisper = {
        model: opts.whisper, script_tokens: toks.length, whisper_tokens: hw.length, matched_tokens: map.filter(x => x >= 0).length,
        cues_checked: measured.length, cues_unmatched: capErr.length - measured.length,
        max_abs_error_seconds: abs.length ? abs[abs.length - 1] : null, median_abs_error_seconds: abs.length ? abs[Math.floor(abs.length / 2)] : null,
        p90_abs_error_seconds: abs.length ? abs[Math.floor(abs.length * 0.9)] : null, per_cue: capErr
      };
    } else res.captions_vs_whisper = { error: (wr.stderr || '').slice(-400) };
  }
  fs.writeFileSync(path.join(outDir, `${tag}qa-results.json`), JSON.stringify(res, null, 2) + '\n');
  return res;
}

// ---------- main ----------
function parseArgs(argv) {
  const o = { stage: 'all', clips: {}, test: false, scenes: null, artDir: path.join(root, 'assets/paintings'),
    manifest: process.env.OTHELLO_MANIFEST && path.resolve(process.env.OTHELLO_MANIFEST),
    storyboard: process.env.OTHELLO_STORYBOARD && path.resolve(process.env.OTHELLO_STORYBOARD),
    cueSheet: process.env.OTHELLO_CUESHEET && path.resolve(process.env.OTHELLO_CUESHEET) };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--stage') o.stage = argv[++i];
    else if (a === '--test') o.test = true;
    else if (a === '--scenes') o.scenes = argv[++i].split(',').map(Number);
    else if (a === '--clip') { const [k, v] = argv[++i].split('='); o.clips[k] = path.resolve(v); }
    else if (a === '--manifest') o.manifest = path.resolve(argv[++i]);
    else if (a === '--storyboard') o.storyboard = path.resolve(argv[++i]);
    else if (a === '--cue-sheet') o.cueSheet = path.resolve(argv[++i]);
    else if (a === '--alignment') o.alignment = path.resolve(argv[++i]);
    else if (a === '--narration') o.narration = path.resolve(argv[++i]);
    else if (a === '--out') o.out = path.resolve(argv[++i]);
    else if (a === '--art-dir') o.artDir = path.resolve(argv[++i]);
    else if (a === '--whisper') o.whisper = argv[++i];
    else if (a === '--whisper-bin') o.whisperBin = argv[++i];
    else if (a === '--no-transcribe') o.transcribe = false;
    else if (a === '--fitted') o.fitted = path.resolve(argv[++i]);
    else if (a === '--impact-phrase') o.impactPhrase = argv[++i];
    else if (a === '--art-map') o.artMap = JSON.parse(fs.readFileSync(path.resolve(argv[++i]), 'utf8'));
    else throw new Error(`unknown arg ${a}`);
  }
  const need = o.stage === 'qa' ? ['out'] : ['manifest', 'storyboard', 'cueSheet', 'narration', 'alignment', 'out'];
  const missing = need.filter(k => !o[k]);
  if (missing.length) {
    console.error(`missing: ${missing.map(k => '--' + k.replace(/[A-Z]/g, c => '-' + c.toLowerCase())).join(', ')}\n` +
      'usage: node tools/film/render-narrated.js --manifest m.json --storyboard sb.json --cue-sheet cues.json --narration <dir> --alignment <dir> --out <dir> [--stage plan|score|mix|qa] [--art-dir <dir>] [--art-map map.json] [--whisper <model>] [--no-transcribe] [--impact-phrase "..."]');
    process.exit(2);
  }
  return o;
}

if (require.main === module) {
  const opts = parseArgs(process.argv.slice(2));
  fs.mkdirSync(opts.out, { recursive: true });
  const tag = opts.test ? 'TEST-' : '';
  const timelinePath0 = path.join(opts.out, `${tag}narrated-timeline.json`);
  if (opts.stage === 'qa') {
    const plan = JSON.parse(fs.readFileSync(timelinePath0, 'utf8'));
    const r = runQa(plan, opts.out, opts.test, opts);
    console.log(JSON.stringify({ stage: 'qa', duration: r.duration_check, loud: r.loudness_mp4_aac, svm: r.speech_vs_music.map(x => x.voice_minus_music_db), cap: r.captions_vs_alignment, whisper: r.captions_vs_whisper && { max: r.captions_vs_whisper.max_abs_error_seconds, median: r.captions_vs_whisper.median_abs_error_seconds, p90: r.captions_vs_whisper.p90_abs_error_seconds, unmatched: r.captions_vs_whisper.cues_unmatched }, transcription: (r.final_mix_transcription || []).map(t => [t.clip_id, t.exact_match, (t.differences || []).length]) }));
    process.exit(0);
  }
  const plan = buildPlan(opts);
  const timelinePath = path.join(opts.out, `${tag}narrated-timeline.json`);
  const vtt = path.join(opts.out, `${tag}Othello-opening-NARRATED.vtt`);
  writeVtt(plan, vtt, opts.test);
  fs.writeFileSync(timelinePath, JSON.stringify(plan, null, 2) + '\n');
  console.log(JSON.stringify({ stage: 'plan', total_seconds: plan.total_seconds, scenes: plan.scenes.map(s => [s.clip_id, s.duration_seconds]), shots: plan.scenes.reduce((a, s) => a + s.shots.length, 0), captions: plan.captions.length, warnings: plan.warnings }));
  if (opts.stage === 'plan') process.exit(0);

  const fittedDir = opts.test ? path.join(opts.out, 'fitted-test') : (opts.fitted || path.join(opts.out, 'fitted'));
  const fitArgs = [path.join(root, 'tools/score/fit-score.js'), '--timeline', timelinePath, '--alignment', opts.alignment, '--out', fittedDir, '--manifest', opts.manifest];
  if (opts.impactPhrase) fitArgs.push('--impact-phrase', opts.impactPhrase);
  const fs_ = spawnSync('node', fitArgs, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });
  if (fs_.status !== 0) throw new Error('fit-score failed');
  console.log(fs_.stdout.trim().split('\n').pop());
  const fitted = path.join(fittedDir, 'Othello-score-fitted-full.flac');
  plan.score = { fitted_full: path.relative(root, fitted), cue_sheet: path.relative(root, path.join(fittedDir, 'fitted-cue-sheet.json')) };
  if (opts.stage === 'score') { fs.writeFileSync(timelinePath, JSON.stringify(plan, null, 2) + '\n'); process.exit(0); }

  plan.mix = mixAudio(plan, opts.out, fitted, opts.test);
  fs.writeFileSync(timelinePath, JSON.stringify(plan, null, 2) + '\n');
  console.log(JSON.stringify({ stage: 'mix', ...plan.mix.measured_final_mix }));
  if (opts.stage === 'mix') process.exit(0);

  plan.video = renderPicture(plan, opts.out, path.join(root, plan.mix.files.mix), vtt, opts.test, opts.artDir);
  fs.writeFileSync(timelinePath, JSON.stringify(plan, null, 2) + '\n');
  console.log(JSON.stringify({ stage: 'picture', video: plan.video, total_seconds: plan.total_seconds }));
}

module.exports = { resolvePhrase, loadAlignment, wordSpans, run, ffprobeDuration, loudness, decodeF32, encodeF32, SR, FPS };
