"""Pinned Matcha-TTS CPU inference support without modifying upstream."""

from __future__ import annotations

import os
import sys
import time
import types
from pathlib import Path

import numpy as np
import psutil
import torch


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "upstream" / "Matcha-TTS"
ESPEAK = ROOT / "models" / "matcha" / "espeak-ng-1.52.0" / "eSpeak NG"
os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", str(ESPEAK / "libespeak-ng.dll"))
os.environ.setdefault("PHONEMIZER_ESPEAK_DATA_PATH", str(ESPEAK / "espeak-ng-data"))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
sys.path.insert(0, str(UPSTREAM))


def install_inference_only_mas_shim() -> None:
    """Avoid building training-only MAS; inference never calls maximum_path."""
    import matcha
    import matcha.utils

    module = types.ModuleType("matcha.utils.monotonic_align")

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("training-only monotonic alignment is unavailable in the inference harness")

    module.maximum_path = unavailable
    sys.modules[module.__name__] = module
    setattr(matcha.utils, "monotonic_align", module)


install_inference_only_mas_shim()

from matcha.cli import load_vocoder, to_waveform  # noqa: E402
from matcha.models.matcha_tts import MatchaTTS  # noqa: E402
from matcha.text import text_to_sequence  # noqa: E402
from matcha.utils.utils import intersperse  # noqa: E402


CHARACTER_NAMES = {
    **dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [
        "ay", "bee", "cee", "dee", "ee", "ef", "gee", "aitch", "eye", "jay", "kay", "el", "em",
        "en", "oh", "pee", "cue", "ar", "ess", "tee", "you", "vee", "double you", "ex", "why", "zee",
    ])),
    **dict(zip("0123456789", ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])),
}


class Engine:
    def __init__(self, threads: int = 4):
        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        self.process = psutil.Process()
        self.threads = threads
        start = time.perf_counter_ns()
        self.model = MatchaTTS.load_from_checkpoint(
            ROOT / "models/matcha/matcha_ljspeech.ckpt",
            map_location="cpu",
            weights_only=False,
        ).eval()
        self.model_load_ms = (time.perf_counter_ns() - start) / 1e6
        start = time.perf_counter_ns()
        self.vocoder, self.denoiser = load_vocoder(
            "hifigan_T2_v1", ROOT / "models/vocoder/generator_v1", "cpu"
        )
        self.vocoder_load_ms = (time.perf_counter_ns() - start) / 1e6
        self.stage = {}
        self.model.encoder.register_forward_pre_hook(lambda *_: self.stage.__setitem__("duration_start", time.perf_counter_ns()))
        self.model.encoder.register_forward_hook(lambda *_: self.stage.__setitem__("duration_done", time.perf_counter_ns()))
        self.model.decoder.register_forward_pre_hook(lambda *_: self.stage.__setitem__("acoustic_start", time.perf_counter_ns()))
        self.model.decoder.register_forward_hook(lambda *_: self.stage.__setitem__("acoustic_done", time.perf_counter_ns()))

    def frontend(self, text: str):
        start = time.perf_counter_ns()
        sequence, phonemes = text_to_sequence(text, ["english_cleaners2"])
        values = intersperse(sequence, 0)
        x = torch.tensor(values, dtype=torch.long).unsqueeze(0)
        lengths = torch.tensor([len(values)], dtype=torch.long)
        return x, lengths, phonemes, (time.perf_counter_ns() - start) / 1e6

    @torch.inference_mode()
    def synthesise(self, text: str, length_scale: float):
        request = time.perf_counter_ns()
        x, lengths, phonemes, frontend_ms = self.frontend(text)
        frontend_done = time.perf_counter_ns()
        self.stage = {}
        synth_start = time.perf_counter_ns()
        output = self.model.synthesise(
            x, lengths, n_timesteps=10, temperature=0.667, length_scale=length_scale
        )
        synth_done = time.perf_counter_ns()
        vocoder_start = time.perf_counter_ns()
        waveform = to_waveform(output["mel"], self.vocoder, self.denoiser)
        pcm_available = time.perf_counter_ns()
        samples = (waveform.numpy() * 32767.0).clip(-32768, 32767).astype(np.int16)
        duration_ms = (self.stage["duration_done"] - self.stage["duration_start"]) / 1e6
        acoustic_ms = (self.stage["acoustic_done"] - self.stage["acoustic_start"]) / 1e6
        other_model_ms = (synth_done - synth_start) / 1e6 - duration_ms - acoustic_ms
        return samples, {
            "phonemes": phonemes,
            "token_count": int(lengths.item()),
            "predicted_durations": [int(value) for value in output["attn"].sum(-1).squeeze().tolist()],
            "mel_frames": int(output["mel_lengths"].item()),
            "frontend_ms": frontend_ms,
            "duration_alignment_ms": duration_ms,
            "acoustic_flow_ms": acoustic_ms,
            "other_model_ms": other_model_ms,
            "model_total_ms": (synth_done - synth_start) / 1e6,
            "vocoder_ms": (pcm_available - vocoder_start) / 1e6,
            "complete_pcm_ms": (pcm_available - request) / 1e6,
            "timestamps_ns": {
                "t_request": request,
                "t_frontend_done": frontend_done,
                "t_duration_done": self.stage["duration_done"],
                "t_acoustic_start": self.stage["acoustic_start"],
                "t_acoustic_done": self.stage["acoustic_done"],
                "t_vocoder_start": vocoder_start,
                "t_vocoder_done": pcm_available,
                "t_pcm_available": pcm_available,
            },
        }

