---
name: episode-initializer
description: Start a new video episode. Use when the user wants to create, start, or set up a new episode/video, or says "new episode". Asks for the title, converts it to kebab-case, creates the isolated folder under episodes/ with a starter manifest.json, then hands off to reference-analyzer.
---

# Episode Initializer

Step 1 of the production pipeline:
**episode-initializer → reference-analyzer → video-spec-builder → render-pipeline**

## Steps

1. **Get the title.** If the user didn't give one, ask:
   > What's the episode title? (e.g. "Building a SaaS in 24 Hours")

2. **Create the episode** from the repo root:
   ```bash
   python3 scripts/init_episode.py "<Episode Title>"
   ```
   - Prints `episodes/<kebab-case-id>` on success.
   - Exit code 2 = the episode already exists. Ask the user whether to **resume** it (skip to whichever step is incomplete, judged by `manifest.json` `status`) or **overwrite** it (`--force` — confirm first, this resets the manifest).

3. **Confirm to the user** the id and the created layout:
   ```
   episodes/<id>/
   ├── manifest.json
   ├── style-guide/{reference-video,frames}/  (+ visual-rules.md later)
   ├── assets/{raw,audio,graphics}/
   ├── transcripts/
   └── output/
   ```

4. **Hand off.** Immediately continue with the `reference-analyzer` skill for this episode id (ask for the style reference video). Don't wait for the user to invoke it.

## Rules
- Never hand-roll the kebab-case — always use the script so ids stay consistent.
- One episode = one folder. Never write episode files outside `episodes/<id>/`. Reusable assets go in `shared/`.
