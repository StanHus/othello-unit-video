export const meta = {
  name: 'uvk-video-compare',
  description: 'Compare productions of one script on a rubric fixed in advance: capture each film the same way, run the per-shot test, score, try to refute every claim, write it up',
  whenToUse: 'When choosing between approaches, or when someone claims one film is better; pass the rubric, the reference script and two or more films in args',
  phases: [
    { title: 'Capture', detail: 'facts per film, measured the same way' },
    { title: 'Judge', detail: 'the per-shot test per film' },
    { title: 'Score', detail: 'the rubric rows across all films, from the saved files' },
    { title: 'Verify', detail: 'three refuters per claim' },
    { title: 'Write', detail: 'table, findings, corrections, not checked' },
  ],
}

// Run from the root of this repository. Every file and folder in args is an absolute path.
// args: { rubric, script, films: [{ name, source, notes? }], out, first_word?, earlier?, repo? }
//   rubric      the fixed rubric: a copy of kit/templates/review/rubric.example.md with every row settled before measuring
//   script      the reference script: a recording manifest (.json) or plain text (.txt)
//   films       two or more; name is a short folder name (stills, animated, 3d), source a video file or a live build
//   out         the comparison folder, outside this repository; each film gets a subfolder there
//   first_word  optional: a word whose first hearing the rubric times
//   earlier     optional: a file of earlier claims to check against the new numbers
//   repo        optional: this repository's path, so that out can be checked to lie outside it
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const films = Array.isArray(A.films) ? A.films : []
if (films.length < 2) throw new Error('args.films needs two or more films')
for (const k of ['rubric', 'script', 'out']) {
  if (!A[k]) throw new Error(`args.${k} is required`)
}
for (const k of ['rubric', 'script', 'out', 'earlier', 'repo']) {
  if (A[k] && !String(A[k]).startsWith('/')) throw new Error(`args.${k} must be an absolute path`)
}
const repo = A.repo ? A.repo.replace(/\/+$/, '') : null
if (repo && (A.out + '/').startsWith(repo + '/')) throw new Error('args.out is inside this repository; the comparison belongs outside it')
if (new Set(films.map(f => f.name)).size !== films.length) throw new Error('every film needs its own name')
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
const SKILL = '.claude/skills/uvk-video-compare/SKILL.md'
const AUDIT = '.claude/skills/uvk-film-audit/SKILL.md'

const FACTS = {
  type: 'object',
  properties: {
    name: { type: 'string' }, seconds: { type: 'number' }, shots: { type: 'number' },
    script_file: { type: 'string' }, whisper_file: { type: 'string' },
    checks: { type: 'array', items: { type: 'string' } },
    on_screen_text: { type: 'string' }, narrator: { type: 'string' }, music: { type: 'string' },
    not_captured: { type: 'array', items: { type: 'string' } }, notes_file: { type: 'string' },
  },
  required: ['name', 'seconds', 'shots', 'notes_file'],
}
const VERDICTS = {
  type: 'object',
  properties: { carries: { type: 'number' }, partly: { type: 'number' }, competes: { type: 'number' }, verdicts_file: { type: 'string' } },
  required: ['carries', 'partly', 'competes', 'verdicts_file'],
}
const SCORE = {
  type: 'object',
  properties: {
    table_markdown: { type: 'string' },
    claims: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, evidence: { type: 'string' } }, required: ['claim', 'evidence'] } },
  },
  required: ['table_markdown', 'claims'],
}
const REFUTE = { type: 'object', properties: { refuted: { type: 'boolean' }, why: { type: 'string' } }, required: ['refuted', 'why'] }

const perFilm = await pipeline(films,
  f => agent(`Follow ${SKILL}, "Capture each film", running commands from the repository root. Capture the film "${f.name}" ` +
    `from ${f.source}${f.notes ? ` (${f.notes})` : ''} and save everything under ${A.out}/${f.name}/: script.txt (or a ` +
    'line in notes.md saying there is none), whisper-noprompt.json, one frame per shot at its midpoint in frames/, ' +
    'shots.json with every shot boundary (soft transitions included) and notes.md. Do not submit answers to any live build.',
    { schema: FACTS, phase: 'Capture', label: `capture:${f.name}` }),
  (facts, f) => facts && agent(`Follow ${AUDIT} for the film "${f.name}" in ${A.out}/${f.name}/: judge every shot in ` +
    "shots.json against the words spoken while it is on screen, on its own merits and without reading any other film's " +
    'verdicts. Save verdicts.json there as {"verdicts": [{"n", "verdict"}]}.',
    { schema: VERDICTS, phase: 'Judge', label: `judge:${f.name}` }).then(v => v && { name: f.name, facts, verdicts: v }))

phase('Score')
const ok = perFilm.filter(Boolean)
if (ok.length < films.length) log(`Left out after failing capture or judging: ${count(films.length - ok.length, 'film')}`)
if (ok.length < 2) {
  log('Fewer than two films were captured and judged, so there is nothing to compare.')
  return { films: ok }
}
const names = ok.map(r => r.name)
const fidelity = `python3 -I tools/review/measure_fidelity.py --reference "${A.script}" --out "${A.out}/fidelity.json" ` +
  names.map(n => `--film ${n}="${A.out}/${n}/script.txt"`).join(' ')
const screen = `python3 -I tools/review/measure_screen.py --dir "${A.out}" --films ${names.join(',')} ` +
  `--reference-words <the reference script's word count>${A.first_word ? ` --first-word "${A.first_word}"` : ''} --out "${A.out}/measures.json"`
const scored = await agent(`Score these films on the rubric in ${A.rubric}: one row per criterion, one column per film, every ` +
  `number from the saved files under ${A.out}. From the repository root, run\n${fidelity}\nleaving out the --film of ` +
  `any film with no script.txt and adding --whisper <name>="${A.out}/<name>/whisper-noprompt.json" for each film that ` +
  `has that file, and\n${screen}\n` +
  "Score fidelity on each film's script, never on a transcript; where a film has no script of its own, leave its " +
  'fidelity unscored and say so in the table. Then list the five strongest comparative claims, each with its numbers ' +
  `and the files they come from. Films: ${JSON.stringify(ok)}`, { schema: SCORE })

phase('Verify')
const ANGLES = [
  'the numbers: recompute them from the saved files',
  'the wording: every quote exact and correctly attributed, other productions described by what they are, nothing of theirs copied',
  'the method: whether the measure was taken the same way for every film',
]
const checked = await pipeline((scored && scored.claims) || [],
  (c, _, k) => parallel(ANGLES.map((angle, i) => () => agent(`Try to refute this claim from the files under ${A.out}; default to ` +
    `refuted=true if the files do not support it. Claim: ${c.claim}. Evidence given: ${c.evidence}. Angle ${i + 1} of 3: ${angle}.`,
    { schema: REFUTE, phase: 'Verify', label: `refute:${k + 1}.${i + 1}` })))
    .then(vs => ({ ...c, survives: vs.filter(Boolean).filter(v => !v.refuted).length >= 2, votes: vs })))
const survived = checked.filter(Boolean).filter(c => c.survives)
const dropped = checked.filter(Boolean).filter(c => !c.survives)
if (dropped.length) log(`Left out of the findings after refutation: ${count(dropped.length, 'claim')}`)

phase('Write')
const doc = await agent(`Write ${A.out}/README.md, plain and short: the rubric table; then the surviving findings, each with ` +
  'its numbers, the strongest counter-argument and the test that would settle it (the shape of research/FINDINGS.md); then ' +
  `corrections: each claim that did not survive and why${A.earlier ? `, and any claim in ${A.earlier} that these numbers contradict` : ''}; ` +
  'then what was not checked. Describe other productions by what they are (an animated version, a 3D version built in ' +
  'code), never by who made them, and quote none of their scripts, transcripts or rubrics. ' +
  `Table: ${(scored && scored.table_markdown) || ''}\nSurviving: ${JSON.stringify(survived)}\nNot surviving: ${JSON.stringify(dropped)}`)
return { films: ok, claims: checked, written: doc }
