"""Baseline and official global-rate gates for pinned Matcha-TTS."""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
import wave
from pathlib import Path

import numpy as np
import psutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from runtime import CHARACTER_NAMES, Engine  # noqa: E402


def load_phase2z_metrics():
    path = ROOT / "experiments/selective-duration/pcm_metrics.py"
    spec = importlib.util.spec_from_file_location("phase2z_pcm_metrics", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.pcm_metrics


pcm_metrics = load_phase2z_metrics()


def percentile(values, q):
    return float(np.percentile(np.asarray(values, dtype=float), q))


def aggregate(records):
    fields = [
        "useful_duration_ms", "pcm_duration_ms", "leading_low_energy_ms", "trailing_low_energy_ms",
        "frontend_ms", "duration_alignment_ms", "acoustic_flow_ms", "other_model_ms",
        "model_total_ms", "vocoder_ms", "complete_pcm_ms",
    ]
    result = {"count": len(records)}
    for field in fields:
        values = [float(item[field]) for item in records]
        result[field] = {
            "min": min(values), "median": statistics.median(values),
            "p95": percentile(values, 95), "max": max(values),
        }
    return result


def write_wav(path, samples, rate=22050):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
        stream.writeframes(samples.tobytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    process = psutil.Process()
    cpu_start = process.cpu_times()
    wall_start = time.perf_counter()
    engine = Engine(args.threads)
    conditions = {"baseline": .95, "global-0.5": .5}

    # Excluded warm-up set.
    for name in ("A", "E", "S", "1", "7"):
        engine.synthesise(CHARACTER_NAMES[name], .95)

    records = {name: [] for name in conditions}
    output_root = ROOT / "results/matcha/raw"
    for condition, scale in conditions.items():
        for item_id, text in CHARACTER_NAMES.items():
            samples, timing = engine.synthesise(text, scale)
            record = {"item_id": item_id, "condition": condition, "length_scale": scale, **timing,
                      **pcm_metrics(samples, 22050)}
            records[condition].append(record)
            path = output_root / condition / f"character-{item_id}.wav"
            write_wav(path, samples)
            path.with_suffix(".json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    # Required 100 warm baseline trials: 20 each over the fixed repetition set.
    warm_trials = []
    for _ in range(20):
        for item_id in ("A", "E", "S", "1", "7"):
            samples, timing = engine.synthesise(CHARACTER_NAMES[item_id], .95)
            warm_trials.append({"item_id": item_id, **timing, **pcm_metrics(samples, 22050)})

    wall_seconds = time.perf_counter() - wall_start
    cpu_end = process.cpu_times()
    cpu_seconds = (cpu_end.user + cpu_end.system) - (cpu_start.user + cpu_start.system)
    info = process.memory_info()
    summary = {
        "cpu_only": True,
        "threads": args.threads,
        "model_load_ms": engine.model_load_ms,
        "vocoder_load_ms": engine.vocoder_load_ms,
        "steady_working_set_bytes": info.rss,
        "peak_working_set_bytes": getattr(info, "peak_wset", None),
        "average_process_cpu_percent_of_machine": cpu_seconds / wall_seconds * 100 / psutil.cpu_count(),
        "conditions": {name: aggregate(values) for name, values in records.items()},
        "warm_100_baseline": aggregate(warm_trials),
    }
    destination = ROOT / "results/matcha/summaries/baseline-global-summary.json"
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

