"""Content-independent PCM metrics with adaptive sustained-energy detection."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def pcm_metrics(samples: np.ndarray, sample_rate: int) -> dict[str, Any]:
    signal = np.asarray(samples, dtype=np.float64).reshape(-1)
    if sample_rate <= 0 or signal.size == 0 or not np.isfinite(signal).all():
        raise ValueError("valid non-empty finite PCM and positive sample rate required")
    normalized = signal / 32768.0 if np.max(np.abs(signal)) > 1.5 else signal
    window = max(1, round(sample_rate * .005))
    squared = normalized * normalized
    rms_curve = np.sqrt(np.convolve(squared, np.ones(window) / window, mode="same"))
    noise_count = max(window, min(signal.size, round(sample_rate * .02)))
    noise = float(np.median(rms_curve[:noise_count]))
    overall = float(np.sqrt(np.mean(squared)))
    threshold = max(.002, noise * 4.0, overall * .08)
    sustained = max(1, round(sample_rate * .012))
    above = rms_curve >= threshold
    run = np.convolve(above.astype(np.int16), np.ones(sustained, dtype=np.int16), mode="same")
    useful = np.flatnonzero(run >= sustained)
    if useful.size:
        first = max(0, int(useful[0] - sustained // 2))
        last = min(signal.size - 1, int(useful[-1] + sustained // 2))
    else:
        first, last = 0, signal.size - 1
    return {
        "sample_count": int(signal.size),
        "pcm_duration_ms": signal.size * 1000.0 / sample_rate,
        "first_useful_energy_ms": first * 1000.0 / sample_rate,
        "last_useful_energy_ms": last * 1000.0 / sample_rate,
        "useful_duration_ms": (last - first + 1) * 1000.0 / sample_rate,
        "leading_low_energy_ms": first * 1000.0 / sample_rate,
        "trailing_low_energy_ms": (signal.size - last - 1) * 1000.0 / sample_rate,
        "peak": float(np.max(np.abs(normalized))),
        "rms": overall,
        "energy_threshold_rms": threshold,
        "clipped": bool(np.max(np.abs(signal)) >= 32768 if np.max(np.abs(signal)) > 1.5 else np.max(np.abs(signal)) > 1.0),
    }

