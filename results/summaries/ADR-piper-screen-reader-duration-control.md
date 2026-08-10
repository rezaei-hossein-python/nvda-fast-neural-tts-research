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

## Phase 2AF diagnostic note

The Phase 2AE graph proof remains valid, but its first listening generator did
not reproduce Piper's `normalize_audio=True` output conversion. The resulting
weak original samples make that listening result a baseline-pipeline failure
(Result A), not evidence that selective duration inherently destroys LESSAC
quality. Correct normalization is required before further acoustic judgment.

## Phase 2AG/2AH evidence

After correction, one- and two-frame separator reductions were judged
voice-quality-preserving across four blinded items. Phase 2AH maps a bounded
cumulative envelope rather than pursuing global compression: P1 saves a median
16 ms, while the stronger clean P6 probe saves 80 ms median across 24 items.
Two blinded P1/P6 candidates are awaiting manual listening; no product decision
has been made.

## Non-goals

This decision does not authorize retraining, NVDA changes, Piper production
changes, another model architecture, or automatic integration.

## Phase 2AH decoded and Phase 2AI status

The completed Phase 2AH key showed that C was P1 in five trials, Original in
two, and P6 in one. All C samples were judged good, so P1—not P6—is the
validated baseline. Phase 2AI corrected the Unicode token classifier, decoded
all 370 former unknown frames, and measured a stronger evidence-bounded V6 at
448 ms median and 693.6 ms P95 over 54 interactive items (versus 560/837.6 ms
original in that run). Character-only median remained 400 ms. The Phase 2AI
blind result then recorded `Y` as an item-level failure: Original, V1, and V6
were all unacceptable. Excluding that failed item, preferences were Original 2,
V1 3, and V6 2. V6 fails the perceptual gate and is not promoted. Phase 2AJ
was not started and no production decision has been made.
Phase 2AJ now ablates V6 rather than strengthening it. It treats `Y` as an
independent baseline pronunciation case, decomposes V6 into five atomic edit
families, and compares A0–A8. Candidate M is A5 (boundary plus terminal), and
Candidate F is A6 (boundary plus one long vowel). The new 24-WAV gate is
blinded and awaiting manual listening; its answer key remains private.

Phase 2AJ listening is now complete: A5 was selected for S, U, W, and button;
Original was selected for 0, exclamation mark, expanded, and unavailable; A6
was selected zero times. This ties A5 and Original at four selections each.
A5 remains the leading modified research candidate because its automatic
duration is stronger, but it is not perceptually validated. A6 is not promoted.
The next gate should explicitly flag pronunciation/quality while comparing
Original and A5 on a broader corpus. No integration is authorized.

Phase 2AK is now decoded: Original won 10 of 14 valid trials and A5 won 4.
`A` and `exclamation mark` were rejected because both Original and A5 were
unacceptable. A5 therefore fails the clear-majority quality gate despite its
material duration reduction. It is not advanced to isolated NVDA testing.

Phase 2AL repeated the frozen policy five times per item. Manual results were
Original 9, A5 8, Same 0 among 17 valid trials; `M` was rejected for both
variants. Repeated-item stability was 6/6 with no flips, so stochasticity
affects aggregate preference balance but does not erase item-structure effects.
A5 remains research-only and is not advanced to NVDA; future work should be
targeted/adaptive rather than a stronger fixed policy.
