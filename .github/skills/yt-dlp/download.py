#!/usr/bin/env python3
"""
yt-dlp download skill.

Usage: python download.py <url>
Output: JSON to stdout
  Success: {"ok": true, "file_path": "...", "title": "...", "filesize": 12345}
  Failure: {"ok": false, "error": "..."}

Downloads video in pre-merged 360p format (no ffmpeg required).
"""

import json
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "No URL provided"}))
        sys.exit(1)

    url = sys.argv[1]
    output_dir = "/tmp/yt-dlp-output"
    os.makedirs(output_dir, exist_ok=True)

    # Use video ID for safe filenames
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "yt_dlp",
                "-f", "b[height<=360]/b",  # pre-merged 360p, fallback to best pre-merged
                "-o", output_template,
                "--no-playlist",
                "--no-overwrites",
                "--restrict-filenames",
                "--print-json",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=240,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "error": "Download timed out (240s)"}))
        sys.exit(1)

    if result.returncode != 0:
        error_msg = result.stderr.strip()[-500:] if result.stderr else "Unknown error"
        print(json.dumps({"ok": False, "error": error_msg}))
        sys.exit(1)

    # Parse yt-dlp JSON output (last line, in case of progress output)
    try:
        lines = result.stdout.strip().split("\n")
        info = json.loads(lines[-1])
    except (json.JSONDecodeError, IndexError):
        print(json.dumps({"ok": False, "error": "Failed to parse yt-dlp output"}))
        sys.exit(1)

    filepath = info.get("_filename", "")
    if not filepath or not os.path.exists(filepath):
        # Reconstruct from parsed info using same %(id)s.%(ext)s template
        video_id = info.get("id")
        ext = info.get("ext")
        if video_id and ext:
            filepath = os.path.join(output_dir, f"{video_id}.{ext}")
        if not filepath or not os.path.exists(filepath):
            print(json.dumps({"ok": False, "error": "Downloaded file not found"}))
            sys.exit(1)

    filesize = os.path.getsize(filepath)
    title = info.get("title", "Unknown")

    print(json.dumps({
        "ok": True,
        "file_path": filepath,
        "title": title,
        "filesize": filesize,
    }))


if __name__ == "__main__":
    main()
