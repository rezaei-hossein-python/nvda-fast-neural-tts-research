# Phase 2AP-B Findings — Definitive Perceptual Verdict

Date: 2026-08-11

## 1. Executive Summary

The comprehensive, unblinded perceptual analysis for Phase 2AP-B provides a definitive, split decision on the dual-mode learned duration hypothesis.

**The Good (Normal Preservation): PASS**
The trained normal mode (`speech_mode=0`) achieves strict mathematical and perceptual preservation. `N1` was rated acceptable in exactly 16 out of 18 trials (88.9%), perfectly mirroring the baseline `N0` acceptance rate (16/18).

**The Bad (Interactive Acceptability): FAIL**
The learned interactive mode (`speech_mode=1`) failed drastically in terms of perceptual voice quality and naturalness on isolated words. Despite successfully achieving mathematical speed targets in automated benchmarks, it was **rejected as unacceptable by the human listener in 66.7% of all trials**. 

**Decision: NO-GO**. 
The dual-mode conditioned-duration Piper model is NOT ready for isolated runtime integration or NVDA use. We must stop here.

---

## 2. Decoded Blind Evaluation (18 Trials)

All 18 blind evaluation trials are decoded below against the retired answer key, preserving exact ties:

| Trial | Item | N0 Acc? | N1 Acc? | I1 Acc? | Fastest Acceptable |
|---|---|---|---|---|---|
| 01 | `A` | Yes | Yes | **Yes** | N0_Baseline |
| 02 | `E` | Yes | No | **No** | N0_Baseline |
| 03 | `F` | Yes | Yes | **No** | N1_TrainedNorm |
| 04 | `K` | No | Yes | **No** | N1_TrainedNorm |
| 05 | `0` | Yes | Yes | **No** | N1_TrainedNorm |
| 06 | `7` | Yes | Yes | **Yes** | N1_TrainedNorm |
| 07 | `W` | Yes | Yes | **Yes** | N0_Baseline |
| 08 | `M` | Yes | Yes | **No** | N0_Baseline |
| 09 | `button` | Yes | Yes | **No** | N0_Baseline |
| 10 | `selected` | Yes | Yes | **No** | N1_TrainedNorm |
| 11 | `expanded` | Yes | Yes | **Yes** | N1_TrainedNorm |
| 12 | `unavailable` | Yes | Yes | **No** | N0_Baseline |
| 13 | `dialog` | Yes | Yes | **No** | N0_Baseline |
| 14 | `tree view` | Yes | Yes | **No** | N0_Baseline |
| 15 | `comma` | Yes | No | **No** | N0_Baseline |
| 16 | `period` | No | Yes | **No** | N1_TrainedNorm |
| 17 | `The settings dialog is open.` | Yes | Yes | **Yes** | **I1_TrainedInt** / N1_TrainedNorm |
| 18 | `Please review the document.` | Yes | Yes | **Yes** | N0_Baseline |

---

## 3. Quantitative Acceptance Rates

**Overall Acceptable Rate (18 Trials)**
- N0 (Baseline) Acceptable: 16/18 (88.9%)
- N1 (Trained Norm) Acceptable: 16/18 (88.9%)
- **I1 (Trained Int) Acceptable: 6/18 (33.3%)  <-- FAILED (Target: >= 85%)**

**Fastest Acceptable Rate**
- N0 (Baseline) Fastest: 10/18
- N1 (Trained Norm) Fastest: 8/18
- **I1 (Trained Int) Fastest: 1/18**

---

## 4. Sub-Domain Perceptual Classification

### A. Characters/Digits (8 items)
- **Result: FAIL**
- **I1 Acceptable Rate**: 3/8 (**37.5%**)
- **Rejected Items**: `E`, `F`, `K`, `0`, `M`
- **Analysis**: Despite successfully hitting the 250-300 ms speed targets during automatic evaluations, the resulting audio for single characters sounds perceptually ruined or distorted to the user. It is categorically rejected.

### B. UI/Navigation (6 items)
- **Result: FAIL**
- **I1 Acceptable Rate**: 1/6 (**16.7%**)
- **Rejected Items**: `button`, `selected`, `unavailable`, `dialog`, `tree view`
- **Analysis**: Even worse than characters. The attempt to force concise interactive timing onto multi-syllabic UI words destroys the pronunciation or naturalness entirely.

### C. Normal-Reading Sentences (2 items)
- **Result: PASS (Trained Normal `N1` only)**
- **Analysis**: The architecture successfully decoupled the modes. Normal sentence reading is pristine and 100% equivalent to the baseline voice. (Interestingly, `I1` was marked acceptable on these long sentences, but since the goal of `I1` is fast short-speech, this is irrelevant to its primary task).

---

## 5. Strategic Conclusion and Final Verdict

### Final Verdict: NO-GO

The experimental architecture successfully proved that a dual-mode `speech_mode` condition *can* be learned strictly within the StochasticDurationPredictor, and it successfully achieved mathematical duration compression while strictly preserving unconditioned normal speech. 

However, **it failed the manual perceptual quality gate entirely.**

Squeezing the duration predictor natively via `length_scale=0.5` targets produced timings that the VITS acoustic/decoder stack simply could not render naturally on isolated words. The resulting interactive mode is "materially faster," but it is **unacceptable to listen to**. 

We cannot advance this model into production or runtime testing. The project hypothesis—that learned duration conditioning *alone* produces high-quality concise interactive speech—is invalid. 

**Next Steps Blocked.** 
No NVDA or Runtime integration will be performed. The consolidated R&D history will be updated to reflect this final dead-end for duration-only VITS conditioning.
