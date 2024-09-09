import boto3  # type: ignore
import os
from botocore.exceptions import ClientError  # type: ignore

s3 = boto3.client("s3")


def get_file_content_from_s3(bucket: str, key: str) -> str:
    """Get the content of a file from S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


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
