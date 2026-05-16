# Eval Report — Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.277**
- Median per-turn latency: 46.27s
- Worst per-turn latency: 53.38s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 0.33 | 5 | 3 | 50.9s |
| C10 | 3 | 0.50 | 5 | 2 | 44.1s |
| C2 | 3 | 0.20 | 5 | 5 | 49.2s |
| C3 | 5 | 0.25 | 5 | 4 | 47.5s |
| C4 | 3 | 0.40 | 5 | 5 | 50.8s |
| C5 | 3 | 0.40 | 5 | 5 | 49.9s |
| C6 | 3 | 0.00 | 5 | 2 | 48.1s |
| C7 | 4 | 0.20 | 5 | 5 | 50.1s |
| C8 | 3 | 0.20 | 4 | 5 | 20.7s |
| C9 | 7 | 0.29 | 5 | 7 | 51.4s |