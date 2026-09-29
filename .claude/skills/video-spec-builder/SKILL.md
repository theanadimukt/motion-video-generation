---
name: video-spec-builder
description: Interactive production-spec intake for an episode — screen/browser tabs and layout, voiceover vs. generated narration, music and ducking, and execution mode (prompt generation vs. direct render). Use after reference-analyzer, or when the user wants to define/edit an episode's spec or manifest.json.
---

# Video Spec Builder

Step 3: **episode-initializer → reference-analyzer → video-spec-builder → render-pipeline**

Requires an episode id (list `episodes/` and ask if unknown). Read `manifest.json` and `style-guide/visual-rules.md` first — pre-fill defaults from them (aspect ratio, pacing) and don't re-ask anything already set unless the user wants to change it.

## How to ask

- Use the `AskUserQuestion` tool for multiple-choice items (batch up to 4 related questions per call). Ask free-text items in plain chat.
- Go section by section. After each section, **write it to `manifest.json` immediately** (edit the JSON, keep formatting at 2-space indent) so progress survives an interruption.
- Paths in the manifest are **episode-relative** (`assets/audio/voiceover.wav`) except `shared/...` which is repo-relative.
- If the user gives a file that lives elsewhere, copy it into the right `assets/` subfolder and record the copied path.

## Section 1 — Format
- Aspect ratio: 16:9 / 9:16 / 1:1 / 4:5 (default: from reference). Resolution follows: 1920x1080, 1080x1920, 1080x1080, 1080x1350.
- Target duration (seconds). FPS (default 30).
→ `format`

## Section 2 — Tabs & Visual Layout
For each screen/browser tab that appears in the video, collect:
- name (e.g. "Dashboard View"), URL or app
- assets: screenshots/recordings (→ `assets/graphics/` or `assets/raw/`)
- capture dimensions (e.g. 1440x900), active window focus
- `focus_area` / highlight zones (e.g. `top-right-metrics`), callout text
- rough order/duration on screen

Keep asking "Another tab?" until done.
→ `tabs[]`: `{ "tab_id": "tab-1", "name", "url", "assets": [], "capture_dimensions": "1440x900", "focus_area", "callouts": [], "order": 1, "duration_sec" }`

## Section 3 — Audio & Narration
Ask exactly: **"Are you providing your own pre-recorded voiceover file?"**
- **Yes** → get the `.wav`/`.mp3` path, copy to `assets/audio/voiceover.<ext>`.
  Set `audio.user_provided_voiceover: true`, `audio.voiceover_file`, `transcription.required: false`.
  Skip script/TTS questions. (Ask only whether they want burned-in captions; if yes set `transcription.required: true` — captions will be derived from their audio, not a script.)
- **No** → ask for the raw script (paste, or a file path). Save it to `transcripts/script.md`.
  Set `audio.user_provided_voiceover: false`, `audio.script_text: "transcripts/script.md"`, `transcription.required: true`, `transcription.file: "transcripts/captions.srt"` (generated later).
  Ask voice preferences (gender/tone/pace/accent) → `audio.voice_style`.

## Section 4 — Music & Ducking
- Background track: list files in `shared/audio/` as options, or a new file path (copy to `assets/audio/`), or "none".
- Ducking under voice (default **-18 dB**) → `audio.music_ducking_db`
- Base music level (default -6 dB) → `audio.music_base_volume_db`
- Fade in / fade out seconds (defaults 1.5 / 2.0)
- BPM (if known) and whether cuts should snap to the beat → `audio.bpm`, `audio.bpm_sync_cuts`

## Section 5 — Execution Mode
Ask exactly: **"Do you want to generate a prompt/spec file for external creation, OR directly trigger local render engines (e.g., Remotion, FFmpeg, Invideo API)?"**
- Prompt/spec → `execution_mode: "prompt_generation"`; ask target tool (Invideo, Runway, Veo, Sora, generic) → `render_engine`.
- Direct render → `execution_mode: "direct_render"`; ask engine: `ffmpeg` (built in) | `remotion` | `hyperframes` | `invideo-api` → `render_engine`.

## Finish
1. Validate: every referenced file exists; `execution_mode` and `render_engine` set; if `user_provided_voiceover` is false a script exists.
2. Set `"status": "spec_complete"`.
3. Show a compact summary table of the spec and ask: **"Ready to run the render pipeline?"** On yes, continue with the `render-pipeline` skill.
