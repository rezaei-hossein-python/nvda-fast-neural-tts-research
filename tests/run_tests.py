"""Dependency-light automatic verification for the isolated research tree."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import torch
import yaml


ROOT = Path(__file__).parents[1]
UPSTREAM = ROOT / "upstream/FastSpeech2"
sys.path.insert(0, str(UPSTREAM))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))


def load_local(name: str):
    path = ROOT / "experiments/selective-duration" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy = load_local("duration_policy")
metrics = load_local("pcm_metrics")


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    count = 0
    commit = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    check(commit == "d4e79eb52e8b01d24703b2dfc0385544092958f3", "source pin")
    count += 1

    lock = json.loads((ROOT / "locks/artifacts.lock.json").read_text())
    for item in lock["artifacts"]:
        path = ROOT / item["local_path"]
        check(path.stat().st_size == item["byte_size"], f"size: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        check(digest.hexdigest() == item["sha256"], f"hash: {path}")
    count += len(lock["artifacts"])

    phones = ["T", "EY1", "S", "sil"]
    source = [1, 12, 1, 10]
    for candidate in policy.POLICIES.values():
        first = policy.apply_policy(phones, source, candidate)
        check(first == policy.apply_policy(phones, source, candidate), "determinism")
        policy.validate_durations(first, len(phones))
        check(first[0] >= candidate.stop_min, "stop minimum")
        check(first[2] >= candidate.fricative_min, "fricative minimum")
        check(first[3] <= candidate.silence_max, "silence maximum")
        count += 1
    for bad, exc in [([1], ValueError), ([1, -1], ValueError), ([1, 1.5], TypeError)]:
        try:
            policy.validate_durations(bad, 2)
        except exc:
            count += 1
        else:
            raise AssertionError("duration validation")

    sample_rate = 22050
    samples = np.concatenate([np.zeros(220, np.int16), np.full(2205, 5000, np.int16)])
    measured = metrics.pcm_metrics(samples, sample_rate)
    check(measured["sample_count"] == samples.size and not measured["clipped"], "PCM metrics")
    count += 1

    pre = yaml.safe_load((UPSTREAM / "config/LJSpeech/preprocess.yaml").read_text())
    model_config = yaml.safe_load((UPSTREAM / "config/LJSpeech/model.yaml").read_text())
    pre["path"]["preprocessed_path"] = str(UPSTREAM / "preprocessed_data/LJSpeech")
    from model import FastSpeech2

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    model = FastSpeech2(pre, model_config).eval()
    targets = torch.tensor([[2, 3, 4]], dtype=torch.long)
    with torch.no_grad():
        output = model(
            torch.tensor([0]), torch.tensor([[10, 11, 12]]), torch.tensor([3]), 3,
            mel_lens=torch.tensor([9]), max_mel_len=9, d_targets=targets,
            p_control=1.0, e_control=1.0,
        )
    check(output[5].tolist() == targets.tolist(), "explicit target propagation")
    check(output[9].tolist() == [9] and output[0].shape[1] == 9, "explicit mel length")
    count += 2

    required = {
        "corpus_item_id", "condition", "token_sequence", "token_classes",
        "baseline_token_durations", "modified_durations", "mel_length",
        "acoustic_ms", "vocoder_ms", "complete_pcm_ms", "pcm_duration_ms",
        "first_useful_energy_ms", "trailing_low_energy_ms", "peak", "rms",
        "model_hash", "vocoder_hash", "pitch_control", "energy_control",
    }
    sidecars = list((ROOT / "results/raw/acoustic").glob("**/*.json"))
    check(bool(sidecars), "sidecars exist")
    for sidecar in sidecars:
        data = json.loads(sidecar.read_text())
        check(required <= data.keys(), f"metadata: {sidecar}")
        check(data["pitch_control"] == data["energy_control"] == 1.0, "unchanged controls")
        check(len(data["token_sequence"]) == len(data["modified_durations"]), "vector length")
        wav = sidecar.with_suffix(".wav")
        with wave.open(str(wav), "rb") as stream:
            check(stream.getnchannels() == 1 and stream.getsampwidth() == 2, "WAV format")
            check(stream.getnframes() * 2 == wav.stat().st_size - 44, "WAV alignment")
    count += len(sidecars)
    print(f"PASS {count} checks; {len(sidecars)} WAV/sidecar pairs verified")


if __name__ == "__main__":
    main()

