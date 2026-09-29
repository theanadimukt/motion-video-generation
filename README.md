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
