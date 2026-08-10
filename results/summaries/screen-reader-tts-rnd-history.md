# Screen-reader neural TTS R&D history

This document records the accepted baseline, rejected experiments, and the
evidence leading to the Piper-internal duration-control investigation.

## Phase 2S — accepted baseline

Adaptive onset shaping was integrated only for eligible cached characters.
Portable testing found materially faster mouse-over, page changes, navigation,
and first-character response with acceptable Piper quality. Ordinary speech
remained unchanged. Sustained character echo can still saturate after several
rapid events; this is the accepted production baseline.

## Phase 2T — rejected scheduler

A one-active/one-pending scheduler with a 180 ms interruption/usefulness policy
was tested. It made overall interaction slower and was rejected. The evidence
showed that deadline interruption traded stale backlog for worse responsiveness.

## Phase 2U — rejected dedicated nonblocking lane

A dedicated player/completion lane produced promising standalone results but
failed in real NVDA. It reported synth completion before audio finished;
NVDA then advanced and cancelled/flushed the player. Synth switching only
temporarily reset the failure. The architecture was rejected.

## Phase 2V — rejected completion-ownership correction

Completion ownership was moved toward actual WavePlayer completion and
controller admission became negligible. Physical character waveform duration
remained dominant, and manual speed was insufficient. No production change
was accepted.

## Phase 2W — Sonata investigation

Sonata source research found Rust execution, a separate gRPC process, persistent
models, and fast/RT voice variants. Its character waveforms remained roughly
half a second and it had no transferable character-specific cache or duration
path. Sonata was not a direct solution for this bottleneck.

## Phase 2X — delivery and acoustic branches

NVDA delivery experiments showed that per-event cancellation could deliver
quickly but destabilized the worker. Track A was rejected. The isolated
FastSpeech2 branch proved explicit duration tensors were possible but did not
meet tail and CPU gates.

## Phase 2Y — Piper global scaling

Piper `length_scale=0.4` shortened interactive audio and sounded promising in
automatic measurements, but manual validation rejected the rushed/quality
tradeoff. Global scaling cannot protect consonants independently.

## Phase 2Z — FastSpeech2 selective duration

The pinned model accepted explicit `d_targets`. Aggressive selective control
reached approximately 143.17 ms median useful duration, but P95 was about
328.42 ms, the longest common unit about 400.73 ms, and complete PCM latency
about 189 ms. HiFi-GAN was approximately 139 ms median. The architecture
failed its gates.

## Phase 2AA — Matcha-TTS

Matcha global `length_scale=0.5` reached approximately 119.50 ms median and
194.22 ms P95 useful duration, but flow plus HiFi-GAN produced approximately
306.14 ms median complete PCM. The CPU latency gate failed before selective
duration, cancellation, WASAPI, or blind listening. Matcha was rejected.

## Phase 2AB — low-latency vocoders

MB-MelGAN reduced FastSpeech2 vocoding to approximately 14.25 ms median and
projected complete generation to about 64.5 ms. PCM validation passed, but the
user found the exact FastSpeech2/aggressive-duration/mel-adaptation/MB-MelGAN
speech uniformly terrible in blind listening. It was rejected for this
configuration; this does not claim MB-MelGAN is universally unusable.

## Phase 2AC — architecture decision

The model-swapping branch was paused. Finite pre-generated inventories and
concise interactive pronunciations were analyzed, but no further architecture
was started. The next bounded investigation is a Piper/VITS inference fork:
expose predicted per-token durations, classify phonetic roles, protect
consonants, compress vowel occupancy/silence/tails, and reuse the original
decoder and voice.

## Phase 2AE/2AF — Piper ONNX duration override and diagnosis

Phase 2AE proved that the existing Lessac graph can retain its duration
predictor while selecting a host-validated per-token override before both
alignment consumers. Disabled and self-duration paths were byte-identical
under deterministic controls, and one-frame changes produced the expected
256-sample change. The first blind set was rejected by the user as weak in
quality. Phase 2AF found that its generator omitted Piper's required
per-utterance `normalize_audio=True` conversion; original samples were weak as
well. Thus the graph mechanism is accepted research evidence, the conservative
policy is rejected as a product candidate, and acoustic quality attribution is
classified as Result A (invalid research baseline), not intrinsic VITS damage.

## What remains learned

The dominant product constraints are physical useful waveform duration,
serialized playback, and quality—not merely a small synthesis-stage latency.
Piper Phase 2S remains the production baseline. The new branch is isolated,
inference-only, and must stop if the existing Lessac model/export cannot expose
and safely override duration plans.
