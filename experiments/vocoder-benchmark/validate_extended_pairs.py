"""Pre-listening validation without revealing the private vocoder assignment."""

from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    lock = json.loads((ROOT / "locks/vocoder-inputs.lock.json").read_text(encoding="utf-8"))
    frozen = {item["relative_path"]: item for item in lock["items"]}
    generated = json.loads((ROOT / "results/vocoders/summaries/extended-pair-validation.json").read_text(encoding="utf-8"))
    pairs = generated["pairs"]
    if len(pairs) != 71:
        raise AssertionError(f"expected 71 pairs, found {len(pairs)}")
    errors = []
    for pair in pairs:
        item = next(item for item in lock["items"] if item["corpus_item_id"] == pair["item_id"] and item["source_model"] == "fastspeech2-aggressive")
        if pair["mel_sha256"] != item["sha256"]:
            errors.append(f"{pair['pair']}: mel hash mismatch")
        expected = item["shape"][0] * 256
        for side in ("a", "b"):
            name = pair["outputs"][side]["path"]
            if any(secret in name.lower() for secret in ("hifi", "melgan", "vocoder")):
                errors.append(f"{pair['pair']}-{side}: answer leakage in filename")
            path = ROOT / "listening/vocoders/extended-blind-test" / name
            try:
                with wave.open(str(path), "rb") as audio:
                    if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 22050):
                        errors.append(f"{name}: invalid format")
                    if abs(audio.getnframes() - expected) > 256:
                        errors.append(f"{name}: unexpected length")
                    samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)
                    if samples.size == 0 or not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 32768:
                        errors.append(f"{name}: invalid PCM")
            except (OSError, EOFError) as exc:
                errors.append(f"{name}: {exc}")
    if errors:
        raise AssertionError("; ".join(errors))
    result = {
        "pairs": len(pairs),
        "wav_files": len(pairs) * 2,
        "valid": True,
        "answer_key_excluded": True,
        "checks": ["same frozen mel hash", "mono 16-bit 22050 Hz", "duration tolerance", "finite nonempty PCM", "no vocoder names in user-facing filenames"],
    }
    output = ROOT / "results/vocoders/summaries/extended-pair-validation-result.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
