# Phase 2AC — architecture decision after the MB-MelGAN rejection

## Disposition

Phase 2AB is closed as a product failure and an engineering success. Multi-Band MelGAN achieved approximately 14.25 ms median FastSpeech2 vocoding, versus approximately 106.87 ms for HiFi-GAN, and approximately 64.5 ms projected complete FastSpeech2 generation including previously measured miscellaneous overhead. Automatic PCM validation passed. The user then reported that the tested blind samples sounded terrible. The exact FastSpeech2/aggressive-duration/mel-remap/MB-MelGAN configuration is rejected and must not enter NVDA.

Phase 2S remains the accepted production baseline. The Piper repository is unchanged.

## Consolidated comparison

| Approach | Quality | Character duration | Generation latency | CPU / memory | NVDA suitability | Failure reason |
| --- | --- | ---: | ---: | --- | --- | --- |
| Phase 2S Piper adaptive cached characters | User-accepted natural Piper voice and faster onset | Physical completion remains long enough to saturate sustained echo | Piper character onset was materially improved; cache misses remain expensive | Existing practical baseline | Accepted baseline | Sustained serial playback saturates after several rapid events |
| Phase 2Z FastSpeech2 aggressive + HiFi-GAN | Acoustic quality not isolated by blind acceptance | Useful median 143 ms; p95 328 ms; longest ~401 ms | Acoustic 20.9 ms; HiFi-GAN 139.1 ms; complete ~189 ms | HiFi-GAN peak process working set ~476 MiB | No | Vocoder latency and long tail fail the automatic gate |
| Phase 2AA Matcha global 0.5 + HiFi-GAN | Neural quality not promoted | Useful median 119.5 ms; p95 194 ms | Flow 122.2 ms; vocoder 171.9 ms; complete ~306 ms | Peak process working set ~506 MiB | No | Flow and vocoder latency remain too high |
| Phase 2AB FastSpeech2 + MB-MelGAN | User reported all tested samples sounded terrible | Same frozen acoustic durations | MB-MelGAN 14.25 ms; projected complete ~64.5 ms | ~96% of one CPU core; peak ~438 MiB | Rejected | Perceptual quality failure in the exact remapped configuration |
| FARGAN | Not evaluated perceptually | Not applicable | Not benchmarked | Codec-style stateful CPU vocoder | No drop-in path | Requires Bark cepstra/pitch conditioning, not the frozen mels |
| LPCNet | Not evaluated perceptually | Not applicable | Not benchmarked | Codec-style stateful CPU vocoder | No drop-in path | Requires LPCNet feature conditioning and an acoustic adapter |
| Sonata standard/RT reference | Source research found character waveforms still roughly half a second | ~500 ms class | Architecture improved general responsiveness, not this cached-character duration | Separate Rust/gRPC process | Not directly transferable | No special character inventory/path solving this bottleneck |
| Phase 2T/2U/2V playback experiments | Phase 2T slower; Phase 2U silent in real NVDA; Phase 2V not accepted | Physical serialization remained | Nonblocking ownership/cancellation contracts failed or regressed | Not production | No | Scheduler/player changes violated responsiveness or NVDA completion semantics |

## Final interactive latency budget

| Stage | Evidence/status | Classification |
| --- | --- | --- |
| Input event → NVDA speech-manager admission | Track A priority/cancellation experiments did not materially improve delivery; serialization remains possible | NVDA architectural constraint / unresolved |
| Speech manager → driver admission | Phase 2S cache path is bounded and already operational | Sufficient on cache hits |
| Cache lookup / immutable PCM reference | No worker, inference, or disk work on accepted cache hits | Sufficiently fast |
| Cache miss → complete PCM | Piper, FastSpeech2+HiFi-GAN, and Matcha+HiFi-GAN measurements show 189–306 ms class paths | Measurable bottleneck |
| First PCM / first audible energy | Existing direct Piper measurements showed roughly 65 ms first sustained-energy delay; adaptive onset shaping improved eligible waveform onset by roughly 26–44 ms | Physical/audio-path constraint plus measurable shaping opportunity |
| Useful spoken information | Depends on the unit's consonant attack and waveform duration, not just inference time | Product-critical unresolved |
| Waveform completion / next serial unit | Phase 2T evidence showed complete waveform drain serializes character playback and causes burst saturation | Physical playback constraint |

The rejected MB-MelGAN result proves that optimizing a 15 ms vocoder stage cannot compensate for unacceptable acoustic quality. It also proves that inference is not the only abstraction to optimize.

## Finite-vocabulary feasibility

A pre-generated inventory is quantitatively practical in storage. Using the locked FastSpeech2 character-unit median duration only as an illustrative lower-bound estimate for 22.05 kHz mono 16-bit PCM:

| Inventory | Assets | Approximate raw PCM |
| --- | ---: | ---: |
| letters + digits | 51 | 0.44 MiB |
| plus punctuation | 66 | 0.56 MiB |
| plus UI words/states | 78 | 0.67 MiB |
| plus ten navigation phrases | 88 | 0.75 MiB |
| plus additional states/phonetic variants | 110 | 0.94 MiB |

Two languages remain under roughly 2 MiB at this illustrative duration, before variants. Memory-mapped lookup or an in-memory table can make lookup effectively sub-millisecond; installation-time generation cost is paid once and voice/language changes regenerate the inventory. Compressed PCM could reduce disk size, but no compression ratio is assumed here.

This does not prove the inventory solves playback: Phase 2S Piper units can be substantially longer than the illustrative FastSpeech2 units. The inventory must therefore pass a direct useful-duration gate and a real playback-burst test. Its advantages are eliminating inference latency, preserving exact offline-generated speaker identity, and bounding the interactive vocabulary without an unbounded queue.

## Concise interactive pronunciation

Generating intentionally concise neural units is plausible in principle, but no accepted evidence currently supports it. Phase 2Y's global `length_scale=0.4` candidate was rejected by the user, and arbitrary waveform shortening, overlap, and scheduler interruption were rejected or unsafe. A future inventory experiment must generate concise pronunciations linguistically, not time-compress normal speech, and must preserve initial/final consonants and punctuation intelligibility.

## Decision: GO, one experiment only

One credible architecture remains: an offline-generated, finite interactive neural inventory using the selected Piper speaker, while unrestricted words, documents, and Read All remain on Phase 2S Piper. This is a proposal only; it is not started in Phase 2AC.

The single next experiment, if authorized, should be:

**Hypothesis:** pre-generated concise interactive units can remove inference latency and keep useful units short enough for sustained character feedback without changing speaker identity or ordinary reading.

**Architecture:** generate a bounded inventory at voice-install time; cache immutable PCM assets locally; use it only for letters, digits, punctuation, common control/state labels, and fixed navigation phrases; route unrestricted speech to Phase 2S.

**Expected latency:** lookup and admission below 1 ms; first audible energy governed by the existing audio path; no worker inference on inventory hits.

**Acceptance thresholds:** common units median useful duration ≤220 ms and p95 ≤300 ms initially; no clipped attacks; 36/36 blind identification twice; no objectionable artifacts; immediate recovery after 20–30 event bursts; bounded inventory and no stale multi-second backlog; ordinary Phase 2S reading unchanged.

**Fast falsification:** generate only the 51 letter/digit units plus punctuation, measure useful duration and direct playback, and perform the blind intelligibility test before adding UI vocabulary. If the duration or quality gate fails, stop without building an NVDA integration.

No model download, NVDA change, Piper change, or add-on work is justified before that bounded proposal is explicitly authorized.

## Approaches no longer justified

Do not repeat generic vocoder substitutions without matching acoustic feature distributions; global duration scaling; arbitrary waveform truncation/time compression; repeated FIFO/deadline/interruption schedulers; dedicated players that report premature NVDA completion; broad Rust/gRPC rewrites without a measured cached-character benefit; or another large model sweep without a new quality/latency hypothesis.

This Phase 2AC documentation is local-only and unpushed.
