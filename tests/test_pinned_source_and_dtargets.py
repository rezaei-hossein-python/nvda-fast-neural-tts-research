import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import torch
import yaml


ROOT = Path(__file__).parents[1]
UPSTREAM = ROOT / "upstream" / "FastSpeech2"
sys.path.insert(0, str(UPSTREAM))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))


def test_pinned_source_version_and_artifact_hashes():
    commit = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    assert commit == "d4e79eb52e8b01d24703b2dfc0385544092958f3"
    lock = json.loads((ROOT / "locks/artifacts.lock.json").read_text())
    for artifact in lock["artifacts"]:
        path = ROOT / artifact["local_path"]
        assert path.stat().st_size == artifact["byte_size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_explicit_dtargets_control_mel_length_and_leave_other_controls_neutral():
    pre = yaml.safe_load((UPSTREAM / "config/LJSpeech/preprocess.yaml").read_text())
    model_config = yaml.safe_load((UPSTREAM / "config/LJSpeech/model.yaml").read_text())
    pre["path"]["preprocessed_path"] = str(UPSTREAM / "preprocessed_data/LJSpeech")
    from model import FastSpeech2

    model = FastSpeech2(pre, model_config).eval()
    source = torch.tensor([[10, 11, 12]], dtype=torch.long)
    lengths = torch.tensor([3], dtype=torch.long)
    targets = torch.tensor([[2, 3, 4]], dtype=torch.long)
    with torch.no_grad():
        output = model(
            torch.tensor([0]), source, lengths, 3,
            mel_lens=torch.tensor([9]), max_mel_len=9,
            d_targets=targets, p_control=1.0, e_control=1.0,
        )
    assert output[5].tolist() == targets.tolist()
    assert output[9].tolist() == [9]
    assert output[0].shape[1] == 9
