import json
from typing import Any


def encode_untrusted_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False)
    return encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
