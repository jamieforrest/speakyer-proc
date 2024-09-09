import logging
import os
import tempfile
from openai import OpenAI

from typing import Literal

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60)

logger = logging.getLogger()


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
