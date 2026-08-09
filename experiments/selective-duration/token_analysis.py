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
    "cee": ["S", "IY1"],
    "checkbox": ["CH", "EH1", "K", "B", "AA2", "K", "S"],
    "ef": ["EH1", "F"],
    "el": ["EH1", "L"],
    "em": ["EH1", "M"],
    "en": ["EH1", "N"],
    "ess": ["EH1", "S"],
    "ljspeech": ["EH1", "L", "JH", "EY1", "S", "P", "IY1", "CH"],
    "standalone": ["S", "T", "AE1", "N", "D", "AH0", "L", "OW2", "N"],
    "vocoder": ["V", "OW1", "K", "OW2", "D", "ER0"],
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
