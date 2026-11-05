# Benchmarks

Old version (previous release) against the current one. Median of 3 runs, headless Qt (offscreen), Python 3.12, a 20,000 line Python file, 11 tabs open, `pylsp` installed. Absolute numbers depend on the machine, so compare the ratios.

| Metric | Old | New | Change |
| --- | --- | --- | --- |
| Startup (ms) | 153 | 139 | 1.1x faster |
| Open a 20k line file (ms) | 2262 | 1393 | 1.6x faster |
| Re-highlight 20k lines (ms) | 5534 | 1505 | 3.7x faster |
| Open 10 more tabs (ms) | 331 | 157 | 2.1x faster |
| Memory with 11 tabs (MB, app + children) | 592 | 101 | 5.9x less |
| Child processes | 3 | 1 | language servers start on demand |
| Typing latency, average (ms) | 13.7 | 3.3 | 4.2x faster |
| Typing latency, 95th percentile (ms) | 44.1 | 6.0 | 7.4x faster |

Where the gains come from:
- Highlighting tracks token positions instead of searching the line for each token, and files are no longer highlighted twice on open.
- Language servers start on the first Ctrl+Space instead of at file open, and the full text is sent then, not on every keystroke.
- All editors share one background event loop.
- Extensions are discovered at startup but only imported when an activation event fires.
