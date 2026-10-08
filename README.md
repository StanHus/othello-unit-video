# Othello unit opening (Grade 9)

A short narrated film to open a Grade 9 unit on *Othello*, and what I learned making it.

The film reads a fixed script in one synthetic voice, over paintings and labelled plates. Six times it stops to ask a
question, and it won't carry on until the student gets it right. I made seven versions in October 2026; the last one
runs 2:54. Along the way I compared it with two other productions of the same script, and tested an AI marker on
student answers I wrote.

The film itself isn't here, because its script belongs to the course it was made for. Everything else is: the
paintings, the player, the tools, the measurements, and a kit that runs the same steps in Claude Code.

None of it has been tried with students yet, and most of the judging was mine, so treat the numbers as a start.

## What I learned

- Stills or animation is still open. I went with stills; the research points both ways, and so do my own numbers.
- Don't cut the script to fit a length. The limit was the voice model, not the script: one model wouldn't go past
  about 140 words a minute, another read the whole thing in 2:54.
- Paintings carry the story but not the structure. Who outranks whom, or where Cyprus is, needs a labelled plate.
- A check you can skip isn't a check. The player won't let you seek past a question you haven't answered.
- Keep what students write, but don't let an AI mark it. The marker I tested got 5 of 63 answers wrong, each time
  where a student's wording drifted from the rubric's.
- Check every narration take twice, with two recognisers that haven't seen the script. One voice model read its own
  instructions aloud before all four of its takes; the first check caught one of four, the second caught all four.
- Before the reading, give only the context the first scene needs. Only 6 of the script's 26 points are needed before
  the play's first line; much of the rest could come while students read.

The evidence for each, what argues against it and how to test it are in [research/FINDINGS.md](research/FINDINGS.md).

## What's here

- [research/](research/): findings, methods and data
- [assets/](assets/): the paintings and a sketch of the score
- [player/](player/): the lesson player, with sample media so it runs without the film
- [tools/](tools/): the scripts that made the film
- [kit/](kit/): the same pipeline as Claude Code skills

## Try the player

```sh
python3 tools/player/make_sample_media.py
node tools/player/serve.js 8780 player
```

Then open http://127.0.0.1:8780/ in a browser. To make a film from your own script, see the commands in
[tools/README.md](tools/README.md#commands), or run the kit from Claude Code ([kit/README.md](kit/README.md)).
