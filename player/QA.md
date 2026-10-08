# Player · browser test record

All runs: Chrome driven through DevTools in a fresh, isolated profile, the page served by `tools/player/serve.js`
(Range requests answered with 206). Media muted for automation; question audio checked by the audio element's source,
not by ear. **No person has watched or listened in these tests.**

## First run, on a 5:44 narrated film with three checks (2026-10-06)

| test | result |
|---|---|
| Film loads, three check markers drawn on the bar | PASS |
| Seek past the first check snaps back to just before it | PASS |
| Natural playback pauses at the check; the card opens, captions hide, the question audio plays | PASS |
| Play refused while the card is open | PASS |
| A wrong option shows its own feedback, the other options stay open, no Continue; a right option gives Next (multi-step) or Continue with the confirmation audio | PASS |
| Continue: the card leaves, the film resumes, captions return | PASS |
| Reload: finished checks and every attempt persist; position resumes before the next open check | PASS |
| After a check is done, seeks before the next check are allowed and seeks past it are clamped | PASS |
| Own words: "fdsf", "fdsf sdfsd qwrt zxcv", "aaaaaa bbbbbb cccc dddd" and a two-word answer refused with no reply; a real sentence saved and shown back as "Your words" | PASS |
| Cards open in their configured corner, 24 px inset | PASS |
| 1440x823 laptop: whole frame and control bar in view | PASS after a fix (frame width now limited by the viewport height) |
| 390x844 phone: the card is a bottom sheet below the film, no horizontal scroll, text box 76 px | PASS |

Defects found and fixed during that run: the control bar fell below the fold at laptop height; the "Your words" block
was unstyled; one card covered a face in its corner and moved to the other corner.

## Re-runs on later films (2026-10-06 and 2026-10-07)

- 2:00 film, three checks: seek clamped before check 1; all three checks answered and stored. PASS.
- 4:31 film, six checks, full and parts mode: six markers; captions raised above the bar; all checks opened at their
  measured times and were stored; in parts mode the tabs unlocked in order and parts advanced on their own. Fixed in
  this run: question audio could override the confirmation when answered within 0.14 s; a stray part tab in full
  mode; captions one line too low. PASS.
- Film with labelled plates: the film is blurred and dimmed while a check card is showing, so the plate behind the card is
  unreadable; the blur clears on Continue. PASS.
- 2:54 film, six checks: an own-words step, its follow-up (with audio) and two choices gate Continue; gibberish
  refused with no reply; answers stored under the configuration's key. PASS.

## Re-run on this repository's page and sample (2026-10-08)

The page restyled (own colours and system fonts, no external requests), the guide's portrait removed, labels made
neutral; the engine script unchanged except optional `title`, `subtitle` and `poster` in the configuration. Sample
from `tools/player/make_sample_media.py` (24 s, three checks; parts of 16 s and 8 s).

| test | result |
|---|---|
| Loads: title and subtitle from the configuration, poster, 0:24, three markers, three caption cues | PASS |
| Seek to 12 s before check 1 snaps back to 7.3 s | PASS |
| Playback pauses at 7.70 s; card bottom-left; film blurred; captions hidden; question audio requested | PASS |
| Play refused while open; wrong option: its feedback, two options still live, no Continue; right option: Continue and confirmation audio | PASS |
| Continue: card hidden, film playing, captions showing; attempts stored (one wrong, one right) | PASS |
| Check 2 at 15.70 s, bottom-right: "fdsf", "aaaaaa bbbbbb cccc dddd" and "fdsf sdfsd qwrt zxcv" refused; a sentence saved and shown back; the follow-up plays its audio and refuses a one-word answer; the final choice gates Continue; both answers stored | PASS |
| Check 3 at 23.70 s; after the film ends all three markers are done and seeking anywhere is allowed | PASS |
| `?parts`: part 2 locked until part 1 and its checks are done; auto-advance to part 2; its check at 7.70 s reads "Check 3 · 3" | PASS |
| 390x844 phone: card is a bottom sheet (top 527 px, frame ends 332 px), no horizontal scroll | PASS |
| Console: no errors; every request local (page, configuration, poster, video with 206 Range replies, captions, audio) | PASS |

## Re-run after the filter and sample changes (2026-10-08)

The own-words filter's list of common words was then replaced with a short list of English function words, and the
sample checks were rewritten on 3.3 with the same steps, corners and times. The run was repeated on that version in
fresh isolated profiles, through the page's own controls.

| test | result |
|---|---|
| Check 1: a seek to 12 s snaps back to 7.3 s; playback pauses at 7.70 s, card bottom-left, film blurred, captions hidden; Play refused; a wrong option shows its feedback with the others live and no Continue; the right option gives Continue, which resumes the film with captions | PASS |
| Check 2 at 15.70 s, bottom-right, question audio played: "fdsf", "aaaaaa bbbbbb cccc dddd", "fdsf sdfsd qwrt zxcv" and "very jealous" refused with a fixed prompt and no reply; a sentence saved and shown back as "Your words"; the follow-up plays its audio, refuses "handkerchief" and saves a sentence; in the final choice a wrong option shows its own feedback, Play is refused, and the right option gives Continue | PASS |
| Check 3 at 23.70 s, bottom-left; the right option gives Continue | PASS |
| Stored: all three checks done, every choice attempt (one wrong), both own-words answers, none of the refused strings | PASS |
| After the last check, seeks to 2 s and 20 s are allowed | PASS |
| `?parts`: part 2 locked while part 1's checks are open; part 2 starts on its own after part 1; its check opens at 7.70 s into the part and reads "Check 3 · 3" | PASS |
| 390x844 phone: the card is a bottom sheet (top 527 px, frame ends 331 px), page 390 px wide, no horizontal scroll | PASS |
| Console: no messages; every request local, media answered with 206 | PASS |

Not tested: a person watching with sound; Safari and Firefox; a screen reader; opening the page from `file://`
(video seeking needs a Range server).
