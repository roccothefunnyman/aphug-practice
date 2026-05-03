# AP Human Geography Practice

A static quiz app of 60 multiple-choice practice questions covering all 7 College Board AP Human Geography units. Built for studying for the AP exam.

Live: see GitHub Pages URL for this repo (`/app/`).

## What's here

- `source/AP_HuG_Practice_Questions.md` — the 60 questions, grouped by unit
- `source/AP_HuG_Practice_Answers.md` — the answer key with letter, headline explanation, topic code, and skill code per question
- `build.py` — parses the two source files into `app/questions.json`
- `app/` — the static web app (HTML / CSS / vanilla JS)

## Build

After editing either source file, rebuild the JSON the app loads:

```
py build.py
```

## Run locally

```
cd app
py -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` directly via `file://` will not work because the page uses `fetch()` to load `questions.json`.

## Deploy

GitHub Pages serves the entire repo from the root. The app lives at `/app/`.

If you change `app.js` or `style.css` in a way that depends on new HTML markup, bump the `?v=N` cache-buster on both `<script>` and `<link>` tags in `index.html`.

## App features

- 60 questions, shuffled per session
- Per-unit progress bars (7 AP HuG units)
- Picker modal: pick All, by unit, only Wrong, only Unanswered, only Correct
- Mastery persists in `localStorage` (`Reset progress` clears it)
- Light / dark theme
- Voice support: read-aloud (TTS), push-to-talk answers (ASR), and a hands-free voice-only mode
- Keyboard: `→` next, `←` back, `V` voice answer, `Esc` close any modal

## Adding or editing questions

1. Edit `source/AP_HuG_Practice_Questions.md`. Each question follows:
   ```
   ### Question N
   <stem, may include markdown tables for stimulus>

   A) <option>
   B) <option>
   C) <option>
   D) <option>
   ```
2. Edit `source/AP_HuG_Practice_Answers.md`. Each answer follows:
   ```
   **QN: <letter> — <headline>**
   <explanation paragraphs>
   *Topic X.Y | Skill N.A*
   ```
3. Run `py build.py` to refresh `app/questions.json`.
4. Commit and push. GitHub Pages redeploys automatically.
