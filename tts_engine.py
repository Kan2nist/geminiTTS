import os
import struct
import mimetypes
from typing import Optional
from google import genai
from google.genai import types

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts: # Skip the main type part
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def generate_speech(api_key: str, text: str, voice_name: str, style_instructions: str, output_path: str, model_name: str):
    """
    Generates speech using Gemini API and saves to output_path.

    Args:
        api_key: The Google Cloud API key.
        text: The text to be spoken.
        voice_name: The name of the voice to use.
        style_instructions: Instructions for style/tone.
        output_path: The full path where the .wav file should be saved.
        model_name: The name of the Gemini model to use.
    """
    client = genai.Client(api_key=api_key)
    model = model_name

    # Construct the prompt with style instructions
    if style_instructions:
        full_text = f"{style_instructions}\n\n{text}"
    else:
        full_text = text

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=full_text),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        ),
    )

    # We need to accumulate the audio data or save the first valid chunk.
    # The example code iterates, but for a single request, we usually expect one continuous stream.
    # We will accumulate data if multiple chunks come, or just take the valid one.

    audio_buffer = bytearray()
    mime_type = "audio/pcm" # Default assumption, will update from chunk

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or not chunk.candidates
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue

        part = chunk.candidates[0].content.parts[0]

        if part.inline_data and part.inline_data.data:
            inline_data = part.inline_data
            audio_buffer.extend(inline_data.data)
            mime_type = inline_data.mime_type

    if len(audio_buffer) > 0:
        # Convert to WAV if needed (pcm usually needs header)
        # The example uses mimetypes.guess_extension to check if it's already a file format
        # but the convert_to_wav logic suggests it receives raw PCM often.

        # If it's raw PCM (likely if mime_type is audio/pcm or similar specific types), we add header.
        # If it's already mp3/wav, we might just save it.
        # However, the example code specifically checks:
        # if file_extension is None -> convert_to_wav

        ext = mimetypes.guess_extension(mime_type)
        if ext is None or ext == ".bin": # .bin often returned for unknown types
             final_data = convert_to_wav(bytes(audio_buffer), mime_type)
        else:
             # If it already has an extension, it might be a container format (like mp3 or wav)
             # But the example force calls convert_to_wav if extension is None.
             # Let's stick to the example logic: checks if extension is found.
             # Actually, for Gemini TTS, usually it returns raw PCM in `audio/pcm`.
             final_data = convert_to_wav(bytes(audio_buffer), mime_type)

        with open(output_path, "wb") as f:
            f.write(final_data)
        return True

    return False

def mock_generate_speech(text: str, output_path: str):
    """
    Mock function to generate a dummy WAV file for testing without API usage.
    """
    # Create a simple dummy WAV file (1 second of silence or noise)
    # 16-bit PCM, 24kHz, Mono
    sample_rate = 24000
    duration = 1 # second
    num_samples = sample_rate * duration
    data = b'\x00\x00' * num_samples # Silence

    header = convert_to_wav(data, "audio/L16;rate=24000")
    with open(output_path, "wb") as f:
        f.write(header)
    return True
