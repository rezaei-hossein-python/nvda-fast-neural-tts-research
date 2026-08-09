import importlib.util
import sys
from pathlib import Path

import pytest


PATH = Path(__file__).parents[1] / "experiments" / "selective-duration" / "duration_policy.py"
SPEC = importlib.util.spec_from_file_location("duration_policy", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_deterministic_and_length_preserved():
    phones = ["S", "EY1", "sp"]
    durations = [4, 12, 8]
    first = MODULE.apply_policy(phones, durations, MODULE.POLICIES["balanced"])
    assert first == MODULE.apply_policy(phones, durations, MODULE.POLICIES["balanced"])
    assert len(first) == len(phones)


def test_consonant_minimum_and_silence_compression():
    result = MODULE.apply_policy(["T", "EY1", "sil"], [1, 10, 10], MODULE.POLICIES["balanced"])
    assert result[0] >= MODULE.POLICIES["balanced"].stop_min
    assert result[2] <= MODULE.POLICIES["balanced"].silence_max


def test_unknown_token_fallback():
    result = MODULE.apply_policy(["???"], [8], MODULE.POLICIES["balanced"])
    assert result == [6]


@pytest.mark.parametrize("values,error", [([1], ValueError), ([1, -1], ValueError), ([1, 1.5], TypeError)])
def test_validation(values, error):
    with pytest.raises(error):
        MODULE.validate_durations(values, 2)
