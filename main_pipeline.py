# """
# main_pipeline.py — Master AI Avatar Pipeline Orchestrator
# ==========================================================
# Location : MODAL/main_pipeline.py

# Two invocation modes
# ---------------------
# A) Ephemeral — default, no prior deploy needed:
#        python main_pipeline.py --text "..." --ref-audio "..." --face "..."

# B) Deployed  — faster if you've already run `modal deploy`:
#        python main_pipeline.py --text "..." --ref-audio "..." --face "..." --use-deployed

# Optional flags:
#   --output-dir  "output"        (default: MODAL/output/)
#   --voice-file  "my_voice.wav"  (override generated voice filename)
#   --use-deployed                (look up already-deployed Modal app)
# """

# import argparse
# import os
# import sys
# from datetime import datetime
# from pathlib import Path

# # ---------------------------------------------------------------------------
# # Path setup — make sibling packages importable regardless of CWD
# # ---------------------------------------------------------------------------
# ROOT = Path(__file__).parent.resolve()
# sys.path.insert(0, str(ROOT / "XTTS-v2"))   # exposes avatar_voice
# sys.path.insert(0, str(ROOT / "WavTOlip"))  # exposes MODAL_HUG_GIT

# # ---------------------------------------------------------------------------
# # Local imports (after path setup)
# # ---------------------------------------------------------------------------
# import modal
# from avatar_voice import generate_avatar_voice  

# # Import the app + function objects (not yet hydrated — that happens at call time)
# from MODAL_HUG_GIT import app as lipsync_app
# from MODAL_HUG_GIT import generate_lipsync_video


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _banner(title: str) -> None:
#     width = 62
#     print("\n" + "=" * width)
#     print(f"  {title}")
#     print("=" * width + "\n")


# def _step(n: int, total: int, msg: str) -> None:
#     print(f"[{n}/{total}] {msg}")


# def _load_env_file() -> None:
#     """Load variables from MODAL/.env into os.environ if present."""
#     env_file = ROOT / ".env"
#     if not env_file.exists():
#         return
#     with open(env_file) as f:
#         for line in f:
#             line = line.strip()
#             if not line or line.startswith("#") or "=" not in line:
#                 continue
#             key, val = line.split("=", 1)
#             key = key.strip()
#             val = val.strip().strip('"').strip("'")
#             if key and val and key not in os.environ:
#                 os.environ[key] = val
#                 print(f"    [.env] Loaded {key}")


# def _check_env() -> None:
#     """Load .env then fail fast if required tokens are still missing."""
#     _load_env_file()
#     token = os.environ.get("REPLICATE_API_TOKEN")
#     if not token:
#         print("REPLICATE_API_TOKEN is not set.\n")
#         print("Option 1 — set in this PowerShell session:")
#         print('  $env:REPLICATE_API_TOKEN = "r8_..."')
#         print("\nOption 2 — create MODAL\\.env file containing:")
#         print("  REPLICATE_API_TOKEN=r8_...")
#         sys.exit(1)


# # ---------------------------------------------------------------------------
# # Inner pipeline — must be called while a Modal context is active
# # ---------------------------------------------------------------------------

# def _run_pipeline_inner(
#     text: str,
#     ref_audio_path: str,
#     face_path: str,
#     output_dir: str,
#     voice_filename,   # str | None
#     lipsync_fn,       # the hydrated Modal function to call
# ) -> str:
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     output_dir_path = Path(output_dir)
#     output_dir_path.mkdir(parents=True, exist_ok=True)

#     for label, path in [("Reference audio", ref_audio_path), ("Face image", face_path)]:
#         if not Path(path).exists():
#             raise FileNotFoundError(f"{label} not found: {path}")

#     TOTAL_STEPS = 3

#     # ── Step 1 : Voice cloning (local, Replicate API) ────────────────────────
#     _step(1, TOTAL_STEPS, "Cloning voice with XTTS-v2...")
#     print(f"    Text        : {text[:80]}{'...' if len(text) > 80 else ''}")
#     print(f"    Ref audio   : {ref_audio_path}\n")

#     voice_name = voice_filename or f"voice_{timestamp}.wav"
#     voice_output_path = str(output_dir_path / voice_name)

#     generated_audio_path = generate_avatar_voice(
#         text=text,
#         reference_audio_path=ref_audio_path,
#         output_path=voice_output_path,
#     )
#     audio_size_kb = Path(generated_audio_path).stat().st_size / 1024
#     print(f"\n    Voice saved -> {generated_audio_path}  ({audio_size_kb:.1f} KB)\n")

#     # ── Step 2 : Lip-sync on Modal GPU ───────────────────────────────────────
#     _step(2, TOTAL_STEPS, "Generating lip-sync video (Modal T4 GPU)...")
#     print(f"    Face image  : {face_path}")
#     print(f"    Audio       : {generated_audio_path}\n")

#     with open(face_path, "rb") as fh:
#         image_bytes = fh.read()
#     with open(generated_audio_path, "rb") as fh:
#         audio_bytes = fh.read()

#     print("    Dispatching to Modal... (this takes 2-5 minutes)\n")
#     video_bytes = lipsync_fn.remote(image_bytes, audio_bytes)

#     # ── Step 3 : Save output ─────────────────────────────────────────────────
#     _step(3, TOTAL_STEPS, "Saving final video...")
#     video_filename = f"avatar_{timestamp}.mp4"
#     video_output_path = str(output_dir_path / video_filename)

#     with open(video_output_path, "wb") as fh:
#         fh.write(video_bytes)

#     video_size_mb = len(video_bytes) / 1024 / 1024
#     print(f"    Video saved -> {video_output_path}  ({video_size_mb:.2f} MB)\n")

#     return video_output_path


# # ---------------------------------------------------------------------------
# # Public entry point — handles both ephemeral and deployed modes
# # ---------------------------------------------------------------------------

# def run_pipeline(
#     text: str,
#     ref_audio_path: str,
#     face_path: str,
#     output_dir: str = "output",
#     voice_filename=None,   # str | None
#     use_deployed: bool = False,
# ) -> str:
#     _check_env()
#     """
#     End-to-end pipeline: TTS -> Lip-sync.

#     Parameters
#     ----------
#     text            : Text for the avatar to speak.
#     ref_audio_path  : Local path to reference audio for voice cloning.
#     face_path       : Local path to the static avatar image (.jpg / .png).
#     output_dir      : Directory where all outputs are saved.
#     voice_filename  : Override the generated WAV filename (optional).
#     use_deployed    : Connect to an already-deployed Modal app instead of
#                       spinning up an ephemeral one.
#                       Requires prior: modal deploy WavTOlip/MODAL_HUG_GIT.py

#     Returns
#     -------
#     str — absolute path to the final lip-synced video.
#     """
#     inner_kwargs = dict(
#         text=text,
#         ref_audio_path=ref_audio_path,
#         face_path=face_path,
#         output_dir=output_dir,
#         voice_filename=voice_filename,
#     )

#     if use_deployed:
#         # ── Deployed mode ────────────────────────────────────────────────────
#         # Connects to the live app without a local app.run() context.
#         # Requires:  modal deploy WavTOlip/MODAL_HUG_GIT.py
#         print("    Mode: connecting to deployed Modal app...\n")
#         fn = modal.Function.lookup(
#             "fyp-avatar-lipsync-backend",
#             "generate_lipsync_video"
#         )
#         return _run_pipeline_inner(lipsync_fn=fn, **inner_kwargs)

#     else:
#         # ── Ephemeral mode (default) ─────────────────────────────────────────
#         # Validate token HERE — before app.run() — because Windows does not
#         # reliably propagate $env: variables into Modal's async event loop.
#         _check_env()
#         print("    Mode: ephemeral Modal app (no prior deploy needed)\n")
#         with lipsync_app.run():
#             return _run_pipeline_inner(lipsync_fn=generate_lipsync_video, **inner_kwargs)


# # ---------------------------------------------------------------------------
# # CLI
# # ---------------------------------------------------------------------------

# def _parse_args() -> argparse.Namespace:
#     parser = argparse.ArgumentParser(
#         description="AI Avatar Pipeline - TTS (XTTS-v2) + Lip-Sync (Wav2Lip + GFPGAN)",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   # Ephemeral mode — no prior deploy needed (default)
#   python main_pipeline.py ^
#       --text "Hello, I am your AI avatar." ^
#       --ref-audio XTTS-v2/ref_audio.wav ^
#       --face WavTOlip/avatar1.jpg

#   # Deployed mode — faster cold-start after `modal deploy WavTOlip/MODAL_HUG_GIT.py`
#   python main_pipeline.py ^
#       --text "Hello, I am your AI avatar." ^
#       --ref-audio XTTS-v2/ref_audio.wav ^
#       --face WavTOlip/avatar1.jpg ^
#       --use-deployed
#         """,
#     )
#     parser.add_argument("--text", "-t", required=True,
#                         help="Text the avatar should speak.")
#     parser.add_argument("--ref-audio", "-r", required=True, metavar="PATH",
#                         help="Reference audio for voice cloning (.wav).")
#     parser.add_argument("--face", "-f", required=True, metavar="PATH",
#                         help="Static avatar image (.jpg / .png).")
#     parser.add_argument("--output-dir", "-o", default="output", metavar="DIR",
#                         help="Output directory (default: output/).")
#     parser.add_argument("--voice-file", default=None, metavar="FILENAME",
#                         help="Override generated WAV filename.")
#     parser.add_argument("--use-deployed", action="store_true",
#                         help="Connect to already-deployed Modal app (requires prior `modal deploy`).")
#     return parser.parse_args()


# def main() -> None:
#     args = _parse_args()

#     _banner("AI Avatar Pipeline  |  XTTS-v2 -> Wav2Lip + GFPGAN")

#     print("  Configuration")
#     print("  " + "-" * 44)
#     print(f"  Text        : {args.text[:70]}{'...' if len(args.text) > 70 else ''}")
#     print(f"  Ref audio   : {args.ref_audio}")
#     print(f"  Face image  : {args.face}")
#     print(f"  Output dir  : {args.output_dir}")
#     print(f"  Mode        : {'deployed' if args.use_deployed else 'ephemeral'}\n")

#     try:
#         final_video = run_pipeline(
#             text=args.text,
#             ref_audio_path=args.ref_audio,
#             face_path=args.face,
#             output_dir=args.output_dir,
#             voice_filename=args.voice_file,
#             use_deployed=args.use_deployed,
#         )

#         _banner("Pipeline Complete!")
#         print(f"  Final video : {final_video}\n")

#     except FileNotFoundError as e:
#         print(f"\n  File error    : {e}")
#         sys.exit(1)
#     except KeyboardInterrupt:
#         print("\n  Pipeline cancelled by user.")
#         sys.exit(0)
#     except Exception as e:
#         print(f"\n  Pipeline error: {e}")
#         raise


# if __name__ == "__main__":
#     main()








"""
main_pipeline.py — Master AI Avatar Pipeline Orchestrator

Two invocation modes
---------------------
A) Ephemeral — default, no prior deploy needed:
       python main_pipeline.py --text "..." --ref-audio "..." --face "..."

B) Deployed  — faster if you've already run `modal deploy`:
       python main_pipeline.py --text "..." --ref-audio "..." --face "..." --use-deployed

Optional flags:
  --output-dir  "output"        (default: MODAL/output/)
  --voice-file  "my_voice.wav"  (override generated voice filename)
  --use-deployed                (look up already-deployed Modal app)
"""

import argparse
import os
import subprocess  
import sys
from datetime import datetime
from pathlib import Path

import modal
from avatar_voice import generate_avatar_voice  

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT / "XTTS-v2"))   
sys.path.insert(0, str(ROOT / "WavTOlip"))


from MODAL_HUG_GIT import app as lipsync_app
from MODAL_HUG_GIT import generate_lipsync_video


def _banner(title: str) -> None:
    width = 62
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width + "\n")


def _step(n: int, total: int, msg: str) -> None:
    print(f"[{n}/{total}] {msg}")


def _load_env_file() -> None:
    """Load variables from MODAL/.env into os.environ if present."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val and key not in os.environ:
                os.environ[key] = val
                print(f"    [.env] Loaded {key}")


def _check_env() -> None:
    """Load .env then fail fast if required tokens are still missing."""
    _load_env_file()
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("REPLICATE_API_TOKEN is not set.\n")
        print("Option 1 — set in this PowerShell session:")
        print('  $env:REPLICATE_API_TOKEN = "r8_..."')
        print("\nOption 2 — create MODAL\\.env file containing:")
        print("  REPLICATE_API_TOKEN=r8_...")
        sys.exit(1)


def _run_pipeline_inner(
    text: str,
    ref_audio_path: str,
    face_path: str,
    output_dir: str,
    voice_filename,   
    lipsync_fn,       
) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    for label, path in [("Reference audio", ref_audio_path), ("Face image", face_path)]:
        if not Path(path).exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    TOTAL_STEPS = 3

    
    _step(1, TOTAL_STEPS, "Cloning voice with XTTS-v2...")
    print(f"    Text        : {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"    Ref audio   : {ref_audio_path}\n")

    voice_name = voice_filename or f"voice_{timestamp}.wav"
    voice_output_path = str(output_dir_path / voice_name)

    generated_audio_path = generate_avatar_voice(
        text=text,
        reference_audio_path=ref_audio_path,
        output_path=voice_output_path,
    )
    audio_size_kb = Path(generated_audio_path).stat().st_size / 1024
    print(f"\n    Voice saved -> {generated_audio_path}  ({audio_size_kb:.1f} KB)\n")

    
    _step(2, TOTAL_STEPS, "Generating lip-sync video (Modal T4 GPU)...")
    print(f"    Face image  : {face_path}")
    print(f"    Audio       : {generated_audio_path}\n")

    with open(face_path, "rb") as fh:
        image_bytes = fh.read()
    with open(generated_audio_path, "rb") as fh:
        audio_bytes = fh.read()

    print("    Dispatching to Modal... (this takes several minutes depending on text length)\n")
    video_bytes = lipsync_fn.remote(image_bytes, audio_bytes)

    
    _step(3, TOTAL_STEPS, "Saving final video...")
    video_filename = f"avatar_{timestamp}.mp4"
    video_output_path = str(output_dir_path / video_filename)

    with open(video_output_path, "wb") as fh:
        fh.write(video_bytes)

    video_size_mb = len(video_bytes) / 1024 / 1024
    print(f"    Video saved -> {video_output_path}  ({video_size_mb:.2f} MB)\n")

    
    _temp_converted_path = video_output_path + ".converted.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_output_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            _temp_converted_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.replace(_temp_converted_path, video_output_path)
    print(f"    Video re-encoded (libx264/yuv420p) -> {video_output_path}\n")

    return video_output_path


def run_pipeline(
    text: str,
    ref_audio_path: str,
    face_path: str,
    output_dir: str = "output",
    voice_filename=None,   # str | None
    use_deployed: bool = False,
) -> str:
    _check_env()
    """
    End-to-end pipeline: TTS -> Lip-sync.

    Parameters
    ----------
    text            : Text for the avatar to speak.
    ref_audio_path  : Local path to reference audio for voice cloning.
    face_path       : Local path to the static avatar image (.jpg / .png).
    output_dir      : Directory where all outputs are saved.
    voice_filename  : Override the generated WAV filename (optional).
    use_deployed    : Connect to an already-deployed Modal app instead of
                      spinning up an ephemeral one.
                      Requires prior: modal deploy WavTOlip/MODAL_HUG_GIT.py

    Returns
    -------
    str — absolute path to the final lip-synced video.
    """
    inner_kwargs = dict(
        text=text,
        ref_audio_path=ref_audio_path,
        face_path=face_path,
        output_dir=output_dir,
        voice_filename=voice_filename,
    )

    if use_deployed:
        print("    Mode: connecting to deployed Modal app...\n")
        fn = modal.Function.lookup(
            "fyp-avatar-lipsync-backend",
            "generate_lipsync_video"
        )
        return _run_pipeline_inner(lipsync_fn=fn, **inner_kwargs)

    else:
        _check_env()
        print("    Mode: ephemeral Modal app (no prior deploy needed)\n")
        with lipsync_app.run():
            return _run_pipeline_inner(lipsync_fn=generate_lipsync_video, **inner_kwargs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Avatar Pipeline - TTS (XTTS-v2) + Lip-Sync (Wav2Lip + GFPGAN)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ephemeral mode — no prior deploy needed (default)
  python main_pipeline.py 
      --text "Hello, I am your AI avatar." 
      --ref-audio XTTS-v2/ref_audio.wav 
      --face WavTOlip/avatar1.jpg

  # Deployed mode — faster cold-start after `modal deploy WavTOlip/MODAL_HUG_GIT.py`
  python main_pipeline.py 
      --text "Hello, I am your AI avatar." 
      --ref-audio XTTS-v2/ref_audio.wav 
      --face WavTOlip/avatar1.jpg 
      --use-deployed
        """,
    )
    parser.add_argument("--text", "-t", required=True,
                        help="Text the avatar should speak.")
    parser.add_argument("--ref-audio", "-r", required=True, metavar="PATH",
                        help="Reference audio for voice cloning (.wav).")
    parser.add_argument("--face", "-f", required=True, metavar="PATH",
                        help="Static avatar image (.jpg / .png).")
    parser.add_argument("--output-dir", "-o", default="output", metavar="DIR",
                        help="Output directory (default: output/).")
    parser.add_argument("--voice-file", default=None, metavar="FILENAME",
                        help="Override generated WAV filename.")
    parser.add_argument("--use-deployed", action="store_true",
                        help="Connect to already-deployed Modal app (requires prior `modal deploy`).")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    _banner("AI Avatar Pipeline  |  XTTS-v2 -> Wav2Lip + GFPGAN")

    print("  Configuration")
    print("  " + "-" * 44)
    print(f"  Text        : {args.text[:70]}{'...' if len(args.text) > 70 else ''}")
    print(f"  Ref audio   : {args.ref_audio}")
    print(f"  Face image  : {args.face}")
    print(f"  Output dir  : {args.output_dir}")
    print(f"  Mode        : {'deployed' if args.use_deployed else 'ephemeral'}\n")

    try:
        final_video = run_pipeline(
            text=args.text,
            ref_audio_path=args.ref_audio,
            face_path=args.face,
            output_dir=args.output_dir,
            voice_filename=args.voice_file,
            use_deployed=args.use_deployed,
        )

        _banner("Pipeline Complete!")
        print(f"  Final video : {final_video}\n")

    except FileNotFoundError as e:
        print(f"\n  File error    : {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Pipeline cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Pipeline error: {e}")
        raise


if __name__ == "__main__":
    main()
