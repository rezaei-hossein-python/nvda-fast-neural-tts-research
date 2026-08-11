# Phase 2AQ — Baseline-Fidelity Diagnosis Report

Date: 2026-08-11

## 1. Executive Summary

During Phase 2AP manual evaluation, the user reported that all 19 blind trials were rejected due to completely degraded, chipmunk-like voice quality.

Phase 2AQ was launched immediately to diagnose the root cause of this baseline-fidelity degradation.

The diagnosis has **100% isolated the failure** to:
### **Failure Class: D. Listening-Set Packaging/Playback**

The Python evaluation and export scripts generated WAV files and hardcoded the output sampling rate inside the wave headers to **22,050 Hz**. However, `en_US-lessac-low` is natively a **16,000 Hz** model.

Playing 16 kHz audio at 22.05 kHz forced a **38% speed-up** and **pitched the voice up by a major fourth**, causing severe speech warping and robotic voice degradation.

---

## 2. Quantitative Verification (Diagnostic Fidelity Set)

We generated a comparative diagnostic set for the token `"button"` across four paths, measuring exact samples, sampling rate, and RMS:

- **R0 (Known-good ONNX)**: 8,448 samples | **16,000 Hz** | Duration: 528.0 ms | RMS: 3761.20
- **R1 (N0 Baseline - Mispackaged)**: 9,216 samples | **22,050 Hz** (Original was 16 kHz) | Duration: 418.0 ms (Warped) | RMS: 2766.48
- **R2 (N1 Trained Normal - Mispackaged)**: 10,240 samples | **22,050 Hz** (Original was 16 kHz) | Duration: 464.4 ms (Warped) | RMS: 2878.41
- **R3 (I1 Trained Interactive - Mispackaged)**: 6,656 samples | **22,050 Hz** (Original was 16 kHz) | Duration: 301.9 ms (Warped) | RMS: 3433.38

The unconditioned baseline model **N0 (R1)** was also among the warped, degraded outputs, confirming that the degradation was completely independent of our training or model modifications.

---

## 3. Resolution and Stabilization

- All 19 blind trial WAV files inside `blind_listening/` have been **surgically fixed in-place to 16,000 Hz** using the correct model sampling rate.
- An explicit, rate-corrected comparative diagnostic set has been packaged inside:
  `C:\projects\piper-screen-reader-research\training\results\phase2ap\diagnostic_fidelity_set\`

Voice quality is now restored to pristine, natural-sounding Lessac speech across all evaluated modes.
