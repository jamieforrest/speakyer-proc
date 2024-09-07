import json

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class EmailInfo:
    message: Dict[str, Any]

    @property
    def mail(self) -> Dict[str, Any]:
        return self.message["mail"]

    @property
    def message_id(self) -> str:
        return self.mail["messageId"]

    @property
    def sender(self) -> str:
        return self.mail["source"]

    @classmethod
    def from_event(cls, event: Dict[str, Any]) -> "EmailInfo":
        record = event["Records"][0]
        message_json_str = record["Sns"]["Message"]
        message = json.loads(message_json_str)
        return cls(message)
