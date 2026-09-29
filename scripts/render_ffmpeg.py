#!/usr/bin/env python3
"""Direct-render path: assemble an episode draft with FFmpeg from manifest.json.

What it does:
  1. Concatenates clips from assets/raw/ (sorted by filename, or `timeline` order
     in the manifest) scaled/padded to the manifest format.
  2. Mixes background music under the voiceover, ducking the music by
     `audio.music_ducking_db` only while speech is detected, with fade in/out.
  3. Burns in subtitles if `transcription.file` points to an .srt/.ass file.

Output: episodes/<id>/output/draft.mp4 (plus mix.wav).

Usage:
    python scripts/render_ffmpeg.py <episode-id> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def run(cmd: list[str], dry: bool) -> None:
    print("$", shlex.join(cmd))
    if not dry:
        subprocess.run(cmd, check=True)


def resolve(path: str | None, episode_dir: Path) -> Path | None:
    """Manifest paths may be episode-relative or repo-relative."""
    if not path:
        return None
    for base in (episode_dir, ROOT):
        p = (base / path).resolve()
        if p.exists():
            return p
    return None


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out or 0)


def speech_segments(voiceover: Path, noise_db: int = -35, min_silence: float = 0.4) -> list[tuple[float, float]]:
    """Invert FFmpeg silencedetect output into (start, end) speech windows."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(voiceover), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    total = duration(voiceover)
    segments, cursor = [], 0.0
    for s, e in zip(starts, ends + [total]):
        if s > cursor:
            segments.append((cursor, s))
        cursor = e
    if cursor < total:
        segments.append((cursor, total))
    return segments


def build_mix(manifest: dict, episode_dir: Path, out: Path, dry: bool) -> Path | None:
    audio = manifest.get("audio", {})
    vo = resolve(audio.get("voiceover_file"), episode_dir)
    music = resolve(audio.get("background_music"), episode_dir)
    if not vo and not music:
        return None

    base_db = audio.get("music_base_volume_db", -6)
    duck_db = audio.get("music_ducking_db", -18)
    fade_in = audio.get("fade_in_sec", 1.5)
    fade_out = audio.get("fade_out_sec", 2.0)

    if vo and not music:
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(vo), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", str(out)], dry)
        return out

    total = duration(vo) + 1.0 if vo else duration(music)
    music_chain = [f"volume={base_db}dB"]
    if vo:
        duck_windows = "+".join(f"between(t,{max(a - 0.15, 0):.2f},{b + 0.25:.2f})" for a, b in speech_segments(vo))
        if duck_windows:
            music_chain.append(f"volume={duck_db}dB:enable='{duck_windows}'")
    music_chain += [
        f"afade=t=in:st=0:d={fade_in}",
        f"afade=t=out:st={max(total - fade_out, 0):.2f}:d={fade_out}",
        f"atrim=0:{total:.2f}",
    ]

    inputs = ["-stream_loop", "-1", "-i", str(music)]
    if vo:
        inputs = ["-i", str(vo)] + inputs
        graph = (f"[1:a]{','.join(music_chain)}[m];"
                 f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[v];"
                 f"[v][m]amix=inputs=2:duration=longest:normalize=0[a]")
    else:
        graph = f"[0:a]{','.join(music_chain)}[a]"
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", graph, "-map", "[a]", str(out)], dry)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("episode_id")
    p.add_argument("--dry-run", action="store_true", help="Print FFmpeg commands without running them")
    args = p.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("error: ffmpeg not found. Install with: brew install ffmpeg")

    episode_dir = ROOT / "episodes" / args.episode_id
    manifest = json.loads((episode_dir / "manifest.json").read_text())
    fmt = manifest.get("format", {})
    w, h, fps = fmt.get("width") or 1920, fmt.get("height") or 1080, fmt.get("fps") or 30
    out_dir = episode_dir / "output"
    out_dir.mkdir(exist_ok=True)

    timeline = manifest.get("timeline") or []
    clips = [resolve(c.get("file"), episode_dir) for c in timeline] if timeline else sorted(
        f for f in (episode_dir / "assets" / "raw").iterdir() if f.suffix.lower() in VIDEO_EXT)
    clips = [c for c in clips if c]
    if not clips:
        sys.exit("error: no clips in assets/raw/ and no resolvable `timeline` entries in manifest.json")

    mix = build_mix(manifest, episode_dir, out_dir / "mix.wav", args.dry_run)

    norm = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}"
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    graph = ";".join(f"[{i}:v]{norm}[v{i}]" for i in range(len(clips)))
    graph += ";" + "".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[vc]"

    subs = resolve(manifest.get("transcription", {}).get("file"), episode_dir)
    if subs:
        escaped = str(subs).replace(":", r"\:").replace("'", r"\'")
        graph += f";[vc]subtitles='{escaped}'[vout]"
    else:
        graph += ";[vc]null[vout]"

    cmd = ["ffmpeg", "-y", "-hide_banner", *inputs]
    maps = ["-map", "[vout]"]
    if mix:
        cmd += ["-i", str(mix)]
        maps += ["-map", f"{len(clips)}:a", "-shortest"]
    cmd += ["-filter_complex", graph, *maps,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_dir / "draft.mp4")]
    run(cmd, args.dry_run)
    print(f"\n✓ {'(dry run) ' if args.dry_run else ''}{(out_dir / 'draft.mp4').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
