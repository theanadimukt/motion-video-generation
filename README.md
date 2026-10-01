# motion-video-generation

A modular, episode-based video production engine run by custom Claude Code skills. Each episode lives in its own folder. Claude collects the assets, extracts frames from a style-reference video, walks you through the spec, and then either writes a prompt package for external tools or renders locally.

## Quick start

```bash
brew install ffmpeg yt-dlp      # system deps
cd motion-video-generation
claude                          # then: "start a new episode"
```

## Pipeline

| # | Skill | What it does | Writes |
|---|---|---|---|
| 1 | `episode-initializer` | Asks for the title, converts it to kebab-case, and creates the folder | `episodes/<id>/manifest.json` |
| 2 | `reference-analyzer` | Downloads the reference video, samples frames (1 fps + scene cuts), and analyzes them visually | `style-guide/frames/`, `visual-rules.md` |
| 3 | `video-spec-builder` | Interactive intake: format, tabs/layout, voiceover vs. script, music and ducking, execution mode | `manifest.json` |
| 4 | `render-pipeline` | `prompt_generation` → spec, per-shot prompts and JSON package; `direct_render` → FFmpeg/Remotion/HyperFrames/Invideo | `output/` |

## Generating a video, step by step

Say "new episode" or "make a video" in Claude Code and it runs all four steps in order, handing off between them on its own. Each step writes its progress to `manifest.json`, so you can stop and come back later. The manifest's `status` field shows where you left off:

```
initialized → style_analyzed → spec_complete → prompts_generated | rendered
```

### Before you start

- Install the system tools: `brew install ffmpeg yt-dlp`. You only need `yt-dlp` to download reference videos from URLs; it can also be installed with `pip install -e ".[download]"`.
- Use Python 3.10 or newer. The scripts need only the standard library.
- Optionally, put reusable assets in `shared/`:
  - brand colors, fonts and watermark in `shared/branding/brand.json`
  - music beds and SFX in `shared/audio/`
  - compositions in `shared/templates/`
- Have these ready if you have them:
  - a style-reference video (a local file or a YouTube/X/Vimeo URL)
  - screenshots or screen recordings
  - a voiceover file or a script
  - a music track

### Step 1 — Create the episode (`episode-initializer`)

1. Give the episode title, for example "Building a SaaS in 24 Hours".
2. Claude runs `python3 scripts/init_episode.py "<title>"`. The script turns the title into a kebab-case id (`building-a-saas-in-24-hours`) and creates `episodes/<id>/`. The new folder contains:
   - a starter `manifest.json`
   - `style-guide/`
   - `assets/{raw,audio,graphics}/`
   - `transcripts/`
   - `output/`
3. If the episode already exists, the script exits with code 2. You then choose:
   - **Resume:** continue from the manifest's current `status`.
   - **Overwrite:** run again with `--force`. This resets the manifest.

Result: `status: "initialized"`.

### Step 2 — Analyze the style reference (`reference-analyzer`)

1. Give a reference video path or URL, or say **skip** to use only `shared/branding/brand.json`.
2. Claude runs `python3 scripts/extract_frames.py <id> "<path-or-url>"`. The script:
   - downloads the video to `style-guide/reference-video/ref.mp4`, writing a `download.log` for URLs
   - samples frames at 1 fps (`fps_*.jpg`) and at scene changes (`scene_*.jpg`, threshold 0.3), at most 120 of each, scaled to 1280 px wide
   - writes `style-guide/frames/metadata.json` with resolution, aspect ratio, fps, duration, scene-cut timestamps, cuts per minute and average shot length
   - fills in `style_reference` and `format` in the manifest
3. You can tune extraction with these flags:
   - `--fps 0.2` for videos longer than 5 minutes
   - `--scene-threshold 0.2` for fast-cut edits
   - `--mode scene` to keep only scene-change frames
   - `--max-frames N` to cap the number of frames per mode
   - `--width N` to change the frame width
4. Claude looks at the frames and writes `style-guide/visual-rules.md`. It covers:
   - typography
   - color and look
   - motion speed and pacing
   - aspect ratio and framing
   - graphics and overlays
   - do/don't rules
   - a table of reference frames

   Anything Claude infers from still frames, such as transitions or easing, is marked `(inferred)`.

Result: `status: "style_analyzed"`.

### Step 3 — Build the spec (`video-spec-builder`)

Claude asks one section at a time and saves each section to `manifest.json` as soon as you answer it:

1. **Format:**
   - aspect ratio: 16:9, 9:16, 1:1 or 4:5. The resolution follows from it.
   - target duration
   - fps (default 30)
2. **Tabs and layout:** for each screen or browser tab, give:
   - its name and URL
   - assets, which Claude copies into `assets/graphics/` or `assets/raw/`
   - capture size
   - `focus_area` and callouts
   - its order and duration
3. **Audio and narration:** "Are you providing your own pre-recorded voiceover file?"
   - **Yes:** Claude copies the file to `assets/audio/voiceover.<ext>`. Captions are optional.
   - **No:** paste a script. Claude saves it to `transcripts/script.md`, asks about voice style, and generates TTS and captions during rendering.
4. **Music and ducking:**
   - track: one from `shared/audio/`, a new file, or none
   - ducking under the voice (default -18 dB)
   - base level (default -6 dB)
   - fade in and fade out (defaults 1.5 s and 2.0 s)
   - BPM, and whether cuts should snap to the beat
5. **Execution mode:**
   - `prompt_generation`: a spec and prompts for an external tool (Invideo, Runway, Veo, Sora or generic).
   - `direct_render`: a local render with `ffmpeg`, `remotion`, `hyperframes` or `invideo-api`.

Claude then checks that every referenced file exists, shows a summary and asks "Ready to run the render pipeline?"

Result: `status: "spec_complete"`.

### Step 4 — Render or generate prompts (`render-pipeline`)

1. **Preflight:** Claude loads the manifest, `visual-rules.md` and `brand.json`. When they conflict, the reference wins on style and the brand wins on logo, colors and fonts.
2. **Shot list:** in both modes, Claude first writes `output/shot-list.json`:
   - Shot lengths come from the reference pacing.
   - If `bpm_sync_cuts` is set, cuts snap to beats.
   - The shots add up to `target_duration_sec`.
3. **Mode A — `prompt_generation`:** writes three things to `output/`:
   - `production-spec.md`, a brief for people
   - `prompts/shot-XX.md`, one standalone prompt per shot, worded for the target engine
   - `prompt-package.json`, the same content in machine-readable form

   Feed these to your external tool.
4. **Mode B — `direct_render`:**
   - **ffmpeg:**
     1. Put clips in `assets/raw/`, or set their order in `manifest.timeline[]`.
     2. Run `python3 scripts/render_ffmpeg.py <id> --dry-run` to review the plan.
     3. Run it again without `--dry-run` to render. The script:
        - normalizes the clips to the format's size and fps and concatenates them
        - ducks the music under detected speech
        - applies the fades
        - burns in subtitles if there are any

        It writes `output/draft.mp4` and `output/mix.wav`.
   - **remotion / hyperframes:** Claude scaffolds `output/<engine>-project/`, builds compositions from the shot list and style rules, and renders `output/final.mp4`. It asks before installing npm packages.
   - **invideo-api:** Claude writes `output/invideo-request.json`. It calls the API only after you confirm, using `INVIDEO_API_KEY` from your environment.
   - **Generated voiceover:** if you didn't provide a voiceover, Claude generates TTS from `transcripts/script.md` into `assets/audio/voiceover.wav`. It asks you which provider to use first. It then transcribes the audio to `transcripts/captions.srt`.
5. **Finish:** Claude checks the outputs. For renders, it uses `ffprobe` to compare duration and resolution with `format`. It then appends an entry to `manifest.outputs[]`.

Result: `status: "prompts_generated"` or `"rendered"`.

### Resuming or re-running a step

- **Pick up where you left off:** say "resume episode `<id>`". Claude reads `status` and starts at the first step that isn't done.
- **Run a single step:** name its skill, for example "re-analyze the reference for `<id>`" or "edit the spec for `<id>`".
- **Re-render after changing assets:** run `python3 scripts/render_ffmpeg.py <id>` again.

## Layout

```
.claude/skills/        episode-initializer · reference-analyzer · video-spec-builder · render-pipeline
shared/branding/       brand.json (colors, fonts, watermark), logos
shared/templates/      reusable compositions
shared/audio/          default music beds, SFX
episodes/<id>/
  manifest.json
  style-guide/{reference-video/, frames/, visual-rules.md}
  assets/{raw/, audio/, graphics/}
  transcripts/
  output/
scripts/
  init_episode.py      title → kebab-case episode scaffold
  extract_frames.py    yt-dlp download + ffmpeg frame sampling + scene-cut stats
  render_ffmpeg.py     concat clips, duck music under VO, burn subtitles
```

## Scripts (usable without Claude)

```bash
python3 scripts/init_episode.py "Building a SaaS in 24 Hours"
python3 scripts/extract_frames.py building-a-saas-in-24-hours "https://youtube.com/watch?v=..."
python3 scripts/extract_frames.py building-a-saas-in-24-hours ~/Desktop/ref.mp4 --mode scene --scene-threshold 0.25
python3 scripts/render_ffmpeg.py building-a-saas-in-24-hours --dry-run
```

## Manifest

```json
{
  "episode_id": "building-a-saas-in-24-hours",
  "title": "Building a SaaS in 24 Hours",
  "status": "initialized | style_analyzed | spec_complete | prompts_generated | rendered",
  "execution_mode": "prompt_generation | direct_render",
  "render_engine": "ffmpeg | remotion | hyperframes | invideo-api | veo | runway | ...",
  "style_reference": {
    "source_url_or_path": "...",
    "downloaded_file": "episodes/<id>/style-guide/reference-video/ref.mp4",
    "frames_directory": "episodes/<id>/style-guide/frames/",
    "analysis_file": "episodes/<id>/style-guide/visual-rules.md"
  },
  "format": { "aspect_ratio": "16:9", "width": 1920, "height": 1080, "fps": 30, "target_duration_sec": 90 },
  "tabs": [{ "tab_id": "tab-1", "name": "Dashboard View", "assets": ["assets/graphics/tab1-preview.png"], "focus_area": "top-right-metrics" }],
  "audio": {
    "user_provided_voiceover": true,
    "voiceover_file": "assets/audio/voiceover.wav",
    "script_text": null,
    "background_music": "shared/audio/ambient-lofi.mp3",
    "music_ducking_db": -18, "music_base_volume_db": -6,
    "fade_in_sec": 1.5, "fade_out_sec": 2.0, "bpm": null, "bpm_sync_cuts": false
  },
  "transcription": { "required": false, "file": null }
}
```

Paths inside the manifest are relative to the episode folder, except `shared/...`, which is relative to the repo root.

## Audio ducking

`render_ffmpeg.py` finds the speech windows in the voiceover with `silencedetect`. It lowers the music by `music_ducking_db` only inside those windows, with 150 ms of pre-roll and 250 ms of release, and applies the fade-in and fade-out. The voice is loudness-normalized to -16 LUFS.
