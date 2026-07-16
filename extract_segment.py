#!/usr/bin/env python3
"""
extract_segment.py

Slice the word-level tokens for one clip's time range out of the full
whisper.cpp transcript JSON, rebasing token times so the clip starts at 0.
Output is written in the same shape make_captions.py consumes.

Usage:
    python3 extract_segment.py clav.json START_MS END_MS out_segment.json

START_MS / END_MS are milliseconds from the start of the full VOD.
"""

import json
import sys


def main():
    if len(sys.argv) != 5:
        print("Usage: extract_segment.py transcript.json START_MS END_MS out.json")
        sys.exit(1)

    src, start_ms, end_ms, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]

    with open(src) as f:
        data = json.load(f)

    tokens = []
    for segment in data.get("transcription", []):
        for tok in segment.get("tokens", []):
            off = tok.get("offsets", {})
            t0, t1 = off.get("from"), off.get("to")
            if t0 is None or t1 is None:
                continue
            # keep any token that overlaps the clip window
            if t1 <= start_ms or t0 >= end_ms:
                continue
            rebased = dict(tok)
            rebased["offsets"] = {
                "from": max(0, t0 - start_ms),
                "to": max(0, t1 - start_ms),
            }
            tokens.append(rebased)

    # single synthetic segment — make_captions.py only reads tokens
    out_data = {"transcription": [{"tokens": tokens}]}
    with open(out, "w") as f:
        json.dump(out_data, f)
    print(f"Extracted {len(tokens)} tokens ({start_ms}-{end_ms}ms) to {out}")


if __name__ == "__main__":
    main()
