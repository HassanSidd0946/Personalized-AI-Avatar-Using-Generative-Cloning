# 🎯 Quick Reference Card - FYP Avatar Lip-Sync Pipeline

**One-page cheat sheet for common operations**

---

## 🚀 Essential Commands

### First Time Setup
```bash
# 1. Install Modal
pip install modal

# 2. Authenticate
modal token new

# 3. Run setup
chmod +x setup.sh && ./setup.sh
```

### Basic Usage
```bash
# Default (uses avatar.jpg + voice.wav)
modal run fyp_avatar_lipsync.py

# Custom files
modal run fyp_avatar_lipsync.py \
  --face-image YOUR_FACE.jpg \
  --audio-file YOUR_AUDIO.wav

# Fast mode
modal run fyp_avatar_lipsync.py --quality fast

# Custom output name
modal run fyp_avatar_lipsync.py --output-file result.mp4
```

---

## 🛠️ Utility Commands

### Audio Operations
```bash
# Convert MP3 to WAV
python utils.py convert input.mp3

# Clean audio (remove noise)
python utils.py clean noisy.wav

# Convert with specific settings
python utils.py convert input.mp3 -r 16000 -o output.wav
```

### Image Operations
```bash
# Resize to 512x512
python utils.py resize large.jpg

# Custom size
python utils.py resize image.jpg -s 1024
```

### Validation
```bash
# Check if files are suitable
python utils.py validate face.jpg audio.wav
```

### Testing
```bash
# Create test data
python utils.py test

# Test GPU
modal run fyp_avatar_lipsync.py::test_gpu
```

---

## 🔧 Common Fixes

### Audio is MP3/M4A
```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 voice.wav
```

### Image too large
```bash
ffmpeg -i large.jpg -vf "scale=512:512" avatar.jpg
```

### Remove background noise
```bash
ffmpeg -i noisy.wav -af "highpass=f=200,lowpass=f=3000" clean.wav
```

### Add silence padding (0.5s)
```bash
ffmpeg -i input.wav -af "apad=pad_dur=0.5" output.wav
```

---

## ⚙️ Configuration Quick Edits

**File:** `config.py`

### Change GPU
```python
GPU_TYPE = "A10G"  # Cheaper than A100
```

### Longer timeout
```python
TIMEOUT = 3600  # 60 minutes for long videos
```

### Adjust lip padding
```python
LIP_PADS = [0, 15, 0, 0]  # More bottom padding
```

### Faster processing
```python
DEFAULT_QUALITY = "fast"
FPS_FAST = 20
BG_UPSAMPLER = None  # Disable background upscaling
```

---

## 📊 Performance Reference

| Video Length | Time (A100) | Cost  |
|--------------|-------------|-------|
| 30 sec       | ~25 sec     | $0.01 |
| 1 min        | ~50 sec     | $0.02 |
| 5 min        | ~6 min      | $0.10 |

**Quality modes:**
- `fast` = 25 FPS, ~30s per minute
- `medium` = 25 FPS, ~45s per minute  
- `high` = 30 FPS, ~60s per minute

---

## 🔍 Debugging Quick Checks

### 1. Check files exist
```bash
ls -lh avatar.jpg voice.wav
```

### 2. View Modal logs
```bash
modal logs
```

### 3. Validate inputs
```bash
python utils.py validate avatar.jpg voice.wav
```

### 4. Test with sample data
```bash
python utils.py test
modal run fyp_avatar_lipsync.py \
  --face-image test_data/test_face.jpg \
  --audio-file test_data/test_audio.wav
```

### 5. Check audio format
```bash
ffprobe voice.wav
```

---

## 🚨 Common Errors & Solutions

| Error | Solution |
|-------|----------|
| "modal: command not found" | `pip install modal` |
| "Not authenticated" | `modal token new` |
| "No face detected" | Use frontal, clear face image |
| "Audio format not supported" | Convert to WAV: `python utils.py convert` |
| "Timeout after 20 min" | Edit config: `TIMEOUT = 3600` |
| "CUDA out of memory" | Reduce image size or batch size |
| "Lips not syncing" | Clean audio, check padding |

---

## 📁 File Locations

```
Your Project/
├── avatar.jpg              # Your face image
├── voice.wav              # Your audio file
├── FINAL_AVATAR.mp4       # Output video
│
├── fyp_avatar_lipsync.py  # Main script
├── config.py              # Settings
├── utils.py               # Tools
└── setup.sh               # Setup script
```

---

## 🎯 Quality Checklist

**Before processing:**
- [ ] Face image is clear and frontal
- [ ] Face takes up 40-60% of image
- [ ] Audio is WAV format (16kHz mono)
- [ ] Audio is clean (no background noise)
- [ ] Files validated: `python utils.py validate`

**After processing:**
- [ ] Lips sync with audio
- [ ] Lips close during silence
- [ ] Face quality is good
- [ ] No artifacts or glitches

---

## 💡 Pro Tips

1. **Best face images:**
   - High resolution (512x512 or higher)
   - Good lighting
   - Neutral expression
   - Looking at camera

2. **Best audio:**
   - Clear speech
   - Minimal background noise
   - 16kHz sample rate
   - Mono channel

3. **Optimize for speed:**
   - Use `--quality fast`
   - Resize images to 512x512
   - Use A10G instead of A100
   - Disable background upsampling

4. **Optimize for quality:**
   - Use `--quality high`
   - High-res face images (1024x1024)
   - Clean audio beforehand
   - Use A100 GPU

---

## 📞 Get Help

1. **Check documentation:**
   - README.md
   - TROUBLESHOOTING.md
   - PROJECT_STRUCTURE.md

2. **Test components:**
   ```bash
   python utils.py test
   modal run fyp_avatar_lipsync.py::test_gpu
   ```

3. **View logs:**
   ```bash
   modal logs --follow
   ```

---

**Print this page for quick reference!**

Version 1.0 | February 2025