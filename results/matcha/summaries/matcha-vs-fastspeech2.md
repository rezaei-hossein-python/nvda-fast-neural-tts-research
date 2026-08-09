# Matcha-TTS versus Phase 2Z FastSpeech2

CPU-only, four PyTorch intra-op threads. Matcha baseline uses official
LJSpeech defaults (`length_scale=0.95`, 10 ODE steps, temperature 0.667) and
the official recommended HiFi-GAN plus denoiser. Global 0.5 is the only
duration experiment reached before the latency stop gate.

| Metric | FastSpeech2 best | Matcha baseline | Matcha global 0.5 | Matcha selective |
|---|---:|---:|---:|---:|
| Median useful duration | 143.17 ms | 292.81 ms | 119.50 ms | Not reached |
| P95 useful duration | 328.42 ms | 432.31 ms | 194.22 ms | Not reached |
| Longest character | 400.73 ms | 543.85 ms | 234.51 ms | Not reached |
| Median leading silence | 19.14 ms | 19.59 ms | 18.05 ms | Not reached |
| Max leading silence | 135.92 ms | 107.07 ms | 73.79 ms | Not reached |
| Acoustic latency | 20.90 ms | 150.49 ms flow | 122.24 ms flow | Not reached |
| Vocoder latency | 139.03 ms | 324.40 ms | 171.89 ms | Not reached |
| Complete PCM | ~189 ms | 484.42 ms | 306.14 ms | Not reached |
| RAM | ~1.03 GB | 0.75 GB steady | 0.75 GB shared run | Not reached |

Matcha global scaling passes the requested duration distribution automatically,
but computation is more than twice the 150 ms hard ceiling. Its best observed
global complete-PCM sample was 225.46 ms. Both the flow decoder and vocoder
individually exceed the 70--80 ms diagnostic threshold. Therefore selective
duration work cannot make this official CPU stack pass the latency gate.

## Gate decision

Reject Matcha and stop. The bounded experiment ended before selective patches,
cancellation, WASAPI, or blind listening. FastSpeech2 is not a winner: its tail
and compute failures remain. Matcha improves duration tails under global 0.5
but is materially slower on this CPU.

