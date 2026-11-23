# CASIA v2.0 pixel-level localisation

Images evaluated: 4964; skipped: {'mask size differs from image': 17}

| Images | Method | Pixel AUC | F1 | IoU |
|---|---|---|---|---|
| all (4964) | ELA heat map | 0.793 | 0.185 | 0.127 |
| all | Noise heat map | 0.494 | 0.028 | 0.019 |
| all | Copy-move regions (flagged 22.2%) | - | 0.075 | 0.048 |
| all | Baseline: whole image | 0.500 | 0.140 | - |
| copy-move (3205) | ELA heat map | 0.824 | 0.163 | 0.112 |
| copy-move | Noise heat map | 0.473 | 0.018 | 0.011 |
| copy-move | Copy-move regions (flagged 32.1%) | - | 0.114 | 0.074 |
| copy-move | Baseline: whole image | 0.500 | 0.106 | - |
| splicing (1759) | ELA heat map | 0.738 | 0.225 | 0.155 |
| splicing | Noise heat map | 0.531 | 0.047 | 0.033 |
| splicing | Copy-move regions (flagged 4.1%) | - | 0.003 | 0.002 |
| splicing | Baseline: whole image | 0.500 | 0.203 | - |
