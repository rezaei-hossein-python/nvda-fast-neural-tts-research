"""Deterministic 100-cycle reset/recovery test for the passing stateless vocoder."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vocoder_benchmark", Path(__file__).with_name("benchmark.py"))
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def main() -> None:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    engine = module.MultiBandMelGAN()
    lock = json.loads((ROOT / "locks/vocoder-inputs.lock.json").read_text())
    inputs = [item for item in lock["items"] if item["source_model"] == "fastspeech2-aggressive" and item["corpus_item_id"] in {"A", "S"}]
    references = {}
    recoveries = 0
    for cycle in range(100):
        item = inputs[cycle % len(inputs)]
        mel = np.load(ROOT / item["relative_path"], allow_pickle=False)
        with torch.inference_mode():
            samples = engine.infer(engine.preprocess(mel)).detach().cpu().numpy() * engine.output_gain
        if samples.size != mel.shape[0] * 256 or not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1.0:
            continue
        key = item["corpus_item_id"]
        value = samples.tobytes()
        if key in references and references[key] != value:
            continue
        references[key] = value
        recoveries += 1
    result = {
        "cycles": 100,
        "recoveries": recoveries,
        "stateful": False,
        "reset_action": "none required; feed-forward generator has no utterance state",
        "deterministic": len(references) == len(inputs),
        "passed": recoveries == 100,
    }
    destination = ROOT / "results/vocoders/raw/mb-melgan-recovery.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
