/* Gated checks for the narrated opening (built by tools/player/build_parts.py). Check voice: none: a chime instead of a recorded question.
   `at` = end of the scene minus 0.3 s, relative to the video. */
window.OTHELLO_FILM_CHECKS = {
  "title": "Othello · Sample opening",
  "subtitle": "Sample media: three silent stills and sample checks",
  "poster": "media/poster.jpg",
  "storageKey": "othello-film-checks-sample-full",
  "parts": [
    {
      "film": "media/Othello-opening-full.mp4",
      "captions": "media/Othello-opening-full.vtt",
      "duration": 24.0,
      "stops": [
        {
          "id": "sample_warning",
          "afterScene": 1,
          "corner": "bl",
          "say": "in Act 3, Scene 3, what does Iago warn Othello against?",
          "ask": "media/sample-audio/ask.wav",
          "correct": "media/sample-audio/correct.wav",
          "steps": [
            {
              "kind": "choice",
              "stem": "In 3.3, what does Iago warn Othello against?",
              "answer": 0,
              "options": [
                "Jealousy",
                "Money",
                "The Senate"
              ],
              "feedback": [
                "Yes: “O, beware, my lord, of jealousy” (3.3).",
                "Not money. Iago warns Othello about a feeling.",
                "Not the Senate. Iago warns Othello about a feeling."
              ]
            }
          ],
          "at": 7.7,
          "sceneStart": 0
        },
        {
          "id": "sample_own_words",
          "afterScene": 2,
          "corner": "br",
          "say": "how does Othello feel by the end of Act 3, Scene 3?",
          "ask": "media/sample-audio/ask.wav",
          "correct": "media/sample-audio/correct.wav",
          "steps": [
            {
              "kind": "own_words",
              "stem": "How does Othello feel by the end of 3.3?",
              "prompt": "Your answer is saved. It is not marked."
            },
            {
              "kind": "probe",
              "stem": "What in the scene made you say that?",
              "prompt": "Name one line or moment.",
              "audio": "media/sample-audio/probe.wav"
            },
            {
              "kind": "choice",
              "stem": "In 3.3, what does Emilia pick up after Desdemona drops it?",
              "answer": 0,
              "options": [
                "A handkerchief",
                "A letter",
                "A ring"
              ],
              "feedback": [
                "Yes: the handkerchief, “her first remembrance from the Moor” (3.3).",
                "Not a letter. Think of the first gift Othello gave her.",
                "Not a ring. Think of the first gift Othello gave her."
              ]
            }
          ],
          "at": 15.7,
          "sceneStart": 8
        },
        {
          "id": "sample_proof",
          "afterScene": 3,
          "corner": "bl",
          "say": "in Act 3, Scene 3, what does Othello demand from Iago?",
          "ask": "media/sample-audio/ask.wav",
          "correct": "media/sample-audio/correct.wav",
          "steps": [
            {
              "kind": "choice",
              "stem": "In 3.3, what does Othello demand from Iago?",
              "answer": 0,
              "options": [
                "Proof he can see",
                "An apology",
                "More soldiers"
              ],
              "feedback": [
                "Yes: “give me the ocular proof” (3.3).",
                "Not an apology. Othello wants to be sure.",
                "Not more soldiers. Othello wants to be sure."
              ]
            }
          ],
          "at": 23.7,
          "sceneStart": 16
        }
      ],
      "part": 1,
      "title": "The full opening"
    }
  ]
};
