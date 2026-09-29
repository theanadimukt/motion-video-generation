#!/usr/bin/env python3
"""Create an isolated episode folder with a starter manifest.json.

Usage:
    python scripts/init_episode.py "Building a SaaS in 24 Hours"
    python scripts/init_episode.py "My Title" --force   # overwrite existing manifest

Prints the episode directory path on success.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES_DIR = ROOT / "episodes"

SUBDIRS = [
    "style-guide/reference-video",
    "style-guide/frames",
    "assets/raw",
    "assets/audio",
    "assets/graphics",
    "transcripts",
    "output",
]


def to_kebab_case(title: str) -> str:
    """'Building a SaaS in 24 Hours!' -> 'building-a-saas-in-24-hours'."""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text)


def build_manifest(episode_id: str, title: str) -> dict:
    base = f"episodes/{episode_id}"
    return {
        "episode_id": episode_id,
        "title": title,
        "status": "initialized",
        "execution_mode": None,
        "render_engine": None,
        "style_reference": {
            "source_url_or_path": None,
            "downloaded_file": None,
            "frames_directory": f"{base}/style-guide/frames/",
            "analysis_file": f"{base}/style-guide/visual-rules.md",
        },
        "format": {
            "aspect_ratio": None,
            "width": None,
            "height": None,
            "fps": 30,
            "target_duration_sec": None,
        },
        "tabs": [],
        "audio": {
            "user_provided_voiceover": None,
            "voiceover_file": None,
            "script_text": None,
            "background_music": None,
            "music_ducking_db": -18,
            "music_base_volume_db": -6,
            "fade_in_sec": 1.5,
            "fade_out_sec": 2.0,
            "bpm": None,
            "bpm_sync_cuts": False,
        },
        "transcription": {"required": None, "file": None},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("title", help="Human-readable episode title")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing manifest.json")
    args = parser.parse_args()

    episode_id = to_kebab_case(args.title)
    if not episode_id:
        print("error: title produced an empty kebab-case id", file=sys.stderr)
        return 1

    episode_dir = EPISODES_DIR / episode_id
    manifest_path = episode_dir / "manifest.json"
    if manifest_path.exists() and not args.force:
        print(f"error: {manifest_path.relative_to(ROOT)} already exists (use --force to overwrite)", file=sys.stderr)
        return 2

    for sub in SUBDIRS:
        (episode_dir / sub).mkdir(parents=True, exist_ok=True)

    manifest_path.write_text(json.dumps(build_manifest(episode_id, args.title), indent=2, ensure_ascii=False) + "\n")
    print(episode_dir.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
