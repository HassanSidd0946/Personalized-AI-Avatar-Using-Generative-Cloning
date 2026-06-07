import replicate
import requests
import os

def generate_avatar_voice(text: str, reference_audio_path: str, output_path: str) -> str:
    """
    Generate cloned voice audio using the xtts-v2 model.

    Args:
        text: The text to synthesize into speech.
        reference_audio_path: Local path to the reference audio file for voice cloning.
        output_path: Local path where the output .wav file will be saved.

    Returns:
        The output_path if successful.

    Raises:
        FileNotFoundError: If the reference audio file does not exist.
    """


    if not os.path.exists(reference_audio_path):
        raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

    try:
        with open(reference_audio_path, "rb") as speaker_file:
            output = replicate.run(
                "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
                # "lucataco/xtts-v2",
                input={
                    "text": text,
                    "speaker": speaker_file,
                    "language": "en"
                }
            )


        audio_url = output
        if not audio_url:
            raise ValueError("Replicate returned an empty output URL.")


        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()  


        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as out_file:
            out_file.write(response.content)

        print(f"[✓] Audio saved to: {output_path}")
        return output_path

    except replicate.exceptions.ReplicateError as e:
        raise Exception(f"error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download audio from URL: {e}") from e


if __name__ == "__main__":
    generate_avatar_voice(
        text="Hello, this is my personalized AI avatar speaking.",
        reference_audio_path="ref_audio.wav",   
        output_path="output/avatar_voice.wav"
    )
