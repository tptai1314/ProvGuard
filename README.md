# ProvGuard: Origin-Labeled Perception and Causal Action Attribution for Mobile GUI Agents

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Manuscript](https://img.shields.io/badge/Paper-main.pdf-red.svg)](main.pdf)

This repository contains the research paper manuscript and reference implementation for **ProvGuard**, an Android framework mechanism defending Mobile GUI Agents against indirect prompt injection via OS-enforced provenance tracking, causal action attribution, and dispatch-time binding.

---

## 📌 Overview

Mobile GUI agents read the screen via the Android accessibility tree and screenshots, executing actions through simulated input events (taps, keystrokes). In current operating systems, untrusted content (e.g., banner ads, spam notifications, or invisible accessibility nodes) carries the same authority as legitimate user instructions. Consequently, indirect prompt injection can hijack agents to perform unauthorized actions (e.g., money transfers, permission grants, data exfiltration).

**ProvGuard** tackles this vulnerability through four OS-level primitives:
1. **Labeling Subsystem (LS):** Inside Android `system_server`, attaches provenance labels (package UID, window type, WebView origin, notification sender) and perceivability status (occlusion, contrast, off-screen clipping) to every accessibility node and screenshot tile.
2. **Perception Adapter (PA):** Exposes origin-labeled accessibility trees and screenshot tiles directly to agent perception pipelines.
3. **Causal Gate (CG):** Intercepts sensitive actions (send, pay, install, share) and evaluates causal attribution via **masked re-execution**—re-evaluating agent decisions with untrusted and imperceptible regions masked without relying on an external LLM judge.
4. **Dispatch-Time Binder (DB):** Atomically binds actions to the observed window token and node identity, preventing UI desynchronization and rebinding attacks.

---

## 📂 Repository Structure

```text
├── main.pdf                       # Compiled paper preprint (ready for committee review)
├── main.tex                       # Primary LaTeX manuscript (Elsevier elsarticle template)
├── sections/                      # Paper sections (Introduction, Methodology, Theory, etc.)
├── appendix/                      # Mathematical proofs and extended experimental protocols
├── figures/                       # Vector figures and TikZ / PGFPlots source files
├── figure_previews/               # Rendered figure previews
├── scripts/                       # Bibliographic and theoretical bound calculation utilities
│
├── ProvGuard/                     # Python Reference Implementation & Verification Suite
│   ├── src/provguard/             # Core mechanism: labeling, lattice, masking, gate, binder
│   ├── tests/                     # Unit and integration test suites (pytest)
│   ├── configs/                   # Configuration files (YAML)
│   ├── scripts/                   # Experiment runners and evaluation scripts
│   ├── docs/                      # Reproducibility guides and data specifications
│   ├── aosp/                      # AOSP integration architecture and framework patches
│   ├── pyproject.toml             # Python packaging specification
│   └── requirements.txt           # Python dependencies
│
└── citation_claim_map.csv         # Audit mapping between empirical claims and citations
```

---

## 🚀 Quick Start (Reproducibility)

The Python reference scaffold implements the formal semantics, integrity lattice, causal gate bounds, and synthetic attack-defense simulations. No GPU, external API keys, or Android device are required to verify the core algorithms.

### 1. Environment Setup

```bash
# Navigate to the reference implementation directory
cd ProvGuard

# Create and activate virtual environment
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Run Test Suite

```bash
pytest -v
```

### 3. Run Synthetic Mechanism Demo

```bash
python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml
```

The script evaluates ProvGuard against synthetic attack vectors (SDK ad surfaces, WebViews, spoofed notifications, overlays, and action rebinding) and outputs structured metric summaries to `outputs/synthetic_demo/`.

---

## 📑 Paper & Mathematical Formulations

- **Preprint PDF:** Read [main.pdf](main.pdf) for the complete theoretical framework, theorems, and experimental designs.
- **Analytical Bounds:** Run `python ProvGuard/scripts/gate_bounds.py --help` to compute Hoeffding and binomial tail bounds for stochastic agent re-execution trials (Theorem 2).
