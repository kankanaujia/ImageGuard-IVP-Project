# CASIA v2.0 evaluation

Images evaluated: 12614 (authentic: 7491, copy-move: 3274, splicing: 1849)
Pipeline errors: 0

Processing time per image: mean 0.441s, median 0.421s, p95 0.696s

| Score | AUC (all) | AUC (JPEG only) | Best threshold | TPR | FPR |
|---|---|---|---|---|---|
| ORB consistent matches | 0.624 | 0.571 | 4 | 0.301 | 0.107 |
| ORB raw matches | 0.636 | 0.578 | 10 | 0.406 | 0.200 |
| ELA peak difference | 0.890 | 0.890 | 21 | 0.876 | 0.174 |
| Noise tile variance ratio | 0.430 | 0.427 | 1.69 | 1.000 | 0.999 |
| Noise residual std | 0.485 | 0.483 | 4.68 | 0.836 | 0.829 |

App decision rule (ORB consistent matches >= 4): accuracy 0.652, precision 0.658, recall 0.301, FPR 0.107, F1 0.413
Confusion: TP 1541, FP 802, FN 3582, TN 6689

| Tamper type | Recall | Precision | FPR | ORB AUC | ELA AUC |
|---|---|---|---|---|---|
| copy-move | 0.412 | 0.627 | 0.107 | 0.687 | 0.876 |
| splicing | 0.104 | 0.193 | 0.107 | 0.512 | 0.915 |

| Format | Authentic | Tampered |
|---|---|---|
| bmp | 54 | 0 |
| jpg | 7437 | 2064 |
| tif | 0 | 3059 |
