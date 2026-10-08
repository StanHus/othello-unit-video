/* Fit the original score to MEASURED narration.
 *
 * Same synthesis palette as generate-score.js (sine table pads, low pulse, filtered air, sparse impacts, bells; no
 * samples), but every bed is regenerated at its planned scene length and each musical move in the cue plan below
 * (INTENT) is placed at the measured time of its spoken anchor (from the word alignment), instead of at a fixed
 * fraction of an estimated length. Beds overlap the next scene by OVERFLOW seconds so scene changes crossfade
 * instead of dipping to silence.
 *
 * Usage: node tools/score/fit-score.js --timeline <out>/narrated-timeline.json --alignment <alignment dir> \
 *          --out <fitted dir> --manifest <recording manifest.json> [--impact-phrase "<exact phrase in scene 8>"]
 * (OTHELLO_MANIFEST and OTHELLO_S8_IMPACT can replace --manifest and --impact-phrase.)
 * The timeline comes from tools/film/render-narrated.js --stage plan; its music anchors come from the cue sheet.
 * The cue plan expects, per scene, at least this many cue-sheet anchors, in spoken order: 4, 3, 3, 2, 3, 2, 3, 3.
 * Writes <out>/<clip_id>-fitted.flac, <out>/Othello-score-fitted-full.flac, <out>/fitted-cue-sheet.json.
 * Does not touch generate-score.js outputs (stems/, cue sheet, the demo bed).
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { resolvePhrase, loadAlignment, encodeF32, SR } = require('../film/render-narrated.js');

const root = path.resolve(__dirname, '..', '..');
const args = process.argv.slice(2);
const arg = (k, d) => { const i = args.indexOf(k); return i >= 0 ? path.resolve(args[i + 1]) : d; };
const rawArg = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const timelinePath = arg('--timeline');
const alignmentDir = arg('--alignment');
const outDir = arg('--out');
const manifestPath = arg('--manifest', process.env.OTHELLO_MANIFEST ? path.resolve(process.env.OTHELLO_MANIFEST) : undefined);
if (!timelinePath || !alignmentDir || !outDir || !manifestPath) {
  console.error('usage: fit-score.js --timeline <timeline.json> --alignment <dir> --out <dir> --manifest <manifest.json> [--impact-phrase "..."]');
  process.exit(2);
}
const IMPACT_PHRASE = rawArg('--impact-phrase') || process.env.OTHELLO_S8_IMPACT || null;
const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf8'));
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const NEEDED_ANCHORS = [4, 3, 3, 2, 3, 2, 3, 3];

const TABLE = new Float32Array(8192);
for (let i = 0; i < TABLE.length; i++) TABLE[i] = Math.sin(2 * Math.PI * i / TABLE.length);
const semitone = n => 440 * Math.pow(2, (n - 69) / 12);
const tone = (f, t, phase = 0) => TABLE[Math.floor((((f * t + phase) % 1 + 1) % 1) * TABLE.length)];
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const smooth = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
const OVERFLOW = 2.0;

// Palette per scene: identical chords/bass/density to generate-score.js.
const PALETTE = [
  { a: [53, 57, 60, 64], b: [50, 53, 57, 64], bass: 38, density: .65 },
  { a: [50, 57, 60], b: [48, 53, 57], bass: 38, density: .5 },
  { a: [53, 57, 60, 64], b: [53, 57, 60, 63], bass: 41, density: .55 },
  { a: [50, 53, 57], b: [50, 53, 56], bass: 38, density: .45 },
  { a: [50, 53, 57], b: [51, 54, 58], bass: 38, density: .36 },
  { a: [43, 50, 58], b: [50, 53, 57], bass: 31, density: .68 },
  { a: [50, 57], b: [50, 57, 64], bass: 38, density: .22 },
  { a: [50, 53, 57, 64], b: [50, 53, 57], bass: 38, density: .48 }
];

/* The cue plan: musical intent per scene, bound to measured anchor times.
 * A[k] = cue-sheet anchor k of the scene (scene-relative start/end seconds). x(phrase) resolves an extra exact phrase. */
const INTENT = [
  (A, d) => ({ why: 'low D + warm fifth after a breath of near-silence; brighten at anchor 2; darken only after anchor 3, with a low impact after its last word; thin at anchor 4',
    fadeIn: [Math.max(0, A[0].start - 1.4), 1.8], bells: [A[1].start], change: [A[2].end, 2.5], booms: [[A[2].end + 0.12, 1]],
    thins: [[A[3].start - 0.3, A[3].end + 0.6, 0.45]] }),
  (A, d) => ({ why: 'measured low pulse from anchor 1; broader air at anchor 2; pull back for anchor 3',
    pulse: [[A[0].start, A[1].start, 0.35]], change: [A[1].start, 2.5], air: [[A[1].start, A[1].start + 7, 2.2]], booms: [[A[1].start - 0.05, 0.7]],
    thins: [[A[2].start - 0.2, A[2].end + 0.4, 0.5]], bells: [A[2].end + 0.25] }),
  (A, d) => ({ why: 'human, luminous harmony beneath anchors 1 and 2; slight unease from anchor 3',
    bells: [A[0].start, A[1].start], change: [A[2].start, 2.0] }),
  (A, d) => ({ why: 'restrained, almost ceremonial pulse; a low accent follows anchor 2, leaving a breath',
    pulse: [[0, d, 0.3]], bells: [A[0].start], change: [A[1].start, 1.8], booms: [[A[1].end + 0.25, 0.8]] }),
  (A, d) => ({ why: 'score nearly away at anchor 1; returns as low dissonance under anchor 2; thin again under anchor 3, no impact',
    thins: [[A[0].start - 0.4, A[0].end + 0.3, 0.12], [A[2].start - 0.2, A[2].end + 0.5, 0.6]], change: [A[1].start, 1.5] }),
  (A, d) => ({ why: 'slow scale-up from anchor 1, with a low impact after it; step back at anchor 2',
    change: [A[0].start, 3.0], swell: [A[0].start, A[1].start, 1.25], booms: [[A[0].end + 0.15, 0.6]], thins: [[A[1].start - 0.3, A[1].end + 0.8, 0.4]] }),
  (A, d) => ({ why: 'minimal sustained tone and faint shimmer, no pulse; the quietest bed, held under the voice',
    level: 0.8, noPulse: true, bells: [[A[0].start, 0.5], [A[2].start, 0.5]], change: [A[1].start, 3.0] }),
  (A, d, x) => {
    const hit = IMPACT_PHRASE ? x(IMPACT_PHRASE) : null;
    return { why: 'return to the opening motif, unresolved; a quiet impact after the impact phrase (if given); thin from anchor 3, fade out after it and leave silence',
      bells: [A[0].start], booms: hit ? [[hit.end + 0.15, 0.55]] : [], change: [A[1].start, 2.5], thins: [[A[2].start - 0.3, d, 0.55]],
      fadeOut: [A[2].end + 0.5, 3.5], booms_sources: hit ? { [IMPACT_PHRASE]: hit } : {} };
  }
];

function synthScene(i, duration, ev, seedBase) {
  const cfg = PALETTE[i];
  const last = i === PALETTE.length - 1 || ev.isLast;
  const len = duration + (last ? 0 : OVERFLOW);
  const frames = Math.round(len * SR);
  const out = new Float32Array(frames * 2);
  let seed = (0x6d2b79f5 ^ (seedBase * 987654321)) >>> 0, air = 0;
  const rand = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return (seed >>> 0) / 4294967296 * 2 - 1; };
  const [fiStart, fiLen] = ev.fadeIn || [0, 1.5];
  const [foStart, foLen] = ev.fadeOut || [len - 2.8, 2.8];
  const [chAt, chLen] = ev.change || [len * .43, 2.4];
  const bells = (ev.bells || []).map(b => Array.isArray(b) ? b : [b, 1]);
  const booms = ev.booms || [];
  const thinAt = t => {
    let g = 1;
    for (const [a, b, lvl] of ev.thins || []) {
      const inn = smooth((t - (a - 0.6)) / 0.6) * (1 - smooth((t - b) / 0.8));
      g = Math.min(g, 1 - (1 - lvl) * inn);
    }
    return g;
  };
  for (let j = 0; j < frames; j++) {
    const t = j / SR;
    const edge = smooth((t - fiStart) / fiLen) * (1 - smooth((t - foStart) / foLen));
    const change = smooth((t - chAt) / chLen);
    const breath = .8 + .2 * tone(.07, t);
    let left = 0, right = 0;
    for (const [chord, weight] of [[cfg.a, 1 - change], [cfg.b, change]]) {
      if (weight < 1e-4) continue;
      for (let n = 0; n < chord.length; n++) {
        const f = semitone(chord[n]), phase = n * .137;
        const signal = tone(f, t, phase) + .24 * tone(2 * f, t, phase) + .07 * tone(3 * f, t, phase);
        const wide = tone(f * 1.0016, t, phase + .29) + .2 * tone(2 * f * 1.0016, t, phase + .29);
        left += weight * signal / chord.length;
        right += weight * wide / chord.length;
      }
    }
    let pulseDepth = ev.noPulse ? 0 : .23;
    for (const [a, b, dep] of ev.pulse || []) if (t >= a && t < b) pulseDepth = Math.max(pulseDepth, dep);
    const slowPulse = (1 - pulseDepth) + pulseDepth * Math.pow(Math.max(0, tone(.18, t)), 2);
    const bass = tone(semitone(cfg.bass), t) * (ev.noPulse ? .85 : slowPulse);
    air = .993 * air + .007 * rand();
    let airGain = 1;
    for (const [a, b, g] of ev.air || []) airGain = Math.max(airGain, 1 + (g - 1) * smooth((t - a) / 1.5) * (1 - smooth((t - (b - 2)) / 2)));
    let boom = 0;
    for (const [q, g] of booms) {
      const u = t - q;
      if (u >= 0 && u < 2) boom += g * Math.exp(-3.8 * u) * (tone(65 - 20 * u, u) * .62 + rand() * .035 * Math.exp(-15 * u));
    }
    let bell = 0;
    for (const [q, g] of bells) {
      const u = t - q;
      if (u >= 0 && u < 5) bell += g * .13 * Math.exp(-.83 * u) * (tone(587.33, u) + .3 * tone(880, u));
    }
    let swell = 1;
    if (ev.swell) { const [a, b, g] = ev.swell; swell = 1 + (g - 1) * smooth((t - a) / Math.max(0.5, b - a)); }
    const thin = thinAt(t), level = ev.level || 1;
    const padLevel = .13 * cfg.density * breath * edge * thin * swell * level;
    left = padLevel * left + .065 * bass * edge * thin * level + .055 * boom * edge + bell * .6 * edge * level + air * .018 * edge * airGain * level;
    right = padLevel * right + .065 * bass * edge * thin * level + .055 * boom * edge + bell * .72 * edge * level + air * .02 * edge * airGain * level;
    out[2 * j] = clamp(left, -.95, .95);
    out[2 * j + 1] = clamp(right, -.95, .95);
  }
  return out;
}

fs.mkdirSync(outDir, { recursive: true });
const total = timeline.total_seconds, N = Math.round(total * SR);
const full = new Float32Array(N * 2);
const sheet = [];
timeline.scenes.forEach((s, k) => {
  const i = s.scene - 1;
  const ms = manifest.scenes[i];
  const al = loadAlignment(alignmentDir, s.clip_id, ms.spoken_text_exact);
  const toScene = t => s.voice.scene_offset_seconds + (t - s.voice.trim_start_seconds);
  const A = s.music_anchors.map(a => ({ phrase: a.phrase, start: a.scene_start_seconds, end: a.scene_end_seconds }));
  if (A.length < NEEDED_ANCHORS[i]) throw new Error(`scene ${s.scene}: the cue plan needs ${NEEDED_ANCHORS[i]} cue-sheet anchors, the timeline has ${A.length}`);
  const extra = {};
  const x = phrase => { const r = resolvePhrase(al, phrase); extra[phrase] = r; return { start: toScene(r.start), end: toScene(r.end) }; };
  const ev = INTENT[i](A, s.duration_seconds, x);
  ev.isLast = k === timeline.scenes.length - 1;
  const bed = synthScene(i, s.duration_seconds, ev, i);
  const file = path.join(outDir, `${s.clip_id}-fitted.flac`);
  encodeF32(bed, 2, file, 'flac');
  const at = Math.round(s.start_seconds * SR);
  for (let j = 0; j < bed.length / 2 && at + j < N; j++) { full[2 * (at + j)] += bed[2 * j]; full[2 * (at + j) + 1] += bed[2 * j + 1]; }
  const r3 = v => Array.isArray(v) ? v.map(r3) : (typeof v === 'number' ? +v.toFixed(3) : v);
  const { why, booms_sources, isLast, ...events } = ev;
  sheet.push({
    scene: s.scene, clip_id: s.clip_id, file: path.relative(root, file), film_start_seconds: s.start_seconds,
    scene_duration_seconds: s.duration_seconds, bed_length_seconds: +(bed.length / 2 / SR).toFixed(3), overflow_into_next_seconds: ev.isLast ? 0 : OVERFLOW,
    intent: why,
    measured_anchors: s.music_anchors.map(a => ({ phrase: a.phrase, scene_start_seconds: a.scene_start_seconds, scene_end_seconds: a.scene_end_seconds, source: a.source })),
    extra_measured_phrases: Object.fromEntries(Object.entries(extra).map(([p, r]) => [p, { scene_start_seconds: +toScene(r.start).toFixed(3), scene_end_seconds: +toScene(r.end).toFixed(3), word_range: r.word_range }])),
    events_scene_seconds: Object.fromEntries(Object.entries(events).map(([k2, v]) => [k2, r3(v)]))
  });
});
let peak = 0;
for (const v of full) peak = Math.max(peak, Math.abs(v));
const fullFile = path.join(outDir, 'Othello-score-fitted-full.flac');
encodeF32(full, 2, fullFile, 'flac');
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
fs.writeFileSync(path.join(outDir, 'fitted-cue-sheet.json'), JSON.stringify({
  status: timeline.status.startsWith('TEST') ? 'TEST-ONLY' : 'fitted to measured narration; original synthesis, no samples',
  source_timeline: path.relative(root, timelinePath), synthesis: 'palette and voices copied from tools/score/generate-score.js',
  sample_rate: SR, total_seconds: total, full_bed: path.relative(root, fullFile), full_bed_sha256: sha(fullFile), full_bed_peak: +peak.toFixed(4),
  deviations_from_sketch: ['scene 5 impact removed so the voice leads', IMPACT_PHRASE ? 'scene 8 impact moved to follow the impact phrase' : 'scene 8 impact removed (no impact phrase given)', 'beds crossfade over 2 s instead of fading to silence at each scene change'],
  scenes: sheet
}, null, 2) + '\n');
console.log(JSON.stringify({ stage: 'score', scenes: sheet.length, total_seconds: total, peak: +peak.toFixed(3), out: path.relative(root, outDir) }));
