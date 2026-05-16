# Eval Report -- Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.434**
- Median per-turn latency: 18.65s
- Worst per-turn latency: 35.15s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 1.00 | 8 | 3 | 13.8s |
| C10 | 3 | 0.50 | 8 | 2 | 26.1s |
| C2 | 3 | 0.40 | 8 | 5 | 14.8s |
| C3 | 5 | 0.50 | 8 | 4 | 18.4s |
| C4 | 3 | 0.60 | 8 | 5 | 20.1s |
| C5 | 3 | 0.60 | 8 | 5 | 14.4s |
| C6 | 3 | 0.00 | 8 | 2 | 12.8s |
| C7 | 4 | 0.40 | 8 | 5 | 21.1s |
| C8 | 3 | 0.20 | 7 | 5 | 20.4s |
| C9 | 7 | 0.14 | 8 | 7 | 24.5s |