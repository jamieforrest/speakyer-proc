import boto3  # type: ignore
import logging
import os
import tempfile

from botocore.exceptions import ClientError  # type: ignore
from concurrent.futures import ThreadPoolExecutor, as_completed
from natsort import natsorted
from openai import OpenAI
from pydub import AudioSegment  # type: ignore
from responses import success_response, error_response
from typing import List, Literal

s3 = boto3.client("s3")
logger = logging.getLogger()
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60)

MAX_TTS_CHARS = 4096


def get_file_content_from_s3(bucket: str, key: str) -> str:
    """Get the content of a file from S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def extract_text_from_raw_data(raw_data: str) -> str | None:
    """Extract the readable content from the raw email data."""
    base_prompt = """Extract the readable content from the raw email data below and respond with just the readable content.
    Don't just give me a summary; give me as much of the readable text as you can and remain as close to the original text as you can.
    You should be showing me just the plain text from the raw data, suitable for sending to a text-to-speech model to read the text aloud.
    Do not include any email metadata information like "from", "to", "subject", etc. Do not include any other explanation or text. ONLY include the readable text in your response.

    Here is the raw data:
    """

    prompt = f"{base_prompt}{raw_data}"

    logger.info(f"Prompt to OpenAI: {prompt}")
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_tokens=16383,
    )
    extracted_text = response.choices[0].message.content
    logger.info(f"Response from OpenAI: {extracted_text}")
    return extracted_text


def reassemble_audio_files(tmp_files: List[str]) -> str:
    """Reassemble the audio files into one."""
    audio_segments = [AudioSegment.from_file(file) for file in tmp_files]
    combined = sum(audio_segments)
    temp_dir = tempfile.gettempdir()
    speech_file_path = os.path.join(temp_dir, "speech.mp3")
    combined.export(speech_file_path, format="mp3")
    return speech_file_path


def text_to_audio(
    text: str,
    filename: str,
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy",
) -> str:
    """Convert text to audio. Returns the path to the audio file."""
    temp_dir = tempfile.gettempdir()
    speech_file_path = os.path.join(temp_dir, filename + ".mp3")
    with openai_client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=voice,
        input=text,
    ) as response:
        response.stream_to_file(speech_file_path)
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


def file_exists(bucket: str, key: str) -> bool:
    """Check if a file exists in S3."""
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            raise e
    else:
        return True


def write_extracted_text_to_s3(bucket: str, key: str, extracted_text: str) -> None:
    """Write the extracted text to S3."""
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=extracted_text,
    )


def write_file_to_s3(bucket: str, key: str, file_path: str) -> None:
    """Write the file to S3."""
    with open(file_path, "rb") as file:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=file,
        )


def new_key_for_processed_file(key: str, prefix: str, ext: str) -> str:
    """Get the key for the processed file."""
    key_parts = key.split("/")
    # extract the key without the extension
    filename = key_parts[-1].split(".")[0]
    return os.path.join(prefix, filename + "." + ext)


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
