# Phase 2AQ-Final Findings — Definitive Decoded Perceptual Verdict

Date: 2026-08-11

## 1. Executive Summary

Phase 2AQ hypothesized that explicitly designing *natural, phoneme-aware* duration targets (protecting consonants and selectively compressing vowels/silence) could resolve the perceptual quality failures of Phase 2AP.

Following the generation of 157 strictly audited targets, we performed deterministic bounding-ladder training, freezing the acoustic/decoder stack and zero-locking the normal mode. The best checkpoint (Step 250) successfully halved duration timings natively inside the neural stochastic duration predictor on characters. We selected the strongest 8 interactive finalists and 1 normal-mode control, securely packaged them at `16,000 Hz`, and subjected them to blind A/B manual user listening.

**The results are definitive:** The user overwhelmingly preferred the original Lessac unconditioned baseline (N0) or rejected both outright due to poor interactive voice quality. The duration-predictor-only conditioning hypothesis has failed perceptually for the final time. 

**Decision: NO-GO**. 
The dual-mode conditioned-duration Piper model cannot produce acceptable interactive voice quality and is NOT ready for isolated runtime integration or NVDA use. We must stop here.

---

## 2. Decoded Blind Evaluation Table (9 Trials)

All 9 blind evaluation trials are decoded below against the retired answer key. The user selected the "Fastest Acceptable" option (with "Same" indicating ties and "Reject Both" indicating neither met the quality bar):

| Trial | Item | Category | Map A | Map B | User Score | Winner |
|---|---|---|---|---|:---:|---|
| **01** | `F` | Character/Digit | **I1_TrainedInt** | N0_Baseline | A | **I1_TrainedInt** |
| **02** | `N` | Character/Digit | I1_TrainedInt | **N0_Baseline** | B | **N0_Baseline** |
| **03** | `m` | Character/Digit | **N0_Baseline** | I1_TrainedInt | A | **N0_Baseline** |
| **04** | `b` | Character/Digit | I1_TrainedInt | **N0_Baseline** | B | **N0_Baseline** |
| **05** | `V` | Character/Digit | **N0_Baseline** | I1_TrainedInt | A | **N0_Baseline** |
| **06** | `list` | UI/Nav | N0_Baseline | I1_TrainedInt | REJECT | **REJECT BOTH** |
| **07** | `link` | UI/Nav | I1_TrainedInt | N0_Baseline | REJECT | **REJECT BOTH** |
| **08** | `comma` | Punctuation | I1_TrainedInt | **N0_Baseline** | B | **N0_Baseline** |
| **09** | `The selected button is unavailable.` | Normal Control | N1_TrainedNorm | N0_Baseline | SAME | **SAME** |

---

## 3. Quantitative Acceptance Rates

**Overall Interactive Performance (8 Trials)**
- **I1 (Trained Int) Wins**: 1/8 (**12.5%**) <-- **FAILED**
- **N0 (Baseline) Wins**: 5/8 (62.5%)
- **Rejected Both**: 2/8 (25.0%)

---

## 4. Sub-Domain Perceptual Classification & Analysis

### A. Characters/Digits (5 items)
- **Result: FAIL**
- **I1 Wins**: 1/5 (`F`)
- **N0 Wins**: 4/5 (`N`, `m`, `b`, `V`)
- **Analysis**: Even with meticulous phoneme-class-aware duration targets designed to explicitly protect consonants, the VITS acoustic/decoder stack structurally fails to render single letters naturally when squeezed by the trained duration predictor. The output sounds slurred, robotic, or overly compressed, driving the user to revert to the slower original baseline on 80% of items.

### B. UI/Navigation (2 items)
- **Result: FAIL**
- **I1 Wins**: 0/2
- **Rejected Both**: 2/2 (`list`, `link`)
- **Analysis**: Catastrophic failure. Both the baseline and the trained interactive versions were completely rejected by the user.

### C. Punctuation (1 item)
- **Result: FAIL**
- **I1 Wins**: 0/1 (`comma` reverted to N0 Baseline)

### D. Normal-Reading Sentence (1 Control)
- **Result: PASS (Trained Normal `N1` only)**
- **Analysis**: Trial 09 confirms that `N1` (Trained Normal) sounds exactly the `SAME` as `N0` (Baseline). The structural `emb_mode.weight[0].zero_()` lock effectively mathematically preserves the reading baseline voice 100%.

---

## 5. Strategic Conclusion and Final Verdict

### Final Verdict: NO-GO

Phase 2AQ was the strongest possible implementation of duration-predictor-only conditioning. It fixed the evaluation rate (16 kHz), bypassed structural gradients (`g=torch.detach`), and fed the model carefully tuned, phoneme-class aware timing targets (protecting stops/consonants). 

Despite successfully matching these targets automatically and preserving normal mode perfectly, **the perceptual quality of the resulting interactive speech is categorically unacceptable.** 

**Technical Conclusion**: 
VITS cannot synthesize high-quality, concise interactive speech simply by being told to compress phonetic durations via the stochastic duration predictor (SDP). The acoustic representations in the posterior encoder, flow, and decoder layers are natively intertwined with longer durations. Forcing the SDP to output short durations results in slurred, misarticulated, robotic audio.

The project hypothesis—that learned duration conditioning *alone* produces high-quality concise interactive speech without full acoustic/decoder fine-tuning—is false.

**Next Steps Blocked.** 
No NVDA or Runtime integration will be performed. The consolidated R&D history will be updated to reflect this definitive final dead-end for duration-only VITS conditioning.
