import logging
import os

from audio_handler import handle_audio
from responses import success_response, error_response
from rss_handler import handle_rss
from s3_utils import (
    get_file_content_from_s3,
)
from text_handler import handle_text

logger = logging.getLogger()


def lambda_handler(event, _):
    bucket = event["bucket"]
    key = event["key"]
    raw_data = get_file_content_from_s3(bucket, key)

    output_bucket = os.environ["OUTPUT_S3_BUCKET"]
    extracted_text, text_key = handle_text(
        input_key=key, raw_data=raw_data, output_bucket=output_bucket
    )
    if not extracted_text:
        return error_response(f"Failed to extract text from {key}")

    audio_key = handle_audio(
        input_key=key, text=extracted_text, output_bucket=output_bucket
    )

    handle_rss(bucket_name=output_bucket)

    return success_response(
        f"Extracted text from {key} stored in {output_bucket}/{text_key} and audio stored in {output_bucket}/{audio_key}"
    )
