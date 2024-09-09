import logging
import os
import tempfile

from ai_tools import extract_text_from_raw_data, text_to_audio
from concurrent.futures import ThreadPoolExecutor, as_completed
from natsort import natsorted
from pydub import AudioSegment  # type: ignore
from responses import success_response, error_response
from s3_utils import (
    file_exists,
    get_file_content_from_s3,
    new_key_for_processed_file,
    write_file_to_s3,
    write_extracted_text_to_s3,
)
from typing import List

logger = logging.getLogger()

MAX_TTS_CHARS = 4096


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


def lambda_handler(event, _):
    bucket = event["bucket"]
    key = event["key"]
    raw_data = get_file_content_from_s3(bucket, key)

    # Extract text from the raw data and store it in S3
    # If the text file already exists, retrieve the text from S3
    output_bucket = os.environ["OUTPUT_S3_BUCKET"]
    text_key = new_key_for_processed_file(key, "texts", "txt")

    text_file_exists = file_exists(output_bucket, text_key)
    if not text_file_exists:
        extracted_text = extract_text_from_raw_data(raw_data)
    else:
        logger.info(
            f"Text file already exists: {output_bucket}/{text_key}, getting text from S3"
        )
        extracted_text = get_file_content_from_s3(output_bucket, text_key)

    if not text_file_exists and extracted_text:
        write_extracted_text_to_s3(output_bucket, text_key, extracted_text)
    elif not extracted_text:
        return error_response(f"Failed to extract text from {key}")

    # Convert the extracted text to audio and store it in S3
    # If the audio file already exists, don't do anything
    audio_key = new_key_for_processed_file(key, "audios", "mp3")
    audio_file_exists = file_exists(output_bucket, audio_key)
    if not audio_file_exists:
        # Chunk the text into smaller pieces
        chunked_texts = chunk_texts(extracted_text)

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

    return success_response(
        f"Extracted text from {key} stored in {output_bucket}/{text_key} and audio stored in {output_bucket}/{audio_key}"
    )
