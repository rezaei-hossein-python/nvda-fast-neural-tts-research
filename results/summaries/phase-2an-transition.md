# Phase 2AN — strategic transition to learned conditioning

Date: 2026-08-10

## Context

The Piper inference-only duration branch (Phase 2AD–2AM) is complete in
[`piper-screen-reader-research`](https://github.com/rezaei-hossein-python/piper-screen-reader-research).

## Evidence summary

| Finding | Implication |
|---|---|
| ONNX duration override works | Technical foundation established |
| A5 ~18% median reduction | Material but insufficient alone |
| Stable item-dependent preference (2AL) | Quality is structural, not random |
| No structural selector (2AM Outcome C) | Fixed inference policies rejected |

## Decision

Stop stronger inference heuristics. Investigate **learned interactive-mode
conditioning** in Piper/VITS training/fine-tuning.

## Production impact

**None.** Phase 2S remains baseline in the NVDA Piper add-on.

## Next bounded work

See piper-screen-reader-research `training/screen-reader-conditioned-piper-architecture.md`.

Outcome A: public Lessac-low checkpoint + dp-only mode embedding design; execute
minimal fine-tune only in a future GPU-authorized phase.
