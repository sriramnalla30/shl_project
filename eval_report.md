# Eval Report -- Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.350**
- Median per-turn latency: 42.52s
- Worst per-turn latency: 728.01s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 0.67 | 8 | 3 | 51.9s |
| C10 | 3 | 0.50 | 5 | 2 | 34.5s |
| C2 | 3 | 0.20 | 5 | 5 | 47.1s |
| C3 | 5 | 0.50 | 8 | 4 | 49.9s |
| C4 | 3 | 0.60 | 8 | 5 | 53.1s |
| C5 | 3 | 0.20 | 8 | 5 | 19.5s |
| C6 | 3 | 0.00 | 8 | 2 | 52.3s |
| C7 | 4 | 0.20 | 5 | 5 | 48.2s |
| C8 | 3 | 0.20 | 4 | 5 | 16.8s |
| C9 | 7 | 0.43 | 5 | 7 | 51.8s |