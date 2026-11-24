# Evaluation (rules mode, 20 made-up cases)

## Auto-accepted items (not flagged for review)

| Category | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Dimensions | 1.00 | 1.00 | 1.00 | 9 | 0 | 0 |
| Material | 1.00 | 1.00 | 1.00 | 19 | 0 | 0 |
| Quantity | 1.00 | 0.94 | 0.97 | 15 | 0 | 1 |
| Timeline | 0.92 | 0.92 | 0.92 | 11 | 1 | 1 |
| Budget | 1.00 | 0.80 | 0.89 | 4 | 0 | 1 |
| Standards | 0.71 | 0.83 | 0.77 | 5 | 2 | 1 |
| **All (micro)** | **0.95** | **0.94** | **0.95** | 63 | 3 | 4 |

## All items (including flagged)

| Category | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Dimensions | 1.00 | 1.00 | 1.00 | 9 | 0 | 0 |
| Material | 1.00 | 1.00 | 1.00 | 19 | 0 | 0 |
| Quantity | 0.94 | 0.94 | 0.94 | 15 | 1 | 1 |
| Timeline | 0.85 | 0.92 | 0.88 | 11 | 2 | 1 |
| Budget | 0.83 | 1.00 | 0.91 | 5 | 1 | 0 |
| Standards | 0.71 | 0.83 | 0.77 | 5 | 2 | 1 |
| **All (micro)** | **0.91** | **0.96** | **0.93** | 64 | 6 | 3 |

Items flagged for review: 4 of 75.
