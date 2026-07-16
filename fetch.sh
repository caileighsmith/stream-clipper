#!/bin/bash
# fetch.sh — OPTIONAL input method: download a VOD via yt-dlp into source/.
#
# This does NOT replace the manual method. You can still just drop your own
# mp4 into source/ yourself — this script is only a convenience for pulling a
# Twitch / Kick (or any yt-dlp-supported) VOD by URL. Either way the file lands
# in source/ and the rest of the CLAUDE.md workflow is identical.
#
# Usage:
#   bash fetch.sh <URL> [output_name] [section]
#
# Examples:
#   bash fetch.sh https://www.twitch.tv/videos/123456789
#   bash fetch.sh https://www.twitch.tv/videos/123456789 speed
#   bash fetch.sh <URL> speed "*1:20:00-1:50:00"   # only that time range
#
# Notes:
#   - output_name defaults to "input" -> source/input.mp4
#   - section uses yt-dlp's --download-sections syntax (great for long VODs;
#     only downloads that window instead of the whole multi-hour stream).
#   - Kick is behind Cloudflare and may need browser impersonation. If a Kick
#     download fails: `pip install curl_cffi`, then re-run with:
#       IMPERSONATE=1 bash fetch.sh <kick-url>

URL="$1"
NAME="${2:-input}"
SECTION="$3"

if [ -z "$URL" ]; then
  echo "Usage: bash fetch.sh <URL> [output_name] [section e.g. *0:10:00-0:20:00]"
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "yt-dlp not found. Install it with: brew install yt-dlp"
  exit 1
fi

mkdir -p source

# Prefer best video+audio, remux to mp4 so the rest of the pipeline just works.
ARGS=( -f "bv*+ba/b" --merge-output-format mp4 -o "source/${NAME}.%(ext)s" )
[ -n "$SECTION" ] && ARGS+=( --download-sections "$SECTION" )
[ "$IMPERSONATE" = "1" ] && ARGS+=( --impersonate chrome )

echo "Fetching into source/${NAME}.mp4 ..."
if yt-dlp "${ARGS[@]}" "$URL"; then
  echo
  echo "Done -> source/${NAME}.mp4"
  echo "Next: tell Claude Code to run the workflow in CLAUDE.md on the video in /source."
else
  echo
  echo "Download failed."
  case "$URL" in
    *kick.com*)
      echo "Kick tip: pip install curl_cffi, then re-run with:"
      echo "  IMPERSONATE=1 bash fetch.sh \"$URL\"" ;;
    *)
      echo "Try updating yt-dlp: brew upgrade yt-dlp (or pip install -U yt-dlp)" ;;
  esac
  exit 1
fi
