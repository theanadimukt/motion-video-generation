---
name: render-pipeline
description: Produce the episode output from a completed manifest.json — either a structured prompt/spec package for external tools (prompt_generation) or a local render via FFmpeg/Remotion/HyperFrames/Invideo (direct_render). Use after video-spec-builder, or when the user says render, build, export, or generate prompts for an episode.
---

# Render Pipeline

Step 4: **episode-initializer → reference-analyzer → video-spec-builder → render-pipeline**

## Preflight
1. Load `episodes/<id>/manifest.json` and `style-guide/visual-rules.md`.
2. If `status` isn't `spec_complete` (or later), or `execution_mode` is null, stop and run `video-spec-builder` first.
3. Load `shared/branding/brand.json` — reference-video rules win on style; brand wins on logo, colors, and fonts when they conflict (note conflicts in the output).

## Shared step — Shot list
Build `output/shot-list.json` first, in both modes. Derive shot lengths from the pacing in visual-rules.md (avg shot length, cuts/min); if `audio.bpm_sync_cuts`, snap cut points to beats (`60 / bpm` seconds). Sum to `format.target_duration_sec`.

```json
[
  { "shot": 1, "start": 0.0, "end": 3.2, "type": "title-card | screen-capture | b-roll | talking-head",
    "tab_id": "tab-1", "visual": "…", "on_screen_text": "…", "narration": "…",
    "motion": "punch-in 110% on focus_area, ease-out 0.4s", "transition_in": "hard cut" }
]
```
Narration comes from `transcripts/script.md` (generated voice) or, for a user voiceover, from a transcript of it if one exists — otherwise leave `narration` as timing notes.

## Mode A — `prompt_generation`
Write to `output/`:
- **`production-spec.md`** — human-readable brief: overview, format, style rules (condensed from visual-rules.md), shot-by-shot table, audio mix instructions (ducking dB, fades, BPM), asset list with paths.
- **`prompts/shot-XX.md`** — one self-contained prompt per shot for the target `render_engine`. Each includes: aspect ratio + resolution, duration, subject/visual, camera/motion, typography + on-screen text, color/look, transition in/out, and "match reference style: <3 key traits>". Keep each prompt standalone — external tools don't see the other files.
- **`prompt-package.json`** — machine-readable `{ episode_id, engine, format, shots: [{ shot, duration, prompt, assets }] }`.

Tune wording to the engine: Veo/Sora/Runway → cinematic scene descriptions; Invideo → script + scene notes + stock/media directions; generic → the full spec.

## Mode B — `direct_render`

### `ffmpeg` (built in)
```bash
python3 scripts/render_ffmpeg.py <episode-id> --dry-run   # show the plan
python3 scripts/render_ffmpeg.py <episode-id>
```
Concatenates `assets/raw/` clips (or `manifest.timeline[]` order: `[{ "file": "assets/raw/x.mp4" }]`), normalizes to `format` W×H/fps, mixes music ducked by `music_ducking_db` wherever speech is detected in the voiceover, applies fades, burns `transcription.file` subtitles if present. Output: `output/draft.mp4`, `output/mix.wav`.

### `remotion` / `hyperframes`
Scaffold the project in `output/<engine>-project/`, generate compositions from `shot-list.json` + visual-rules.md (reuse components from `shared/templates/`), then render to `output/final.mp4`. For HyperFrames, use the `hyperframes` skill. Ask before installing npm packages.

### `invideo-api`
Build the request payload from `prompt-package.json` into `output/invideo-request.json`. **Do not call the API without explicit confirmation** — it's an external, possibly billed service. Needs `INVIDEO_API_KEY` in the environment; never write keys to files.

### Generated voiceover / captions
If `user_provided_voiceover` is false: generate TTS from `transcripts/script.md` (ask which provider; the `media-use` skill can do it) → `assets/audio/voiceover.wav`, then transcribe it to `transcripts/captions.srt` and set `transcription.file`. Skip this entirely when the user supplied their own voiceover and didn't request captions.

## Finish
- Verify outputs exist (and for renders, `ffprobe` duration/resolution match `format`).
- Set `manifest.status` to `"prompts_generated"` or `"rendered"` and append to `manifest.outputs[]`: `{ "file", "created_at", "mode" }`.
- Report the output paths to the user.
