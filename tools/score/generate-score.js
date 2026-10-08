/* Original instrumental score sketches: one bed per scene, synthesised from a sine table (pads, low pulse, filtered
 * air, sparse low impacts, bells) with a seeded PRNG. No speech, samples, loops or third-party music.
 *
 * Usage:
 *   node tools/score/generate-score.js --out <dir>                       # the published sketch: 8 beds, 234 s
 *   node tools/score/generate-score.js --out <dir> --manifest <recording manifest.json> \
 *        [--anchors anchors.json --cue-sheet <dir>/cue-sheet.json]
 * Writes <out>/stems/<clip_id>-original-score-sketch.flac and <out>/bed-demo.m4a (the stems in order).
 * Without --manifest the scene lengths are the published sketch's (41, 29, 30, 22, 29, 26, 30, 27 s), so the run
 * reproduces assets/score-sketch.m4a. With --manifest each bed lasts (words / 140 wpm) * 60 + 4 s: an estimate,
 * not a synchronisation; tools/score/fit-score.js refits the beds to measured narration.
 * --anchors is a JSON array with one array of exact spoken phrases per scene; every phrase must occur in that
 * scene's spoken_text_exact. They are written to the cue sheet, which tools/film/render-narrated.js reads.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const outDir = path.resolve(opt('--out') || 'score');
const manifestPath = opt('--manifest') || process.env.OTHELLO_MANIFEST;
const anchorsPath = opt('--anchors');
const cueSheetPath = opt('--cue-sheet');
const manifest = manifestPath ? JSON.parse(fs.readFileSync(path.resolve(manifestPath), 'utf8')) : null;
const anchors = anchorsPath ? JSON.parse(fs.readFileSync(path.resolve(anchorsPath), 'utf8')) : null;

const RATE = 48000;
const TABLE = new Float32Array(8192);
for (let i = 0; i < TABLE.length; i++) TABLE[i] = Math.sin(2 * Math.PI * i / TABLE.length);
const semitone = n => 440 * Math.pow(2, (n - 69) / 12);
const tone = (f, t, phase = 0) => TABLE[Math.floor((((f * t + phase) % 1 + 1) % 1) * TABLE.length)];
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const smooth = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
const run = a => {
  const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...a], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr || `ffmpeg exited ${r.status}`);
};
// Per scene: chord a fading to chord b (MIDI notes), bass note, pad density, impacts and bells at fractions of the bed.
const scenes = [
  { a: [53, 57, 60, 64], b: [50, 53, 57, 64], bass: 38, density: .65, booms: [.48], bells: [.18, .78] },
  { a: [50, 57, 60], b: [48, 53, 57], bass: 38, density: .5, booms: [.2, .7], bells: [.5] },
  { a: [53, 57, 60, 64], b: [53, 57, 60, 63], bass: 41, density: .55, booms: [], bells: [.15, .74] },
  { a: [50, 53, 57], b: [50, 53, 56], bass: 38, density: .45, booms: [.82], bells: [.12] },
  { a: [50, 53, 57], b: [51, 54, 58], bass: 38, density: .36, booms: [.68], bells: [] },
  { a: [43, 50, 58], b: [50, 53, 57], bass: 31, density: .68, booms: [.34, .72], bells: [.12] },
  { a: [50, 57], b: [50, 57, 64], bass: 38, density: .22, booms: [], bells: [.25, .76] },
  { a: [50, 53, 57, 64], b: [50, 53, 57], bass: 38, density: .48, booms: [.08], bells: [.3] }
];
const SKETCH_SECONDS = [41, 29, 30, 22, 29, 26, 30, 27];
if (manifest && manifest.scenes.length !== scenes.length) throw new Error(`the palette has ${scenes.length} scenes, the manifest ${manifest.scenes.length}`);
const clipIds = manifest ? manifest.scenes.map(s => s.clip_id) : scenes.map((_, i) => `vo_intro_${String(i + 1).padStart(2, '0')}`);
const scoreDurations = manifest
  ? manifest.scenes.map(s => Math.round(s.spoken_text_exact.trim().split(/\s+/).length / 140 * 60 + 4))
  : SKETCH_SECONDS;
if (anchors) {
  if (!manifest) throw new Error('--anchors needs --manifest to check the phrases against the script');
  manifest.scenes.forEach((s, i) => { for (const phrase of anchors[i] || []) if (!s.spoken_text_exact.includes(phrase)) throw new Error(`scene ${i + 1}: anchor not in the script: ${phrase}`); });
}
const cueSheet = clipIds.map((clip_id, i) => ({
  scene: i + 1, clip_id, score_file: `stems/${clip_id}-original-score-sketch.flac`,
  spoken_anchors: ((anchors && anchors[i]) || []).map(phrase => ({ phrase, recorded_cue_seconds: null })),
  score_sketch_duration_seconds: scoreDurations[i],
  note: 'Score sketch length is an estimate, not a synchronization claim. fit-score.js refits it to measured narration.'
}));
if (cueSheetPath) {
  fs.mkdirSync(path.dirname(path.resolve(cueSheetPath)), { recursive: true });
  fs.writeFileSync(path.resolve(cueSheetPath), JSON.stringify({
    status: 'original instrumental sketches; anchors not yet measured',
    spoken_text_source: manifest ? path.basename(manifestPath) : null,
    scenes: cueSheet
  }, null, 2) + '\n');
}

fs.mkdirSync(path.join(outDir, 'stems'), { recursive: true });
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'othello-score-'));
const stemPaths = [];
function writeScene(i) {
  const cfg = scenes[i], duration = scoreDurations[i], frames = duration * RATE;
  const wavPath = path.join(temp, `scene-${i + 1}.wav`);
  const fd = fs.openSync(wavPath, 'w');
  const header = Buffer.alloc(44);
  header.write('RIFF', 0); header.writeUInt32LE(36 + frames * 4, 4); header.write('WAVEfmt ', 8);
  header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20); header.writeUInt16LE(2, 22);
  header.writeUInt32LE(RATE, 24); header.writeUInt32LE(RATE * 4, 28);
  header.writeUInt16LE(4, 32); header.writeUInt16LE(16, 34); header.write('data', 36);
  header.writeUInt32LE(frames * 4, 40); fs.writeSync(fd, header);
  let seed = (0x6d2b79f5 ^ (i * 987654321)) >>> 0, air = 0;
  const rand = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return (seed >>> 0) / 4294967296 * 2 - 1; };
  const chunk = Buffer.alloc(4096 * 4);
  for (let start = 0; start < frames; start += 4096) {
    const count = Math.min(4096, frames - start);
    for (let j = 0; j < count; j++) {
      const t = (start + j) / RATE, p = t / duration;
      const edge = smooth(t / 2.2) * smooth((duration - t) / 3.2);
      const change = smooth((p - .43) / .2);
      const breath = .8 + .2 * tone(.07, t);
      let left = 0, right = 0;
      for (const [chord, weight] of [[cfg.a, 1 - change], [cfg.b, change]]) {
        for (let n = 0; n < chord.length; n++) {
          const f = semitone(chord[n]), phase = n * .137;
          const signal = tone(f, t, phase) + .24 * tone(2 * f, t, phase) + .07 * tone(3 * f, t, phase);
          const wide = tone(f * 1.0016, t, phase + .29) + .2 * tone(2 * f * 1.0016, t, phase + .29);
          left += weight * signal / chord.length;
          right += weight * wide / chord.length;
        }
      }
      const slowPulse = .77 + .23 * Math.pow(Math.max(0, tone(.18, t)), 2);
      const bass = tone(semitone(cfg.bass), t) * slowPulse;
      air = .993 * air + .007 * rand();
      let boom = 0;
      for (const q of cfg.booms) {
        const u = t - q * duration;
        if (u >= 0 && u < 2) boom += Math.exp(-3.8 * u) * (tone(65 - 20 * u, u) * .62 + rand() * .035 * Math.exp(-15 * u));
      }
      let bell = 0;
      for (const q of cfg.bells) {
        const u = t - q * duration;
        if (u >= 0 && u < 5) bell += .13 * Math.exp(-.83 * u) * (tone(587.33, u) + .3 * tone(880, u));
      }
      const padLevel = .13 * cfg.density * breath * edge;
      left = padLevel * left + .065 * bass * edge + .055 * boom + bell * .6 + air * .018 * edge;
      right = padLevel * right + .065 * bass * edge + .055 * boom + bell * .72 + air * .02 * edge;
      chunk.writeInt16LE(Math.round(clamp(left, -.95, .95) * 32767), j * 4);
      chunk.writeInt16LE(Math.round(clamp(right, -.95, .95) * 32767), j * 4 + 2);
    }
    fs.writeSync(fd, chunk, 0, count * 4);
  }
  fs.closeSync(fd);
  const target = path.join(outDir, cueSheet[i].score_file);
  run(['-i', wavPath, '-c:a', 'flac', '-compression_level', '5', target]);
  stemPaths.push(target);
  console.log(`scene ${i + 1}/${scenes.length}: ${duration}s`);
}
for (let i = 0; i < scenes.length; i++) writeScene(i);
const listPath = path.join(temp, 'stems.ffconcat');
fs.writeFileSync(listPath, 'ffconcat version 1.0\n' + stemPaths.map(p => `file '${p}'`).join('\n') + '\n');
run(['-f', 'concat', '-safe', '0', '-i', listPath, '-c:a', 'aac', '-b:a', '192k',
  '-movflags', '+faststart', path.join(outDir, 'bed-demo.m4a')]);
fs.rmSync(temp, { recursive: true, force: true });
console.log(JSON.stringify({ scenes: scenes.length, stems: stemPaths.length, estimated_seconds: scoreDurations.reduce((a, b) => a + b, 0), voice_included: false }));
