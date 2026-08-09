# Phase 2Z FastSpeech2 selective-duration findings

## Status

Stopped at the explicit acoustic failure gate. No NVDA integration was made.
The pinned FastSpeech2 model supports explicit token durations when `d_targets`
is supplied together with the corresponding `mel_lens` and `max_mel_len`.

## Source facts

- Upstream: `https://github.com/ming024/FastSpeech2`
- Commit: `d4e79eb52e8b01d24703b2dfc0385544092958f3`
- FastSpeech2 and repository-bundled HiFi-GAN code licenses: MIT.
- Normal inference expands predicted integer durations after applying global
  `d_control`. Explicit `d_targets` bypass that calculation and are passed to
  `LengthRegulator`.

## Complete 36-character measurements

All values below are content-independent aggregate measurements at 22,050 Hz,
CPU-only, four PyTorch intra-op threads. The adaptive useful-energy detector
uses a 5 ms RMS window, a threshold equal to the maximum of 0.002 normalized
RMS, four times the estimated first-20-ms noise floor, and 8% of utterance RMS,
with a 12 ms sustained requirement.

| Condition | Median useful ms | P95 useful ms | Maximum useful ms | Median PCM ms | Median complete-PCM ms |
|---|---:|---:|---:|---:|---:|
| Normal | 309.09 | 535.15 | 699.41 | 394.74 | 291.92 |
| Global 0.5 | 132.43 | 265.05 | 345.49 | 197.37 | 183.90 |
| Selective conservative | 233.17 | 457.68 | 590.84 | 319.27 | 265.92 |
| Selective balanced | 184.60 | 399.12 | 497.55 | 255.42 | 229.73 |
| Selective aggressive | 143.17 | 328.42 | 400.73 | 203.17 | 189.32 |

The aggressive policy protects stops and fricatives while compressing vowels,
sonorants, and silence most strongly. It meets the median useful-duration goal
but fails the 220 ms P95 and 260 ms long-name allowances. Four common items
remain above 260 ms, with the longest at 400.73 ms. Median complete-PCM latency
also remains above the 150 ms hard ceiling; HiFi-GAN is the dominant component
(139.10 ms median vocoder time, plus the duration-prediction and explicit-target
acoustic passes).

## Decision

The FastSpeech2/LJSpeech hypothesis fails the specified gate without damaging
protected consonant duration further. Per the phase rules, blind listening,
cancellation/recovery, and WASAPI direct-PCM tests were not advanced. The next
model-level research candidate should be Matcha-TTS, with the same isolated
artifact, duration, latency, memory, and blind-identification gates.

