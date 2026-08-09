# Extended blind vocoder test

This is a vocoder-only comparison. Every pair uses the same locked Phase 2Z aggressive-selective FastSpeech2 mel tensor, then separate HiFi-GAN and Multi-Band MelGAN inference. The existing 0.85 MB-MelGAN PCM headroom policy is unchanged. No acoustic generation, NVDA scheduling, Piper code, or Phase 2S behavior is changed.

The user-facing set contains 71 pairs: 19 critical character names, 12 punctuation names, 12 UI phrases, 10 navigation phrases, 10 medium sentences, 5 long sentences, and 3 sustained passages. Pair-side assignment is randomized independently with seed `20260809`; the answer key is intentionally ignored and stored outside the listening directory.

Automatic validation checks each pair’s frozen-mel hash, 22050 Hz mono 16-bit WAV format, expected duration tolerance, finite nonempty PCM, no clipping, and no vocoder name in user-facing filenames. Long-speech timing is recorded separately as wall time, generated duration, and RTF; it is a vocoder stress diagnostic, not a claim that MB-MelGAN should replace Phase 2S for Read All.

The accepted short-character reference remains approximately 14.25 ms median MB-MelGAN vocoder time and 106.87 ms median HiFi-GAN control time. The extended character subset measured approximately 19.39 ms versus 171.20 ms respectively at one thread; the original locked 100-run benchmark remains authoritative for the headline latency claim.
