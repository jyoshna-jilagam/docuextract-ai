import json
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "config" / "extraction_schema.json"
_validator = Draft7Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def validate(obj):
    return [f"{'/'.join(map(str, e.path)) or 'root'}: {e.message}" for e in _validator.iter_errors(obj)]


def parse_and_validate(text):
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json: {exc.msg}"]
    return obj, validate(obj)
