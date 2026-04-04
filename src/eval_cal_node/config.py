"""Config loading for Eval Cal Node."""

import json
from pathlib import Path

from eval_cal_node.errors import ConfigError
from eval_cal_node.validation.schema_loader import validate_against_schema

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "cal_node_config.json"


def load_config(config_path: Path | None = None) -> dict:
    """Load and validate the node config."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        config = json.load(f)

    validate_against_schema(config, "cal_node_config")

    for name, param in config.get("parameters", {}).items():
        if param["current_value"] < param["param_min"] or param["current_value"] > param["param_max"]:
            raise ConfigError(
                f"Parameter '{name}': current_value {param['current_value']} "
                f"outside [{param['param_min']}, {param['param_max']}]"
            )

    return config


def get_allowed_parameters(config: dict) -> dict[str, dict]:
    """Return only parameters with allowed=true."""
    return {
        name: param
        for name, param in config["parameters"].items()
        if param.get("allowed", False)
    }
