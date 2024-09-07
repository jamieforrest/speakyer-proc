import boto3  # type: ignore
import json
import os

s3 = boto3.client("s3")


def lambda_handler(event, _):
    """Ensure that we only save emails from white-listed senders."""

    # Extract the sender's email from the SNS message

    record = event["Records"][0]
    message_json_str = record["Sns"]["Message"]
    message = json.loads(message_json_str)
    mail = message["mail"]
    sender = mail["source"]

    # Check if the sender is whitelisted
    if sender.lower() in [
        email.lower() for email in os.environ["WHITELIST"].split(",")
    ]:
        # Store email in S3
        s3.put_object(
            Bucket=os.environ["S3_BUCKET"],
            Key=f"emails/{mail['messageId']}.json",
            Body=json.dumps(message),
        )
        return {"statusCode": 200, "body": f"Email from {sender} stored."}
    else:
        # Reject the email
        return {"statusCode": 403, "body": f"Email from {sender} rejected."}
