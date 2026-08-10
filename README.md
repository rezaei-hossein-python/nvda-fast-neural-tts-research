# NVDA fast neural TTS research

Reproducible R&D on low-latency neural TTS architectures for screen-reader
interaction. This repository records **architecture exploration and evidence**,
not production code. Rejected experiments are retained intentionally because the
project is evidence-driven.

The production NVDA Piper add-on and Phase 2S baseline live in a separate
repository and are not modified here.

## What this repository contains

Chronological investigation of whether neural TTS can deliver short, intelligible,
high-quality screen-reader acoustic units on CPU, without sacrificing voice
identity. Major threads:

### FastSpeech2 (Phase 2X–2Z)

Pinned [ming024/FastSpeech2](https://github.com/ming024/FastSpeech2) (MIT).
Explicit `d_targets` duration tensors were proven feasible. Aggressive selective
duration reached ~143 ms median useful duration but failed P95, tail-length,
and complete-PCM latency gates. HiFi-GAN vocoding alone was ~139 ms median.

### Matcha-TTS (Phase 2AA)

Official Matcha-TTS v0.0.7. Global `length_scale=0.5` met acoustic-duration
distribution targets but the CPU pipeline (~306 ms median complete PCM) failed
the latency gate before selective duration or listening.

### Vocoders (Phase 2AB)

HiFi-GAN, Multi-Band MelGAN, and FARGAN/LPCNet compatibility analysis.
MB-MelGAN reduced vocoding to ~14 ms median but blind listening rejected the
FastSpeech2 + aggressive-duration + mel-adaptation + MB-MelGAN configuration.

### Sonata (Phase 2W)

Investigated as an alternative runtime. Character waveforms remained ~500 ms;
no transferable character-specific cache or duration path.

### Piper duration control (Phase 2AC–2AM)

Documented in [`piper-screen-reader-research`](https://github.com/rezaei-hossein-python/piper-screen-reader-research).
Inference-time ONNX duration override was proven; A5 (~18% median reduction)
showed stable item-dependent preference but no generalizable selector. Phase 2AM
ended with Outcome C.

## Current direction (Phase 2AN)

The inference-only branch is complete. The strategic transition is to **learned
screen-reader conditioning in Piper/VITS** — teaching a compact interactive
speech mode rather than post-hoc duration manipulation. See the Piper research
repository `training/` area and `results/summaries/screen-reader-tts-rnd-history.md`.

## Roadmap

| Status | Topic |
|---|---|
| **Completed** | FastSpeech2, Matcha, vocoder, Sonata, Piper inference-time optimization |
| **Current** | Learned interactive-mode feasibility (Phase 2AN) |
| **Future (if successful)** | Trained prototype, isolated NVDA integration, production architecture, multilingual/Persian |

## Repository layout

```text
corpus/           Evaluation text
experiments/      FastSpeech2 selective duration, Matcha, vocoder benchmarks
locks/            Pinned upstream identities and artifact hashes
results/          Summaries, ADRs, and chronology (no raw audio or weights)
tests/            Regression tests for research harnesses
```

## Pinned sources

Recorded in `locks/`. Upstream repositories, virtual environments, checkpoints,
and generated audio are intentionally untracked. Reproduce from lock files and
documented download locations.

## Related repositories

- **Piper screen-reader research**: isolated Piper/VITS duration and conditioning work
- **Production add-on**: NVDA Piper driver (Phase 2S; not modified by this repo)
