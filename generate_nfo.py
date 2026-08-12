#!/usr/bin/env python3
"""
generate_nfo.py — Auto-generates Kodi-format NFO files for ErsatzTV's
Music Video Credits Mode, matching the real folder structure:

    /opt/media/<Artist Name>/<Song Title>.mkv   (or .mp4, .avi, .mov, .m4v)

For every video file found WITHOUT a matching .nfo beside it, creates:

    /opt/media/<Artist Name>/<Song Title>.nfo

Existing .nfo files are never touched or overwritten — safe to re-run
as often as you want. Meant to run on a cron timer (every 20-30 min),
not by hand.

Usage:
    python3 generate_nfo.py                  # uses /opt/media
    python3 generate_nfo.py /some/other/path # override the media root
"""

import sys
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

MEDIA_ROOT = "/opt/media"
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
LOG_FILE = "generate_nfo.log"  # written inside the media root


def log(media_root, message):
    """Timestamped logging — cron jobs have no console to watch live."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with open(Path(media_root) / LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # a logging failure should never crash the actual job


def generate_nfo_content(artist, song):
    """Kodi-format NFO matching ErsatzTV's Music Video Credits Mode."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<musicvideo>\n'
        f'  <title>{escape(song)}</title>\n'
        f'  <artist>{escape(artist)}</artist>\n'
        '</musicvideo>\n'
    )


def process_media_root(media_root):
    media_path = Path(media_root)
    if not media_path.exists():
        log(media_root, f"ERROR: media root does not exist: {media_root}")
        return {"created": 0, "skipped": 0, "errors": 1}

    created, skipped, errors = 0, 0, 0

    for artist_folder in sorted(media_path.iterdir()):
        if not artist_folder.is_dir():
            continue  # ignore stray files sitting directly in the media root

        artist_name = artist_folder.name.strip()
        if not artist_name:
            continue

        for video_file in sorted(artist_folder.iterdir()):
            if not video_file.is_file():
                continue
            if video_file.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            nfo_path = video_file.with_suffix(".nfo")
            if nfo_path.exists():
                skipped += 1
                continue  # never overwrite — could be a manually-edited NFO

            song_name = video_file.stem.strip()

            try:
                content = generate_nfo_content(artist_name, song_name)
                with open(nfo_path, "w", encoding="utf-8") as f:
                    f.write(content)
                log(media_root, f"Created: {nfo_path.relative_to(media_path)}  (Artist: {artist_name} / Song: {song_name})")
                created += 1
            except Exception as e:
                log(media_root, f"ERROR creating NFO for {video_file}: {e}")
                errors += 1

    log(media_root, f"Run complete. Created: {created}, Skipped (already exist): {skipped}, Errors: {errors}")
    return {"created": created, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else MEDIA_ROOT
    process_media_root(root)
