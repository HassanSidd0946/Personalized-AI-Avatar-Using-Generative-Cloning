import modal
import os

# 1. 🐳 DOCKER MAGIC!
# Hum PyTorch 1.7.1 ka pre-built Docker image utha rahe hain (Wav2Lip ki exact requirement).
# Is se koi "version mismatch" ya "dependency hell" ka error nahi ayega.
image = (
    modal.Image.from_registry("pytorch/pytorch:1.7.1-cuda11.0-cudnn8-devel")
    .apt_install("ffmpeg", "git", "libgl1-mesa-glx", "libglib2.0-0", "wget")
    .pip_install(
        "numpy==1.21.6",  # Purana numpy taake Wav2Lip crash na ho
        "scipy", 
        "opencv-python", 
        "librosa==0.9.2", 
        "tqdm", 
        "basicsr", 
        "facexlib", 
        "gfpgan"
    )
    .run_commands("git clone https://github.com/ajay-s-n/Wav2Lip-GFPGAN.git /workspace/Wav2Lip")
    .workdir("/workspace/Wav2Lip")
    # Reliable HuggingFace links se weights download karo
    .run_commands(
        "wget -q 'https://huggingface.co/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth' -O checkpoints/wav2lip_gan.pth",
        "wget -q 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth' -O checkpoints/GFPGANv1.4.pth"
    )
)

app = modal.App("fyp-docker-wav2lip")

# 2. 🚀 Cloud GPU Execution
@app.function(image=image, gpu="T4", timeout=1200) # T4 GPU purane CUDA k sath best chalta hai
def generate_avatar(image_bytes: bytes, audio_bytes: bytes):
    print("🚀 Running inside Docker Container on Cloud GPU...")
    
    with open("input.jpg", "wb") as f:
        f.write(image_bytes)
    with open("audio.wav", "wb") as f:
        f.write(audio_bytes)
    
    # Exact inference command jo lips ko pause karti hai aur sync karti hai
    os.system("python inference.py --face input.jpg --audio audio.wav --outfile output.mp4 --pads 0 10 0 0 --face_restore")
    
    with open("output.mp4", "rb") as f:
        return f.read()

# 3. 💻 Local Trigger
@app.local_entrypoint()
def main(face_path: str = "my_face.jpg", audio_path: str = "my_audio.wav"):
    print("📤 Sending files to Docker container on Modal...")
    
    with open(face_path, "rb") as f:
        img = f.read()
    with open(audio_path, "rb") as f:
        aud = f.read()
        
    result_video = generate_avatar.remote(img, aud)
    
    with open("FINAL_DOCKER_AVATAR.mp4", "wb") as f:
        f.write(result_video)
        
    print("✅ 10/10 Video Downloaded: FINAL_DOCKER_AVATAR.mp4")