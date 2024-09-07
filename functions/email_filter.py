import boto3  # type: ignore
import json
import os
from models import EmailInfo
from responses import error_response, forbidden_response, success_response

s3 = boto3.client("s3")


def validate_sender(sender: str) -> bool:
    """Check if the sender is whitelisted."""
    return sender.lower() in [
        email.lower() for email in os.environ["WHITELIST"].split(",")
    ]


def lambda_handler(event, _):
    """Ensure that we only save emails from white-listed senders."""

    # Extract the sender's email from the SNS message

    email_info = EmailInfo.from_event(event)
    sender = email_info.sender

    # Check if the sender is whitelisted
    if validate_sender(sender):
        # Store email in S3
        try:
            bucket = os.environ["S3_BUCKET"]
            key = f"emails/{email_info.message_id}.json"
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(email_info.message),
            )
            return success_response(f"Email from {sender} stored.")
        except Exception as e:
            # TODO alert sender of error
            return error_response(f"Error saving email from {sender}: {e}")
    else:
        # Reject the email
        return forbidden_response(f"Email from {sender} rejected.")
