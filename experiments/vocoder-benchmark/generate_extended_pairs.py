"""Generate paired, opaque HiFi-GAN/MB-MelGAN listening files."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "listening/vocoders/extended-blind-test"
RAW = ROOT / "results/vocoders/raw/extended-pairs"
SEED = 20260809


def load_benchmark():
    path = ROOT / "experiments/vocoder-benchmark/benchmark.py"
    spec = importlib.util.spec_from_file_location("phase2ab_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(lock: dict) -> list[dict]:
    required_chars = {"A", "B", "D", "E", "F", "G", "J", "K", "P", "S", "T", "V", "X", "Z", "1", "3", "6", "7", "9"}
    punctuation = {f"punctuation-{i:02}" for i in range(2, 14)}
    ui = {f"ui-{i:02}" for i in range(1, 13)}
    navigation = {f"navigation-{i:02}" for i in range(1, 11)}
    medium = {f"medium-{i:02}" for i in range(1, 11)}
    long = {f"long-{i:02}" for i in range(1, 6)}
    sustained = {"sustained-100", "sustained-250", "sustained-500"}
    wanted = required_chars | punctuation | ui | navigation | medium | long | sustained
    records = [item for item in lock["items"] if item["source_model"] == "fastspeech2-aggressive" and item["corpus_item_id"] in wanted]
    if len(records) != 71:
        raise RuntimeError(f"expected 71 extended items, found {len(records)}")
    return sorted(records, key=lambda item: (item["category"], item["corpus_item_id"]))


def write_wav(path: Path, samples: np.ndarray) -> None:
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    values = (samples * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
        output.writeframes(values.tobytes())


def main() -> None:
    benchmark = load_benchmark()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    lock = json.loads((ROOT / "locks/vocoder-inputs.lock.json").read_text(encoding="utf-8"))
    items = selected(lock)
    for path in (DEST, RAW):
        path.mkdir(parents=True, exist_ok=True)
    engines = {"hifigan": benchmark.HiFiGAN(), "mb_melgan": benchmark.MultiBandMelGAN()}
    rng = random.Random(SEED)
    answer_key = []
    validation = []
    measurements = []
    for index, item in enumerate(items, 1):
        mel_path = ROOT / item["relative_path"]
        mel = np.load(mel_path, allow_pickle=False)
        assignment = ["hifigan", "mb_melgan"]
        rng.shuffle(assignment)
        pair_id = f"set-{index:03}"
        answer_key.append({"pair": pair_id, "item_id": item["corpus_item_id"], "category": item["category"], "a": assignment[0], "b": assignment[1]})
        pair_validation = {"pair": pair_id, "category": item["category"], "item_id": item["corpus_item_id"], "mel_sha256": sha256(mel_path), "outputs": {}}
        for side, candidate in zip(("a", "b"), assignment):
            engine = engines[candidate]
            request = time.perf_counter_ns()
            value = engine.preprocess(mel)
            output = engine.infer(value).detach().cpu().numpy().astype(np.float32, copy=False) * engine.output_gain
            elapsed_ms = (time.perf_counter_ns() - request) / 1e6
            wav_path = DEST / f"{pair_id}-{side}.wav"
            write_wav(wav_path, output)
            raw_path = RAW / f"{pair_id}-{candidate}.wav"
            write_wav(raw_path, output)
            duration_ms = output.size / 22050 * 1000
            measurements.append({"pair": pair_id, "category": item["category"], "item_id": item["corpus_item_id"], "candidate": candidate, "wall_ms": elapsed_ms, "audio_duration_ms": duration_ms, "rtf": (elapsed_ms / 1000) / (duration_ms / 1000), "peak": float(np.max(np.abs(output))), "samples": int(output.size)})
            pair_validation["outputs"][side] = {"sample_rate": 22050, "samples": int(output.size), "finite": bool(np.isfinite(output).all()), "clipping": bool(np.max(np.abs(output)) >= 1.0), "path": wav_path.name}
        validation.append(pair_validation)
    (ROOT / "results/vocoders/summaries/extended-blind-answer-key.json").write_text(json.dumps({"seed": SEED, "pairs": answer_key}, indent=2) + "\n", encoding="utf-8")
    (ROOT / "results/vocoders/summaries/extended-pair-validation.json").write_text(json.dumps({"pairs": validation, "measurements": measurements}, indent=2) + "\n", encoding="utf-8")
    categories = [f"{i['pair']} — {i['category']}" for i in [{"pair": f"set-{n:03}", "category": item["category"]} for n, item in enumerate(items, 1)]]
    (DEST / "category-index.txt").write_text("\n".join(categories) + "\n", encoding="utf-8")
    (DEST / "scoring.txt").write_text(
        "Extended blind vocoder comparison\n\n"
        "For each pair, listen to A and B, replay if needed, then record:\n"
        "Preferred: A / B / Same\n"
        "Intelligibility: A better / B better / Same\n"
        "Naturalness: A better / B better / Same\n"
        "Voice identity: A better / B better / Same\n"
        "Artifacts: A / B / Both / Neither\n"
        "Notes: ________________________________\n\n"
        "Pay attention to buzzing, metallic or robotic sound, muffling, weak fricatives, smeared stops, clicks, crackle, unstable vowels or pitch, breath/noise artifacts, word boundaries, and degradation during long speech.\n",
        encoding="utf-8",
    )
    print(json.dumps({"pairs": len(items), "directory": str(DEST), "answer_key": "results/vocoders/summaries/extended-blind-answer-key.json"}, indent=2))


if __name__ == "__main__":
    main()
