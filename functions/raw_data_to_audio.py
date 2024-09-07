import json


def lambda_handler(event, _):
    print("event: ", event)
    return {
        "statusCode": 200,
        "body": json.dumps("Hello from Lambda!"),
    }
