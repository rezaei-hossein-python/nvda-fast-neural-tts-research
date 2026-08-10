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

## Phase 2AG — corrected selective-duration listening gate

The corrected normalized four-item gate compared original Piper with one- and
two-frame separator reductions for `F`, `S`, `A`, and `button`. All variants
preserved voice quality. The original `button` sample was the user's preferred
pronunciation in Trial 04. This is the first valid perceptual evidence that a
small selective duration change can be safe; it is not evidence that broader
compression is safe.

## Phase 2AH — quality-preserving duration envelope

The bounded P0–P6 ladder measured cumulative separator, terminal, and one-frame
vowel reductions over 24 interactive items. P1 saved a median 16 ms, while the
strongest clean P6 policy saved a median 80 ms and reduced median duration from
576 to 480 ms. Automatic PCM checks passed. Two blinded candidates (P1 and P6)
were prepared for manual listening; no perceptual conclusion has yet been
recorded.

## What remains learned

The dominant product constraints are physical useful waveform duration,
serialized playback, and quality—not merely a small synthesis-stage latency.
Piper Phase 2S remains the production baseline. The new branch is isolated,
inference-only, and must stop if the existing Lessac model/export cannot expose
and safely override duration plans.

## Phase 2AH decoded result and Phase 2AI audited frontier

The Phase 2AH key showed Trial C was P1 in five trials, Original in two, and P6
in one. Because the user judged all eight C samples good in speed and quality,
only P1 is perceptually validated by this result. P6 is not promoted: it
appeared as C only once. The P0–P6 automatic measurements remain valid
structural evidence, but not a substitute for the decoded perceptual gate.

Phase 2AI fully decoded the former 370-frame `protected/unknown` pool: 178
BOS/EOS boundary frames, 92 stress/control frames, and 100 frames of valid IPA
speech tokens previously missed by a mojibake-damaged classifier. Piper `_` is
an inserted PAD/separator token, `^` is BOS, and `$` is EOS. Unicode-safe
classification now protects all consonants, stress/length controls, and other
speech-bearing tokens.

P1 became V1. Across 54 interactive items, original Piper measured 560 ms
median, 776 ms P90, 837.6 ms P95, and 1264 ms maximum in the final run. V1
measured 544/760/821.6/1248 ms. V6, the strongest evidence-bounded combined
plan, measured 448/614.4/693.6/1024 ms and saved 128 ms median and 160 ms P95.
Character-only median/P95/max improved from 520/672/704 ms to 400/544/592 ms,
still far from the <=300 ms median objective. V6 adds no operation beyond V5;
this is the diminishing-return stop rather than authorization to touch
consonants or unknown speech. V1 and V6 were selected for an eight-trial,
24-WAV blind quality gate. No NVDA integration occurred.

The completed Phase 2AI listening result had one explicit item-level failure:
Trial 3 was `Y`, and Original, V1, and V6 were all unacceptable. Among the
other seven trials, the user preferred Original twice, V1 three times, and V6
twice. V6 therefore failed the Phase 2AI perceptual gate; the shared `Y`
failure does not attribute the problem specifically to V6. No stronger policy
was promoted and Phase 2AJ was not started.
