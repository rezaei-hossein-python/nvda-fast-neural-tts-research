"""Freeze the already-selected Phase 2Z/2AA acoustic outputs for vocoder-only tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import argparse
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/vocoders/raw/inputs"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def items():
    fsbench = load("phase2z_corpus", ROOT / "experiments/selective-duration/benchmark.py")
    for category, item_id, text in fsbench.corpus_items():
        if category in {"character", "punctuation", "ui"}:
            yield category, item_id, text


@torch.inference_mode()
def freeze_fastspeech2(records: list[dict]) -> None:
    fsbench = load("phase2z_benchmark", ROOT / "experiments/selective-duration/benchmark.py")
    engine = fsbench.Engine()
    policy = fsbench.duration_policy.POLICIES["aggressive"]
    for category, item_id, text in items():
        phones = engine.frontend.phones(text)
        sequence = engine.frontend.sequence(phones)
        baseline, _ = engine.acoustic(sequence)
        durations = [int(value) for value in baseline[5][0].tolist()]
        modified = fsbench.duration_policy.apply_policy(phones, durations, policy)
        output, _ = engine.acoustic(sequence, d_targets=modified)
        frames = int(output[9][0])
        mel = output[1][0, :frames].detach().cpu().numpy().astype(np.float32)
        save("fastspeech2-aggressive", category, item_id, mel, records, {
            "source_model_hash": engine.model_hash,
            "condition": "Phase 2Z aggressive selective",
            "sample_rate": engine.sample_rate,
            "hop_length": engine.hop_length,
            "mel_fmin": 0,
            "mel_fmax": 8000,
            "log_base": "natural",
        })


@torch.inference_mode()
def freeze_matcha(records: list[dict]) -> None:
    matcha_runtime = load("phase2aa_runtime", ROOT / "experiments/matcha-duration/runtime.py")
    engine = matcha_runtime.Engine(threads=4)
    checkpoint = ROOT / "models/matcha/matcha_ljspeech.ckpt"
    for category, item_id, text in items():
        x, lengths, _phonemes, _elapsed = engine.frontend(text)
        output = engine.model.synthesise(
            x, lengths, n_timesteps=10, temperature=0.667, length_scale=.5
        )
        frames = int(output["mel_lengths"].item())
        mel = output["mel"][0, :, :frames].transpose(0, 1).detach().cpu().numpy().astype(np.float32)
        save("matcha-global-0.5", category, item_id, mel, records, {
            "source_model_hash": digest(checkpoint),
            "condition": "Phase 2AA global 0.5",
            "sample_rate": 22050,
            "hop_length": 256,
            "mel_fmin": 0,
            "mel_fmax": 8000,
            "log_base": "natural",
        })


def save(source: str, category: str, item_id: str, mel: np.ndarray, records: list[dict], common: dict) -> None:
    if mel.ndim != 2 or mel.shape[1] != 80 or not np.isfinite(mel).all():
        raise ValueError(f"invalid mel for {source}/{category}/{item_id}: {mel.shape}")
    path = OUT / source / f"{category}-{item_id}.npy"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, mel, allow_pickle=False)
    records.append({
        "source_model": source,
        "corpus_item_id": item_id,
        "category": category,
        "relative_path": path.relative_to(ROOT).as_posix(),
        "shape": list(mel.shape),
        "dtype": str(mel.dtype),
        "byte_size": path.stat().st_size,
        "sha256": digest(path),
        "represented_duration_ms": mel.shape[0] * common["hop_length"] / common["sample_rate"] * 1000,
        **common,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("fastspeech2", "matcha"), required=True)
    args = parser.parse_args()
    lock_path = ROOT / "locks/vocoder-inputs.lock.json"
    if lock_path.exists():
        previous = json.loads(lock_path.read_text(encoding="utf-8"))
        records = [item for item in previous["items"] if not item["source_model"].startswith(args.source)]
    else:
        records = []
    if args.source == "matcha":
        freeze_matcha(records)
    else:
        freeze_fastspeech2(records)
    records.sort(key=lambda item: (item["source_model"], item["category"], item["corpus_item_id"]))
    lock = {
        "schema_version": 1,
        "purpose": "Frozen acoustic representations for Phase 2AB vocoder-only timing",
        "timing_excludes_acoustic_generation": True,
        "items": records,
    }
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(records), "sources": sorted({x["source_model"] for x in records})}, indent=2))


if __name__ == "__main__":
    main()
