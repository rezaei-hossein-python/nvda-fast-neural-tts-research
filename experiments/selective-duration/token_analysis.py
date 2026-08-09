"""Pinned FastSpeech2 English frontend with explicit phone visibility."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np


# Fixed public-corpus pronunciations absent from the pinned LibriSpeech lexicon.
# This deliberately avoids a network-dependent frontend fallback.
FIXED_PRONUNCIATIONS = {
    "aitch": ["EY1", "CH"],
    "ar": ["AA1", "R"],
    "backslash": ["B", "AE1", "K", "S", "L", "AE2", "SH"],
    "backend": ["B", "AE1", "K", "EH2", "N", "D"],
    "cee": ["S", "IY1"],
    "checkbox": ["CH", "EH1", "K", "B", "AA2", "K", "S"],
    "deterministic": ["D", "IH0", "T", "ER2", "M", "AH0", "N", "IH1", "S", "T", "IH0", "K"],
    "ef": ["EH1", "F"],
    "el": ["EH1", "L"],
    "em": ["EH1", "M"],
    "en": ["EH1", "N"],
    "fricatives": ["F", "R", "IH1", "K", "AH0", "T", "IH0", "V", "Z"],
    "ess": ["EH1", "S"],
    "ljspeech": ["EH1", "L", "JH", "EY1", "S", "P", "IY1", "CH"],
    "interactive": ["IH2", "N", "T", "ER0", "AE1", "K", "T", "IH0", "V"],
    "interface": ["IH1", "N", "T", "ER0", "F", "EY2", "S"],
    "standalone": ["S", "T", "AE1", "N", "D", "AH0", "L", "OW2", "N"],
    "update": ["AH0", "P", "D", "EY1", "T"],
    "vocoder": ["V", "OW1", "K", "OW2", "D", "ER0"],
    "waveform": ["W", "EY1", "V", "F", "AO2", "R", "M"],
    "zwnj": ["Z", "IY1", "D", "AH0", "B", "AH0", "L", "Y", "UW1", "EH1", "N", "JH", "EY1"],
}


def read_lexicon(path: Path) -> dict[str, list[str]]:
    lexicon: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = re.split(r"\s+", line.strip())
        if fields and fields[0].lower() not in lexicon:
            lexicon[fields[0].lower()] = fields[1:]
    return lexicon


class Frontend:
    def __init__(self, upstream: Path):
        self.upstream = upstream
        self.lexicon = read_lexicon(upstream / "lexicon" / "librispeech-lexicon.txt")

    def phones(self, text: str) -> list[str]:
        phones: list[str] = []
        for word in re.split(r"([,;.\-?!\s+])", text.strip("!'(),.:;? ")):
            if not word or word.isspace():
                continue
            if re.fullmatch(r"[^\w\s]", word):
                values = ["sp"]
            elif word.lower() in self.lexicon:
                values = self.lexicon[word.lower()]
            elif word.lower() in FIXED_PRONUNCIATIONS:
                values = FIXED_PRONUNCIATIONS[word.lower()]
            else:
                raise ValueError(f"fixed corpus word absent from pinned lexicon: {word!r}")
            phones.extend("sp" if re.fullmatch(r"[^\w\s]?", value) else value for value in values)
        return phones

    def sequence(self, phones: list[str]) -> np.ndarray:
        from text import text_to_sequence

        encoded = "{" + " ".join(phones) + "}"
        return np.asarray(text_to_sequence(encoded, ["english_cleaners"]), dtype=np.int64)
