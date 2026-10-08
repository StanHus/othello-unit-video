# Player with gated checks

A single HTML page (`index.html`, no build step, no external requests) that plays a narrated film and stops it at
fixed points for a check. The film continues only after a right answer. It is not a chatbot: nothing replies to
what a student types.

## Try it with the sample

```
python3 tools/player/make_sample_media.py        # 24 s silent sample from three published images, chimes for the questions
node tools/player/serve.js 8780 player           # needs HTTP Range for video seeking
open http://127.0.0.1:8780/                      # the full sample film, three checks
open "http://127.0.0.1:8780/?parts"              # the same film in two parts
```

The sample checks in `sample/checks.json` are samples that exercise the mechanics (a choice, an own-words
answer with a follow-up, choices with their own feedback). For a real film, render it with
`tools/film/render-narrated.js` and run `tools/player/build_parts.py` with your own checks and parts.

## Rules it enforces

- Own-words answers are kept and shown back, refused only if they look like gibberish or are too short (fewer than
  four words, a run of repeated letters, too few real words), and never scored.
- After an own-words answer, one scripted follow-up asks the student for a reason; that answer is saved and never
  judged either.
- A wrong choice shows its own feedback and leaves the other options open; Continue appears only after the right one.
  "Hear the scene again" replays the scene the check is about.
- Seeking cannot pass an unanswered check: a seek beyond it snaps back to just before it.
- In parts mode (`?parts`) later parts unlock only after the earlier parts and their checks are done, and parts
  advance on their own.
- The film is blurred and dimmed while a check card is showing, so a plate or painting on screen cannot give the answer away.
- The page plays a silent clip on the first tap or key press, so that question audio started later by the page is
  not blocked by mobile autoplay rules.
- Attempts, own words and position are saved in the browser's localStorage under one key per configuration.
  Captions sit above the control bar and hide while a card is showing. Under 720 px wide the card becomes a bottom sheet.

## Configuration

`index.html` loads `content/checks.js` (full film) and `content/checks-parts.js` (parts), written by
`tools/player/build_parts.py`:

```
window.OTHELLO_FILM_CHECKS = {
  "title": "...", "subtitle": "...",            // optional page title and the line under it
  "poster": "media/poster.jpg",
  "storageKey": "othello-film-checks-v1-full",  // one key per configuration
  "parts": [{
    "part": 1, "title": "...", "film": "media/....mp4", "captions": "media/....vtt", "duration": 174.5,
    "stops": [{
      "id": "unique id", "at": 34.08,           // seconds into this part's video; the film pauses here
      "sceneStart": 0.0,                         // where "Hear the scene again" jumps to
      "corner": "bl",                            // bl or br: where the card opens
      "say": "the words of the spoken question",  // shown under "Show the words"
      "ask": "media/....wav", "correct": "media/....wav",   // question audio; confirmation audio after the last right answer
      "steps": [
        {"kind": "choice", "stem": "...", "options": ["...", "..."], "answer": 0, "feedback": ["...", "..."]},
        {"kind": "own_words", "stem": "...", "prompt": "label above the text box"},
        {"kind": "probe", "stem": "...", "prompt": "...", "audio": "media/....wav"}
      ]
    }]
  }]
};
```

`window.OTHELLO_FILM_CHECKS_PARTS` has the same shape with one entry per part. A probe step follows an own-words step;
the last step of a check should be a choice, since only a right choice shows Continue. `build_parts.py` takes the
checks without `at` and `sceneStart` (`afterScene` instead) and fills both from the measured timeline.

Browser test record: `QA.md`.
