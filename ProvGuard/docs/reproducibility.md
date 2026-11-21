# Reproducibility

Synthetic runs capture the configuration path/hash, seed, Python/platform versions, and an
explicit non-paper-result label. The same seed controls Python and NumPy.

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml
```

Generated files live under the configured output directory. `trials.jsonl` is the raw
normalized record; `results.json` is derived from it; plots are derived only from the JSON.
Delete and rerun the directory to reproduce it. The timestamp in `run_metadata.json` is
expected to differ; trial content and aggregate values should not.

For real runs, additionally capture the AOSP tag/patch hashes/build fingerprint, device and
kernel versions, agent commit/checkpoint/model digests, decoding parameters, benchmark
artifact hashes/licenses, seeds/repetitions, raw transcripts, all callback samples, and native
success-checker versions. A result without these fields is not publication provenance.

