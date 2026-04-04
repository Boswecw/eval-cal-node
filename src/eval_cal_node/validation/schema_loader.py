"""Schema loading utilities for Eval Cal Node."""

import json
from pathlib import Path

import jsonschema

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

_cache: dict[str, dict] = {}


def load_schema(name: str) -> dict:
    """Load a JSON schema by name (without .schema.json suffix)."""
    if name in _cache:
        return _cache[name]
    path = _SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path) as f:
        schema = json.load(f)
    _cache[name] = schema
    return schema


def validate_against_schema(data: dict, schema_name: str) -> None:
    """Validate data against a named schema. Raises SchemaValidationError on failure."""
    from eval_cal_node.errors import SchemaValidationError

    schema = load_schema(schema_name)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(f"Schema validation failed for {schema_name}: {e.message}") from e
