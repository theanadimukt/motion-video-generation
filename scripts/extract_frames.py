#!/usr/bin/env python3
"""Fetch a style-reference video and sample frames from it with FFmpeg.

The source can be a local file or a URL (YouTube, X, Vimeo, ... via yt-dlp).
Frames land in episodes/<id>/style-guide/frames/ and a metadata.json with
probe data + scene-cut statistics is written next to them, which the
reference-analyzer skill uses to build visual-rules.md.

Usage:
    python scripts/extract_frames.py <episode-id> <path-or-url> [--mode fps|scene|both]
        [--fps 1] [--scene-threshold 0.3] [--max-frames 120] [--width 1280]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def require(binary: str, hint: str) -> None:
    if shutil.which(binary) is None:
        sys.exit(f"error: '{binary}' not found on PATH. Install with: {hint}")


def is_url(source: str) -> bool:
    return bool(re.match(r"^https?://", source))


def download(url: str, dest_dir: Path) -> Path:
    require("yt-dlp", "brew install yt-dlp  (or: pipx install yt-dlp)")
    dest_dir.mkdir(parents=True, exist_ok=True)
    log = dest_dir / "download.log"
    cmd = [
        "yt-dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", str(dest_dir / "ref.%(ext)s"),
        "--no-playlist",
        "--print", "after_move:filepath",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(f"$ {' '.join(cmd)}\n\n{result.stdout}\n{result.stderr}")
    if result.returncode != 0:
        sys.exit(f"error: yt-dlp failed (see {log.relative_to(ROOT)})")
    path = Path(result.stdout.strip().splitlines()[-1])
    return path if path.exists() else dest_dir / "ref.mp4"


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    num, _, den = v.get("avg_frame_rate", "0/1").partition("/")
    fps = round(float(num) / float(den or 1), 3) if float(den or 1) else 0
    return {
        "width": w,
        "height": h,
        "aspect_ratio": classify_ratio(w, h),
        "fps": fps,
        "duration_sec": round(float(data["format"].get("duration", 0)), 2),
        "has_audio": any(s.get("codec_type") == "audio" for s in data["streams"]),
    }


def classify_ratio(w: int, h: int) -> str:
    if not w or not h:
        return "unknown"
    r = w / h
    for name, target in {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 0.8, "4:3": 4 / 3, "21:9": 21 / 9}.items():
        if abs(r - target) < 0.03:
            return name
    return f"{w}:{h}"


def detect_scene_cuts(video: Path, threshold: float) -> list[float]:
    """Return timestamps (seconds) where FFmpeg's scene score exceeds threshold."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video), "-an",
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", result.stderr)]


def extract(video: Path, frames_dir: Path, vf: str, prefix: str, max_frames: int) -> list[Path]:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
         "-vf", vf, "-fps_mode", "vfr", "-frames:v", str(max_frames), "-q:v", "3",
         str(frames_dir / f"{prefix}_%04d.jpg")],
        check=True,
    )
    return sorted(frames_dir.glob(f"{prefix}_*.jpg"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("episode_id")
    p.add_argument("source", help="Local video path or URL")
    p.add_argument("--mode", choices=["fps", "scene", "both"], default="both")
    p.add_argument("--fps", type=float, default=1.0, help="Frames per second for fps mode")
    p.add_argument("--scene-threshold", type=float, default=0.3)
    p.add_argument("--max-frames", type=int, default=120, help="Cap per mode")
    p.add_argument("--width", type=int, default=1280, help="Scale frames to this width (keeps ratio)")
    args = p.parse_args()

    require("ffmpeg", "brew install ffmpeg")
    require("ffprobe", "brew install ffmpeg")

    episode_dir = ROOT / "episodes" / args.episode_id
    if not (episode_dir / "manifest.json").exists():
        sys.exit(f"error: episode '{args.episode_id}' not initialized. Run scripts/init_episode.py first.")

    ref_dir = episode_dir / "style-guide" / "reference-video"
    frames_dir = episode_dir / "style-guide" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.jpg"):
        old.unlink()

    if is_url(args.source):
        video = download(args.source, ref_dir)
    else:
        src = Path(args.source).expanduser().resolve()
        if not src.exists():
            sys.exit(f"error: file not found: {src}")
        ref_dir.mkdir(parents=True, exist_ok=True)
        video = ref_dir / f"ref{src.suffix.lower() or '.mp4'}"
        if src != video:
            shutil.copy2(src, video)

    info = probe(video)
    scale = f"scale='min({args.width},iw)':-2"
    frames: list[Path] = []
    if args.mode in ("fps", "both"):
        frames += extract(video, frames_dir, f"fps={args.fps},{scale}", "fps", args.max_frames)
    if args.mode in ("scene", "both"):
        frames += extract(video, frames_dir, f"select='gt(scene,{args.scene_threshold})',{scale}", "scene", args.max_frames)

    cuts = detect_scene_cuts(video, args.scene_threshold)
    minutes = info["duration_sec"] / 60 if info["duration_sec"] else 0
    shots = [b - a for a, b in zip([0.0, *cuts], [*cuts, info["duration_sec"]]) if b > a]
    metadata = {
        "source": args.source,
        "video_file": str(video.relative_to(ROOT)),
        **info,
        "scene_threshold": args.scene_threshold,
        "scene_cut_timestamps": [round(c, 2) for c in cuts],
        "cuts_per_minute": round(len(cuts) / minutes, 1) if minutes else None,
        "avg_shot_length_sec": round(sum(shots) / len(shots), 2) if shots else None,
        "frame_count": len(frames),
        "frames": [f.name for f in frames],
    }
    (frames_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    manifest_path = episode_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["style_reference"].update({
        "source_url_or_path": args.source,
        "downloaded_file": str(video.relative_to(ROOT)),
    })
    manifest.setdefault("format", {})
    for key in ("aspect_ratio", "width", "height"):
        if not manifest["format"].get(key):
            manifest["format"][key] = info[key]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps({k: metadata[k] for k in (
        "video_file", "width", "height", "aspect_ratio", "fps", "duration_sec",
        "cuts_per_minute", "avg_shot_length_sec", "frame_count")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
