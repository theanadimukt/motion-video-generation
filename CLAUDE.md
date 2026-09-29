# motion-video-generation

Episode-based video production engine. Every video is an isolated folder in `episodes/<kebab-case-id>/` driven by its `manifest.json`.

## Pipeline (skills in `.claude/skills/`)
1. `episode-initializer` — title → kebab-case folder + manifest (`scripts/init_episode.py`)
2. `reference-analyzer` — reference video → frames → `style-guide/visual-rules.md` (`scripts/extract_frames.py`)
3. `video-spec-builder` — interactive intake → `manifest.json` (tabs, audio, music, execution mode)
4. `render-pipeline` — prompt package **or** direct render (`scripts/render_ffmpeg.py`)

When the user says "new episode" / "make a video", start at step 1 and chain through.

## Rules
- Never write episode files outside that episode's folder; reusable things go in `shared/`.
- Manifest paths are episode-relative, except `shared/...` (repo-relative).
- `manifest.status` progresses: initialized → style_analyzed → spec_complete → prompts_generated | rendered.
- Ask before installing tools/packages or calling paid external APIs.
