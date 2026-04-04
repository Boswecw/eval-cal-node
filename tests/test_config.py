"""Tests for node config loading and validation (Slice B)."""

import json
import pytest
from pathlib import Path

from eval_cal_node.config import load_config, get_allowed_parameters
from eval_cal_node.errors import ConfigError, SchemaValidationError


def _write_config(tmp_path, config_data):
    path = tmp_path / "config.json"
    with open(path, "w") as f:
        json.dump(config_data, f)
    return path


def _base_config(**overrides):
    cfg = {
        "node_revision": "cal_node_rev1",
        "min_sample_size": 5,
        "min_recurrence": 3,
        "effect_floor": 0.15,
        "sensitivity_factor": 0.5,
        "hold_after_decline_cycles": 3,
        "min_new_recurrence": 2,
        "rounding_digits": 6,
        "parameters": {
            "hazard_hidden_uplift_strength": {
                "current_value": 0.20,
                "param_min": 0.05,
                "param_max": 0.50,
                "max_movement": 0.05,
                "allowed": True,
            }
        },
    }
    cfg.update(overrides)
    return cfg


class TestConfigLoading:
    """Slice B required tests."""

    def test_valid_config_loads_correctly(self, tmp_path):
        """Test 1: Valid config loads correctly."""
        path = _write_config(tmp_path, _base_config())
        config = load_config(path)
        assert config["node_revision"] == "cal_node_rev1"
        assert "hazard_hidden_uplift_strength" in config["parameters"]

    def test_unknown_parameter_in_block_accepted_by_schema(self, tmp_path):
        """Test 2: Unknown parameter names are accepted by schema (additionalProperties on params)."""
        cfg = _base_config()
        cfg["parameters"]["totally_unknown_param"] = {
            "current_value": 0.5,
            "param_min": 0.1,
            "param_max": 0.9,
            "max_movement": 0.1,
            "allowed": False,
        }
        path = _write_config(tmp_path, cfg)
        config = load_config(path)
        allowed = get_allowed_parameters(config)
        assert "totally_unknown_param" not in allowed

    def test_allowed_false_excluded(self, tmp_path):
        """Test 3: allowed=false parameter is excluded from calibration targets."""
        cfg = _base_config()
        cfg["parameters"]["hazard_hidden_uplift_strength"]["allowed"] = False
        path = _write_config(tmp_path, cfg)
        config = load_config(path)
        allowed = get_allowed_parameters(config)
        assert "hazard_hidden_uplift_strength" not in allowed

    def test_out_of_range_current_value_fails(self, tmp_path):
        """Test 4: Out-of-range current_value fails closed."""
        cfg = _base_config()
        cfg["parameters"]["hazard_hidden_uplift_strength"]["current_value"] = 0.99
        path = _write_config(tmp_path, cfg)
        with pytest.raises(ConfigError, match="outside"):
            load_config(path)

    def test_production_config_loads(self):
        """Test the actual production config file loads and validates."""
        config = load_config()
        assert config["node_revision"] == "cal_node_rev1"
        allowed = get_allowed_parameters(config)
        assert len(allowed) == 13

    def test_missing_required_field_fails(self, tmp_path):
        """Missing required field fails schema validation."""
        cfg = _base_config()
        del cfg["min_sample_size"]
        path = _write_config(tmp_path, cfg)
        with pytest.raises(SchemaValidationError):
            load_config(path)
