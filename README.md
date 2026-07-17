# Stream Clipper

Turn a local IRL stream VOD into short, captioned, vertical clips ready to
upload to TikTok — **100% local and free**. No cloud APIs for transcription or
video processing.

Transcription runs on [whisper.cpp](https://github.com/ggerganov/whisper.cpp)
(Metal-accelerated), and all cutting/cropping/caption-burning runs on FFmpeg
with VideoToolbox hardware encoding.

## How it works

This project is designed to be driven by **[Claude Code](https://claude.com/claude-code)**
following the instructions in [`CLAUDE.md`](CLAUDE.md). The workflow is a series
of deliberate steps:

1. **Transcribe** — whisper.cpp (medium model) transcribes the source VOD into a
   timestamped transcript (SRT + full JSON with word-level timestamps).
2. **Analyze** — the transcript is scanned for clip-worthy moments (funny beats,
   hot takes, emotional moments, self-contained stories) and a review file is
   written to `review/clip-review.md`. **Nothing is cut yet.**
3. **Approve** — you review the suggestions and reply with which clips to cut
   (e.g. "cut 1, 3, 5") plus any timestamp/crop tweaks.
4. **Cut + format** — approved clips are cut from the source, cropped to 9:16,
   captioned, and encoded to `clips/`.

To run it, drop an mp4 in `source/` and tell Claude Code:

> Run the workflow in CLAUDE.md on the video in /source.

## Requirements

- macOS on Apple Silicon
- [Homebrew](https://brew.sh)
- **FFmpeg built with libass** (for burning `.ass` captions — see note below)
- whisper.cpp (`whisper-cli`) + the **large-v3** model (better punctuation →
  better captions; run it with `-mc 0 -sns`, see notes)
- (optional) [yt-dlp](https://github.com/yt-dlp/yt-dlp) — to download a VOD by
  URL instead of supplying your own mp4

### ⚠️ FFmpeg must have the `ass` filter (libass)

Caption burning uses FFmpeg's `ass` filter, which requires FFmpeg to be built
with **libass**. Some Homebrew FFmpeg builds are minimal and omit it. Check with:

```bash
ffmpeg -filters | grep -w ass
```

If that prints nothing, your FFmpeg can't burn captions. Install the full build:

```bash
brew install ffmpeg-full
```

`ffmpeg-full` is keg-only (it won't shadow your existing `ffmpeg`), so invoke it
by its full path when burning captions:

```
/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg ...
```

## Setup

```bash
bash setup.sh
```

This installs FFmpeg + whisper.cpp and creates the working folders. Then
download a whisper model, e.g. the medium model:

```bash
bash "$(brew --prefix whisper-cpp)/share/whisper-cpp/models/download-ggml-model.sh" medium
```

## Fetching a VOD by URL (optional)

Instead of manually placing an mp4 in `source/`, you can download a Twitch or
Kick VOD (anything yt-dlp supports) with the helper script:

```bash
bash fetch.sh <URL> [output_name] [section]
```

```bash
# whole VOD -> source/input.mp4
bash fetch.sh https://www.twitch.tv/videos/123456789

# name it, so it lands at source/speed.mp4
bash fetch.sh https://www.twitch.tv/videos/123456789 speed

# only download a time window (great for multi-hour VODs)
bash fetch.sh https://www.twitch.tv/videos/123456789 speed "*1:20:00-1:50:00"
```

- **Twitch** is reliable. **Kick** sits behind Cloudflare and may need browser
  impersonation — if a download fails, `pip install curl_cffi` and re-run with
  `IMPERSONATE=1 bash fetch.sh <kick-url>`.
- The manual method (drop your own mp4 in `source/`) still works exactly the
  same — this is purely optional.
- Downloaded files land in `source/` and are git-ignored like any other input.

## Folder structure

```
/stream-clipper
  source/        <- raw input mp4 goes here          (git-ignored)
  transcripts/   <- whisper output: srt / json / txt (git-ignored)
  review/        <- markdown clip suggestions         (git-ignored)
  clips/         <- final rendered clips              (git-ignored)
  CLAUDE.md          <- workflow + rules for Claude Code
  make_captions.py   <- whisper JSON -> chunked .ass captions
  extract_segment.py <- slice word-level tokens for one clip's time range
  fetch.sh           <- (optional) download a VOD by URL into source/
  setup.sh
```

> **Note:** The working folders (`source/`, `transcripts/`, `review/`, `clips/`)
> are git-ignored and won't appear on a fresh clone. Running `setup.sh` recreates
> them.

## Scripts

- **`make_captions.py`** — converts whisper.cpp full-JSON (`-ojf`) into a styled
  `.ass` subtitle file, chunked into short 2–4 word phrases for TikTok-style
  burned-in captions. Handles whisper's sub-word tokenization (merges
  continuations, clitics, and punctuation into whole words) and filters special
  tokens.
- **`extract_segment.py`** — slices the word-level tokens for a single clip's
  time range out of the full transcript JSON and rebases their timestamps to the
  clip start, so captions line up when burned onto a cut clip.
- **`fetch.sh`** *(optional)* — downloads a Twitch/Kick (or any yt-dlp-supported)
  VOD by URL straight into `source/`. See "Fetching a VOD by URL" above.

## Format / output

- Target length 20–60s (hard cap 90s)
- 9:16 vertical, center crop by default
- Burned-in captions in short 2–4 word chunks
- mp4 / H.264, encoded with VideoToolbox

## Notes & caveats

- **Crop assumes a 1920×1080 landscape source** with a roughly centered subject.
  VODs that are already vertical, a different resolution, or where the subject
  roams will need the crop adjusted per source (check with `ffprobe` first).
- **Whisper hallucination loops** — over noisy sections (loud crowds, music) the
  transcript can loop a single phrase many times. large-v3 is especially prone
  to this, so it's run with `-mc 0 -sns` (no context carry-over + suppress
  non-speech tokens), which prevents the loops. Cleaning the audio first
  (denoise / voice-band filter, see the Transcribe step) also helps. Any loops
  that still slip through are audio artifacts, not real speech — skip them
  during analysis.
- Keep it local/free: no cloud transcription or clipping APIs unless you
  explicitly add one.
