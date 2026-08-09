"""Create an opaque randomized HiFi-GAN/MB-MelGAN listening set."""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "listening/vocoders/blind-test"
SEED = 20260809
ITEMS = ["character-A", "character-E", "character-S", "character-F", "character-T", "character-K", "character-1", "character-7",
         "punctuation-punctuation-01", "punctuation-punctuation-06", "ui-ui-01", "ui-ui-03", "ui-ui-12"]


def main() -> None:
    entries = []
    for item in ITEMS:
        for candidate in ("hifigan", "mb_melgan"):
            source = ROOT / f"results/vocoders/raw/{candidate}/fastspeech2-aggressive/{item}.wav"
            if not source.exists():
                raise FileNotFoundError(source)
            entries.append((item, candidate, source))
    random.Random(SEED).shuffle(entries)
    DEST.mkdir(parents=True, exist_ok=True)
    key = []
    for index, (item, candidate, source) in enumerate(entries, 1):
        name = f"trial-{index:03}.wav"
        shutil.copyfile(source, DEST / name)
        key.append({"trial": name, "item_id": item, "vocoder": candidate})
    key_path = ROOT / "results/vocoders/summaries/blind-answer-key.json"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps({"seed": SEED, "trials": key}, indent=2) + "\n", encoding="utf-8")
    (DEST / "README.txt").write_text(
        "Play trial files in numeric order. For each, record the perceived item and quality notes. "
        "Do not open the answer key until scoring is complete.\n",
        encoding="utf-8",
    )
    print(json.dumps({"trials": len(key), "directory": str(DEST), "answer_key": str(key_path)}, indent=2))


if __name__ == "__main__":
    main()
