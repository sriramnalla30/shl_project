# Eval Report -- Markdown Trace Replay

- Server: `http://localhost:8000`
- Traces evaluated: **10**
- **Mean Recall@10: 0.450**
- Median per-turn latency: 0.27s
- Worst per-turn latency: 0.60s

## Per-trace

| trace | turns | recall@10 | recs | n_expected | median_lat |
|-------|-------|-----------|------|------------|------------|
| C1 | 4 | 0.67 | 8 | 3 | 0.4s |
| C10 | 3 | 0.50 | 8 | 2 | 0.3s |
| C2 | 3 | 0.40 | 8 | 5 | 0.2s |
| C3 | 5 | 0.75 | 8 | 4 | 0.2s |
| C4 | 3 | 0.40 | 8 | 5 | 0.2s |
| C5 | 3 | 0.40 | 8 | 5 | 0.2s |
| C6 | 3 | 0.50 | 8 | 2 | 0.3s |
| C7 | 4 | 0.20 | 8 | 5 | 0.2s |
| C8 | 3 | 0.40 | 8 | 5 | 0.3s |
| C9 | 7 | 0.29 | 8 | 7 | 0.3s |