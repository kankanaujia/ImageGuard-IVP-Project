# CASIA v2.0 evaluation

Images evaluated: 12614 (authentic: 7491, copy-move: 3274, splicing: 1849)
Pipeline errors: 0

Processing time per image: mean 0.670s, median 0.600s, p95 1.179s

| Score | AUC (all) | AUC (JPEG only) | Best threshold | TPR | FPR |
|---|---|---|---|---|---|
| ORB consistent matches | 0.602 | 0.550 | 4 | 0.298 | 0.106 |
| ORB raw matches | 0.632 | 0.577 | 9 | 0.382 | 0.186 |
| ELA peak difference | 0.890 | 0.890 | 21 | 0.876 | 0.174 |
| Noise tile variance ratio | 0.430 | 0.427 | 5.96e+05 | 0.001 | 0.000 |
| Noise residual std | 0.486 | 0.483 | 4.67 | 0.837 | 0.828 |
| ELA heat map: strongest block | 0.580 | 0.574 | 3.55 | 0.751 | 0.517 |
| ELA heat map: unusual share | 0.556 | 0.543 | 0.0005 | 0.755 | 0.525 |
| Noise heat map: strongest block | 0.507 | 0.506 | 2.79 | 0.671 | 0.638 |
| Noise heat map: unusual share | 0.494 | 0.496 | 0.0005 | 0.460 | 0.453 |

App decision rule (copy-move group >= 5 consistent matches and copy >= 40 px from source): accuracy 0.656, precision 0.764, recall 0.223, FPR 0.047, F1 0.345
Confusion: TP 1142, FP 353, FN 3981, TN 7138

| Tamper type | Recall | Precision | FPR | ORB AUC | ELA AUC |
|---|---|---|---|---|---|
| copy-move | 0.321 | 0.749 | 0.047 | 0.660 | 0.876 |
| splicing | 0.049 | 0.205 | 0.047 | 0.499 | 0.915 |

| Format | Authentic | Tampered |
|---|---|---|
| bmp | 54 | 0 |
| jpg | 7437 | 2064 |
| tif | 0 | 3059 |
