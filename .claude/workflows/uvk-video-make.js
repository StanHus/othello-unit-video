export const meta = {
  name: 'uvk-video-make',
  description: 'Build a unit video: script check, verified narration, paintings and plates, render with QA, shot audit, QA record',
  whenToUse: 'A unit-video project outside this repository with a recording manifest, the script as text, a storyboard and a cue sheet; pass absolute paths in args',
  phases: [
    { title: 'Script', detail: 'prove the manifest is the script, word for word' },
    { title: 'Narration', detail: 'one clip at a time, verified twice, aligned, pace measured' },
    { title: 'Pictures', detail: 'paintings, then the plates built over them, every image checked by eye' },
    { title: 'Render', detail: 'plan, render and QA against the acceptance list' },
    { title: 'Audit', detail: 'per-shot test by independent judges' },
    { title: 'Report', detail: 'QA record and open items' },
  ],
}

// Run from the root of this repository. Every path in args is absolute; the project lives outside the repository and
// every output goes under it.
// args: {
//   project, manifest, script_text,          the project folder, its recording manifest, the script as plain text
//   narration_dir,                           the takes folder, <project>/narration/takes/vNN
//   voice?: { model, voice, style },         TTS settings; default: the folder's narration-manifest.json, else the tool's
//   length_cap_s?,                           stop after narration when the projected film is longer
//   briefs?, refs_dir?, finish_dir?,         paintings (uvk-art-make); refs/ and finished/ default to beside the briefs
//   plate_content?, plates_out?,             plates (uvk-plates-make); output defaults to the content file's folder
//   storyboard, cue_sheet,                   render inputs (uvk-film-make)
//   art_dir?, art_map?,                      the paintings folder (--art-dir) and a JSON file of {"<shot>": "<image>"}
//                                            that sets a shot's picture (--art-map)
//   lead_in?, tail?, bold?, impact_phrase?,  renderer settings: OTHELLO_LEAD_IN, OTHELLO_TAIL, OTHELLO_BOLD, --impact-phrase
//   fitted?, out,                            the fitted score (default <out>/fitted) and the render output folder,
//                                            <project>/film/vNN/render; the audit saves verdicts.json one folder up
//   repo?                                    this repository's path, when the session runs elsewhere
// }
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
for (const k of ['project', 'manifest', 'script_text', 'narration_dir', 'storyboard', 'cue_sheet', 'out']) {
  if (!A[k]) throw new Error(`args.${k} is required`)
}
for (const k of ['project', 'manifest', 'script_text', 'narration_dir', 'briefs', 'refs_dir', 'finish_dir', 'plate_content', 'plates_out',
  'storyboard', 'cue_sheet', 'art_dir', 'art_map', 'fitted', 'out', 'repo']) {
  if (A[k] && !String(A[k]).startsWith('/')) throw new Error(`args.${k} must be an absolute path`)
}
const dirOf = p => p.replace(/\/[^/]*$/, '')
const repo = A.repo ? A.repo.replace(/\/+$/, '') : null
if (repo) {
  // every folder the run writes into, the ones derived from inputs included
  const outputs = [
    ['args.project', A.project], ['args.narration_dir', A.narration_dir], ['args.fitted', A.fitted], ['args.out', A.out],
    ['the folder of args.manifest (fidelity.json is written there)', dirOf(A.manifest)],
    ['the folder of args.briefs (the paintings are written there)', A.briefs && dirOf(A.briefs)],
    ['args.finish_dir (default: finished/ beside the briefs)', A.briefs && (A.finish_dir || dirOf(A.briefs) + '/finished')],
    ['args.plates_out (default: the folder of args.plate_content)', A.plate_content && (A.plates_out || dirOf(A.plate_content))],
  ]
  for (const [what, p] of outputs) {
    if (p && (p + '/').startsWith(repo + '/')) throw new Error(`${what} lies inside this repository; project outputs belong outside it`)
  }
}
const ctx = `Run every command from the root of this repository (${repo || 'the current working directory'}); the tools are in tools/ and ` +
  `tools/README.md gives their inputs. The project is ${A.project}, outside the repository: pass its paths to the tools by flag and write every ` +
  `output under it, never into the repository. Recording manifest: ${A.manifest}. Follow kit/docs/STANDARDS.md and the named skill ` +
  `(.claude/skills/<name>/SKILL.md). The model key comes from the environment (GENAI_API_KEY or GEMINI_API_KEY); never write a key to a file, ` +
  `a commit or a log.`

const SCRIPT = {
  type: 'object',
  properties: {
    verbatim: { type: 'boolean' }, reference_words: { type: 'number' }, manifest_words: { type: 'number' },
    in_order: { type: 'number' }, differences: { type: 'array', items: { type: 'string' } },
  },
  required: ['verbatim', 'differences'],
}
const NARRATION = {
  type: 'object',
  properties: {
    model: { type: 'string' }, voice: { type: 'string' },
    clips: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          clip_id: { type: 'string' }, words: { type: 'number' }, speech_seconds: { type: 'number' }, wpm: { type: 'number' },
          matched_ratio: { type: 'number' }, attempts: { type: 'number' }, accepted: { type: 'boolean' },
          faults: { type: 'array', items: { type: 'string' } },
        },
        required: ['clip_id', 'accepted'],
      },
    },
    projected_seconds: { type: 'number' },
  },
  required: ['clips', 'projected_seconds'],
}
const PICTURES = {
  type: 'object',
  properties: { files: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } }, contact_sheet: { type: 'string' } },
  required: ['files', 'problems'],
}
const RENDER = {
  type: 'object',
  properties: {
    seconds: { type: 'number' }, lufs: { type: 'number' }, true_peak_dbtp: { type: 'number' },
    voice_over_music_db: { type: 'array', items: { type: 'number' } }, captions_equal_script: { type: 'boolean' },
    max_caption_chars: { type: 'number' }, transcription_faults: { type: 'array', items: { type: 'string' } },
    failures: { type: 'array', items: { type: 'string' } }, passed: { type: 'boolean' }, film: { type: 'string' },
  },
  required: ['seconds', 'passed'],
}

phase('Script')
const script = await agent(`${ctx}\nProve that the manifest's spoken_text_exact, scene after scene, is the script in ${A.script_text} word for word. ` +
  `Run python3 tools/review/measure_fidelity.py --reference ${A.script_text} --film manifest=${A.manifest} ` +
  `--out ${A.manifest.replace(/[^/]+$/, 'fidelity.json')} --diffs and report its counts. verbatim is true only when every reference word is ` +
  `found in order and the manifest has exactly as many words; list every difference. Do not edit the script or the manifest.`, { schema: SCRIPT })
if (!script || !script.verbatim) {
  log('The manifest is not the script word for word. Stopping before any generation.')
  return { stopped: 'script', script }
}

phase('Narration')
const v = A.voice || {}
const voice = (v.model || v.voice || v.style)
  ? `model ${v.model || "the tool's default"}, voice ${v.voice || "the tool's default"}, direction ${v.style ? JSON.stringify(v.style) : "the tool's default"}`
  : `the model, voice and direction recorded in ${A.narration_dir}/narration-manifest.json if it exists, else the tool's defaults`
const around = `lead-ins ${A.lead_in ? JSON.stringify(A.lead_in) : '(LEAD_IN in tools/film/render-narrated.js)'} and tails ` +
  `${A.tail ? JSON.stringify(A.tail) : '(TAIL in tools/film/render-narrated.js)'}`
const narration = await agent(`${ctx}\nFollow the uvk-narration-make skill. Generate every clip of the manifest into ${A.narration_dir} with ` +
  `tools/narration/generate_takes.py, using ${voice}. Pass the same model, voice and direction on every run into that folder, and never run two ` +
  `generators into it at once; if the folder already records a different model, voice or direction, generate nothing and report every clip as ` +
  `not accepted with that fault, since one folder holds one voice. Verify every take twice: tools/narration/verify_take.py (blind transcription ` +
  `and word diff), then tools/narration/align_words.py --no-prompt on that clip (no extra speech). Regenerate a failing clip with ` +
  `--only <clip_id> --force up to three times, and record every fault. Then align every clip with align_words.py --narration ` +
  `${A.narration_dir} --all; for a clip below 0.93 matched, align it with --no-prompt too and keep the alignment that matches more words. ` +
  `Report per clip the words, the speech span in seconds (first to last aligned word), words a minute over that span, the matched ratio and ` +
  `the attempts, and the projected film length: the speech spans plus the ${around}. Never time-stretch a take or change a word.`,
  { schema: NARRATION })
if (!narration || !narration.clips.length || narration.clips.some(c => !c.accepted)) {
  log(narration ? 'Some clips failed verification. Stopping before pictures.' : 'The narration stage returned nothing. Stopping before pictures.')
  return { stopped: 'narration', script, narration }
}
if (A.length_cap_s && narration.projected_seconds > A.length_cap_s) {
  log(`Projected ${narration.projected_seconds} s is over the ${A.length_cap_s} s cap. Try another model with the same voice, or split the ` +
    'film into parts; never cut words or stretch a take.')
  return { stopped: 'pace', script, narration }
}

// Plates are built over paintings, so they wait for them: built in parallel, a plate could use a missing or stale painting.
phase('Pictures')
let art = null
if (A.briefs) {
  const artDir = dirOf(A.briefs)
  art = await agent(`${ctx}\nFollow the uvk-art-make skill. Generate every painting in ${A.briefs} that is not yet on disk with ` +
    `tools/art/generate_paintings.py --briefs ${A.briefs} --refs-dir ${A.refs_dir || artDir + '/refs'} --out ${artDir}. Where the storyboard ` +
    `${A.storyboard} names a finished painting that does not exist yet, make it from its source with tools/art/finish_paintings.py ` +
    `--out ${A.finish_dir || artDir + '/finished'}. Open every new image, and compare each finished painting with its source, since a repaint ` +
    `can change content. Check for text, drawn borders, faces, each character against the bible, and the object its line needs. List every ` +
    `problem; hide none.`, { schema: PICTURES, phase: 'Pictures', label: 'paintings' })
} else {
  log('No args.briefs: no paintings generated; the paintings the storyboard names must already exist.')
}
let plates = null
if (A.plate_content) {
  plates = await agent(`${ctx}\nFollow the uvk-plates-make skill. Build the plates with tools/plates/build_plates.py --content ` +
    `${A.plate_content} --out ${A.plates_out || dirOf(A.plate_content)}. Check the contact sheet, then every plate at full size, for clipping, ` +
    `overlaps and lines crossing labels, and check each plate's on_screen_text in plates.json against the manifest. List every problem.`,
    { schema: PICTURES, phase: 'Pictures', label: 'plates' })
} else {
  log('No args.plate_content: no plates built; the plates the storyboard names must already exist.')
}
const pictureProblems = [...((art && art.problems) || []), ...((plates && plates.problems) || [])]
if (pictureProblems.length) log(`Picture problems to fix before the film is shared: ${pictureProblems.length}`)

phase('Render')
const settings = [
  A.lead_in && `lead-ins ${JSON.stringify(A.lead_in)} (OTHELLO_LEAD_IN)`,
  A.tail && `tails ${JSON.stringify(A.tail)} (OTHELLO_TAIL)`,
  A.bold && `caption words to bold ${JSON.stringify(A.bold)} (OTHELLO_BOLD)`,
  A.impact_phrase && `the last music impact on ${JSON.stringify(A.impact_phrase)} (--impact-phrase)`,
].filter(Boolean)
const flags = `--manifest ${A.manifest} --storyboard ${A.storyboard} --cue-sheet ${A.cue_sheet} --narration ${A.narration_dir} ` +
  `--alignment ${A.narration_dir}/alignment --out ${A.out}${A.art_dir ? ` --art-dir ${A.art_dir}` : ''}` +
  `${A.art_map ? ` --art-map ${A.art_map}` : ''}${A.fitted ? ` --fitted ${A.fitted}` : ''}`
const render = await agent(`${ctx}\nFollow the uvk-film-make skill. Render with node tools/film/render-narrated.js ${flags}. ` +
  `Settings: ${settings.length ? settings.join('; ') + '; the variables go in the environment as JSON, quoted for the shell' : "the renderer's defaults"}. ` +
  `The default lead-ins and tails and the cue plan in tools/score/fit-score.js are written for eight scenes; for any other count follow the ` +
  `skill. Storyboard art paths are absolute, or file names found in --art-dir, unless --art-map sets the shot's picture. ` +
  `Run --stage plan first and fix any anchor it rejects in the storyboard, never in the script; then render in full; then run ` +
  `node tools/film/render-narrated.js --stage qa --out ${A.out} ` +
  `--manifest ${A.manifest} --whisper large-v3-turbo. Report each acceptance check of the skill with its measured number, and set passed only ` +
  `when every one passes.`, { schema: RENDER })

phase('Audit')
let audit = null
if (!render) {
  log('The render stage returned nothing; no shot audit.')
} else {
  try {
    audit = await workflow(repo ? { scriptPath: `${repo}/.claude/workflows/uvk-film-audit.js` } : 'uvk-film-audit',
      { render_out: A.out, out: dirOf(A.out), ...(repo ? { repo } : {}) })
  } catch (e) {
    log(`The uvk-film-audit workflow could not run (${(e && e.message) || e}); audit by hand with the uvk-film-audit skill.`)
  }
}

phase('Report')
const report = await agent(`${ctx}\nWrite the QA record for this build at ${A.out}/QA.md, plain and short: what passed, with its numbers; ` +
  `what failed; the picture problems; the shot-audit totals by count and by screen time and who judged them, or that no audit ran; and what ` +
  `was not tested. Label anything estimated as an estimate. Results: ` +
  JSON.stringify({ script, narration, art, plates, render, audit }))
return { script, narration, art, plates, render, audit, report }
