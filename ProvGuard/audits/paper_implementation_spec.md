# Paper implementation specification

## Identity and central task

- **Title:** *ProvGuard: Origin-Labeled Perception and Causal Action Attribution for
  Mobile GUI Agents*
- **Status stated by the paper:** design, formal analysis, and evaluation plan; no AOSP
  implementation or empirical measurements yet; all empirical results are placeholders.
- **Central task:** prevent attacker-controlled or user-imperceptible GUI content from
  causing protected mobile-agent actions without user endorsement, while binding actions to
  the observed target.
- **Method:** ProvGuard, comprising the Label Service, Perception Adapter, Causal Gate,
  Dispatch Binder, and SystemUI endorsement path.

## Formal data structures

- Region: accessibility node or fixed-grid screenshot tile; content is separated from
  geometry and interaction flags (Definition 1).
- Provenance record `r=(uid,wtype,org,snd,sens,perc)` (Eq. 1).
- Seven-label integrity lattice `usr <= sys <= app <= {web,sdk,ntf} <= unt`, with the
  three channel labels incomparable (Definition 4).
- Observation, action triple `(op,tgt,arg)`, resolved target, control/strict equivalence,
  OS-held transcript `(T,a_<t,o_<=t)`, decision function, sink/clearance, untrusted set,
  trusted projection, support probability, binding `(tau,nu,gamma,uid)`.

## Algorithms and equations to implement

1. P1-P4 perceivability: on-screen fraction, unoccluded fraction using combined opacity,
   WCAG contrast ratio, rendered area/effective alpha (Definition 3).
2. Default labeling policy and screenshot-tile join (Eq. 2).
3. Action target resolution and control/strict equivalence.
4. Untrusted set (Eq. 3) and content-only masking/trusted projection (Eq. 4).
5. Algorithm 1 Label Service (reference semantics; Android collectors are external).
6. Algorithm 2 Causal Gate: protected classification, optional high-attribution early
   escalation, masked stateless re-execution, empirical support, pass/escalate.
7. Algorithm 3 Dispatch Binder: token/owner/top-touchable/node-digest checks.
8. Algorithm 4 composition with user endorsement and re-observation.
9. Deterministic trusted-sufficiency condition (Eq. 5).
10. Exact stochastic pass probability (Eq. 6), Bernoulli KL/Chernoff/Hoeffding bounds,
    sufficient and exact minimum trial counts.
11. ASR, FBR, and TSR (Eqs. 7-9); Wilson intervals and exact McNemar test.
12. Complexity/overhead formulae are documented/audited; model-call accounting is exposed
    through run records rather than claimed as measured performance.

## Inputs and outputs

Inputs are labeled observations, authentic task, dispatched action history, proposed action,
policy/sink configuration, callback samples, and live-window/node state. Outputs are labels
and bindings, gate pass/escalate decision with evidence, endorsement status, dispatch or
reobserve status, normalized per-trial logs, aggregate metrics, and plots derived from logs.

## Default policy and settings

- Protected sinks: send, pay, install, grant, delete, share, type-untrusted.
- Default clearances: `sys` for grant/install; `app` for share/send/pay/delete/type-untrusted.
- Table 7 defaults: sampled `k=5`, threshold 0.5, control equivalence, tile size 32,
  contrast 3.0, maximum occluding opacity 0.8, on-screen/visible fraction 0.5,
  minimum alpha 0.05. Greedy evaluation uses `k=1`.

## Metrics and statistical protocol

ASR per channel plus suite-native metrics; benign FBR and TSR with endorsement/denial;
endorsement rate; gate latency p50/p95; re-execution tokens; per-field label precision and
recall; perceivability precision/recall; binder false rejects; sink coverage; trusted-support
distributions. Attack cases are repeated at least five times; report 95% Wilson intervals and
paired McNemar tests. Final repetitions/seeds are paper placeholders.

## Baselines and ablations

- B0 released agent, no defense.
- B1 spotlighting-style delimiters based on the same OS labels.
- B2 defensive system prompt reconstructed only from its description because exact text is
  not published.
- B3 client-visible agent-side taint/no-write-down approximation.
- B4 OS-Sentinel external formal-verifier/VLM detector.
- PG-L labels only, PG-G gate only, PG-B binding only, PG-minus-perceivability,
  PG-attention-only, and full PG.

## Datasets, agents, and testbed

Agents: Mobile-Agent-v3/GUI-Owl, DroidRun/Mobilerun, Open-AutoGLM, UI-TARS. Attack
suites: AgentHazard, MobileWorldSafety, GhostEI-Bench, Not-an-A11y A1-A9, UI
desynchronization, channel attacks, action rebinding, and new adaptive G1-G3 variants.
Benign: AndroidWorld (116 tasks) and AndroidLab (138 tasks). Testbed: ProvGuard-patched
AOSP on unspecified Pixel devices, plus compatible emulator for AndroidWorld. Versions,
checkpoints, Pixel models, AOSP tag, kernel, paraphrase protocol, study size, and ethics
approval are placeholders.

## Assumptions

A1 trusted system_server/SurfaceFlinger/kernel and unforgeable/non-reassigned identities;
A2 complete mediation; A3 one-sided label/perceivability error; A4 authentic OS-recorded
task; A5 faithful independent stateless callback; A6 atomic dispatch check/enqueue and no
redirection; A7 target framework performs node identity/digest check.

## Limitations and uncovered channels

G1 app-drawn third-party content, G2 history steering through unprotected actions, G3
geometry retained by masking, G4 incomplete sink coverage, G5 remote callback fidelity,
G6 availability/escalation attacks, G7 stochastic tail. Also: top-level-only WebView origin,
approximate perceivability, incomplete app sink rules, node semantic changes without digest
changes, no malicious-agent/OS/side-channel defense, cost and endorsement burden.

## Conceptual/external/placeholder components

Actual AOSP services and patches; SurfaceFlinger sampling; SystemUI UI; agent bindings;
benchmark artifacts; model calls; attention rollout; human perceivability study; AppFunctions
coverage; energy; all paper Tables 8-9 and Figure 9 measurements. These are adapters/TODOs,
not synthetic substitutes.

