---
name: reference-analyzer
description: Analyze a style-reference video for an episode. Use when the user provides a reference video (local path or YouTube/X/Vimeo URL), asks to "match the style of" a video, or after episode-initializer. Downloads the video, extracts frames with FFmpeg, inspects them visually, and writes style-guide/visual-rules.md.
---

# Reference Analyzer

Step 2: **episode-initializer → reference-analyzer → video-spec-builder → render-pipeline**

Requires an episode id. If unknown, list `episodes/` and ask which one.

## 1. Get the reference

Ask:
> Share a style reference video — a local file path or a URL (YouTube, X, Vimeo…). Or say "skip" to use the shared brand defaults.

On **skip**: write `visual-rules.md` from `shared/branding/brand.json` only, note "No reference video" at the top, and go to step 4.

## 2. Download + extract frames

```bash
python3 scripts/extract_frames.py <episode-id> "<path-or-url>"
```

Defaults: 1 fps sampling **and** scene-change frames (threshold 0.3), max 120 each, scaled to 1280px wide. Tune when needed:
- Long video (> 5 min): `--fps 0.2` to keep the frame count manageable.
- Fast-cut edit (few frames captured): `--scene-threshold 0.2`.
- Only scene changes: `--mode scene`.

Output:
- `style-guide/reference-video/ref.mp4` (+ `download.log` for URLs)
- `style-guide/frames/fps_*.jpg`, `scene_*.jpg`
- `style-guide/frames/metadata.json` — resolution, aspect ratio, fps, duration, scene-cut timestamps, cuts/min, avg shot length
- `manifest.json` → `style_reference` and `format` filled in

If `yt-dlp` is missing, tell the user to run `brew install yt-dlp` (don't install it yourself without asking). If the site blocks download, ask the user to download it manually and give a local path.

## 3. Look at the frames (multimodal analysis)

Read `metadata.json` first for the hard numbers. Then **view the frames with the Read tool** — all `scene_*` frames (up to ~40) plus every Nth `fps_*` frame to cover the timeline evenly (~20). Compare consecutive scene frames to infer transitions.

Only claim what the frames or metadata support. Motion curves and transition types are inferred from stills — mark them `(inferred)`; mark anything you can't tell as `unknown` rather than guessing.

## 4. Write `style-guide/visual-rules.md`

Use exactly this structure:

```markdown
# Visual Rules — <Episode Title>
Source: <url/path> · <W>x<H> · <aspect> · <fps>fps · <duration>s · analyzed <date>

## Summary
<3–4 sentences: overall vibe, what makes it recognizable>

## Typography
| Element | Font style (family guess, weight) | Size (% of frame height) | Placement | Case | Color | Effects (shadow/stroke/bg box) |
|---|---|---|---|---|---|---|
| Headline / title card | | | | | | |
| Captions / subtitles | | | | | | |
| Lower thirds | | | | | | |
| Callout labels | | | | | | |
Caption style: words per line, word-by-word highlight?, safe-zone margin.

## Color & Look
Palette (hex estimates), background treatment, contrast, grading (warm/cool/desaturated), grain/vignette.

## Motion Speed & Pacing
- Cuts per minute: <from metadata> · Avg shot length: <s>
- Pacing curve: <e.g. fast hook first 5s, then 3–4s shots>
- Transitions: hard cut / fade / whip pan / zoom / slide — with rough frequency
- Animation curves (inferred): ease-out pop-ins, spring overshoot, linear slides…
- Camera/screen motion: punch-ins, Ken Burns, zoom-to-cursor, static

## Aspect Ratio & Framing
- Canvas: <16:9 | 9:16 | 1:1> at <W>x<H>
- Margins/safe padding: <% of width/height>
- Subject framing: centered / rule-of-thirds / split-screen
- Screen recordings: device frame? rounded corners? drop shadow? background fill (blur/gradient/solid)?

## Graphics & Overlays
Lower-thirds, UI callouts/highlight boxes, arrows, emoji/stickers, progress bars, logos/watermark position.

## Do / Don't
- Do: <5 concrete rules to replicate>
- Don't: <3 things that would break the style>

## Frame References
| Frame | Timestamp | What it demonstrates |
|---|---|---|
```

## 5. Update + hand off

Set `manifest.json` → `"status": "style_analyzed"`. Summarize the 3–5 most defining style traits to the user, then continue with the `video-spec-builder` skill.
