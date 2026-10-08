export const meta = {
  name: 'uvk-feedback-sweep',
  description: "Sweep every feedback source on a unit video, check each item against the build, and sort what is open: apply now, needs the project's decision, or outside this project's control",
  whenToUse: 'Before a new version, or when asked what feedback is left; pass the project folder, the source files and, optionally, a summary of the current build',
  phases: [
    { title: 'Read', detail: 'one reader per source: exact words and where they are' },
    { title: 'Sort', detail: 'each item checked against the build, then sorted' },
    { title: 'Critic', detail: 'what was missed' },
  ],
}

// args: { project, sources: [paths], build_summary?, repo? }
// Runs from the repository root: the player engine is in player/, the tools in tools/, the rules in
// kit/docs/STANDARDS.md. project and every source are absolute paths; repo, this repository's path, is optional and
// lets the script check that the project lies outside it. It changes no files; applying the result is a separate step.
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
if (!A.project) throw new Error('args.project is required')
if (!Array.isArray(A.sources) || !A.sources.length) throw new Error('args.sources is required')
for (const p of [A.project, ...A.sources, ...(A.repo ? [A.repo] : [])]) {
  if (!String(p).startsWith('/')) throw new Error(`${p} must be an absolute path`)
}
const repo = A.repo ? A.repo.replace(/\/+$/, '') : null
if (repo && (A.project + '/').startsWith(repo + '/')) throw new Error('args.project is inside this repository; projects live outside it')
const build = A.build_summary || "as the project's README and QA records describe it"
const n = (k, word) => `${k} ${word}${k === 1 ? '' : 's'}`

const ITEMS = {
  type: 'object',
  properties: {
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          quote: { type: 'string' }, where: { type: 'string' },
          voice: { type: 'string', enum: ['source', 'quoted'] }, ask: { type: 'string' },
        },
        required: ['quote', 'where', 'voice', 'ask'],
      },
    },
  },
  required: ['items'],
}
const SORT = {
  type: 'object',
  properties: {
    group: { type: 'string', enum: ['already-done', 'apply-now', 'needs-decision', 'outside-control'] },
    evidence: { type: 'string' }, decision: { type: 'string' },
  },
  required: ['group', 'evidence'],
}
const CRITIC = { type: 'object', properties: { missed: { type: 'array', items: { type: 'string' } } }, required: ['missed'] }

phase('Read')
const read = await pipeline(A.sources,
  src => agent(`Read ${src} in full. List every piece of feedback or open question about the unit video, its checks or its player: ` +
    `quote = the exact words; where = the section, page or line; voice = "source" for the document's own words, "quoted" for words ` +
    `it reports from someone else; ask = what the item asks for, in one line.`,
    { schema: ITEMS, phase: 'Read', label: `read:${src.split('/').pop()}` }),
  (r, src) => r && r.items.map(it => ({ ...it, source: src })))
const unread = A.sources.filter((src, i) => !read[i])
if (unread.length) log(`Not read, so missing from the sweep: ${unread.join(', ')}`)

const byAsk = new Map()
for (const it of read.filter(Boolean).flat()) {
  const key = it.ask.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
  if (byAsk.has(key)) byAsk.get(key).also.push({ source: it.source, where: it.where, quote: it.quote, voice: it.voice })
  else byAsk.set(key, { ...it, also: [] })
}
const items = [...byAsk.values()]
const repeats = items.reduce((k, it) => k + it.also.length, 0)
log(`${n(items.length, 'distinct item')} from ${n(A.sources.length - unread.length, 'source')}; ${n(repeats, 'repeat')} merged into them`)

phase('Sort')
const results = await pipeline(items,
  (it, _, i) => agent(`Project folder: ${A.project}. Current build: ${build}. Feedback item: ${JSON.stringify(it)}. ` +
    `Before deciding, check the project's files and this repository's player/ and tools/: a feature that seems missing may already be there. ` +
    `Groups: already-done (the build already does it; evidence says where); apply-now (inside the fixed script, the rules in ` +
    `kit/docs/STANDARDS.md and the decisions already made); needs-decision (it conflicts with a decision already made or one of those ` +
    `rules; name it in decision); outside-control (it changes what this project does not own, such as the script's words, check questions ` +
    `supplied with it, or someone else's files or environment, or it needs an answer no source gives). Change nothing.`,
    { schema: SORT, phase: 'Sort', label: `sort:${i + 1}` }),
  (s, it) => ({ ...it, ...(s || { group: 'unsorted', evidence: 'the sorting agent failed' }) }))
const sorted = results.map((s, i) => s || { ...items[i], group: 'unsorted', evidence: 'not sorted' })

phase('Critic')
const critic = await agent(`Sources: ${JSON.stringify(A.sources)}. Sorted items: ${JSON.stringify(sorted)}. What was missed: a source not ` +
  `read in full, an item not checked against the files, a quotation taken as the source's own words or the reverse, repeats merged that ` +
  `ask for different things, the same request listed twice, or an item in the wrong group? Name the source and the item each time.`,
  { schema: CRITIC, phase: 'Critic' })
const group = g => sorted.filter(s => s.group === g)
return {
  already_done: group('already-done'), apply_now: group('apply-now'), needs_decision: group('needs-decision'),
  outside_control: group('outside-control'), unsorted: group('unsorted'), unread, missed: (critic && critic.missed) || [],
}
