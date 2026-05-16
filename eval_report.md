# Eval Report -- Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.369**
- Median per-turn latency: 19.18s
- Worst per-turn latency: 44.69s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 1.00 | 8 | 3 | 12.4s |
| C10 | 3 | 0.50 | 8 | 2 | 28.1s |
| C2 | 3 | 0.00 | 1 | 5 | 10.3s |
| C3 | 5 | 0.50 | 8 | 4 | 22.6s |
| C4 | 3 | 0.60 | 8 | 5 | 18.6s |
| C5 | 3 | 0.40 | 8 | 5 | 15.3s |
| C6 | 3 | 0.00 | 8 | 2 | 22.6s |
| C7 | 4 | 0.40 | 8 | 5 | 27.1s |
| C8 | 3 | 0.00 | 2 | 5 | 12.8s |
| C9 | 2 | 0.29 | 8 | 7 | 21.9s |