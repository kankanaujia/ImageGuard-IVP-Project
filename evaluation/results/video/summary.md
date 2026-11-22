# Synthetic video benchmark

| Edit | Clips | Expected check | Detected (expected check) | Detected (any check) | scene · repeat · motion |
|---|---|---|---|---|---|
| insertion | 15 | scene | 14/15 | 15/15 | 14 · 10 · 13 |
| freeze | 15 | repeat | 15/15 | 15/15 | 0 · 15 · 5 |
| deletion | 15 | motion | 14/15 | 14/15 | 0 · 12 · 14 |

False alarms on clean clips:

| Check | Clips with any flag | Flags per minute |
|---|---|---|
| scene | 0/15 | 0.00 |
| repeat | 15/15 | 25.24 |
| motion | 5/15 | 4.02 |
| any | 15/15 | — |

Processing time per clip: mean 2.44s, max 3.12s; clips with errors: 0
