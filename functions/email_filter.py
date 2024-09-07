import boto3  # type: ignore
import logging
import json
import os
from models import EmailInfo
from responses import error_response, forbidden_response, success_response
from typing import Any, Dict

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

logger = logging.getLogger()


def validate_sender(sender: str) -> bool:
    """Check if the sender is whitelisted."""
    return sender.lower() in [
        email.lower() for email in os.environ["WHITELIST"].split(",")
    ]


def invoke_next_lambda(payload: Dict[str, Any]) -> None:
    function_name = os.environ["NEXT_LAMBDA"]
    logger.info(f"Invoking {function_name} with payload: {payload}")
    # invoke the next lambda synchronously
    # response = lambda_client.invoke(
    #     FunctionName=function_name,
    #     InvocationType="RequestResponse",
    #     Payload=json.dumps(payload),
    # )
    logger.info(f"Response from {function_name}: {hi}")


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
            payload = {"bucket": bucket, "key": key, "sender": sender}
            invoke_next_lambda(payload)
            return success_response(f"Email from {sender} stored.")
        except Exception as e:
            # TODO alert sender of error
            return error_response(f"Error saving email from {sender}: {e}")
    else:
        # Reject the email
        return forbidden_response(f"Email from {sender} rejected.")
