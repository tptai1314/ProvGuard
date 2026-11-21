# Implementation notes

## Scope

The manuscript specifies an Android OS mechanism but states that it has not been built.
This repository therefore separates two concerns:

1. `src/provguard/` is an executable reference model of Definitions 1-14, Equations
   (1)-(9), Algorithms 1-4, and the analytical results used by Table 5/Figure 7.
2. `aosp/`, agent adapters, and benchmark adapters identify the exact integration boundary
   that cannot be honestly implemented without a pinned AOSP checkout, devices, model
   artifacts, and benchmark licenses.

The reference model is useful for unit testing policy semantics, constructing normalized
logs, validating the gate's binomial calculations, and generating the paper's result tables
from real logs later. It does not establish Assumptions 1, 2, 5, 6, or 7 on Android.

## Paper-to-code choices

- A region keeps content separate from geometry so masking can preserve hit-testing.
- `IntegrityLabel` implements the exact partial order; `web`, `sdk`, and `ntf` are
  incomparable, and pairwise joins become `unt`.
- Unknown perceivability evidence fails closed (`perc=0`), as required by Section 5.1.
- Sink classification uses explicit system-sink metadata and configurable semantic-role
  rules. It never claims complete coverage for app-defined send/pay/delete controls.
- Callback exceptions count as non-equivalent trials, so the gate fails closed.
- `DispatchBinder` uses a Python lock to model Algorithm 3's atomic region. This is a
  reference behavior only; the theorem requires the actual WindowManager/input lock.
- Synthetic G1 content is deliberately app-labeled. Its residual success demonstrates the
  documented boundary instead of concealing it.

## Conceptual-only components

Attention-rollout early escalation is represented by an optional score/cutoff, but no
attention extractor is invented. SystemUI endorsement UI, Android isolated-process
callbacks, compositor sampling, real model prefix caching, and AppFunctions coverage are
external implementation/evaluation tasks.

