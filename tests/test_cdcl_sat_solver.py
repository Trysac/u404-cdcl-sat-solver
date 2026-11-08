"""Behavior tests for the public API of cdcl_sat_solver."""

from __future__ import annotations

import pytest

import cdcl_sat_solver


def test_normalize_trims_and_lowercases() -> None:
    assert cdcl_sat_solver.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        cdcl_sat_solver.normalize(value)


def test_version_is_semver() -> None:
    parts = cdcl_sat_solver.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
