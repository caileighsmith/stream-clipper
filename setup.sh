#!/bin/bash
# Stream Clipper - Environment Setup (macOS / Apple Silicon)
# Run this once before using Claude Code on this project.

set -e

echo "=== Checking Homebrew ==="
if ! command -v brew &> /dev/null; then
  echo "Homebrew not found. Install it first: https://brew.sh"
  exit 1
fi

echo "=== Installing FFmpeg ==="
brew install ffmpeg

echo "=== Installing whisper.cpp ==="
brew install whisper-cpp

echo "=== Creating project folders ==="
mkdir -p source transcripts review clips

echo "=== Verifying installs ==="
ffmpeg -version | head -n 1
whisper-cpp --help > /dev/null 2>&1 && echo "whisper-cpp installed OK"

echo ""
echo "Setup complete. Next steps:"
echo "1. Drop your source mp4 into the /source folder"
echo "2. Download a whisper.cpp model, e.g.:"
echo "   bash \$(brew --prefix whisper-cpp)/share/whisper-cpp/models/download-ggml-model.sh medium"
echo "3. Open this folder in Claude Code and say:"
echo "   'Transcribe the video in /source and follow the workflow in CLAUDE.md'"
