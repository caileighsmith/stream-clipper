#!/usr/bin/env python3
"""
make_captions.py

Converts whisper.cpp word-level timestamp JSON into a styled .ass
subtitle file, chunked into short phrases (2-4 words) for burned-in
TikTok-style captions.

Usage:
    python3 make_captions.py transcript.json captions.ass

Expected input JSON shape (whisper.cpp -ojf / --output-json-full):
{
  "transcription": [
    {
      "tokens": [
        {"text": " hey",  "offsets": {"from": 120, "to": 340}, ...},
        {"text": " guys", "offsets": {"from": 340, "to": 620}, ...},
        {"text": "[_TT_74]", "offsets": {"from": 620, "to": 620}, ...},
        ...
      ]
    },
    ...
  ]
}

Per-token ms times live under offsets.from / offsets.to. The token
stream also contains special tokens ([_BEG_], [_TT_*], [_EOT_], ...)
which are filtered out via SPECIAL_TOKEN_RE.
"""

import json
import re
import sys

# whisper.cpp emits special tokens (e.g. [_BEG_], [_TT_244], [_EOT_]) inline
# in the token stream. They carry no real text and must be skipped.
SPECIAL_TOKEN_RE = re.compile(r"^\[_.*\]$")

# --- config ---
CHUNK_MIN_WORDS = 2
CHUNK_MAX_WORDS = 4
CHUNK_MAX_DURATION_MS = 2200  # don't let a chunk sit on screen too long

# ASS styling — tweak freely
ASS_STYLE = (
    "Style: Caption,Montserrat Bold,64,"
    "&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
    "-1,0,0,0,100,100,0,0,1,4,2,2,80,80,320,1"
)
# Font size 64 on a 1080x1920 vertical canvas (readable TikTok caption size).
# Alignment 2 = bottom-center. MarginV 320 keeps text above TikTok's bottom UI.


def ms_to_ass_time(ms):
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    cs = (ms % 1000) // 10
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def load_words(json_path):
    with open(json_path) as f:
        data = json.load(f)
    # whisper tokenizes at the sub-word level: a token that begins with a
    # leading space starts a new word, while a token WITHOUT one is a
    # continuation of the previous word — this covers sub-word pieces
    # ("cost"+"al"), clitics ("it"+"'s") and trailing punctuation ("care"+".").
    # Merge continuations onto the preceding word so the 2-4 word chunker
    # counts real words, not fragments.
    words = []
    for segment in data.get("transcription", []):
        for tok in segment.get("tokens", []):
            raw = tok["text"]
            text = raw.strip()
            if not text or SPECIAL_TOKEN_RE.match(text):
                continue
            # whisper.cpp full-JSON stores per-token ms times under
            # offsets.from / offsets.to (absolute ms from start of audio).
            offsets = tok.get("offsets", {})
            t0, t1 = offsets["from"], offsets["to"]

            starts_new_word = raw[:1].isspace() or not words
            if starts_new_word:
                if text in ("-", "--", "—"):
                    continue  # standalone dialogue dash — not spoken, drop it
                words.append({"text": text, "t0": t0, "t1": t1})
            else:
                words[-1]["text"] += text
                words[-1]["t1"] = t1
    return words


def chunk_words(words):
    chunks = []
    current = []
    start_ms = None

    for w in words:
        if not current:
            start_ms = w["t0"]
        current.append(w)

        duration = w["t1"] - start_ms
        if len(current) >= CHUNK_MAX_WORDS or duration >= CHUNK_MAX_DURATION_MS:
            chunks.append(current)
            current = []
        elif len(current) >= CHUNK_MIN_WORDS and w["text"].endswith((".", "!", "?")):
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)
    return chunks


def build_ass(chunks, out_path):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{ASS_STYLE}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for chunk in chunks:
        start = ms_to_ass_time(chunk[0]["t0"])
        end = ms_to_ass_time(chunk[-1]["t1"])
        text = " ".join(w["text"] for w in chunk).upper()
        lines.append(f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{text}\n")

    with open(out_path, "w") as f:
        f.writelines(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 make_captions.py transcript.json captions.ass")
        sys.exit(1)

    words = load_words(sys.argv[1])
    if not words:
        print("No words found — check the JSON structure matches your whisper.cpp output.")
        sys.exit(1)

    chunks = chunk_words(words)
    build_ass(chunks, sys.argv[2])
    print(f"Wrote {len(chunks)} caption chunks to {sys.argv[2]}")


if __name__ == "__main__":
    main()
