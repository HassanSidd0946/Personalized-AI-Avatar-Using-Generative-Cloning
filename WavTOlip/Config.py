# Configuration for FYP Avatar Lip-Sync Pipeline
# Edit these settings to customize your pipeline

# ============================================================================
# GPU SETTINGS
# ============================================================================

# GPU type to use (options: "A100", "A10G", "T4", "any")
GPU_TYPE = "A100"

# Timeout in seconds (increase for longer videos)
TIMEOUT = 1200  # 20 minutes

# Memory allocation in MB
MEMORY = 16384  # 16GB

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================

# Default quality mode (options: "high", "medium", "fast")
DEFAULT_QUALITY = "high"

# Lip padding adjustment [top, bottom, left, right]
# Increase bottom padding (second value) if chin is cut off
LIP_PADS = [0, 10, 0, 0]

# FPS settings
FPS_FAST = 25
FPS_HIGH = 30

# ============================================================================
# FACE RESTORATION (GFPGAN) SETTINGS
# ============================================================================

# Enable face restoration
FACE_RESTORE = True

# Upscale face region
FACE_UPSAMPLE = True

# Background upsampler (options: "realesrgan", None)
BG_UPSAMPLER = "realesrgan"

# Only process center face (faster, recommended)
ONLY_CENTER_FACE = True

# ============================================================================
# FILE SETTINGS
# ============================================================================

# Default input filenames
DEFAULT_FACE_IMAGE = "avatar.jpg"
DEFAULT_AUDIO_FILE = "voice.wav"
DEFAULT_OUTPUT_FILE = "FINAL_AVATAR.mp4"

# Temporary directory
TMP_DIR = "/tmp/lipsync_pipeline"

# ============================================================================
# AUDIO SETTINGS
# ============================================================================

# Target audio sample rate (Hz)
AUDIO_SAMPLE_RATE = 16000

# Audio channels (1=mono, 2=stereo)
AUDIO_CHANNELS = 1

# ============================================================================
# MODEL SETTINGS
# ============================================================================

# Wav2Lip model checkpoint
WAV2LIP_CHECKPOINT = "checkpoints/wav2lip_gan.pth"

# GFPGAN model version (options: "GFPGANv1.4.pth", "GFPGANv1.3.pth")
GFPGAN_MODEL = "GFPGANv1.4.pth"

# Face detection model
FACE_DETECTION_MODEL = "face_detection/detection/sfd/s3fd-619a316812.pth"

# ============================================================================
# ADVANCED SETTINGS
# ============================================================================

# Enable verbose logging
VERBOSE = True

# Save intermediate outputs (for debugging)
SAVE_INTERMEDIATE = False

# Batch size for processing (increase for more GPU memory)
BATCH_SIZE = 16

# ============================================================================
# NOTES
# ============================================================================

# LIP_PADS explanation:
# - [0, 10, 0, 0] means: no padding on top/left/right, 10px padding on bottom
# - Bottom padding is critical for including the full mouth region
# - Adjust if you see:
#   * Chin cut off -> increase bottom padding (try 15)
#   * Too much neck -> decrease bottom padding (try 5)
#   * Face too high -> increase top padding
#   * Face too low -> decrease top padding

# GPU_TYPE notes:
# - A100: Fastest, most expensive (~$1.10/hr)
# - A10G: Good balance (~$0.60/hr)
# - T4: Cheaper but slower (~$0.20/hr)
# - "any": Let Modal choose (not recommended for production)

# QUALITY vs SPEED tradeoff:
# - "fast": 25 FPS, basic restoration, ~30s per minute of video
# - "medium": 25 FPS, standard restoration, ~45s per minute
# - "high": 30 FPS, full restoration + upscaling, ~60s per minute