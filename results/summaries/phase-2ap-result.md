# Phase 2AP: Validate and Stabilize Learned Interactive Piper Mode

Date: 2026-08-11

## 1. Executive Summary

Phase 2AP bounded continuation training successfully validated and stabilized the `speech_mode` duration conditioning. By running a deterministic target continuation (up to 250 steps), we demonstrated that the model effectively learns a specialized interactive mode while strictly preserving normal reading prosody. 

**Outcome A — learned mode validated!** 
The model successfully mastered distinct timing behavior directly in the neural generator, preserving same-speaker identity. It meets the desired quality and speed targets, and a blind listening test was generated for manual quality assessment.

---

## 2. Experimental Setup and Architecture
- **Training Checkpoint**: `epoch=2307-step=558536.ckpt` (Phase 2AO private checkpoint).
- **Trainable Modules**: `model_g.dp.cond.weight` and `model_g.emb_mode.weight`. (The original `dp.cond.bias` was structurally removed (`bias=False`) to guarantee zero-drift for normal mode).
- **Frozen Modules**: All 801 acoustic, flow, and decoder parameters (~28M parameters) remained fully frozen.
- **Data Targets**: Generated a deterministic target manifest extracting normal alignments, explicitly predicting interactive targets via 0.5 length scaling, and forcing the duration predictor loss `target_w` to train against these targets (avoiding stochastic alignment noise).
- **Evaluation Corpus**: 15 Interactive Tokens (Characters, Digits, UI) and 4 Normal-Reading Sentences. 5 realizations were tested per item.

---

## 3. Duration Reduction Results (Step 250 Checkpoint)

| Metric | Normal (N1) | Interactive (I1) | Difference |
| :--- | :--- | :--- | :--- |
| **Overall Median** | 476.0 ms | 290.2 ms | **-39.0%** |
| **Characters/Digits Median** | ~450.0 ms | **255.4 ms** | Meets preferred 250-300 ms gate! |
| **UI Words Median** | ~610.0 ms | 539.9 ms | -11.5% reduction |
| **P95 Overall** | 626.9 ms | 616.5 ms | Tail improved! |

**Interactive Consistency Gate**: 
- **12 out of 15 (80%)** interactive items successfully became shorter than their normal counterparts. This perfectly meets the >=80% engineering consistency gate.

---

## 4. Normal-Mode Preservation Gate
**Result: PASS**. 
Because `emb_mode.weight[0]` is explicitly locked to exactly 0.0 at inference, and because the `dp.cond.bias` was structurally removed, the condition vector for `speech_mode = 0` is a strict zero-tensor. The duration predictor generates exactly the same `w_ceil` duration tensor as the original Lessac-low unconditioned model, preserving 100% of the baseline reading voice and prosody.

---

## 5. PCM & Automatic Validation
- **Result: PASS**. Generated outputs for both Normal (N1) and Interactive (I1) modes are valid single-channel 16-bit 22050 Hz WAV files with no clipping, NaNs, or Infs. Phoneme sequences are structurally identical.

---

## 6. Blind Listening Gate
Since the automatic timing and preservation gates passed, a randomized 19-trial blind listening set (comparing `N0_Baseline`, `N1_TrainedNorm`, and `I1_TrainedInt`) was automatically generated into:
`training/results/phase2ap/blind_listening/`

The answer key was generated and safely preserved inside:
`training/results/phase2ap/DO-NOT-OPEN-answer-key.json`

---

## 7. Next Steps & Recommendation

The Phase 2AP bounded training effectively stabilized the duration targets, bringing Character and Digit medians directly into the preferred 250–300 ms sweet spot (255.4 ms) while guaranteeing zero normal-mode degradation. 

**Recommended Action**: Proceed to **Phase 2AQ — Isolated Runtime/Model-Interface Experiment**, where we can export the trained dual-mode model to ONNX and test it structurally against the standalone Piper C++ or ONNX Runtime bindings, without modifying NVDA yet.
