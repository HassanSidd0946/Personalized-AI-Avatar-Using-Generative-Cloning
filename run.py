"""
run.py — CLI Entry Point for AI Avatar Pipeline
================================================
Location : MODAL/run.py

This script is the ONLY entry point. It handles all input resolution
(direct text vs .txt file) and delegates to main_pipeline.run_pipeline().

main_pipeline.py is never modified — it stays a pure, importable module.

Usage:
------
  # Option A: Direct text string
  python run.py --text "Hello, I am your AI avatar." ^
                --ref-audio XTTS-v2/ref_audio.wav ^
                --face WavTOlip/avatar1.jpg

  # Option B: Text from a .txt file
  python run.py --text-file scripts/demo_script.txt ^
                --ref-audio XTTS-v2/ref_audio.wav ^
                --face WavTOlip/avatar1.jpg

  # Optional flags (same as before):
  #   --output-dir  results/
  #   --voice-file  my_voice.wav
  #   --use-deployed
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the pipeline — run.py is always executed from MODAL/ root
# ---------------------------------------------------------------------------
from main_pipeline import run_pipeline


# ---------------------------------------------------------------------------
# Text resolution
# ---------------------------------------------------------------------------

def resolve_text(args: argparse.Namespace) -> str:
    """
    Return the final cleaned text string from either --text or --text-file.

    Rules applied to file input:
      - Newlines replaced with spaces        (prevents XTTS-v2 mumbling)
      - Multiple consecutive spaces collapsed (clean output)
      - Leading/trailing whitespace stripped

    Raises SystemExit if neither argument is provided, both are provided,
    the file doesn't exist, or the file is empty after cleaning.
    """

    # ── Mutual exclusivity guard ─────────────────────────────────────────────
    if args.text and args.text_file:
        _die(
            "Provide either --text OR --text-file, not both.",
            hint='python run.py --text "Hello world" ...'
        )

    if not args.text and not args.text_file:
        _die(
            "You must provide either --text or --text-file.",
            hint=(
                'python run.py --text "Hello world" ...\n'
                "  OR\n"
                "  python run.py --text-file scripts/my_script.txt ..."
            )
        )

    # ── Direct text ──────────────────────────────────────────────────────────
    if args.text:
        text = args.text.strip()
        if not text:
            _die("--text value is empty after stripping whitespace.")
        _log_source("direct --text argument", preview=text)
        return text

    # ── File input ───────────────────────────────────────────────────────────
    file_path = Path(args.text_file)

    if not file_path.exists():
        _die(f"Text file not found: {file_path}")

    if file_path.suffix.lower() != ".txt":
        print(f"  ⚠  Warning: '{file_path.name}' is not a .txt file — proceeding anyway.")

    raw = file_path.read_text(encoding="utf-8")

    # Clean: newlines → spaces, collapse multi-spaces, strip ends
    cleaned = " ".join(raw.split())

    if not cleaned:
        _die(f"Text file is empty after cleaning: {file_path}")

    _log_source(f"file: {file_path}", preview=cleaned)

    # Show what was cleaned so the user can verify
    original_lines = raw.strip().count("\n") + 1
    if original_lines > 1:
        print(f"    Lines in file    : {original_lines}")
        print(f"    Newlines removed : {original_lines - 1}  (collapsed to spaces)")

    return cleaned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_source(source: str, preview: str) -> None:
    max_preview = 90
    truncated = preview[:max_preview] + ("..." if len(preview) > max_preview else "")
    print(f"\n  Text source  : {source}")
    print(f"  Preview      : {truncated}")
    print(f"  Total chars  : {len(preview)}\n")


def _die(message: str, hint: str = "") -> None:
    print(f"\n❌  {message}")
    if hint:
        print(f"\n  Example:\n  {hint}")
    print()
    sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="AI Avatar Pipeline — XTTS-v2 voice cloning + Wav2Lip lip-sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Input modes (mutually exclusive):
  --text        Provide the script directly as a string.
  --text-file   Path to a .txt file containing the script.
                Newlines are automatically collapsed to spaces.

Examples:
  python run.py ^
      --text "Hello, I am your AI avatar." ^
      --ref-audio XTTS-v2/ref_audio.wav ^
      --face WavTOlip/avatar1.jpg

  python run.py ^
      --text-file scripts/fyp_demo.txt ^
      --ref-audio XTTS-v2/ref_audio.wav ^
      --face WavTOlip/slient_head.mp4 ^
      --output-dir results/fyp_demo
        """,
    )

    # ── Input source (mutually exclusive) ────────────────────────────────────
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--text", "-t",
        default=None,
        metavar="STRING",
        help="Avatar script as a direct string.",
    )
    input_group.add_argument(
        "--text-file", "-tf",
        default=None,
        metavar="PATH",
        help="Path to a .txt file containing the avatar script.",
    )

    # ── Required pipeline inputs ─────────────────────────────────────────────
    parser.add_argument(
        "--ref-audio", "-r",
        required=True,
        metavar="PATH",
        help="Reference audio (.wav) for voice cloning.",
    )
    parser.add_argument(
        "--face", "-f",
        required=True,
        metavar="PATH",
        help="Avatar image (.jpg/.png) or video (.mp4).",
    )

    # ── Optional pipeline flags ───────────────────────────────────────────────
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        metavar="DIR",
        help="Output directory (default: output/).",
    )
    parser.add_argument(
        "--voice-file",
        default=None,
        metavar="FILENAME",
        help="Override generated voice filename (default: voice_<timestamp>.wav).",
    )
    parser.add_argument(
        "--use-deployed",
        action="store_true",
        help=(
            "Connect to an already-deployed Modal app instead of ephemeral mode. "
            "Requires prior: modal deploy WavTOlip/MODAL_HUG_GIT.py"
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # ── Banner ────────────────────────────────────────────────────────────────
    width = 62
    print("\n" + "=" * width)
    print("  AI Avatar Pipeline  |  run.py")
    print("=" * width)

    # ── Resolve input text ────────────────────────────────────────────────────
    text = resolve_text(args)

    # ── Print full config ─────────────────────────────────────────────────────
    print("  Configuration")
    print("  " + "-" * 44)
    print(f"  Ref audio    : {args.ref_audio}")
    print(f"  Face input   : {args.face}")
    print(f"  Output dir   : {args.output_dir}")
    print(f"  Modal mode   : {'deployed' if args.use_deployed else 'ephemeral'}\n")

    # ── Delegate to pipeline ──────────────────────────────────────────────────
    try:
        final_video = run_pipeline(
            text=text,
            ref_audio_path=args.ref_audio,
            face_path=args.face,
            output_dir=args.output_dir,
            voice_filename=args.voice_file,
            use_deployed=args.use_deployed,
        )

        print("\n" + "=" * width)
        print("  Pipeline Complete!")
        print("=" * width)
        print(f"\n  Final video  : {final_video}\n")

    except FileNotFoundError as e:
        _die(f"File error: {e}")
    except KeyboardInterrupt:
        print("\n  Pipeline cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌  Pipeline error: {e}")
        raise


if __name__ == "__main__":
    main()