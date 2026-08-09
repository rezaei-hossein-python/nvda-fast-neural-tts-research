# Phase 2AB low-latency CPU vocoder comparison

## Scope and method

This experiment vocoded locked, pre-generated acoustic tensors. Acoustic-model work is excluded from vocoder timing. The corpus contains 63 items from each source: A-Z, 0-9, the fixed punctuation set, and fixed UI microphrases. A, E, S, 1, and 7 each received 20 measured warm runs (100 core runs per source/configuration) after five excluded warm-ups.

Facts, measurements, and projections are separated below. Raw arrays, PCM, WAV, and per-request JSON remain ignored.

## Compatibility findings

| Vocoder | Expected input | FastSpeech2 | Matcha | Adapter | Risk |
| --- | --- | --- | --- | --- | --- |
| HiFi-GAN control | 80-bin natural-log mel, 0-8000 Hz, 22.05 kHz, hop 256 | Direct | Direct | None | None |
| FARGAN | 18 Bark cepstra plus pitch period/correlation, 16 kHz, 10 ms frames | Incompatible | Incompatible | Would require a trained acoustic adapter | Standard mel does not encode the trained pitch/conditioning semantics |
| LPCNet | 18 Bark cepstra plus pitch period/correlation, 16 kHz, 10 ms frames | Incompatible | Incompatible | Would require a trained acoustic adapter | Same incompatibility; not a drop-in mel vocoder |
| Multi-Band MelGAN | 80-bin log10 mel, 80-7600 Hz, 22.05 kHz, hop 256, standardized | Approximate deterministic remap | Approximate deterministic remap | exp, filter-bank pseudoinverse/remap, log10, official mean/scale | Must pass blind quality testing |

FARGAN and LPCNet were not timed because doing so would require training a new feature adapter, outside this isolated substitution experiment. FARGAN processes 160 samples per 10 ms frame at 16 kHz, uses four 40-sample subframes, has recurrent state, and requires continuation/reset state. The Opus comments identify approximately 15 ms of vocoder lookahead in the related DRED path. LPCNet is likewise stateful and conditioned on codec features rather than mels.

## CPU timing

Primary figures use PyTorch's default 10 threads for HiFi-GAN and the measured best one-thread setting for Multi-Band MelGAN. Times are milliseconds over the 100 core warm runs.

| Metric | HiFi-GAN / FS2 | MB-MelGAN / FS2 | HiFi-GAN / Matcha | MB-MelGAN / Matcha |
| --- | ---: | ---: | ---: | ---: |
| compatible input | direct | approximate remap | direct | approximate remap |
| adapter median | 0.027 | 0.062 | 0.029 | 0.062 |
| warm median | 106.87 | 14.25 | 138.60 | 13.33 |
| p95 | 160.38 | 19.83 | 190.33 | 19.57 |
| minimum | 59.92 | 8.20 | 95.20 | 8.64 |
| maximum | 195.27 | 27.18 | 197.05 | 23.31 |
| process CPU (% of one core) | 953% | 96% | 963% | 97% |
| incremental working set | 227 MiB | 190 MiB | 258 MiB | 192 MiB |
| peak process working set | 476 MiB | 438 MiB | 506 MiB | 439 MiB |
| clipping after fixed PCM headroom | 0 | 0 | 0 | 0 |
| duration preserved | yes | yes | yes | yes |

The bounded 1/2/4/8/default thread matrix showed that MB-MelGAN is fastest and most stable at one thread. Its default-10-thread FS2 result was 22.85 ms median / 31.77 ms p95. HiFi-GAN failed the 70/100 ms gate at every setting; its best observed default result still failed p95.

The MB-MelGAN remap initially produced a maximum float peak of 1.17124. A fixed 0.85 PCM headroom gain was therefore applied after inference; it changes level, not duration, and eliminated conversion clipping across all 126 outputs. This choice is disclosed rather than treated as a model-quality fix.

## Combined projections

These are arithmetic projections, not integrated measurements:

| Stack | Acoustic median | Vocoder median | Acoustic + vocoder | Projected complete PCM with prior miscellaneous overhead |
| --- | ---: | ---: | ---: | ---: |
| FastSpeech2 aggressive + MB-MelGAN | 20.90 | 14.25 | 35.15 | approximately 64.5 |
| Matcha global 0.5 + MB-MelGAN | 122.24 | 13.33 | 135.57 | approximately 147.6 |

FastSpeech2 has the clear compute opportunity. Matcha only narrowly projects under 150 ms because its flow stage remains dominant.

## State, recovery, and validity

Multi-Band MelGAN's tested generator is feed-forward and holds no cross-utterance recurrent state. Alternating two locked clips for 100 cycles produced 100/100 finite, duration-correct, byte-deterministic recoveries without reset or reconstruction. Automatic checks found no NaN/Inf, malformed lengths, or clipping after headroom.

## Decision

Multi-Band MelGAN passes the Phase 2AB automatic latency, p95, recovery, and basic validity gates. It does not yet pass the phase's perceptual requirement. The frequency-domain adapter is approximate, and the model weights have no separately stated license. The generated blind comparison must determine whether intelligibility, fricatives/stops, and LJSpeech speaker identity survive.

No NVDA or Piper production integration occurred.
