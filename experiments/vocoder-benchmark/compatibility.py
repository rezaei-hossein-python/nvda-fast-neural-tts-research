"""Vocoder feature-domain declarations and validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Compatibility:
    name: str
    expected: str
    fastspeech2: str
    matcha: str
    adapter: str
    risk: str


VOCODERS = {
    "hifigan": Compatibility(
        "HiFi-GAN control", "80-bin natural-log mel, 0-8000 Hz, 22050 Hz, hop 256",
        "direct", "direct", "none", "none",
    ),
    "fargan": Compatibility(
        "FARGAN", "18 Bark cepstra plus pitch period/correlation, 16 kHz, 10 ms frames",
        "incompatible", "incompatible", "requires a trained acoustic adapter",
        "mel-to-codec features cannot recover trained pitch/conditioning semantics",
    ),
    "lpcnet": Compatibility(
        "LPCNet", "18 Bark cepstra plus pitch period/correlation, 16 kHz, 10 ms frames",
        "incompatible", "incompatible", "requires a trained acoustic adapter",
        "standard mels are not LPCNet conditioning features",
    ),
    "mb_melgan": Compatibility(
        "Multi-Band MelGAN", "80-bin log10 mel, 80-7600 Hz, 22050 Hz, hop 256, standardized",
        "bounded deterministic remap", "bounded deterministic remap",
        "mel filter-bank remap plus official mean/scale normalization",
        "frequency remap is approximate and requires blind quality validation",
    ),
}


def validate_mel(mel: np.ndarray) -> None:
    if mel.dtype != np.float32:
        raise TypeError("frozen mel must be float32")
    if mel.ndim != 2 or mel.shape[1] != 80:
        raise ValueError("frozen mel must have shape [frames, 80]")
    if mel.shape[0] < 1 or not np.isfinite(mel).all():
        raise ValueError("frozen mel must be finite and nonempty")
