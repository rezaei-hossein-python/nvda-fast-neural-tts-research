from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import wave
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("compatibility", Path(__file__).with_name("compatibility.py"))
compatibility = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compatibility
spec.loader.exec_module(compatibility)

bench_spec = importlib.util.spec_from_file_location("vocoder_benchmark", Path(__file__).with_name("benchmark.py"))
benchmark = importlib.util.module_from_spec(bench_spec)
sys.modules[bench_spec.name] = benchmark
bench_spec.loader.exec_module(benchmark)


def test_compatibility_is_explicit():
    assert compatibility.VOCODERS["hifigan"].fastspeech2 == "direct"
    assert compatibility.VOCODERS["fargan"].fastspeech2 == "incompatible"
    assert compatibility.VOCODERS["lpcnet"].matcha == "incompatible"


def test_mel_validation():
    compatibility.validate_mel(np.zeros((4, 80), dtype=np.float32))
    with pytest.raises(ValueError):
        compatibility.validate_mel(np.zeros((4, 79), dtype=np.float32))
    with pytest.raises(TypeError):
        compatibility.validate_mel(np.zeros((4, 80), dtype=np.float64))


def test_lock_integrity_when_frozen():
    path = ROOT / "locks/vocoder-inputs.lock.json"
    if not path.exists():
        pytest.skip("frozen inputs not generated yet")
    lock = json.loads(path.read_text(encoding="utf-8"))
    assert lock["timing_excludes_acoustic_generation"] is True
    assert {item["source_model"] for item in lock["items"]} == {
        "fastspeech2-aggressive", "matcha-global-0.5"
    }
    assert len(lock["items"]) == 156
    for item in lock["items"]:
        path = ROOT / item["relative_path"]
        assert path.stat().st_size == item["byte_size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_remapper_is_deterministic_and_valid():
    source = np.linspace(-8, 1, 400, dtype=np.float32).reshape(5, 80)
    adapter = benchmark.MelRemapper()
    first = adapter(source)
    second = adapter(source)
    assert first.shape == source.shape
    assert first.dtype == np.float32
    assert np.isfinite(first).all()
    np.testing.assert_array_equal(first, second)


def test_wav_metrics_detect_invalid_output():
    valid = benchmark.wav_metrics(np.zeros(256, dtype=np.float32), 256)
    assert valid["finite"] and valid["duration_preserved"] and not valid["clipping"]
    clipped = benchmark.wav_metrics(np.array([1.0], dtype=np.float32), 1)
    assert clipped["clipping"]


def test_artifact_hash_locks():
    lock = json.loads((ROOT / "locks/vocoder-artifacts.lock.json").read_text())
    expected = {item["role"]: item["sha256"] for item in lock["artifacts"]}
    paths = {
        "HiFi-GAN control used by Phase 2Z and Phase 2AA": ROOT / "models/hifigan/generator_LJSpeech.pth.tar",
        "official Opus neural model bundle containing FARGAN weights": ROOT / "models/vocoder/fargan/opus_data-a5177ec6fb7d15058e99e57029746100121f68e4890b1467d4094aa336b6013e.tar.gz",
        "official ParallelWaveGAN LJSpeech Multi-Band MelGAN v2 archive": ROOT / "models/vocoder/mb-melgan/ljspeech_multi_band_melgan.v2.tar.gz",
    }
    for role, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[role]


def test_final_timing_records_are_complete_and_valid():
    for name in ("hifigan-fastspeech2-aggressive-tdefault.json", "mb_melgan-fastspeech2-aggressive-t1.json"):
        result = json.loads((ROOT / "results/vocoders/raw" / name).read_text())
        assert result["core_runs"] == 100
        assert result["summary"]["valid"] is True
        assert result["summary"]["clipped_outputs"] == 0
        for record in result["records"]:
            assert {"adapter_ms", "inference_ms", "pcm_conversion_ms", "total_vocoder_ms"} <= record.keys()
            assert record["total_vocoder_ms"] >= record["inference_ms"]


def test_generated_wavs_are_valid():
    files = list((ROOT / "results/vocoders/raw/mb_melgan").rglob("*.wav"))
    assert len(files) == 126
    for path in files:
        with wave.open(str(path), "rb") as source:
            assert source.getnchannels() == 1
            assert source.getsampwidth() == 2
            assert source.getframerate() == 22050
            assert source.getnframes() > 0


def test_recovery_and_comparison_outputs():
    recovery = json.loads((ROOT / "results/vocoders/raw/mb-melgan-recovery.json").read_text())
    assert recovery == {
        "cycles": 100, "recoveries": 100, "stateful": False,
        "reset_action": "none required; feed-forward generator has no utterance state",
        "deterministic": True, "passed": True,
    }
    comparison = (ROOT / "results/vocoders/summaries/vocoder-comparison.md").read_text()
    assert "| HiFi-GAN / FS2 | MB-MelGAN / FS2 |" in comparison


def test_extended_pair_validation_result():
    result = json.loads((ROOT / "results/vocoders/summaries/extended-pair-validation-result.json").read_text())
    assert result == {
        "pairs": 71,
        "wav_files": 142,
        "valid": True,
        "answer_key_excluded": True,
        "checks": ["same frozen mel hash", "mono 16-bit 22050 Hz", "duration tolerance", "finite nonempty PCM", "no vocoder names in user-facing filenames"],
    }
