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
MIN_DISPLAY_MS = 700          # floor so short captions stay readable

# A chunk never spans two sentences: these end one.
SENTENCE_ENDINGS = (".", "!", "?", "…")

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


def split_sentences(words):
    """Group the word stream into sentences so a caption never straddles a
    sentence boundary. A sentence ends on . ! ? … — even a one-word sentence
    ("Sure.") stands on its own instead of gluing onto the next line."""
    sentences = []
    current = []
    for w in words:
        current.append(w)
        if w["text"].endswith(SENTENCE_ENDINGS):
            sentences.append(current)
            current = []
    if current:  # trailing run-on with no terminal punctuation
        sentences.append(current)
    return sentences


def chunk_sentence(words):
    """Split one sentence into 2-4 word phrases. Avoids leaving a lonely
    trailing word (5 words -> 3+2, not 4+1) and respects the max duration."""
    chunks = []
    i, n = 0, len(words)
    while i < n:
        remaining = n - i
        take = min(CHUNK_MAX_WORDS, remaining)
        # avoid orphaning a single word at the end of the sentence
        if remaining - take == 1 and take > CHUNK_MIN_WORDS:
            take -= 1
        # shrink if the phrase would sit on screen too long — but a mere pause
        # shouldn't fragment speech into 1-word flashes, so don't shrink below
        # CHUNK_MIN_WORDS here. Genuinely short *sentences* still stand alone
        # because split_sentences already isolated them.
        while take > CHUNK_MIN_WORDS and words[i + take - 1]["t1"] - words[i]["t0"] > CHUNK_MAX_DURATION_MS:
            take -= 1
        chunks.append(words[i:i + take])
        i += take
    return chunks


def chunk_words(words):
    chunks = []
    for sentence in split_sentences(words):
        chunks.extend(chunk_sentence(sentence))
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
    for idx, chunk in enumerate(chunks):
        start_ms = chunk[0]["t0"]
        end_ms = chunk[-1]["t1"]
        # hold short captions on screen long enough to read, but never overlap
        # the next caption's start
        if end_ms - start_ms < MIN_DISPLAY_MS:
            end_ms = start_ms + MIN_DISPLAY_MS
            if idx + 1 < len(chunks):
                end_ms = min(end_ms, chunks[idx + 1][0]["t0"])
        start = ms_to_ass_time(start_ms)
        end = ms_to_ass_time(end_ms)
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
