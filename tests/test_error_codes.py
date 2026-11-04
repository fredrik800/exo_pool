"""Regression tests for the Zodiac eXO error code diagnostics.

The production files depend on Home Assistant. These tests extract and execute
only the small, dependency-free mapping and sensor property, so they run with
the repository's existing pytest setup without a full HA instance.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "custom_components" / "exo_pool" / "api.py"
SENSOR_PATH = ROOT / "custom_components" / "exo_pool" / "sensor.py"


def _error_codes():
    tree = ast.parse(API_PATH.read_text(encoding="utf-8"))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "ERROR_CODES"
                for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def _error_code_text_value(code):
    tree = ast.parse(SENSOR_PATH.read_text(encoding="utf-8"))
    sensor_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ErrorCodeTextSensor"
    )
    getter = next(
        node for node in sensor_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "native_value"
    )
    getter.decorator_list = []  # Evaluate the property getter as a plain function.
    module = ast.fix_missing_locations(ast.Module(body=[getter], type_ignores=[]))
    namespace = {"ERROR_CODES": _error_codes()}
    exec(compile(module, str(SENSOR_PATH), "exec"), namespace)
    sensor = SimpleNamespace(coordinator=SimpleNamespace(
        data={"equipment": {"swc_0": {"error_code": code}}}
    ))
    return namespace["native_value"](sensor)


@pytest.mark.parametrize(("code", "expected"), [
    (0, "No Error"),
    (1, "No Flow"),
    (3, "Low Conductivity"),
    (9, "ORP Stop"),
    (2, "Unknown Error"),
    (999, "Unknown Error"),
])
def test_error_code_text_sensor(code, expected):
    assert _error_code_text_value(code) == expected


def test_string_code_from_device_is_supported():
    assert _error_code_text_value("1") == "No Flow"
