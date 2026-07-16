# Stream Clipper — Project Instructions

## What this project does
Takes a local IRL stream VOD (mp4), transcribes it, identifies clip-worthy
moments, and cuts/formats short clips for TikTok (@litsocialmoments).

## Environment
- Platform: macOS (Apple Silicon)
- Transcription: whisper.cpp (Metal-accelerated, local, free — no API calls)
- Video processing: FFmpeg (with videotoolbox hardware encoding)
- Input (optional): yt-dlp can download a Twitch/Kick VOD into /source via
  `fetch.sh`. Manually dropping an mp4 into /source works too — both are fine.
- No cloud APIs should be used for transcription or clipping unless I
  explicitly ask for one. Keep this pipeline 100% local/free.

## Folder structure
```
/stream-clipper
  /source          <- raw input mp4 goes here
  /transcripts      <- whisper output (json/srt/txt)
  /review           <- markdown clip-suggestion files for me to approve
  /clips            <- final cut clips land here
  CLAUDE.md
```

## Workflow (do these as separate steps, don't skip ahead)

0. **(Optional) Get the source video**
   The source mp4 can arrive two ways — both are fine:
   - I drop an mp4 into /source myself, OR
   - Download it by URL:  `bash fetch.sh <URL> [name] [section]`
     (Twitch is reliable; Kick may need IMPERSONATE=1 — see fetch.sh.)
   Either way, proceed once there's exactly one video in /source.

1. **Transcribe**
   Run whisper.cpp (medium model) on the source file in /source, output
   timestamped transcript (SRT + JSON) into /transcripts.

2. **Analyze for clip-worthy moments**
   Read the transcript and flag candidate moments based on the criteria
   below. Output a review file to /review/clip-review.md — DO NOT cut
   any video yet at this stage. I need to approve first.

   Review file format:
   ```
   ## Clip 1: [working title]
   - Start: 00:12:04
   - End: 00:12:52
   - Why: [1-2 sentence reason this is clip-worthy]

   ## Clip 2: ...
   ```

3. **Wait for my approval**
   I'll respond with something like "cut clips 1, 3, 5" or "cut all" or
   give edits to timestamps. Only proceed to step 4 once I confirm.

4. **Cut + format approved clips**
   For each approved clip:
   - Cut from source using FFmpeg (stream copy where possible for speed,
     re-encode only where needed for accurate cut points)
   - Crop/format as specified below
   - Burn in captions generated from the whisper transcript for that
     time range
   - Use videotoolbox for hardware-accelerated encoding
   - Save to /clips with a descriptive filename (e.g. 01_funny-rant.mp4)

## Clip-worthy criteria (IRL content)
Since this is mostly IRL/talking content, prioritize moments driven by
what's SAID, not visual action. Look for:
- Funny reactions, punchlines, or unexpected turns in a story
- Bold/controversial statements or hot takes
- Genuine emotional moments (excitement, shock, frustration)
- Self-contained stories or rants with a clear beginning/end
- Callbacks or running bits that would make sense out of context
- Natural "hook" openings — the first line should make someone stop
  scrolling

Avoid moments that:
- Require context from 10+ minutes earlier to make sense
- Are mid-sentence cuts or trail off without a natural end point
- Are just filler/dead air

## Format requirements
- Target length: 20–60 seconds (hard cap 90s)
- Aspect ratio: 9:16 vertical
  - Default: center crop (since IRL content is usually centered on you)
  - If I flag a clip as needing a specific crop position, use that instead
- Captions: burned in, short-phrase chunks (2-4 words at a time), NOT
  word-by-word and NOT full sentences at once
- Output format: mp4, H.264, ready to upload directly to TikTok

## Caption workflow (locked — don't improvise a different approach)
1. For each approved clip's time range, extract the matching word-level
   segment from the full transcript JSON.
2. Run `make_captions.py` on that segment to produce a `.ass` caption
   file chunked into 2-4 word phrases (script lives in project root).
3. Burn captions into the clip with FFmpeg using the `ass` filter, e.g.:
   ```
   ffmpeg -i clip_raw.mp4 -vf "ass=captions.ass" \
     -c:v h264_videotoolbox -c:a copy clip_final.mp4
   ```
4. If a caption line looks visually wrong (overlapping, too long, cut
   off) when previewed, prefer re-chunking over manually editing the
   .ass file — adjust CHUNK_MAX_WORDS/CHUNK_MAX_DURATION_MS in
   make_captions.py rather than hand-patching individual lines.

## Cost/performance notes
- whisper.cpp medium model is the default — don't upgrade to large-v3
  unless transcript accuracy is clearly a problem
- Always use videotoolbox for encoding, not software encoding, to keep
  render times reasonable on this machine
- For long VODs (2hrs+), transcription will take a while — that's fine,
  just let it run
