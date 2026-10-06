import json
from typing import Any

class Helper:
    @staticmethod
    def as_json_string(value: Any) -> str | None:
        """Helper to normalize lists, dicts, or strings into JSON string."""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
        
helper = Helper()