# Screen-Reader TTS Research Phase Ledger

This document is the durable source of truth for the screen-reader neural TTS performance research (Phase 2), mapping every attempted hypothesis, mechanism, and conclusion from the production baseline forward.

## Status Classifications
- `PRODUCTION BASELINE`
- `VALIDATED FOUNDATION`
- `PARTIAL / RESEARCH EVIDENCE`
- `REJECTED`
- `INVALIDATED`
- `SUPERSEDED`
- `CURRENT`

---

## 1. Consolidated Research History

### Phase 2S
- **Purpose:** Production add-on baseline.
- **Mechanism:** Standard Piper NVDA driver.
- **Result:** Functional but perceptually sluggish for high-speed users.
- **Status:** `PRODUCTION BASELINE`

### Phase 2T / 2U / 2V
- **Purpose:** Improve responsiveness via scheduling/completion/queue experiments.
- **Mechanism:** Worker thread tuning, early cutoff thresholds.
- **Result:** Slower behavior; premature completion; physical waveform duration remained the fundamental limit.
- **Reason not to repeat:** Scheduling changes alone do not solve acoustic-unit duration.
- **Status:** `REJECTED`

### Phase 2W
- **Purpose:** Evaluate NVDA Sonata engine as an alternative.
- **Mechanism:** Sonata investigation.
- **Result:** Not sufficiently advantageous for the target screen-reader use case.
- **Status:** `REJECTED`

### Phase 2X / 2Y
- **Purpose:** Typed-event/cancellation handling and global Piper rate scaling.
- **Mechanism:** `length_scale` global parameter tuning and aggressive cancellation.
- **Result:** Event delivery improved but worker stability failed; global `length_scale` produced shorter speech but unacceptable perceptual quality.
- **Status:** `REJECTED`

### Phase 2Z / 2AA / 2AB
- **Purpose:** Alternative fast acoustic models.
- **Mechanism:** FastSpeech2, Matcha, MB-MelGAN, low-latency vocoders.
- **Result:** Inferior latency, problematic tail duration, perceptual-quality failures.
- **Status:** `REJECTED`

### Phase 2AC
- **Purpose:** Refocus on the most viable engine.
- **Mechanism:** Architecture decision to stop model swapping and investigate Piper/VITS internally.
- **Result:** Established the path forward.
- **Status:** `VALIDATED FOUNDATION`

### Phase 2AD / 2AE
- **Purpose:** Piper ONNX duration-boundary proof and manual override mechanism.
- **Mechanism:** Exposing and overwriting the stochastic duration predictor output array before upsampling.
- **Result:** Technical override mechanism was successfully proved. However, early listening results were flawed due to mismatched evaluation pipelines.
- **Status:** 
  - technical duration override = `VALIDATED FOUNDATION`
  - old listening conclusion = `INVALIDATED`

### Phase 2AF
- **Purpose:** Baseline pipeline correction.
- **Mechanism:** Normalization/equivalence correction for research validation pipelines.
- **Result:** Restored exact alignment with the production Lessac baseline.
- **Status:** `VALIDATED FOUNDATION`

### Phase 2AG
- **Purpose:** Safe micro-reductions.
- **Mechanism:** Tiny 1–2 frame separator/silence reductions.
- **Result:** Preserved perceptual quality but provided minimal speedup.
- **Status:** `VALIDATED FOUNDATION` (as limited mechanism evidence only, not a general production policy).

### Phase 2AH through 2AM
- **Purpose:** Heuristic phoneme duration reduction.
- **Mechanism:** A5/V1/V6 structural-selector research (heuristic reduction of vowels and consonants based on syntax position).
- **Result:** Produced useful speed reductions but exhibited strong item-dependent user preferences. No robust fixed or structural routing policy emerged; selectors failed to generalize.
- **Status:** `REJECTED` as deployment strategy. `PARTIAL / RESEARCH EVIDENCE` for phonetic sensitivity.

### Phase 2AN
- **Purpose:** Dual-mode architectural model design.
- **Mechanism:** Conditioned Piper architecture feasibility (evaluating `speech_mode` embedding).
- **Result:** VITS architecture accepts mode conditioning smoothly.
- **Status:** `VALIDATED FOUNDATION`

### Phase 2AO
- **Purpose:** Initial local CPU dual-mode training proof.
- **Mechanism:** Training `speech_mode` embedding and `dp.cond` while freezing all other weights (approx. 50k parameters).
- **Result:** Learned `speech_mode` distinct behaviors; duration specialization was demonstrated. Initial quality conclusions were limited by later evaluation defects.
- **Status:** `VALIDATED FOUNDATION` for trainability. `SUPERSEDED` for final perceptual conclusions.

### Phase 2AP / 2AQ diagnostic correction
- **Purpose:** Pipeline debug.
- **Mechanism:** Fixed a severe sample rate mismatch (16-kHz Lessac PCM incorrectly written with 22.05-kHz WAV headers causing "kitten/chipmunk" distortion).
- **Result:** Eliminated the distortion artifact.
- **Status:** All previous listening conclusions derived from mislabeled files are `INVALIDATED`. The sample-rate regression test is permanently preserved.

### Phase 2AP-B
- **Purpose:** Duration-predictor-only conditioned model definitive listening.
- **Mechanism:** Re-evaluation of the purely duration-trained model at the correct sample rate.
- **Result:** NO-GO. Fast timing was learned, but interactive audio quality was insufficient (slurred/robotic).
- **Status:** `REJECTED`

### Phase 2AQ
- **Purpose:** Natural phoneme-aware duration target training.
- **Mechanism:** Using an expanded corpus with targeted length compression (protecting stops, compressing vowels/silence).
- **Result:** NO-GO. The final compact listening set failed (I1 wins: 1/8, N0 wins: 5/8, reject both: 2/8).
- **Conclusion:** Duration-only conditioning remains insufficient even with substantially better duration targets.
- **Status:** `REJECTED`

### Phase 2AR
- **Purpose:** Minimal decoder residual acoustic adapter.
- **Mechanism:** Unfreezing `dec.cond` (~115k params total) to adapt acoustic synthesis for forced short durations.
- **Result:** Stage 1 manual result showed the adapter has real acoustic influence, but merely swaps failure classes (improves plosives/boundaries, degrades nasals/sibilants) rather than producing a stable net perceptual improvement (I2 acceptance: 3/5).
- **Status:** `PARTIAL / RESEARCH EVIDENCE`

### Phase 2AS
- **Purpose:** Test transition-preserving latent-core compression.
- **Mechanism:** Generating normal acoustic latent sequences, protecting the leftmost and rightmost 16ms frames of each phone, and compressing only stationary interior frames by 50%.
- **Result:** Landmark breakthrough. 8/8 items acceptable, 8/8 wins or ties against baseline, zero phonetic failures on F, N, m, b, list, and comma.
- **Status:** `VALIDATED FOUNDATION`

### Phase 2AT
- **Purpose:** Generalization and deployability validation of the frozen 2AS mechanism.
- **Mechanism:** Running the frozen warp dynamically inside a modular host-level runtime across a 151-item corpus.
- **Result:** 100% structural pass, 100% bit-identical R1/R2 equivalence, max latency overhead <= 3.0 ms. Dynamic warp successfully accelerated letters (20.5% median) and digits (22.0% median), while safely bypassing short co-articulated continuous text. Double-blind human evaluation validated outstanding generalization: R2 achieved 100% acceptability and 100% wins + ties rate on baseline-acceptable trials (3 outright wins, 10 perceptual ties). Three rejections and one warning were traced to inherent baseline Lessac defects, confirming 0% candidate-induced regressions.
- **Status:** `SUCCESS (PASS)` (Fully validated generalization and deployability result; transition-preserving latent-core-warp is officially ready for host-level integration)

---

## 2. Frozen Findings / Do Not Repeat Without New Evidence
*   scheduler-only fixes;
*   premature completion ownership;
*   cancellation-heavy worker churn;
*   Sonata replacement;
*   FastSpeech2 replacement;
*   Matcha replacement;
*   MB-MelGAN route;
*   global `length_scale`;
*   global Sonic as primary solution;
*   A5/V6 fixed duration surgery;
*   structure-based A5 routing;
*   duration-predictor-only `speech_mode`;
*   15-token aggressive target training;
*   Phase 2AQ natural duration-only training;
*   training the Phase 2AR global decoder adapter longer;
*   immediate phoneme-class MoE without new evidence.

---

## 3. External Deep Research Conclusion

Comparative R&D against historical and contemporary high-speed screen-reader TTS systems yielded these evidence-backed findings:

### eSpeak NG
High-rate intelligibility relies on nonlinear rate behavior, context-sensitive timing, pause-specific rules, minimum duration floors, stress/position effects, and transition/allophone-aware synthesis. It is not one duration multiplier.

### RHVoice
Important mechanism: full acoustic/state trajectory can be preserved while the physical frame period is shortened. This is materially different from deleting duration frames before acoustic realization.

### DECtalk
Uses rate-regime-dependent pause/phoneme handling combined with explicit acoustic/formant realization.

### NVDA/Sonata
Rate boost frequently delegates to engine-native rate controls or Sonic. These do not reveal a missing Piper acoustic algorithm, and global post-PCM Sonic is already tested.

### Strongest Cross-Engine Lesson
> **Do not decide only how many frames each phone receives. Determine which parts of its acoustic evolution may be compressed.**

Context and within-phone temporal role matter more than simple phone class.
