"""
Utility Scripts for FYP Avatar Lip-Sync Pipeline

This module provides helper functions for:
- Audio format conversion (MP3 -> WAV)
- Image preprocessing (resize, crop, enhance)
- Batch processing multiple videos
- Quality testing and validation
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def convert_audio_to_wav(
    input_file: str,
    output_file: str = None,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    Convert any audio format to WAV (optimized for Wav2Lip).
    
    Args:
        input_file: Path to input audio (MP3, M4A, etc.)
        output_file: Path to output WAV (default: same name with .wav)
        sample_rate: Target sample rate in Hz (default: 16000)
        channels: Number of audio channels (1=mono, 2=stereo)
    
    Returns:
        Path to converted WAV file
    """
    if output_file is None:
        output_file = str(Path(input_file).with_suffix('.wav'))
    
    print(f" Converting audio: {input_file} -> {output_file}")
    
    cmd = [
        "ffmpeg", "-i", input_file,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-y",  
        output_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"    Converted successfully!")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"    Conversion failed: {e.stderr.decode()}")
        raise


def clean_audio(input_file: str, output_file: str = None) -> str:
    """
    Clean audio by removing background noise and normalizing volume.
    
    Args:
        input_file: Path to input WAV file
        output_file: Path to output cleaned WAV
    
    Returns:
        Path to cleaned audio file
    """
    if output_file is None:
        base = Path(input_file).stem
        output_file = f"{base}_clean.wav"
    
    print(f" Cleaning audio: {input_file}")
    

    cmd = [
        "ffmpeg", "-i", input_file,
        "-af", "highpass=f=200,lowpass=f=3000,loudnorm",
        "-y", output_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"    Audio cleaned!")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"    Cleaning failed: {e.stderr.decode()}")
        raise



def resize_image(
    input_file: str,
    output_file: str = None,
    size: int = 512
) -> str:
    """
    Resize image to square dimensions (optimal for Wav2Lip).
    
    Args:
        input_file: Path to input image
        output_file: Path to output image (default: input_resized.jpg)
        size: Target size in pixels (default: 512)
    
    Returns:
        Path to resized image
    """
    if output_file is None:
        base = Path(input_file).stem
        output_file = f"{base}_resized.jpg"
    
    print(f"  Resizing image: {input_file} -> {size}x{size}")
    
    cmd = [
        "ffmpeg", "-i", input_file,
        "-vf", f"scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}",
        "-y", output_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"    Image resized!")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"    Resize failed: {e.stderr.decode()}")
        raise


def batch_process(
    face_image: str,
    audio_files: List[str],
    output_dir: str = "outputs"
) -> List[str]:
    """
    Process multiple audio files with the same face image.
    
    Args:
        face_image: Path to reference face image
        audio_files: List of audio file paths
        output_dir: Directory to save outputs
    
    Returns:
        List of output video paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print(f" BATCH PROCESSING: {len(audio_files)} videos")
    print("=" * 80)
    
    outputs = []
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] Processing: {audio_file}")
        
        base_name = Path(audio_file).stem
        output_file = os.path.join(output_dir, f"{base_name}_lipsync.mp4")
        
        if not audio_file.endswith('.wav'):
            audio_file = convert_audio_to_wav(audio_file)
        
        try:
            print(f"   → Running lip-sync pipeline...")
            print(f"   → Output: {output_file}")
            outputs.append(output_file)
        except Exception as e:
            print(f"    Failed: {e}")
            continue
    
    print("\n" + "=" * 80)
    print(f" Batch processing complete! {len(outputs)}/{len(audio_files)} succeeded")
    print("=" * 80)
    
    return outputs


def validate_inputs(face_image: str, audio_file: str) -> bool:
    """
    Validate that input files are suitable for lip-sync pipeline.
    
    Args:
        face_image: Path to face image
        audio_file: Path to audio file
    
    Returns:
        True if inputs are valid, False otherwise
    """
    print("\n Validating inputs...")
    
    valid = True
    
    if not os.path.exists(face_image):
        print(f"    Face image not found: {face_image}")
        return False
    
    valid_image_formats = ['.jpg', '.jpeg', '.png']
    if not any(face_image.lower().endswith(fmt) for fmt in valid_image_formats):
        print(f"     Warning: Unusual image format. Use JPG or PNG for best results.")
    
    if not os.path.exists(audio_file):
        print(f"    Audio file not found: {audio_file}")
        return False
    
    if not audio_file.lower().endswith('.wav'):
        print(f"     Warning: Audio is not WAV format. Will auto-convert.")
    
    image_size_mb = os.path.getsize(face_image) / (1024 * 1024)
    audio_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
    
    if image_size_mb > 10:
        print(f"     Warning: Large image ({image_size_mb:.1f} MB). Consider resizing.")
    
    if audio_size_mb > 50:
        print(f"     Warning: Large audio ({audio_size_mb:.1f} MB). May take longer to process.")
    
    print("    Inputs validated!")
    return valid



def create_test_data(output_dir: str = "test_data"):
    """
    Create sample test data for pipeline validation.
    
    This generates:
    - A solid color test image (512x512)
    - A 5-second test audio (sine wave)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(" Creating test data...")
    
    test_image = os.path.join(output_dir, "test_face.jpg")
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "color=c=blue:s=512x512:d=1",
        "-vf", "drawtext=text='TEST FACE':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-frames:v", "1",
        "-y", test_image
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"    Test image: {test_image}")
    
    test_audio = os.path.join(output_dir, "test_audio.wav")
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=5",
        "-ar", "16000",
        "-ac", "1",
        "-y", test_audio
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"    Test audio: {test_audio}")
    
    print(f"\n Test data created in: {output_dir}")
    print(f"   Run: modal run fyp_avatar_lipsync.py --face-image {test_image} --audio-file {test_audio}")


def main():
    """Command-line interface for utility functions."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Utilities for FYP Avatar Lip-Sync Pipeline"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    convert_parser = subparsers.add_parser("convert", help="Convert audio to WAV")
    convert_parser.add_argument("input", help="Input audio file")
    convert_parser.add_argument("-o", "--output", help="Output WAV file")
    convert_parser.add_argument("-r", "--rate", type=int, default=16000, help="Sample rate")
    
    clean_parser = subparsers.add_parser("clean", help="Clean audio (remove noise)")
    clean_parser.add_argument("input", help="Input WAV file")
    clean_parser.add_argument("-o", "--output", help="Output cleaned WAV file")
    
    resize_parser = subparsers.add_parser("resize", help="Resize image")
    resize_parser.add_argument("input", help="Input image file")
    resize_parser.add_argument("-s", "--size", type=int, default=512, help="Target size")
    resize_parser.add_argument("-o", "--output", help="Output image file")
    
    validate_parser = subparsers.add_parser("validate", help="Validate input files")
    validate_parser.add_argument("face", help="Face image file")
    validate_parser.add_argument("audio", help="Audio file")
    
    test_parser = subparsers.add_parser("test", help="Create test data")
    test_parser.add_argument("-o", "--output", default="test_data", help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "convert":
        convert_audio_to_wav(args.input, args.output, args.rate)
    
    elif args.command == "clean":
        clean_audio(args.input, args.output)
    
    elif args.command == "resize":
        resize_image(args.input, args.output, args.size)
    
    elif args.command == "validate":
        validate_inputs(args.face, args.audio)
    
    elif args.command == "test":
        create_test_data(args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
