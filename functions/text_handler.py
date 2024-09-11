import logging

from ai_tools import extract_text_from_raw_data
from s3_utils import (
    file_exists,
    get_file_content_from_s3,
    new_key_for_processed_file,
    write_text_to_s3,
)
from typing import Tuple

logger = logging.getLogger()


def handle_text(
    input_key: str, raw_data: str, output_bucket: str
) -> Tuple[str | None, str]:
    """Handle the text extraction and storage.

    Extract text from the raw data and store it in S3
    If the text file already exists, retrieve the text from S3
    Parameters:
        input_key (str): The key of the raw data input file
        raw_data (str): The raw data to extract text from
        output_bucket (str): The S3 bucket to store the extracted text
    Returns:
        Tuple[str | None, str]: The extracted text and the key of the text file
    """
    text_key = new_key_for_processed_file(input_key, "texts", "txt")

    text_file_exists = file_exists(output_bucket, text_key)
    if not text_file_exists:
        extracted_text = extract_text_from_raw_data(raw_data)
    else:
        logger.info(
            f"Text file already exists: {output_bucket}/{text_key}, getting text from S3"
        )
        extracted_text = get_file_content_from_s3(output_bucket, text_key)

    if not text_file_exists and extracted_text:
        write_text_to_s3(output_bucket, text_key, extracted_text)

    return extracted_text, text_key
