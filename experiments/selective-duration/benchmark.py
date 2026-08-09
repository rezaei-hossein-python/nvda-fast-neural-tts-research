"""CPU-only pinned FastSpeech2 selective-duration benchmark."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import statistics
import sys
import time
import wave
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "upstream" / "FastSpeech2"
sys.path.insert(0, str(UPSTREAM))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
os.environ.setdefault("NLTK_DATA", str(ROOT / ".nltk_data"))


def local_module(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


duration_policy = local_module("duration_policy")
pcm_module = local_module("pcm_metrics")
token_module = local_module("token_analysis")


CHARACTER_NAMES = {
    **dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [
        "ay", "bee", "cee", "dee", "ee", "ef", "gee", "aitch", "eye", "jay", "kay", "el", "em",
        "en", "oh", "pee", "cue", "ar", "ess", "tee", "you", "vee", "double you", "ex", "why", "zee",
    ])),
    **dict(zip("0123456789", ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = np.asarray(samples, dtype=np.int16)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(values.tobytes())


class Engine:
    def __init__(self):
        torch.set_grad_enabled(False)
        self.process = psutil.Process()
        self.preprocess = yaml.safe_load((UPSTREAM / "config/LJSpeech/preprocess.yaml").read_text())
        self.model_config = yaml.safe_load((UPSTREAM / "config/LJSpeech/model.yaml").read_text())
        self.preprocess["path"]["preprocessed_path"] = str(UPSTREAM / "preprocessed_data/LJSpeech")
        self.preprocess["path"]["lexicon_path"] = str(UPSTREAM / "lexicon/librispeech-lexicon.txt")
        self.sample_rate = self.preprocess["preprocessing"]["audio"]["sampling_rate"]
        self.hop_length = self.preprocess["preprocessing"]["stft"]["hop_length"]
        self.frontend = token_module.Frontend(UPSTREAM)
        from model import FastSpeech2
        import hifigan

        start = time.perf_counter_ns()
        self.model = FastSpeech2(self.preprocess, self.model_config)
        checkpoint_path = ROOT / "models/fastspeech2/900000.pth.tar"
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(checkpoint["model"])
        self.model.eval().requires_grad_(False)
        hconfig = json.loads((UPSTREAM / "hifigan/config.json").read_text())
        self.vocoder = hifigan.Generator(hifigan.AttrDict(hconfig))
        vocoder_path = ROOT / "models/hifigan/generator_LJSpeech.pth.tar"
        vcheckpoint = torch.load(vocoder_path, map_location="cpu", weights_only=False)
        self.vocoder.load_state_dict(vcheckpoint["generator"])
        self.vocoder.eval()
        self.vocoder.remove_weight_norm()
        self.load_time_ms = (time.perf_counter_ns() - start) / 1e6
        self.model_hash = sha256(checkpoint_path)
        self.vocoder_hash = sha256(vocoder_path)

    def acoustic(self, sequence: np.ndarray, d_control: float = 1.0, d_targets=None):
        text = torch.from_numpy(sequence).unsqueeze(0)
        lengths = torch.tensor([len(sequence)], dtype=torch.long)
        target = None if d_targets is None else torch.tensor([d_targets], dtype=torch.long)
        target_mel_length = None if d_targets is None else int(sum(d_targets))
        mel_lengths = None if target_mel_length is None else torch.tensor([target_mel_length], dtype=torch.long)
        start = time.perf_counter_ns()
        output = self.model(
            torch.tensor([0]), text, lengths, len(sequence),
            mel_lens=mel_lengths, max_mel_len=target_mel_length,
            d_targets=target, p_control=1.0, e_control=1.0, d_control=d_control,
        )
        elapsed = (time.perf_counter_ns() - start) / 1e6
        return output, elapsed

    def vocode(self, mel: torch.Tensor, mel_length: int):
        start = time.perf_counter_ns()
        wav = self.vocoder(mel.transpose(1, 2)).squeeze().cpu().numpy()
        wav = (wav * 32768.0).clip(-32768, 32767).astype(np.int16)
        wav = wav[: mel_length * self.hop_length]
        return wav, (time.perf_counter_ns() - start) / 1e6

    def synthesize(self, text: str, condition: str, policy_name: str | None = None, global_control: float = .5):
        stamps = {"t_request": time.perf_counter_ns()}
        phones = self.frontend.phones(text)
        sequence = self.frontend.sequence(phones)
        stamps["t_frontend_done"] = time.perf_counter_ns()
        stamps["t_acoustic_start"] = time.perf_counter_ns()
        baseline, baseline_ms = self.acoustic(sequence)
        baseline_durations = [int(value) for value in baseline[5][0].tolist()]
        if condition == "normal":
            output, acoustic_ms, modified, control = baseline, baseline_ms, baseline_durations, 1.0
        elif condition == "global":
            output, acoustic_ms = self.acoustic(sequence, d_control=global_control)
            modified = [int(value) for value in output[5][0].tolist()]
            control = global_control
        else:
            policy = duration_policy.POLICIES[policy_name]
            modified = duration_policy.apply_policy(phones, baseline_durations, policy)
            output, acoustic_ms = self.acoustic(sequence, d_targets=modified)
            control = 1.0
        stamps["t_acoustic_done"] = time.perf_counter_ns()
        stamps["t_vocoder_start"] = time.perf_counter_ns()
        mel_length = int(output[9][0])
        samples, vocoder_ms = self.vocode(output[1], mel_length)
        stamps["t_vocoder_done"] = stamps["t_pcm_available"] = time.perf_counter_ns()
        metrics = pcm_module.pcm_metrics(samples, self.sample_rate)
        return samples, {
            "condition": condition,
            "selective_policy": policy_name,
            "token_sequence": phones,
            "token_classes": [duration_policy.classify_phone(value) for value in phones],
            "baseline_token_durations": baseline_durations,
            "modified_durations": modified,
            "global_control": control,
            "mel_length": mel_length,
            "frontend_ms": (stamps["t_frontend_done"] - stamps["t_request"]) / 1e6,
            "acoustic_ms": acoustic_ms,
            "vocoder_ms": vocoder_ms,
            "complete_pcm_ms": (stamps["t_pcm_available"] - stamps["t_request"]) / 1e6,
            "timestamps_ns": stamps,
            "sample_rate": self.sample_rate,
            "model_hash": self.model_hash,
            "vocoder_hash": self.vocoder_hash,
            "pitch_control": 1.0,
            "energy_control": 1.0,
            **metrics,
        }


def corpus_items() -> list[tuple[str, str, str]]:
    items = [("character", value, CHARACTER_NAMES[value]) for value in CHARACTER_NAMES]
    for filename, category in [("punctuation.txt", "punctuation"), ("ui_phrases.txt", "ui"), ("navigation.txt", "navigation")]:
        for index, text in enumerate((ROOT / "corpus" / filename).read_text().splitlines(), 1):
            if text.strip():
                items.append((category, f"{category}-{index:02}", text.strip()))
    long_lines = [x for x in (ROOT / "corpus/long_form.txt").read_text().splitlines() if x.strip()]
    items.extend(("long-form", f"long-{i+1}", text) for i, text in enumerate(long_lines))
    return items


def summarize(records: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["condition_label"], []).append(record)
    result = {}
    for name, values in grouped.items():
        common = [item for item in values if item["category"] == "character"]
        source = common or values
        result[name] = {
            "count": len(values),
            "common_character_count": len(common),
            "useful_duration_ms": {
                "min": min(x["useful_duration_ms"] for x in source),
                "median": statistics.median(x["useful_duration_ms"] for x in source),
                "p95": percentile([x["useful_duration_ms"] for x in source], 95),
                "max": max(x["useful_duration_ms"] for x in source),
            },
            "pcm_duration_ms": {
                "median": statistics.median(x["pcm_duration_ms"] for x in source),
                "p95": percentile([x["pcm_duration_ms"] for x in source], 95),
            },
            "leading_low_energy_ms_median": statistics.median(x["leading_low_energy_ms"] for x in source),
            "complete_pcm_ms_median": statistics.median(x["complete_pcm_ms"] for x in source),
            "acoustic_ms_median": statistics.median(x["acoustic_ms"] for x in source),
            "vocoder_ms_median": statistics.median(x["vocoder_ms"] for x in source),
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="run proof corpus subset")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    engine = Engine()
    output_root = ROOT / "results/raw/acoustic"
    records = []
    items = corpus_items()
    if args.quick:
        items = [item for item in items if item[1] in {"A", "E", "S", "1", "7"}]
    conditions = [("normal", None), ("global", None)] + [("selective", name) for name in duration_policy.POLICIES]
    for category, item_id, text in items:
        applicable = conditions if category != "long-form" else conditions[:2]
        for condition, policy in applicable:
            label = policy or condition
            samples, metadata = engine.synthesize(text, condition, policy)
            metadata.update({"corpus_item_id": item_id, "category": category, "condition_label": label})
            path = output_root / label / f"{category}-{item_id}.wav"
            write_wav(path, samples, engine.sample_rate)
            path.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            records.append(metadata)
    summary = {
        "cpu_only": not torch.cuda.is_available(),
        "torch_version": torch.__version__,
        "torch_threads": torch.get_num_threads(),
        "model_load_ms": engine.load_time_ms,
        "working_set_bytes": engine.process.memory_info().rss,
        "conditions": summarize(records),
    }
    destination = ROOT / "results/summaries/acoustic-summary.json"
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
