# Local Real-Video Sample & Sparse Verification Workspace

- **`real_sample_1m.mp4`**: Lossless stream-copied (`-c copy`) ~66.67s keyframe-aligned slice (`[0.0, 66.666667]` across 8 IDR GOPs) extracted non-destructively from the local test recording (source file preserved intact outside the repository).
- Large media binaries (`samples/*.mp4`, `samples/*.wav`) and generated run artifacts (`samples/results/`) are excluded via `.gitignore` so Git history stays lightweight.
- Run the industrial sparse configuration matrix anytime via:

```powershell
.\.venv\Scripts\python.exe scripts\run_sparse_sample_matrix.py
```

- Run pytest including real-sample industrial checks (auto-skipped only when `real_sample_1m.mp4` is absent):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ --cov=autosilenttrimmer -v
```
