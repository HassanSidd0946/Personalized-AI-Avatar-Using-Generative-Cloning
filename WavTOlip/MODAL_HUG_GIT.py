import modal
import os
from pathlib import Path

REPO_PATH = Path(__file__).parent / "Wav2Lip"

image = (
    modal.Image.from_registry("pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "UTC"})
    .apt_install(
        "ffmpeg",
        "wget",
        "git",
        "libgl1-mesa-glx",
        "libglib2.0-0"
    )

    .pip_install(
        "numpy==1.21.6",
        "scipy==1.7.3",
        "opencv-python==4.6.0.66",
        "librosa==0.9.2",
        "numba==0.55.1",
        "tqdm",
        "resampy"
    )

    .run_commands(
        "pip install basicsr facexlib gfpgan Pillow --no-deps",
        "pip install addict future lmdb pyyaml requests tb-nightly yapf filterpy --no-deps",
        "pip install --force-reinstall --no-deps numpy==1.21.6 scipy==1.7.3"
    )
    .add_local_dir(str(REPO_PATH), remote_path="/workspace/Wav2Lip")
)

app = modal.App("fyp-avatar-lipsync-backend")


@app.function(
    image=image,
    gpu="T4",
    timeout=1200
)
def generate_lipsync_video(image_bytes: bytes, audio_bytes: bytes) -> bytes:
    import subprocess
    import sys
    import shutil
    import cv2

    os.chdir("/workspace/Wav2Lip")

    print("=== Starting Wav2Lip + GFPGAN Pipeline ===")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Save input files
    print("\n[1/4] Saving input files...")
    with open("input.jpg", "wb") as f:
        f.write(image_bytes)
    print(f"  ✓ Saved input.jpg ({len(image_bytes)/1024:.1f} KB)")

    with open("audio.wav", "wb") as f:
        f.write(audio_bytes)
    print(f"  ✓ Saved audio.wav ({len(audio_bytes)/1024:.1f} KB)")

    # Run Wav2Lip inference
    print("\n[2/4] Running Wav2Lip inference...")
    cmd = [
        "python", "inference.py",
        "--checkpoint_path", "checkpoints/wav2lip_gan.pth",
        "--face", "input.jpg",
        "--audio", "audio.wav",
        "--outfile", "temp_output.mp4",
        "--pads", "0", "10", "0", "0",
        "--resize_factor", "1",
        "--nosmooth"
    ]

    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"    {line}")

    if result.returncode != 0:
        print(f"   Wav2Lip failed!")
        if result.stderr:
            print(f"  Error: {result.stderr}")
        raise RuntimeError(f"Wav2Lip failed with exit code {result.returncode}")

    if not os.path.exists("temp_output.mp4"):
        raise FileNotFoundError("temp_output.mp4 was not generated")

    temp_size = os.path.getsize("temp_output.mp4") / 1024 / 1024
    print(f"  ✓ Wav2Lip completed ({temp_size:.2f} MB)")

    print("\n[3/4] Applying GFPGAN face restoration...")
    try:
        from gfpgan import GFPGANer

        restorer = GFPGANer(
            model_path='checkpoints/GFPGANv1.3.pth',
            upscale=1,
            arch='clean',
            channel_multiplier=2,
            bg_upsampler=None
        )
        print("  ✓ GFPGAN model loaded")

        cap = cv2.VideoCapture('temp_output.mp4')
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"  Video: {width}x{height} @ {fps}fps, {total_frames} frames")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('restored_no_audio.mp4', fourcc, fps, (width, height))

        frame_count = 0
        last_percent = -1

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            _, _, restored_frame = restorer.enhance(
                frame,
                has_aligned=False,
                only_center_face=False,
                paste_back=True,
                weight=0.5
            )

            out.write(restored_frame)
            frame_count += 1

            percent = int(100 * frame_count / total_frames)
            if percent >= last_percent + 10:
                print(f"    Progress: {percent}% ({frame_count}/{total_frames} frames)")
                last_percent = percent

        cap.release()
        out.release()

        print(f"  ✓ GFPGAN completed ({frame_count} frames)")

        print("\n   Re-adding audio track...")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", "restored_no_audio.mp4",
            "-i", "temp_output.mp4",
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "output.mp4"
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"   FFmpeg warning: {result.stderr}")
            shutil.copy("temp_output.mp4", "output.mp4")
        else:
            final_size = os.path.getsize("output.mp4") / 1024 / 1024
            print(f"  ✓ Audio added ({final_size:.2f} MB)")

    except Exception as e:
        print(f"   GFPGAN failed: {e}")
        print(f"  Using original Wav2Lip output")
        shutil.copy("temp_output.mp4", "output.mp4")

    # Return output
    print("\n[4/4] Preparing output...")
    with open("output.mp4", "rb") as f:
        output_bytes = f.read()

    print(f"  ✓ Final output: {len(output_bytes)/1024/1024:.2f} MB")
    print("\n=== Pipeline Complete ===\n")

    return output_bytes


@app.local_entrypoint()
def main(face_path: str = "", audio_path: str = ""):
    """
    Standalone entrypoint — use this for direct Wav2Lip-only runs.

    Usage:
        modal run WavTOlip/MODAL_HUG_GIT.py --face-path avatar.jpg --audio-path voice.wav
    """
    print("\n" + "="*60)
    print("  🎬 Wav2Lip + GFPGAN (standalone mode)")
    print("="*60 + "\n")

    if not face_path or not audio_path:
        print(" Missing required arguments!\n")
        print("Usage:")
        print('  modal run WavTOlip/MODAL_HUG_GIT.py --face-path "avatar.jpg" --audio-path "voice.wav"')
        return

    if not os.path.exists(face_path):
        print(f" Face image not found: {face_path}")
        return

    if not os.path.exists(audio_path):
        print(f" Audio file not found: {audio_path}")
        return

    if not REPO_PATH.exists():
        print(f" Wav2Lip repo not found at: {REPO_PATH}")
        return

    print(f"📸 Face Image : {face_path}")
    print(f"🎵 Audio File : {audio_path}\n")

    with open(face_path, "rb") as f:
        image_bytes = f.read()

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print(" Sending to Modal GPU...\n")

    try:
        output_bytes = generate_lipsync_video.remote(image_bytes, audio_bytes)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"OUTPUT_{timestamp}.mp4"

        with open(output_file, "wb") as f:
            f.write(output_bytes)

        print(f"\n Saved: {output_file} ({len(output_bytes)/1024/1024:.2f} MB)\n")

    except Exception as e:
        print(f"\n Error: {e}\n")
