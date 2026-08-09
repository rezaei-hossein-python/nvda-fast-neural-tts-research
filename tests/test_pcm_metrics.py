import importlib.util
import sys
from pathlib import Path

import numpy as np


PATH = Path(__file__).parents[1] / "experiments" / "selective-duration" / "pcm_metrics.py"
SPEC = importlib.util.spec_from_file_location("pcm_metrics", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_pcm_metrics_are_aligned_and_content_free():
    sample_rate = 22050
    silence = np.zeros(round(sample_rate * .01), dtype=np.int16)
    tone = (np.sin(np.arange(round(sample_rate * .1)) * .1) * 8000).astype(np.int16)
    metrics = MODULE.pcm_metrics(np.concatenate([silence, tone]), sample_rate)
    assert metrics["sample_count"] == len(silence) + len(tone)
    assert 0 <= metrics["first_useful_energy_ms"] <= 25
    assert not metrics["clipped"]
