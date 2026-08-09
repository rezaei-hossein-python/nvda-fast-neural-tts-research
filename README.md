# NVDA fast neural acoustic research

Isolated, CPU-only research evaluating whether explicit or model-native
duration controls can produce short, intelligible screen-reader acoustic
units. This repository does not contain or modify the NVDA Piper add-on.

Upstream source: `ming024/FastSpeech2` at
`d4e79eb52e8b01d24703b2dfc0385544092958f3` (MIT). Downloaded checkpoints,
virtual environments, raw measurements, and generated audio are intentionally
untracked. Reproducible identities are recorded in `locks/`.

Phase 2AA evaluates official Matcha-TTS `v0.0.7` at commit
`77804265f877b0c42f13cfdece6541dde7838090`. Its global duration control met
the acoustic-duration distribution but the official CPU pipeline failed the
complete-PCM latency gate, so selective patches and listening were not run.
