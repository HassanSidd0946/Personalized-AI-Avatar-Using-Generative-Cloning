# 🔧 Troubleshooting Guide - FYP Avatar Lip-Sync Pipeline

This guide covers common issues and their solutions.

---

## 📋 Table of Contents

1. [Installation Issues](#installation-issues)
2. [Authentication Issues](#authentication-issues)
3. [File Format Issues](#file-format-issues)
4. [Face Detection Issues](#face-detection-issues)
5. [Lip-Sync Quality Issues](#lip-sync-quality-issues)
6. [Performance Issues](#performance-issues)
7. [GPU/Memory Issues](#gpumemory-issues)
8. [Output Issues](#output-issues)

---

## Installation Issues

### ❌ "modal: command not found"

**Solution:**
```bash
# Install Modal
pip install modal

# Or with pip3
pip3 install modal

# Verify installation
modal --version
```

### ❌ "ffmpeg: command not found"

**Solution:**

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Add to PATH environment variable
3. Restart terminal

### ❌ "Python version not supported"

**Solution:**
```bash
# Check Python version (must be 3.9 or 3.10)
python --version

# Install correct version if needed
# macOS:
brew install python@3.10

# Ubuntu:
sudo apt install python3.10
```

---

## Authentication Issues

### ❌ "Not authenticated with Modal"

**Solution:**
```bash
# Create new token (opens browser)
modal token new

# Verify authentication
modal token verify
```

### ❌ "Token expired"

**Solution:**
```bash
# Refresh token
modal token new --force
```

---

## File Format Issues

### ❌ "Face image not found"

**Checklist:**
- [ ] File exists in current directory
- [ ] Filename is correct (case-sensitive)
- [ ] File extension is included (.jpg, .png)

**Solution:**
```bash
# List files in current directory
ls -la

# Check if file exists
ls avatar.jpg

# Run with full path
modal run fyp_avatar_lipsync.py --face-image /full/path/to/avatar.jpg
```

### ❌ "Audio format not supported"

**Problem:** Wav2Lip requires WAV format.

**Solution:**
```bash
# Convert MP3 to WAV
python utils.py convert input.mp3

# Or manually with ffmpeg
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
```

**Supported conversions:**
- MP3 → WAV
- M4A → WAV
- AAC → WAV
- FLAC → WAV

### ❌ "Image too large" or "Timeout during upload"

**Solution:**
```bash
# Resize image to 512x512
python utils.py resize large_image.jpg

# Or manually with ffmpeg
ffmpeg -i large.jpg -vf "scale=512:512" avatar.jpg
```

---

## Face Detection Issues

### ❌ "No face detected in image"

**Possible causes:**
1. Face is too small in image
2. Face is at extreme angle
3. Face is partially occluded
4. Image quality is too low

**Solutions:**

**1. Check image quality:**
```bash
# Validate your inputs
python utils.py validate avatar.jpg voice.wav
```

**2. Use a better image:**
- ✅ Clear, frontal face
- ✅ Good lighting
- ✅ Face takes up 40-60% of image
- ❌ Profile/side views
- ❌ Sunglasses covering eyes
- ❌ Masks covering mouth

**3. Crop face manually:**
```bash
# Crop to face region
ffmpeg -i full_image.jpg -vf "crop=512:512:x:y" face_crop.jpg
```

### ❌ "Multiple faces detected"

**Solution:** Use `--only_center_face` flag (enabled by default).

If issue persists:
```bash
# Crop to single face
ffmpeg -i multi_face.jpg -vf "crop=512:512:x:y" single_face.jpg
```

---

## Lip-Sync Quality Issues

### ❌ "Lips not syncing with audio"

**Possible causes:**
1. Audio quality is poor (background noise)
2. Audio format issues
3. Padding is incorrect
4. Face angle is wrong

**Solutions:**

**1. Clean audio:**
```bash
# Remove background noise
python utils.py clean noisy_audio.wav

# Or manually
ffmpeg -i input.wav -af "highpass=f=200,lowpass=f=3000,loudnorm" clean.wav
```

**2. Check audio format:**
```bash
# Get audio info
ffprobe voice.wav

# Convert to optimal format
ffmpeg -i input.wav -ar 16000 -ac 1 voice_optimized.wav
```

**3. Adjust padding:**

Edit `config.py`:
```python
# Try different padding values
LIP_PADS = [0, 15, 0, 0]  # More bottom padding
# or
LIP_PADS = [5, 10, 0, 0]  # Add top padding
```

**4. Use frontal face:**
- Face should be looking directly at camera
- Avoid tilted heads
- Avoid extreme angles

### ❌ "Lips don't close during silence"

This is a **core feature** of Wav2Lip - it should work automatically.

**If not working:**

**1. Check audio file:**
```bash
# Visualize waveform
ffplay -showmode 1 voice.wav
```

Silence should show flat lines (amplitude near 0).

**2. Ensure proper silence in audio:**
```bash
# Add 0.5s silence at start/end
ffmpeg -i input.wav -af "apad=pad_dur=0.5" output.wav
```

**3. Verify Wav2Lip model:**
```bash
# Should use wav2lip_gan.pth (not wav2lip.pth)
# GAN model is better at handling silence
```

### ❌ "Mouth shape looks weird"

**Solution:**

**1. Increase face restoration:**
```python
# In fyp_avatar_lipsync.py, ensure GFPGAN is enabled
"--face_restore",
"--face_upsample",
```

**2. Try different quality mode:**
```bash
# High quality (slower but better)
modal run fyp_avatar_lipsync.py --quality high
```

**3. Use higher resolution input:**
```bash
# Resize to 1024x1024 instead of 512x512
ffmpeg -i face.jpg -vf "scale=1024:1024" face_hires.jpg
```

---

## Performance Issues

### ❌ "Processing takes too long"

**Expected times (A100 GPU):**
- 30s video: ~20-30s processing
- 1min video: ~40-60s processing
- 5min video: ~5-6min processing

**If slower:**

**1. Use faster quality mode:**
```bash
modal run fyp_avatar_lipsync.py --quality fast
```

**2. Check GPU type:**
```python
# In fyp_avatar_lipsync.py
@app.function(
    gpu="A100",  # Fastest
    # vs
    gpu="T4",    # Slower
)
```

**3. Reduce FPS:**
Edit `config.py`:
```python
FPS_FAST = 20  # Instead of 25
```

### ❌ "Timeout error after 20 minutes"

**Solution:**

For longer videos, increase timeout:

```python
# In fyp_avatar_lipsync.py
@app.function(
    gpu="A100",
    timeout=3600,  # 60 minutes instead of 1200 (20 min)
)
```

---

## GPU/Memory Issues

### ❌ "CUDA out of memory"

**Solutions:**

**1. Reduce batch size:**
```python
# In config.py
BATCH_SIZE = 8  # Instead of 16
```

**2. Use smaller input:**
```bash
# Resize to 512x512
python utils.py resize large_face.jpg -s 512
```

**3. Disable background upsampling:**
```python
# In config.py
BG_UPSAMPLER = None  # Instead of "realesrgan"
```

### ❌ "GPU not available"

**Check GPU allocation:**
```bash
# Test GPU
modal run fyp_avatar_lipsync.py::test_gpu
```

**Expected output:**
```
GPU device: NVIDIA A100-SXM4-40GB
GPU memory: 40.0 GB
✅ GPU tensor operations working!
```

If no GPU detected, contact Modal support.

---

## Output Issues

### ❌ "Output video not generated"

**Debug steps:**

**1. Check logs:**
```bash
# Run with verbose output
modal run fyp_avatar_lipsync.py 2>&1 | tee pipeline.log
```

**2. Check intermediate files:**
Look for files in `/tmp/lipsync_pipeline/` (in the container).

**3. Verify checkpoints:**
```bash
# In the Modal function, verify checkpoints exist
ls /workspace/Wav2Lip/checkpoints/
```

Should show:
- `wav2lip_gan.pth`
- `GFPGANv1.4.pth`

### ❌ "Video is corrupted or won't play"

**Solution:**

**1. Re-encode with ffmpeg:**
```bash
ffmpeg -i FINAL_AVATAR.mp4 -c:v libx264 -c:a aac output_fixed.mp4
```

**2. Check codec:**
```bash
# Get video info
ffprobe FINAL_AVATAR.mp4
```

### ❌ "Audio-video sync is off"

**This should not happen** with Wav2Lip, but if it does:

**Solution:**
```bash
# Fix sync manually
ffmpeg -i input.mp4 -itsoffset 0.5 -i input.mp4 -map 0:v -map 1:a -c copy output.mp4
```

---

## Advanced Debugging

### Enable Debug Mode

Edit `fyp_avatar_lipsync.py`:

```python
# Add verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Save intermediate outputs
SAVE_INTERMEDIATE = True
```

### Check Modal Logs

```bash
# View recent logs
modal logs

# Follow logs in real-time
modal logs --follow
```

### Test Individual Components

**Test audio conversion:**
```bash
python utils.py convert test.mp3
```

**Test image resize:**
```bash
python utils.py resize test.jpg
```

**Test GPU:**
```bash
modal run fyp_avatar_lipsync.py::test_gpu
```

---

## Getting Help

If issues persist:

1. **Check logs:** `modal logs`
2. **Validate inputs:** `python utils.py validate face.jpg audio.wav`
3. **Try test data:** `python utils.py test`
4. **Review config:** Check `config.py` settings

**Need more help?**
- Modal docs: https://modal.com/docs
- Wav2Lip issues: https://github.com/Rudrabha/Wav2Lip/issues
- GFPGAN issues: https://github.com/TencentARC/GFPGAN/issues

---

## Quick Fixes Checklist

- [ ] Modal installed: `pip install modal`
- [ ] Authenticated: `modal token new`
- [ ] ffmpeg installed: `ffmpeg -version`
- [ ] Input files exist: `ls avatar.jpg voice.wav`
- [ ] Audio is WAV format: Convert with `python utils.py convert`
- [ ] Face is frontal and clear
- [ ] Image size is reasonable (< 2MB)
- [ ] Audio is clean (no background noise)
- [ ] Padding is correct: Check `config.py`

---

**Last updated:** February 2025  
**Version:** 1.0  
**Pipeline:** Wav2Lip + GFPGAN on Modal A100