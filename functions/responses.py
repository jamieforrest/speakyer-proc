from typing import Any, Dict


def success_response(message: str) -> Dict[str, Any]:
    return {"statusCode": 200, "body": message}


def forbidden_response(message: str) -> Dict[str, Any]:
    return {"statusCode": 403, "body": message}


def error_response(message: str) -> Dict[str, Any]:
    return {"statusCode": 500, "body": message}
