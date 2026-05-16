# Eval Report -- Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.433**
- Median per-turn latency: 18.71s
- Worst per-turn latency: 31.30s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 1.00 | 8 | 3 | 7.2s |
| C10 | 3 | 0.50 | 8 | 2 | 8.0s |
| C2 | 3 | 0.20 | 8 | 5 | 25.1s |
| C3 | 5 | 0.50 | 8 | 4 | 24.8s |
| C4 | 3 | 0.60 | 8 | 5 | 22.0s |
| C5 | 3 | 0.00 | 1 | 5 | 23.2s |
| C6 | 3 | 0.50 | 8 | 2 | 19.1s |
| C7 | 4 | 0.20 | 8 | 5 | 18.0s |
| C8 | 3 | 0.40 | 7 | 5 | 10.1s |
| C9 | 7 | 0.43 | 8 | 7 | 29.7s |