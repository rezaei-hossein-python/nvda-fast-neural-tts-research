# Matcha-TTS architecture audit

## Pinned implementation

Official `shivammehta25/Matcha-TTS`, stable tag `v0.0.7`, commit
`77804265f877b0c42f13cfdece6541dde7838090`, MIT source license.

## Inference chain

`english_cleaners2` converts text to IPA using a persistent eSpeak backend.
The symbol sequence is interspersed with blank token zero. `TextEncoder`
produces token acoustic means (`mu_x`), predicted log durations (`logw`), and
the input mask. `MatchaTTS.synthesise` exponentiates `logw`, applies the global
`length_scale`, rounds up, and calls `generate_path` to create a monotonic
token/frame alignment. That alignment expands `mu_x` to frame length. The CFM
decoder integrates the conditional flow for the selected ODE step count and
returns a normalized mel. The official LJSpeech path denormalizes the mel and
uses the recommended Tacotron2-finetuned HiFi-GAN V1 plus its bias denoiser to
produce 22,050 Hz PCM.

## Duration questions

1. Predicted token durations are exposed indirectly as `exp(logw)` and directly
   in the returned alignment sums after rounding/scaling.
2. They can be extracted during inference from the encoder output.
3. The public inference API cannot accept arbitrary token durations.
4. The smallest defensible intervention would be between `w = exp(logw) * mask`
   and `generate_path`, replacing only `w_ceil` with a validated tensor.
5. Official `length_scale` multiplies every predicted duration uniformly.
6. The official ONNX graph exposes temperature and global length scale only;
   it does not expose token-duration input or output.
7. Duration can technically be altered without retraining because the flow
   decoder consumes the expanded `mu_y`, but this needs a research wrapper.
8. A small package-excluded wrapper/patch is feasible.
9. Such a wrapper would preserve the encoder, `generate_path`, conditioning,
   CFM solver, temperature, speaker state, and vocoder semantics.
10. Official LJSpeech inference uses HiFi-GAN V1 fine-tuned on Tacotron2. In
    measured CPU inference it was a major latency contributor.

## Runtime controls and ownership

- CLI default: 10 ODE steps, temperature 0.667, LJSpeech speaking rate 0.95.
- ONNX exporter default: 5 ODE steps; its graph may embed the same vocoder.
- ONNX exposes only `[temperature, length_scale]` scales.
- Training can consume precomputed durations for loss/alignment, but this is
  distinct from the public synthesis API.

## Research compatibility shim

The stable source requires a Cython monotonic-alignment extension used by the
training `forward` method. MSVC is unavailable on this machine. The isolated
inference harness registers a fail-closed placeholder: any training/MAS call
raises immediately. `synthesise` does not call MAS. Upstream remains clean.

## Persian feasibility (deferred)

Matcha supports custom datasets and custom symbol/front-end definitions. A
credible ManaTTS path would require Persian normalization, a Persian-aware
phoneme inventory and G2P (including ZWNJ and mixed-script policy), compatible
text symbols, dataset file lists, mel statistics, and full Matcha training.
Monotonic alignments are learned through MAS or may be precomputed after a
model exists. A Persian-compatible vocoder should be trained or validated for
the target recording domain. Deployment would include a distinct acoustic
checkpoint, front end, and likely vocoder; no Persian acquisition or training
was attempted here.

