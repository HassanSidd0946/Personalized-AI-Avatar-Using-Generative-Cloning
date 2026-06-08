# Configuration for FYP Avatar Lip-Sync Pipeline

GPU_TYPE = "A100"

TIMEOUT = 1200 

MEMORY = 16384  

DEFAULT_QUALITY = "high"

LIP_PADS = [0, 10, 0, 0]

FPS_FAST = 25
FPS_HIGH = 30

FACE_RESTORE = True

FACE_UPSAMPLE = True

BG_UPSAMPLER = "realesrgan"

ONLY_CENTER_FACE = True

DEFAULT_FACE_IMAGE = "avatar.jpg"
DEFAULT_AUDIO_FILE = "voice.wav"
DEFAULT_OUTPUT_FILE = "FINAL_AVATAR.mp4"

TMP_DIR = "/tmp/lipsync_pipeline"

AUDIO_SAMPLE_RATE = 16000

AUDIO_CHANNELS = 1

WAV2LIP_CHECKPOINT = "checkpoints/wav2lip_gan.pth"

GFPGAN_MODEL = "GFPGANv1.4.pth"

FACE_DETECTION_MODEL = "face_detection/detection/sfd/s3fd-619a316812.pth"

VERBOSE = True

SAVE_INTERMEDIATE = False

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
