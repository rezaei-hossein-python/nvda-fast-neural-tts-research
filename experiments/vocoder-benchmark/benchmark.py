"""CPU-only vocoder timing over locked, pre-generated acoustic representations."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
import wave
from pathlib import Path

import librosa
import numpy as np
import psutil
import scipy.signal
import torch
import yaml


ROOT = Path(__file__).resolve().parents[2]
FS = ROOT / "upstream/FastSpeech2"
PWG = ROOT / "upstream/MB-MelGAN"
sys.path[:0] = [str(FS), str(PWG)]
CORE = {"A", "E", "S", "1", "7"}

# ParallelWaveGAN 0.6.x imports the legacy SciPy alias removed in newer SciPy.
if not hasattr(scipy.signal, "kaiser"):
    scipy.signal.kaiser = scipy.signal.windows.kaiser


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class MelRemapper:
    """Approximate source-mel magnitudes in the official MB-MelGAN domain."""

    def __init__(self):
        source = librosa.filters.mel(sr=22050, n_fft=1024, n_mels=80, fmin=0, fmax=8000)
        target = librosa.filters.mel(sr=22050, n_fft=1024, n_mels=80, fmin=80, fmax=7600)
        self.mapping = (target @ np.linalg.pinv(source)).astype(np.float32)

    def __call__(self, mel: np.ndarray) -> np.ndarray:
        magnitude = np.exp(np.clip(mel, -20.0, 10.0))
        remapped = magnitude @ self.mapping.T
        return np.log10(np.maximum(remapped, 1e-10)).astype(np.float32)


class HiFiGAN:
    name = "hifigan"
    output_gain = 1.0

    def __init__(self):
        import hifigan
        config = json.loads((FS / "hifigan/config.json").read_text())
        self.model = hifigan.Generator(hifigan.AttrDict(config))
        path = ROOT / "models/hifigan/generator_LJSpeech.pth.tar"
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(checkpoint["generator"])
        self.model.eval().requires_grad_(False)
        self.model.remove_weight_norm()
        self.artifact_hash = digest(path)

    def preprocess(self, mel: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(mel.T).unsqueeze(0)

    def infer(self, value: torch.Tensor) -> torch.Tensor:
        return self.model(value).reshape(-1)


class MultiBandMelGAN:
    name = "mb_melgan"
    # Fixed headroom for deterministic float-to-PCM conversion. The largest
    # observed locked-corpus peak before conversion was 1.17124.
    output_gain = .85

    def __init__(self):
        from parallel_wavegan import models
        from parallel_wavegan.layers import PQMF
        folder = ROOT / "models/vocoder/mb-melgan/train_nodev_ljspeech_multi_band_melgan.v2"
        config_path = folder / "config.yml"
        checkpoint_path = folder / "checkpoint-1000000steps.pkl"
        self.config = yaml.safe_load(config_path.read_text())
        cls = getattr(models, self.config["generator_type"])
        self.model = cls(**self.config["generator_params"])
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(checkpoint["model"]["generator"])
        self.model.pqmf = PQMF(
            subbands=self.config["generator_params"]["out_channels"],
            **self.config.get("pqmf_params", {}),
        )
        self.model.register_stats(str(folder / "stats.h5"))
        self.model.eval().requires_grad_(False)
        self.model.remove_weight_norm()
        self.remapper = MelRemapper()
        self.artifact_hash = digest(ROOT / "models/vocoder/mb-melgan/ljspeech_multi_band_melgan.v2.tar.gz")

    def preprocess(self, mel: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(self.remapper(mel))

    def infer(self, value: torch.Tensor) -> torch.Tensor:
        return self.model.inference(value, normalize_before=True).reshape(-1)


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values), q))


def wav_metrics(samples: np.ndarray, expected: int) -> dict:
    finite = bool(np.isfinite(samples).all())
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    return {
        "samples": int(samples.size),
        "expected_samples": expected,
        "duration_preserved": abs(samples.size - expected) <= 256,
        "finite": finite,
        "clipping": bool(peak >= 1.0),
        "peak": peak,
        "rms": float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if samples.size else 0.0,
        "dc_offset": float(np.mean(samples)) if samples.size else 0.0,
    }


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (samples * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())


def load_inputs(source: str) -> list[dict]:
    lock = json.loads((ROOT / "locks/vocoder-inputs.lock.json").read_text())
    return [item for item in lock["items"] if item["source_model"] == source]


@torch.inference_mode()
def run(candidate: str, source: str, threads: int, repeats: int) -> dict:
    if threads > 0:
        torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    process = psutil.Process()
    working_set_before = process.memory_info().rss
    load_start = time.perf_counter_ns()
    engine = HiFiGAN() if candidate == "hifigan" else MultiBandMelGAN()
    load_ms = (time.perf_counter_ns() - load_start) / 1e6
    items = load_inputs(source)
    warm = np.load(ROOT / items[0]["relative_path"], allow_pickle=False)
    for _ in range(5):
        engine.infer(engine.preprocess(warm))
    records = []
    benchmark_wall_start = time.perf_counter()
    cpu_start = sum(process.cpu_times()[:2])
    for item in items:
        mel = np.load(ROOT / item["relative_path"], allow_pickle=False)
        count = repeats if item["corpus_item_id"] in CORE else 1
        for trial in range(count):
            request = time.perf_counter_ns()
            pre_start = time.perf_counter_ns()
            value = engine.preprocess(mel)
            pre_done = time.perf_counter_ns()
            infer_start = time.perf_counter_ns()
            output = engine.infer(value)
            infer_done = time.perf_counter_ns()
            samples = output.detach().cpu().numpy().astype(np.float32, copy=False) * engine.output_gain
            pcm_done = time.perf_counter_ns()
            metrics = wav_metrics(samples, mel.shape[0] * 256)
            records.append({
                "source_model": source, "candidate": candidate,
                "corpus_item_id": item["corpus_item_id"], "category": item["category"], "trial": trial,
                "adapter_ms": (pre_done - pre_start) / 1e6,
                "inference_ms": (infer_done - infer_start) / 1e6,
                "pcm_conversion_ms": (pcm_done - infer_done) / 1e6,
                "total_vocoder_ms": (pcm_done - request) / 1e6,
                **metrics,
            })
        if item["category"] in {"character", "punctuation", "ui"}:
            write_wav(ROOT / f"results/vocoders/raw/{candidate}/{source}/{item['category']}-{item['corpus_item_id']}.wav", samples)
    cpu_seconds = sum(process.cpu_times()[:2]) - cpu_start
    wall_seconds = time.perf_counter() - benchmark_wall_start
    core = [r for r in records if r["corpus_item_id"] in CORE]
    totals = [r["total_vocoder_ms"] for r in core]
    result = {
        "candidate": candidate, "source_model": source,
        "threads": torch.get_num_threads(), "thread_setting": "default" if threads == 0 else threads,
        "artifact_hash": engine.artifact_hash, "load_ms": load_ms,
        "output_gain": engine.output_gain,
        "working_set_before_bytes": working_set_before,
        "working_set_bytes": process.memory_info().rss,
        "incremental_working_set_bytes": process.memory_info().rss - working_set_before,
        "peak_working_set_bytes": getattr(process.memory_info(), "peak_wset", process.memory_info().rss),
        "benchmark_cpu_seconds": cpu_seconds,
        "benchmark_wall_seconds": wall_seconds,
        "process_cpu_percent_of_one_core": 100 * cpu_seconds / wall_seconds,
        "core_runs": len(core), "records": records,
        "summary": {
            "minimum_ms": min(totals), "median_ms": statistics.median(totals),
            "p95_ms": percentile(totals, 95), "maximum_ms": max(totals),
            "adapter_median_ms": statistics.median(r["adapter_ms"] for r in core),
            "inference_median_ms": statistics.median(r["inference_ms"] for r in core),
            "pcm_conversion_median_ms": statistics.median(r["pcm_conversion_ms"] for r in core),
            "valid": all(r["finite"] and r["duration_preserved"] for r in records),
            "clipped_outputs": sum(r["clipping"] for r in records),
        },
    }
    thread_label = "default" if threads == 0 else str(threads)
    destination = ROOT / f"results/vocoders/raw/{candidate}-{source}-t{thread_label}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("hifigan", "mb_melgan"), required=True)
    parser.add_argument("--source", choices=("fastspeech2-aggressive", "matcha-global-0.5"), required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    result = run(args.candidate, args.source, args.threads, args.repeats)
    print(json.dumps({k: result[k] for k in ("candidate", "source_model", "threads", "load_ms", "working_set_bytes")} | {"summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
