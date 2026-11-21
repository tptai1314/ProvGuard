# ProvGuard

Reference implementation and reproducibility scaffold for *ProvGuard: Origin-Labeled
Perception and Causal Action Attribution for Mobile GUI Agents*.

ProvGuard labels Android GUI regions by origin and perceivability, tests protected actions
by re-running the agent on a content-masked transcript, and binds dispatch to the observed
window and node. This repository implements the paper's formal semantics, analytical gate
bounds, metrics, synthetic mechanism tests, and external-integration contracts.

> **No paper-level experimental results are claimed by this repository unless real benchmark
> outputs are generated and their provenance is recorded.**

> **This repository does not automatically download datasets or run paper-level experiments.
> Real experiments are intended to be executed on EC2 after the required datasets,
> benchmarks, models, and credentials are manually provisioned.**

The manuscript itself says that ProvGuard has not yet been implemented on AOSP and that
all empirical results are placeholders. Accordingly, the runnable Python is a reference
model and analysis harness—not a substitute for the Android framework changes listed in
[`aosp/README.md`](aosp/README.md).

## Implemented

- Definitions 1-14: regions, provenance, P1-P4, the integrity lattice, actions,
  equivalence, transcripts, sinks, masking, causal support, and bindings.
- Equations (1)-(6): provenance representation, tile-label joins, untrusted sets, trusted
  projections, deterministic trusted support, and exact stochastic pass probability.
- Algorithms 1-4 as reference semantics: labeling, gating, binding, and composed steps.
- Theorem 2 calculations: exact binomial tails, KL/Chernoff and Hoeffding bounds, exact and
  sufficient trial counts (including the Table 5 `q0=.2, q1=.8, delta=.01` case).
- Equations (7)-(9): per-channel ASR, benign FBR, and TSR; plus Wilson intervals, exact
  McNemar, endorsement, latency, precision/recall, binder-reject, and sink-coverage helpers.
- B0 no defense; B1 delimiter transform; explicitly description-based B2 prompt; B3
  agent-side taint approximation. B4 OS-Sentinel is an honest external adapter stub.
- Synthetic cases for SDK surfaces, WebViews, notifications, overlays, imperceptible nodes,
  foreground rebinding, benign send, and the known G1 app-drawn-content gap.
- Config capture, hashes, seeds, normalized JSONL, aggregate JSON, and plots derived from
  result files.

## Install

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

No GPU, network, Android device, or external dataset is needed for tests and the synthetic
demo.

## Quick start

```bash
python -m provguard.cli --help
pytest -q
python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml
```

The demo writes `trials.jsonl`, `results.json`, `calibration.json`, `ablation.json`,
`run_metadata.json`, and `attack_success_by_channel.png` under
`outputs/synthetic_demo/`. Every artifact is labeled **synthetic smoke-test output, not a
paper result**, except calibration, which is labeled analytical rather than experimental.

Individual stages:

```bash
python scripts/run_experiment.py --config configs/synthetic_demo.yaml --stage calibrate
python scripts/run_experiment.py --config configs/synthetic_demo.yaml --stage evaluate
python scripts/run_experiment.py --config configs/synthetic_demo.yaml --stage ablate
python scripts/make_plots.py \
  --input outputs/synthetic_demo/results.json \
  --output outputs/synthetic_demo
python scripts/gate_bounds.py --q0 0.2 --q1 0.8 --theta 0.5 --delta 0.01
```

## Paper-to-code map

| Paper object | Code |
|---|---|
| Definitions 1, 2, 6, 8 | `schemas.py` |
| P1-P4 | `perceivability.py` |
| Definition 4 and Eq. 2 | `lattice.py`, `labeling.py` |
| Definition 7 | `actions.py` |
| Eqs. 3-4 | `masking.py` |
| Algorithm 2 / Defs. 13-14 | `gate.py` |
| Algorithm 3 | `binder.py` |
| Algorithm 4 | `pipeline.py` |
| Eq. 6 / Theorem 2 / Table 5 | `statistics.py`, `scripts/gate_bounds.py` |
| Eqs. 7-9 and Section 8.5 | `metrics.py` |
| Tables 6-7 integration | `adapters/`, `configs/` |

The exhaustive mapping is in
[`audits/paper_to_code_traceability.csv`](audits/paper_to_code_traceability.csv).

## Configuration

`configs/default.yaml` follows Table 7's design defaults. `synthetic_demo.yaml` is the
offline smoke test. `experiment_template.yaml` is an EC2 provisioning template with
deliberate `TODO_PIN_*` fields; it must not be used as publication provenance until all are
replaced.

The main fields are seed/repetitions/output path, synthetic versus real mode, local
`data.root`, gate trials/threshold/equivalence, and analytical `q0/q1/delta`. Configurations
never contain executable shell commands.

## Real-data workflow

Real AOSP/agent execution is external to this repository until the missing patches and
bindings are implemented. Do not download suites during tests. Manually provision and
normalize existing real logs according to [`docs/data_format.md`](docs/data_format.md), then:

```bash
python -m provguard.cli validate-data --root /mnt/provguard-data/normalized
python scripts/run_experiment.py \
  --config configs/experiment_template.yaml \
  --stage evaluate
```

This computes metrics from already-generated local logs. It does not launch devices,
agents, model APIs, or benchmarks. See
[`docs/ec2_experiment_guide.md`](docs/ec2_experiment_guide.md).

## Project structure

```text
ProvGuard/
  aosp/                  Android integration boundary; no fabricated patch
  audits/                specification, traceability, math/gap/result audits
  configs/               defaults, synthetic demo, EC2 template
  docs/                  formats, adapters, implementation and EC2 guides
  examples/              schema-only synthetic fixture
  outputs/               generated artifacts only
  scripts/               demo, stage, plotting, and bound entry points
  src/provguard/         reference model and experiment package
    adapters/            local benchmark and external agent contracts
    baselines/           B0-B4 implementations/wrappers
    experiments/         calibration/evaluation/ablation runners
  tests/                 offline deterministic unit and CLI tests
```

## Reproducibility and result integrity

Synthetic records are deterministic under a fixed seed; the run timestamp is not. Raw
records precede aggregate JSON, and plots read only aggregate files. Real runs must record
AOSP/build/patch hashes, device/kernel, agent/model/checkpoint identities, benchmark
versions/licenses, native success checkers, seeds, callback samples, and raw transcripts.
See [`docs/reproducibility.md`](docs/reproducibility.md) and
[`audits/result_integrity_audit.md`](audits/result_integrity_audit.md).

## Known gaps and limitations

The repository does not yet contain an AOSP patch, a Pixel build, agent/model artifacts,
external benchmark data, OS-Sentinel, a human perceivability study, attention extraction,
or paper-level measurements. The method itself does not cover G1 app-drawn third-party
content by default, G2 history steering, G3 geometry, missed sinks, dishonest remote
callbacks, availability attacks, or the stochastic tail. Top-level WebView labels do not
separate iframes, and app send/pay/delete rules are incomplete.

See [`audits/implementation_gaps.md`](audits/implementation_gaps.md) and
[`TODO_IMPLEMENTATION.md`](TODO_IMPLEMENTATION.md) for the exact remaining work.

## Documentation

- [`docs/implementation_notes.md`](docs/implementation_notes.md)
- [`docs/data_format.md`](docs/data_format.md)
- [`docs/baseline_adapters.md`](docs/baseline_adapters.md)
- [`docs/reproducibility.md`](docs/reproducibility.md)
- [`docs/ec2_experiment_guide.md`](docs/ec2_experiment_guide.md)

## Research-use notice

This is an unaudited research prototype. Do not treat the reference binder as an Android
security boundary, and do not deploy it to protect real payments, permissions, messages, or
data until the AOSP implementation and its assumptions have been independently reviewed.

