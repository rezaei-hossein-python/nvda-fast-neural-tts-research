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
## Phase 2AJ — V6 ablation and baseline-outlier diagnosis

Phase 2AJ isolated the Phase 2AI `Y` failure before policy scoring. `Y`
phonemizes as `w ˈ a ɪ`; its active token plan is short and contains no
consonant-duration edit opportunity. The original graph does not expose a
duration output and separate ONNX sessions are stochastic, so byte-identical
PCM cannot be demanded across paths; the self-duration path did use the
supplied vector exactly. Because Original, V1, and V6 were all unacceptable,
`Y` remains an independent Lessac/eSpeak pronunciation or item-level baseline
issue, not evidence for changing duration control.

The V6 edit families were decomposed into E1 (first PAD), E2 (remaining PAD
plus BOS/EOS), E3 (terminal PAD/EOS), E4 (one long vowel), and E5 (additional
long vowels). A0–A8 ablations over seven prior usable items plus eight
confirmation items found A5 (E1+E2+E3) as the conservative middle candidate
and A6 (E1+E2+E4) as the frontier candidate. A deterministic adaptive rule was
not justified by seven preference observations. A5 measured 544 ms median and
811.2 ms P95; A6 measured 560 ms median and 838.4 ms P95 in the final ablation
run, versus A1/V1 at 656/988.8 ms and A8/V6 at 544/806.4 ms. These are
automatic results only. A new 24-WAV blind gate was generated; no Phase 2AJ
listening result has been decoded and no Phase 2AK work began.

The Phase 2AJ gate then returned valid preferences on all eight items. The key
mapped selections to A5 on S, U, W, and button, and to Original on 0,
exclamation mark, expanded, and unavailable. Counts were Original 4, A5 4,
and A6 0. Relative to Phase 2AI, S moved Original→A5; U and W moved V1→A5;
0 stayed Original; exclamation mark and expanded moved V6→Original; and
unavailable moved V1→Original. A5 is the leading modified research candidate
because it ties Original in preference while retaining the stronger automatic
duration result. It is not yet perceptually validated, and A6 is not promoted.
The same-voice/quality/shortened-plan hypothesis is provisionally supported,
but not established as a universal fixed policy. The next phase should use a
broader explicitly quality-flagged Original-versus-A5 gate; no NVDA integration
or automatic Phase 2AK execution follows from this result.
## Phase 2AK — decisive Original versus frozen A5 gate

Phase 2AK freezes A5 and expands validation to 38 items: 18 characters, 7
digits, 5 punctuation names, and 8 UI/navigation utterances. Automatic safety
passed all 76 renders. A5 reduced character median/P95 from 520/800 ms to
392/672 ms, digit median/P95 from 624/758.4 to 480/619.2 ms, punctuation from
592/1139.2 to 496/944 ms, and UI from 576/852 to 456/697.6 ms. A fixed 16-trial,
32-WAV Original-versus-A5 gate was generated with explicit overall preference,
quality, pronunciation, and problem fields. Its answer key remains private;
no perceptual conclusion has yet been recorded.

Phase 2AL manual decoding produced 17 valid preferences: Original 9, A5 8,
Same 0; `M` was rejected because both variants were unacceptable. The six
repeated items were perfectly stable across two realizations: S/W/button
consistently A5, R/U/0 consistently Original; 6/6 stable, no flips or rejected
repeat. Relative to Phase 2AK's 10–4 Original/A5 result, stochastic repeat
sampling materially narrowed the aggregate gap, but repeated-item stability
indicates item structure matters more than random preference flipping. A5
retains 624→520 ms median and 912→720 ms P95 duration, but remains below the
clear-majority acceptance gate and research-only. No Phase 2AM work began.

## Phase 2AL — stochastic repeatability of frozen A5

Phase 2AL found two internal ONNX `RandomNormalLike` nodes with no exposed
random inputs or seed, so common-random-number pairing was not feasible without
changing graph semantics. Five paired Original/A5 realizations were generated
for each of 12 informative items, with randomized execution order: 60 pairs,
120 raw WAVs, and an 18-trial/36-WAV blinded subset. Overall median duration was
624 ms Original versus 520 ms A5, with a median 112 ms saving. Median within-
item duration standard deviation was 41.2 ms Original and 45.7 ms A5; RMS and
spectral-centroid variability were also recorded. The subset is awaiting manual
quality/pronunciation scoring; its key remains private and no Phase 2AM work
began.

The completed Phase 2AK gate produced 14 valid preferences and two shared
rejections. Original was preferred 10 times and A5 four times. Trial 04 was
`A`; Trial 10 was `exclamation mark`; both Original and A5 were unacceptable,
so neither is attributed to A5. Overlapping items were unstable relative to
Phase 2AJ: only S remained A5-preferred; U, W, expanded, unavailable, and
button moved to Original, 0 remained Original, and exclamation mark became a
shared rejection. Despite A5's material duration reduction, it fails the
clear-majority quality/preference gate and is rejected as a general interactive
policy. It remains a research artifact only; no NVDA testing or stronger policy
is authorized.

## Phase 2AM — structural selector decision

Phase 2AM extracted phoneme-class counts, PAD/boundary occupancy, E1/E2/E3
frame savings, boundary-to-speech ratios, cumulative displacement before
speech/stress/consonants, and token-duration features from all Phase 2AL
realizations. Stable A5 items (S, W, button) and stable Original items (R, U,
0) overlapped substantially. The strongest one-feature thresholds classified
only 5/6 stable items and failed leave-one-item-out tests on multiple held-out
items. A representative boundary threshold matched 4/5 secondary observations
but misclassified unavailable. No conservative, identity-free selector was
justified; no new policy or listening set was generated. Outcome C: retain A5
and Original as research evidence only and stop before Phase 2AN.

## Phase 2AN — transition to learned Piper conditioning

Phase 2AN publishes the completed inference R&D record and begins screen-reader-
conditioned Piper feasibility work in the isolated
[`piper-screen-reader-research`](https://github.com/rezaei-hossein-python/piper-screen-reader-research)
repository.

**Strategic conclusion:** inference-time duration manipulation is technically
viable but not sufficiently generalizable as a fixed or simple structure-routed
policy. The new hypothesis is that Piper/VITS should learn a dedicated
interactive speech mode (`speech_mode = normal | interactive`) while preserving
one speaker identity.

**Phase 2AN deliverables (design only, no training):**

- Piper v1.5.0 training architecture map
- Duration-predictor-only mode conditioning as preferred first experiment
- Public Lessac-low checkpoint identified on Hugging Face (`epoch=2307-step=558536.ckpt`)
- Licensing audit (GPL Piper code, MIT HF checkpoints, Blizzard research dataset)
- Minimal 17-token prototype design and acceptance gates
- **Outcome A:** fine-tuning feasible; GPU required for execution

Production Phase 2S remains untouched. No NVDA integration occurred.
