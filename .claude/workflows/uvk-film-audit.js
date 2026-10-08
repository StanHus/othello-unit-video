export const meta = {
  name: 'uvk-film-audit',
  description: 'The per-shot test on a rendered film: two independent judges per shot, a third when they split, totals by count and by screen time',
  whenToUse: 'After a render and its QA, before sharing; pass the render folder as args.render_out',
  phases: [
    { title: 'List', detail: 'one row per shot: times, the words spoken, its frame' },
    { title: 'Judge', detail: 'a story lens and a structure lens per shot' },
    { title: 'Reconcile', detail: 'agree, or a third judge decides; then the totals' },
  ],
}

// Run from the root of this repository. Every path in args is absolute.
// args: { render_out, out?, repo? }
//   render_out  a render folder from tools/film/render-narrated.js after --stage qa: narrated-timeline.json,
//               Othello-opening-NARRATED.vtt and frames/ (one frame per cut)
//   out         optional: a folder outside this repository to save verdicts.json in, in the format
//               tools/review/measure_screen.py reads
//   repo        optional: this repository's path, so that out can be checked to lie outside it
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
if (!A.render_out) throw new Error('args.render_out is required: a render folder that has been through --stage qa')
for (const k of ['render_out', 'out', 'repo']) {
  if (A[k] && !String(A[k]).startsWith('/')) throw new Error(`args.${k} must be an absolute path`)
}
const repo = A.repo ? A.repo.replace(/\/+$/, '') : null
if (repo && A.out && (A.out + '/').startsWith(repo + '/')) throw new Error('args.out is inside this repository; project outputs belong outside it')
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

const SHOTS = {
  type: 'object',
  properties: {
    shots: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          n: { type: 'number' }, start: { type: 'number' }, end: { type: 'number' },
          line: { type: 'string' }, frame: { type: 'string' },
        },
        required: ['n', 'start', 'end', 'line', 'frame'],
      },
    },
  },
  required: ['shots'],
}
const VERDICT = {
  type: 'object',
  properties: {
    look_at: { type: 'string' },
    picture: { type: 'string' },
    verdict: { type: 'string', enum: ['carries', 'partly', 'competes'] },
    fix: { type: 'string' },
  },
  required: ['look_at', 'picture', 'verdict'],
}
const RULE = 'Verdicts: carries = the picture shows what the line is about; partly = it shows some of it; ' +
  'competes = the picture is about something else. A narrator figure talking to camera is partly when the line is about ' +
  "the student's task or the film's framing, and competes when it is about a character or a concept. For a line that " +
  'does not carry, give the fix: a plate for a structural line (a definition, a list, a place, a rank), or a painting ' +
  'that shows a story line.'
const LOOK = 'Give where a student should look during the line (look_at), what the picture shows (picture) and the verdict.'

phase('List')
const listed = await agent(`Read ${A.render_out}/narrated-timeline.json and change nothing. Its scenes[].shots[] hold every cut in ` +
  'film order, with start_seconds, end_seconds and spoken_anchor, and each scene holds its spoken_text_exact. List every shot: ' +
  'n (1 for the first cut, counted across scenes), start, end, line (the exact words spoken while it is on screen: from its ' +
  "spoken_anchor up to the next shot's anchor, the first shot of a scene from the scene's first word and the last to the " +
  `scene's end; check them against ${A.render_out}/Othello-opening-NARRATED.vtt) and frame (the absolute path of the file in ` +
  `${A.render_out}/frames/ whose name starts with cut- and n in two digits: cut-01, cut-02 and so on).`, { schema: SHOTS })
const shots = (listed && listed.shots) || []
if (!shots.length) {
  log('No shots listed. Run tools/film/render-narrated.js --stage qa on the render first, so that frames/ exists.')
  return { counts: null, share_of_screen_time_pct: null, rows: [] }
}
log(`${count(shots.length, 'shot')} to judge`)

const judged = await pipeline(shots,
  s => parallel([
    () => agent(`Open the frame ${s.frame}. Line spoken while it is on screen: "${s.line}". Lens: story, the events and ` +
      `people the line tells of. Does the picture show what the line being spoken is about? ${LOOK} ` +
      `Judge this shot on its own. ${RULE}`,
      { schema: VERDICT, phase: 'Judge', label: `story:${s.n}` }),
    () => agent(`Open the frame ${s.frame}. Line spoken while it is on screen: "${s.line}". Lens: structure, the term, rank, ` +
      `place, list or idea the line teaches. Does the picture show what the line being spoken is about? ${LOOK} ` +
      `Judge this shot on its own. ${RULE}`,
      { schema: VERDICT, phase: 'Judge', label: `structure:${s.n}` }),
  ]),
  async (votes, s) => {
    const v = (votes || []).filter(Boolean)
    if (v.length === 2 && v[0].verdict === v[1].verdict) return { ...s, ...v[0], judges: 2 }
    const why = v.length === 2 ? `Two judges disagree: ${JSON.stringify(v)}.`
      : v.length === 1 ? `One judge said ${JSON.stringify(v[0])}; the other failed.` : 'Both judges failed.'
    const tie = await agent(`Open the frame ${s.frame} for the line "${s.line}". ${why} Decide. ${RULE}`,
      { schema: VERDICT, phase: 'Reconcile', label: `tie:${s.n}` })
    if (tie) return { ...s, ...tie, judges: v.length + 1 }
    return v.length === 1 ? { ...s, ...v[0], judges: 1 } : null
  })

phase('Reconcile')
const rows = judged.filter(r => r && r.verdict)
if (rows.length < shots.length) log(`Not judged, and left out of the totals: ${count(shots.length - rows.length, 'shot')}`)
const single = rows.filter(r => r.judges < 2).length
if (single) log(`Judged by one judge only: ${count(single, 'shot')}`)
const KINDS = ['carries', 'partly', 'competes']
const seconds = k => rows.filter(r => r.verdict === k).reduce((t, r) => t + (r.end - r.start), 0)
const total = rows.reduce((t, r) => t + (r.end - r.start), 0) || 1
const counts = {}
const share = {}
for (const k of KINDS) {
  counts[k] = rows.filter(r => r.verdict === k).length
  share[k] = Math.round(100 * seconds(k) / total)
}
if (A.out) {
  await agent(`Write ${A.out}/verdicts.json with exactly this content, and change nothing else: ` +
    JSON.stringify({ verdicts: rows.map(r => ({ n: r.n, verdict: r.verdict })) }), { phase: 'Reconcile', label: 'save' })
}
return {
  judged_by: 'two independent judges per shot (a story lens and a structure lens), a third when they split',
  counts,
  share_of_screen_time_pct: share,
  rows,
}
