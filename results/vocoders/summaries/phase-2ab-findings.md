# Phase 2AB findings

Phase 2AB isolated vocoder cost by freezing the Phase 2Z FastSpeech2 aggressive and Phase 2AA Matcha global-0.5 acoustic outputs. The current HiFi-GAN control failed the required 70 ms median / 100 ms p95 gate. Official FARGAN and LPCNet were eliminated as substitutions because their Bark-cepstral and pitch conditioning is not supplied by either acoustic model; benchmarking them would require training a new adapter.

The single justified fourth candidate, official LJSpeech Multi-Band MelGAN v2 from ParallelWaveGAN, passed automatically. At one CPU thread its FastSpeech2-input result was 14.25 ms median and 19.83 ms p95; Matcha-input result was 13.33 ms and 19.57 ms. Adapter overhead was approximately 0.062 ms median. A fixed 0.85 output gain prevented PCM conversion clipping without changing duration. The candidate recovered deterministically for 100/100 alternating requests.

The result is promising but provisional. Its 0-8000 Hz natural-log to 80-7600 Hz log10 mel adapter is mathematically bounded but approximate. Blind comparison against HiFi-GAN is mandatory before the vocoder can be recommended for any later model-stack experiment.

The main NVDA Piper repository remained frozen at Phase 2S. No NVDA integration, add-on, scheduling change, or production backend was created.

## Phase 2AB final disposition

The extended blind test was stopped after the user reported that all tested samples sounded terrible. This is a failed perceptual acceptance gate. The exact tested configuration was FastSpeech2 aggressive selective mels, a deterministic 0–8000 Hz natural-log to 80–7600 Hz log10 mel remap, official LJSpeech Multi-Band MelGAN v2, and the documented 0.85 PCM headroom. It does not establish that Multi-Band MelGAN is universally poor.

Engineering result: approximately 14 ms median CPU vocoding and approximately 65 ms projected complete generation were demonstrated. Product result: the generated speech was unacceptable for intelligibility, naturalness, consonant detail, speaker identity, and/or artifact tolerance. No NVDA or Piper integration is justified. The listening exercise was stopped without scoring the remaining pairs.

The failure cannot be isolated to the vocoder from this A/B result alone. The tested output combines four possible contributors: FastSpeech2 acoustic quality, aggressive duration compression, mel-domain remapping, and MB-MelGAN inference. HiFi-GAN was the control, but the user rejected the tested output rather than identifying one component in isolation. The exact attribution remains unknown.
