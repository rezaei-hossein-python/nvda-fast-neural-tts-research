"""Applicable Phase 2AA gates after the CPU latency stop decision."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).parents[1]
UPSTREAM = ROOT / "upstream/Matcha-TTS"
RUNTIME = ROOT / "experiments/matcha-duration/runtime.py"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_runtime():
    spec = importlib.util.spec_from_file_location("matcha_research_runtime", RUNTIME)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    checks = 0
    commit = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    check(commit == "77804265f877b0c42f13cfdece6541dde7838090", "pinned source")
    check(not subprocess.check_output(["git", "-C", str(UPSTREAM), "status", "--short"], text=True), "clean source")
    checks += 2

    lock = json.loads((ROOT / "locks/matcha-artifacts.lock.json").read_text())
    for item in lock["artifacts"]:
        path = ROOT / item["local_path"]
        check(path.stat().st_size == item["byte_size"], f"size {path}")
        check(hash_file(path) == item["sha256"], f"hash {path}")
        checks += 2
    environment = (ROOT / "locks/matcha-environment-lock.txt").read_text()
    for required in ("Python==3.12.10", "torch==2.13.0+cpu", "phonemizer==3.4.0", "eSpeak-NG==1.52.0"):
        check(required in environment, f"environment lock {required}")
        checks += 1

    summary = json.loads((ROOT / "results/matcha/summaries/baseline-global-summary.json").read_text())
    phase2z = json.loads((ROOT / "results/summaries/acoustic-summary.json").read_text())
    check(phase2z["conditions"]["aggressive"]["useful_duration_ms"]["median"] == 143.1746031746032,
          "Phase 2Z comparison data")
    check(summary["warm_100_baseline"]["count"] == 100, "100 warm iterations")
    checks += 2

    runtime = load_runtime()
    engine = runtime.Engine(threads=4)
    baseline_samples, baseline = engine.synthesise(runtime.CHARACTER_NAMES["A"], .95)
    fast_samples, fast = engine.synthesise(runtime.CHARACTER_NAMES["A"], .5)
    check(baseline_samples.size > 0 and fast_samples.size > 0, "baseline inference")
    check(sum(baseline["predicted_durations"]) == baseline["mel_frames"], "duration consistency")
    check(fast["mel_frames"] < baseline["mel_frames"], "official global rate control")
    checks += 3

    metric_path = ROOT / "experiments/selective-duration/pcm_metrics.py"
    spec = importlib.util.spec_from_file_location("phase2z_metric_test", metric_path)
    metric_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = metric_module
    spec.loader.exec_module(metric_module)
    measured = metric_module.pcm_metrics(fast_samples, 22050)
    check(measured["sample_count"] == fast_samples.size and not measured["clipped"], "metric extraction")
    checks += 1

    sidecars = list((ROOT / "results/matcha/raw").glob("**/*.json"))
    check(len(sidecars) == 72, "sidecar count")
    required_fields = {"item_id", "condition", "length_scale", "predicted_durations", "mel_frames",
                       "frontend_ms", "duration_alignment_ms", "acoustic_flow_ms", "vocoder_ms",
                       "complete_pcm_ms", "useful_duration_ms", "peak", "rms", "clipped"}
    for sidecar in sidecars:
        data = json.loads(sidecar.read_text())
        check(required_fields <= data.keys(), f"sidecar metadata {sidecar}")
        check(sum(data["predicted_durations"]) == data["mel_frames"], f"sidecar duration vector {sidecar}")
        with wave.open(str(sidecar.with_suffix(".wav")), "rb") as wav:
            check(wav.getnchannels() == 1 and wav.getsampwidth() == 2 and wav.getframerate() == 22050,
                  f"WAV validity {sidecar}")
        checks += 3

    architecture = (ROOT / "results/matcha/summaries/matcha-architecture.md").read_text()
    comparison = (ROOT / "results/matcha/summaries/matcha-vs-fastspeech2.md").read_text()
    check("public inference API cannot accept arbitrary token durations" in architecture, "duration audit")
    check("Not reached" in comparison and "Reject Matcha and stop" in comparison, "stop-gate documentation")
    checks += 2
    print(f"PASS {checks} applicable checks; selective-policy/articulation tests not reached after CPU gate failure")


if __name__ == "__main__":
    main()

