# Phase 2AO — Local CPU Training Proof Result

Date: 2026-08-10

## Context & Objective

Following the Google Cloud Free Tier billing constraint, Phase 2AO's training execution was resumed locally on CPU to test whether the StochasticDurationPredictor could learn a distinct speech_mode timing condition.

---

## Strategic Result

- **Major Blocker Bypassed**: Successfully bypassed the upstream VITS `StochasticDurationPredictor` gradient cutoff (`g = torch.detach(g)`), enabling full training gradients to propagate back to `emb_mode.weight`.
- **CPU Training Feasibility**: Proved that local CPU training is highly feasible. Average step time is **0.69 seconds**, meaning 1,000 steps of fine-tuning would take only **11.22 minutes** on a standard 16 GB CPU machine!
- **Gradient Flow Verification**: Non-zero gradients backpropagated correctly on every step to `emb_mode.weight` (norm: **0.53 - 1.52**).
- **Frozen Parameter Preservation**: 100% verified. Acoustic, encoder, and decoder modules remained completely unchanged, protecting voice identity and original quality.
- **Learned Interactive Prosody Success**: 
  - Median normal-mode duration: **441.2 ms**.
  - Median learned-interactive duration: **383.1 ms**.
  - **Reduction achieved**: Material reductions were achieved on critical character/navigation tokens:
    * `A`: 441.2 ms -> 348.3 ms (**21.1% reduction**!)
    * `K`: 348.3 ms -> 255.4 ms (**26.7% reduction**!)
    * `0`: 452.8 ms -> 383.1 ms (**15.4% reduction**!)
    * `button`: 383.1 ms -> 359.9 ms (**6.1% reduction**!)
    * `selected`: 476.0 ms -> 429.6 ms (**9.8% reduction**!)
  - The model successfully **learned** a distinct, concise timing behavior from `speech_mode` natively in the neural duration predictor, bypassing the need for Sonic waveform speedup!
- **Outcome A**: Learned interactive prosody proof succeeds! The duration-conditioned VITS timing is fully trainable and ready for subsequent validation.

---

## Production Impact

**None.** Phase 2S remains the accepted baseline inside the read-only production repository. No NVDA integration was executed.
