#!/bin/bash
# Quick Start Setup Script for FYP Avatar Lip-Sync Pipeline

set -e  # Exit on error

echo "=================================="
echo "FYP Avatar Lip-Sync Pipeline Setup"
echo "=================================="
echo ""

# Check if Modal is installed
if ! command -v modal &> /dev/null; then
    echo "📦 Installing Modal CLI..."
    pip install modal
else
    echo "✅ Modal CLI already installed"
fi

# Check if ffmpeg is installed (for audio conversion)
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  Warning: ffmpeg not found. Install it for audio conversion:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    echo "   Windows: https://ffmpeg.org/download.html"
else
    echo "✅ ffmpeg found"
fi

# Authenticate with Modal if not already done
echo ""
echo "🔑 Checking Modal authentication..."
if ! modal token verify &> /dev/null; then
    echo "Please authenticate with Modal (browser will open)..."
    modal token new
else
    echo "✅ Already authenticated with Modal"
fi

# Create sample test data
echo ""
echo "🧪 Creating test data..."
python utils.py test

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Run test: modal run fyp_avatar_lipsync.py --face-image test_data/test_face.jpg --audio-file test_data/test_audio.wav"
echo "2. Or use your own files: modal run fyp_avatar_lipsync.py --face-image YOUR_FACE.jpg --audio-file YOUR_AUDIO.wav"
echo ""
echo "Need help? Check README.md for documentation"
echo ""