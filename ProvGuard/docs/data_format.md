# Data format

No dataset is downloaded automatically. All external material must be provisioned manually
under the path configured as `data.root`.

## Normalized directory

```text
<data.root>/
  trials.jsonl
  transcripts/                 # optional full per-trial transcript files
  artifacts/                   # optional screenshots, trees, and device logs
  provenance.json              # recommended source URLs, versions, hashes, licenses
```

Each `trials.jsonl` row must contain:

- `trial_id`: unique string;
- `suite`: AgentHazard, MobileWorldSafety, GhostEI-Bench, Not-an-A11y, UI-desync,
  channel-attacks, action-rebinding, AndroidWorld, AndroidLab, or an explicit new suite;
- `channel`: paper Table 6 channel name;
- `trial_type`: `attack` or `benign`;
- `ground_truth_protected`: boolean;
- `protected`: whether the sink classifier fired;
- `gate_decision`: `pass` or `escalate`;
- `dispatch_status`: `delivered`, `reobserve`, or `dropped`;
- `adversarial_success`: boolean, according to the suite's native success checker;
- `task_completed`: boolean, according to the suite's native benign checker;
- `endorsed`: boolean;
- recommended: agent, configuration, seed, repetition, labels, perceivability truth,
  callback samples, latency, token counts, model/checkpoint digest, device build fingerprint.

## Observation and transcript schema

The in-memory schema is defined in `provguard.schemas`. Each region includes kind, content,
bounds/z-order/interaction flags, provenance `(uid,wtype,org,snd,sens,perc)`, integrity
label, and optional binding `(window_token,node_id,digest,owner_uid)`. Pixel tiles should
refer to local artifact hashes rather than embedding large images in JSONL.

## Suite provisioning

The paper lists the following external suites: AgentHazard, MobileWorldSafety,
GhostEI-Bench, Not-an-A11y A1-A9, UI desynchronization, ad/WebView/notification channel
attacks, and action rebinding. Benign workloads are AndroidWorld and AndroidLab. Obtain
each artifact from its publisher, accept any license/registration terms, pin a version, and
normalize its native results. If an artifact is not public, do not substitute another suite;
record it as unavailable.

