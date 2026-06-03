import replicate
import requests
import os

def generate_avatar_voice(text: str, reference_audio_path: str, output_path: str) -> str:
    """
    Generate cloned voice audio using the lucataco/xtts-v2 model on Replicate.

    Args:
        text: The text to synthesize into speech.
        reference_audio_path: Local path to the reference audio file for voice cloning.
        output_path: Local path where the output .wav file will be saved.

    Returns:
        The output_path if successful.

    Raises:
        FileNotFoundError: If the reference audio file does not exist.
        Exception: For Replicate API or download failures.
    """

    # --- Validate reference audio exists before making any API calls ---
    if not os.path.exists(reference_audio_path):
        raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

    try:
        # --- Open the reference audio and run the model ---
        # Only the three bare-minimum inputs are passed: text, speaker, language
        with open(reference_audio_path, "rb") as speaker_file:
            output = replicate.run(
                "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
                input={
                    "text": text,
                    "speaker": speaker_file,
                    "language": "en"
                }
            )


        # --- The model returns a URL string pointing to the generated audio ---
        audio_url = output
        if not audio_url:
            raise ValueError("Replicate returned an empty output URL.")

        print(f"[✓] Audio generated. Downloading from: {audio_url}")

        # --- Download the audio file from the returned URL ---
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()  # Raise an error for bad HTTP status codes

        # --- Ensure the output directory exists, then save the .wav file ---
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as out_file:
            out_file.write(response.content)

        print(f"[✓] Audio saved to: {output_path}")
        return output_path

    except replicate.exceptions.ReplicateError as e:
        raise Exception(f"Replicate API error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download audio from URL: {e}") from e


# ---------------------------------------------------------------------------
# Entry point — replace these values with your actual inputs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # REPLICATE_API_TOKEN must be set in your environment:
    #   export REPLICATE_API_TOKEN="r8_..."
    generate_avatar_voice(
        text="Hello, this is my personalized AI avatar speaking.",
        reference_audio_path="ref_audio.wav",   # Your voice sample (3–15 sec ideal)
        output_path="output/avatar_voice.wav"
    )