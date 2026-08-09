"""Deterministic selective phoneme-duration policies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


VOWELS = frozenset("AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW".split())
STOPS = frozenset("B D G K P T".split())
FRICATIVES = frozenset("CH DH F HH JH S SH TH V Z ZH".split())
SONORANTS = frozenset("L M N NG R W Y".split())
SILENCE = frozenset({"sil", "sp", "spn", "pau", "<pad>", "@sp", "@sil"})


@dataclass(frozen=True)
class Policy:
    name: str
    vowel_factor: float
    stop_factor: float
    fricative_factor: float
    sonorant_factor: float
    silence_factor: float
    unknown_factor: float
    vowel_min: int
    stop_min: int
    fricative_min: int
    sonorant_min: int
    silence_max: int
    unknown_min: int
    edge_consonant_bonus: int = 1

    def metadata(self) -> dict:
        return asdict(self)


POLICIES = {
    "conservative": Policy("conservative", .72, 1.0, .92, .88, .35, .85, 3, 2, 3, 2, 2, 1),
    "balanced": Policy("balanced", .52, 1.0, .82, .72, .20, .72, 2, 2, 3, 2, 1, 1),
    "aggressive": Policy("aggressive", .38, .90, .70, .58, .10, .58, 2, 2, 2, 1, 1, 1),
}


def normalize_phone(phone: str) -> str:
    value = phone.strip().strip("{}@_")
    while value and value[-1].isdigit():
        value = value[:-1]
    return value.upper() if value.lower() not in SILENCE else value.lower()


def classify_phone(phone: str) -> str:
    value = normalize_phone(phone)
    if value.lower() in SILENCE:
        return "silence"
    if value in VOWELS:
        return "vowel"
    if value in STOPS:
        return "stop"
    if value in FRICATIVES:
        return "fricative"
    if value in SONORANTS:
        return "sonorant"
    return "unknown"


def validate_durations(durations: Sequence[int], token_count: int) -> None:
    if len(durations) != token_count:
        raise ValueError("duration vector length must equal token count")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in durations):
        raise TypeError("durations must be integers")
    if any(value < 0 for value in durations):
        raise ValueError("durations must be nonnegative")


def apply_policy(phones: Sequence[str], durations: Iterable[int], policy: Policy) -> list[int]:
    source = [int(value) for value in durations]
    validate_durations(source, len(phones))
    output: list[int] = []
    last = len(phones) - 1
    for index, (phone, value) in enumerate(zip(phones, source)):
        kind = classify_phone(phone)
        if value == 0:
            output.append(0)
            continue
        factor = getattr(policy, f"{kind}_factor")
        if kind == "silence":
            adjusted = min(policy.silence_max, max(0, round(value * factor)))
        else:
            minimum = getattr(policy, f"{kind}_min")
            adjusted = max(minimum, round(value * factor))
            if kind in {"stop", "fricative"} and index in {0, last}:
                adjusted = max(adjusted, minimum + policy.edge_consonant_bonus)
        output.append(int(adjusted))
    validate_durations(output, len(phones))
    return output

