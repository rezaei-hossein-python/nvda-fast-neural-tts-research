# ADR: investigate Piper screen-reader duration control

## Decision

Investigate a Piper/VITS screen-reader-specific inference fork that exposes
predicted token durations and selectively modifies them before alignment
generation. This is research-only and is not integrated into NVDA or Phase 2S.

## Why

Phase 2S already provides acceptable Piper voice quality and materially faster
interactive onset. Replacement models repeatedly traded quality, CPU latency,
or integration safety. Piper/VITS already predicts token durations before its
alignment path, so it offers the smallest evidence-backed intervention point.

## Why this differs from Phase 2Y

Phase 2Y applied one global `length_scale=0.4` multiplier. Phase 2AD will instead
classify phonetic roles, preserve information-bearing consonant floors, shorten
vowel steady-state occupancy, reduce silence, cap tails, and then invoke the
original alignment and decoder. No post-hoc time compression is intended.

## Scope and guardrails

- inference-only; no retraining in the first experiment;
- no NVDA integration, add-on, scheduler, cache, or production change;
- preserve the original model artifact and provide exact fallback;
- use bounded conservative, balanced, and aggressive policies;
- reject malformed or unstable output;
- preserve pitch, energy, speaker conditioning, and decoder semantics initially;
- stop if the existing Lessac ONNX graph cannot expose/override durations without
  an unavailable trainable/exportable checkpoint.

## Success gate

At least one policy must materially outperform global scaling while preserving
consonants, recognizable Piper identity, valid PCM, and a useful duration
distribution (common-unit median <=180 ms, P95 <=220 ms, with intelligible
long units <=260 ms). Only then may a small blind listening set be prepared.

## Non-goals

This decision does not authorize retraining, NVDA changes, Piper production
changes, another model architecture, or automatic integration.
