import logging
import os
import tempfile

from ai_tools import text_to_audio
from concurrent.futures import ThreadPoolExecutor, as_completed
from natsort import natsorted
from pydub import AudioSegment  # type: ignore
from s3_utils import (
    file_exists,
    new_key_for_processed_file,
    write_file_to_s3,
)
from typing import List

MAX_TTS_CHARS = 4096

logger = logging.getLogger()


def reassemble_audio_files(tmp_files: List[str]) -> str:
    """Reassemble the audio files into one."""
    audio_segments = [AudioSegment.from_file(file) for file in tmp_files]
    combined = sum(audio_segments)
    temp_dir = tempfile.gettempdir()
    speech_file_path = os.path.join(temp_dir, "speech.mp3")
    combined.export(speech_file_path, format="mp3")
    return speech_file_path


def chunk_texts(text: str, max_length: int = MAX_TTS_CHARS) -> List[str]:
    chunks = text.split("\n")
    chunks_to_return = []
    for chunk in chunks:
        if len(chunk) > max_length:
            # If the chunk is too long, raise an error
            # TODO: Handle this more gracefully
            raise ValueError("Text chunk is too long")
        if chunk:
            # Only add non-empty chunks
            chunks_to_return.append(chunk)
    return chunks_to_return


def handle_audio(input_key: str, text: str, output_bucket: str) -> str:
    """Handle the audio conversion and storage.

    Convert the extracted text to audio and store it in S3
    If the audio file already exists, don't do anything

    """
    audio_key = new_key_for_processed_file(input_key, "audios", "mp3")
    audio_file_exists = file_exists(output_bucket, audio_key)
    if not audio_file_exists:
        # Chunk the text into smaller pieces
        chunked_texts = chunk_texts(text)

        # Convert each chunk to audio in parallel
        futures = []
        chunk_files = []
        with ThreadPoolExecutor() as executor:
            for idx, chunk in enumerate(chunked_texts):
                futures.append(executor.submit(text_to_audio, chunk, str(idx), "alloy"))

            chunk_files = [future.result() for future in as_completed(futures)]

        # Reassemble the audio files and write the final audio file to S3
        tmp_file = reassemble_audio_files(natsorted(chunk_files))
        write_file_to_s3(output_bucket, audio_key, tmp_file)
    else:
        logger.info(f"Audio file already exists: {output_bucket}/{audio_key}")

    return audio_key
