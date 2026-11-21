# Idea Fidelity Report: ProvGuard

Source of truth: `Idea_02_ProvGuard/idea.pdf` (compiled from `idea.tex`, 2026-10-03). The PDF text was extracted and checked against `idea.tex`; they are identical in content. Everything below is extracted from that document. Nothing here is added by the writing agent except where marked "(derived)".

## 1. Exact title / working title

ProvGuard: Origin-Labeled Perception and Causal Action Attribution for Mobile GUI Agents.

## 2. Core research field

Mobile systems security. Specifically: Android OS mechanisms for the integrity of actions taken by LLM/VLM-driven GUI agents against indirect prompt injection delivered through the screen (accessibility tree and pixels). Primary venue in the PDF: ACM MobiSys 2027. Alternative venues named: NDSS, USENIX Security, IEEE S&P, MobiCom.

## 3. Core technical keywords

- mobile GUI agent, VLM/LLM agent, accessibility tree, screenshot, Android
- origin label, provenance record, perceivability bit, window type, owning package UID, WebView document origin, notification sender, SDK Runtime surface, overlay
- indirect prompt injection, environmental injection, UI desynchronization, hidden / low-contrast nodes, action rebinding, foreground change in the observe-to-act gap
- causal attribution, masked re-execution (MELON-style), region-level attention attribution (cheaper approximation)
- dispatch-time binding, window token, node id, input dispatcher, accessibility action path
- integrity policy, label lattice, sink list / protected actions, no LLM judge in the trusted path
- information-flow control (IFC), taint tracking (as the family the property is weaker than)

## 4. System model entities

Trusted:
- system_server components: WindowManager, AccessibilityManagerService, NotificationManager, SurfaceFlinger
- the ProvGuard enforcement module (Label Service, Causal Gate, Dispatch Binder)

Untrusted:
- the agent and its model (VLM/LLM, possibly an on-device SLM)
- all third-party apps; web content in WebViews; ad SDKs (Privacy Sandbox SDK Runtime); notification senders; repackaged apps

Other entities:
- the user (task issuer; endorser of flagged actions)
- Perception Adapter middleware shipped with the agent SDK
- open-source agents under test: Mobile-Agent-v3, DroidRun, AutoGLM / Open-AutoGLM, UI-TARS

## 5. Main mathematical objects

- Provenance record per accessibility node and per screenshot tile: (owning package UID, window type, WebView document origin, notification sender and sensitivity class, perceivability bit)
- Perceivability bit computed by the compositor: occluded, off-screen, below-contrast, non-rendered
- A small label lattice: {user, system, installed-app-first-party, web, ad/SDK, notification-untrusted}
- A sink list of protected actions: send, pay, install, grant permission, delete, share
- The causal dependency set of a protected action (which observed regions the action causally depends on)
- Masked re-execution: re-run the agent's last decision step with untrusted-labeled regions masked; action persists -> attributed to user task; action disappears -> attributed to untrusted content
- Observe-to-act window: (window token, node id) observed vs. current target at dispatch
- Integrity property (stated as "precise, weaker-than-IFC but checkable"): no protected action is executed whose causal dependency set includes untrusted-origin or user-invisible content, unless the user endorses it; actions always target the window and node that were observed
- Stochastic-model caveat: masked re-execution may be unstable; repeated trials and a confidence rule are needed

## 6. Proposed algorithm name

ProvGuard (system name). Component names: Label Service, Perception Adapter, Causal Gate, Dispatch Binder. The attribution test is "masked re-execution adapted to GUI steps" (MELON-style). No separate algorithm acronym is given in the PDF; the manuscript keeps "ProvGuard" and the four component names.

## 7. Theorem names and directions

The PDF states no theorem by name. It states one target property and several directions that a theory section must formalize (derived from the Threat Model, Core Idea, Novelty Boundary, and Potential Risks sections):

- T-direction 1 (integrity / soundness of the gate): under the trust assumptions, no protected action whose causal dependency set includes untrusted-origin or user-invisible content is dispatched without user endorsement.
- T-direction 2 (dispatch binding closes the observe-to-act rebinding window): an action is dispatched only to the (window token, node id) that was observed; a foreground change between observation and action is rejected.
- T-direction 3 (masked re-execution as a causal test): characterize when "action persists under masking" is a valid test of causal dependence, including the stochastic-model case ("repeated trials and a confidence rule").
- T-direction 4 (the property is weaker than IFC but checkable): state precisely what is and is not guaranteed relative to classical IFC / taint tracking (CaMeL-style fixed control flow does not apply because GUI control flow is content-dependent).
- T-direction 5 (cost): masked re-execution doubles model calls on protected actions only; characterize the gate overhead.

The PDF does not claim optimality, sharpness, matching lower bounds, or "first" results (it explicitly says novelty "requires further literature verification"). The manuscript must not introduce such claims.

## 8. Experiment plan

- Platform: AOSP on Pixel devices; attacks reproduced from public repositories (AgentHazard AWAttackerApplier, MobileWorldSafety, GhostEI-Bench)
- Agents: Mobile-Agent-v3, DroidRun, AutoGLM / Open-AutoGLM, UI-TARS, with and without ProvGuard's labeled perception
- Attacks: in-app third-party content; ads via SDK Runtime and WebView; notifications; hidden / low-contrast nodes; repackaged-app desync; foreground rebinding; adaptive paraphrased payloads
- Metrics: attack success rate per channel; false block rate on benign tasks; task success (AndroidWorld, AndroidLab); per-action gate latency; re-execution token cost
- Ablations: labels only; gate only; binding only; perceivability bit on/off; cheap attribution vs. masked re-execution
- Killer experiment: labels only (no OS gate) on two open-source agents vs. AgentHazard and the arXiv 2510.27140 channel attacks; then add the causal gate. Thesis confirmed if labels alone move ASR by < 10 points but the gate removes most remaining attacks at < 10% false blocks.
- Benign-utility study: task success and latency with labels and gating enabled

## 9. Baseline methods

- No defense
- Spotlighting-style delimiting in the prompt
- MobileWorldSafety's defensive system prompt
- Agent-side taint (AOHP-like) without OS labels
- OS-Sentinel post-hoc detection

## 10. Seed references (as given in the PDF)

Attack / measurement:
- "Not an A11y" (arXiv 2608.08939)
- MobileWorldSafety (arXiv 2608.17659)
- UI Desynchronization (arXiv 2609.16732)
- AgentHazard (MobiSys 2026), AWAttackerApplier
- arXiv 2510.27140 (channel attacks; unnamed in PDF)
- Zero-Permission Manipulation (arXiv 2601.12349)
- PUSV (arXiv 2604.18860)
- Visual Confused Deputy (arXiv 2603.14707)
- GhostEI-Bench

Defense / IFC / provenance:
- Aura (arXiv 2602.10915)
- AOHP, Android Open Harness Project (arXiv 2606.23449)
- CaMeL (SaTML 2026)
- FIDES (arXiv 2505.23643)
- Permissive IFC for LLMs (TMLR 2025)
- NeuroTaint (arXiv 2604.23374)
- FlowSeal (arXiv 2609.14003)
- APPA (arXiv 2607.24625)
- MELON (ICML 2025)
- ACE (NDSS 2026), IsolateGPT (NDSS 2025)
- OS-Sentinel (arXiv 2510.24411), MATE (arXiv 2609.22724)
- Spotlighting (prompt delimiting baseline)

Classic systems:
- TaintDroid (OSDI 2010), CamFlow, Cloak and Dagger (S&P 2017), overlay malware at scale (MobiSys 2019)

Benchmarks / agents:
- AndroidWorld, AndroidLab, Mobile-Agent-v3, DroidRun, AutoGLM / Open-AutoGLM, UI-TARS

Platform facts referenced:
- Android Privacy Sandbox SDK Runtime; Android 15 sensitive-notification classification; `isAccessibilityTool`; Google AppFunctions

All of these must be resolved to real metadata before use (see `citation_search_log.md`). Several are arXiv IDs in the 2601 to 2609 range; each must be checked to exist and to match the stated title.

## 11. Explicit risks or assumptions

- Label explosion and over-blocking: most screens mix origins; a protected action may legitimately depend on third-party text (e.g., a product name); endorsement UX must be measured
- Masked re-execution may be unstable on stochastic models; need repeated trials and a confidence rule
- Collision risk: Aura with a real implementation, or an AppFunctions-era design that bypasses GUI entirely
- WebView origin granularity may be too coarse (document-level, not per node)
- Perceivability bit requires compositor-side occlusion and contrast computation (hardest piece)
- Reviewers may ask "why not abandon GUI for AppFunctions"; answer with coverage data
- Attacker cannot compromise system_server or the agent's own process memory
- Novelty of the masked re-execution adaptation requires further literature verification (MELON authors may extend to GUI)

## 12. What the paper is NOT about

- Not about cloud/tool-calling agents with discrete labeled tool outputs (that is CaMeL/FIDES/ACE territory; the PDF says removing the phone reduces the problem to ordinary IFC, which is already solved)
- Not about confidentiality of outgoing sensitive data as the headline (that is AOHP's focus); the headline asset is action integrity, with cross-app confidentiality secondary
- Not about training or fine-tuning a safer model; no OS-side LLM judge in the trusted path
- Not about hardware support (explicitly "no hardware support needed")
- Not about full IFC / non-interference; the property is explicitly "weaker than IFC but checkable"
- Not about federated learning, differential privacy, wireless channels, mechanism design, incentives, or any other neighboring topic
- Not a measurement-only paper (unless the killer experiment shows labels alone suffice, in which case the PDF says the paper shrinks to a measurement contribution)
- Not about post-hoc trajectory auditing as the mechanism (OS-Sentinel, MATE are baselines, not the method)

---

# LOCKED PAPER SPECIFICATION

## Locked topic

OS-level provenance (origin and perceivability) labeling of everything a mobile GUI agent perceives on Android, combined with a judge-free causal attribution gate (masked re-execution of the agent's decision step) and dispatch-time target binding, to prevent protected actions that causally depend on untrusted-origin or user-invisible screen content.

## Locked problem statement

Can the Android OS attach an origin and perceivability label to every UI region an agent observes (owning package, window type, WebView origin, notification sender, SDK Runtime process, overlay status, user-visible or hidden), carry that label through the agent's decision, and refuse any protected action whose causal dependency set includes untrusted-origin or user-invisible content, without an LLM judge in the trusted path, while also guaranteeing that actions target the window and node that were observed?

## Locked method family

ProvGuard, an Android framework mechanism with four components:
1. Label Service (AccessibilityManagerService, WindowManager, SurfaceFlinger hooks): provenance records and perceivability bits per node and per screenshot tile
2. Perception Adapter (agent-SDK middleware): labeled trees and tiles in a standard format; unlabeled fallback for legacy agents
3. Causal Gate (system service): intercepts protected actions; masked re-execution via sandboxed callback into the agent's own model; cheap attention-based approximation as an evaluated alternative; policy over a small label lattice and sink list
4. Dispatch Binder (input dispatch and accessibility action path): verifies window token and node id at dispatch

## Locked theoretical goals

- Formal definitions: provenance record, label lattice and join, perceivability, protected action (sink), causal dependency set, masked re-execution test, observe-to-act consistency
- Gate soundness theorem: under stated trust assumptions and a stated model of the agent's decision function, any protected action dispatched without endorsement has a causal dependency set free of untrusted-origin and user-invisible regions (relative to the masked re-execution oracle); state precisely what the oracle can and cannot detect
- Dispatch-binding theorem: rebinding attacks that change the foreground window or node between observation and dispatch are rejected
- Stochastic re-execution analysis: a repeated-trial confidence rule with a bound on the probability of misattribution under a stated model
- Label monotonicity / join lemma over the lattice; perceivability composition lemma
- Explicit comparison statement: the property is weaker than non-interference; state the gap (e.g., implicit flows the gate does not test)
- Complexity: label computation per frame, gate cost in model calls and tokens, binding check cost
- All results honestly labeled; no "optimal", "sharp", "matching", "first" claims

## Locked experiment family

- Platform: AOSP on Pixel; attack suites: AgentHazard (AWAttackerApplier), MobileWorldSafety, GhostEI-Bench, Not-an-A11y nine vectors, UI Desynchronization, arXiv 2510.27140 channel attacks, action rebinding, adaptive paraphrased payloads
- Agents: Mobile-Agent-v3, DroidRun, AutoGLM / Open-AutoGLM, UI-TARS
- Benign utility: AndroidWorld, AndroidLab
- Metrics: per-channel ASR, false block rate, task success, gate latency, re-execution token cost
- Ablations: labels only; gate only; binding only; perceivability bit on/off; cheap attribution vs. masked re-execution
- Killer experiment as stated in the PDF
- All results are placeholders until experiments are run; clearly labeled

## Locked baseline family

No defense; Spotlighting-style prompt delimiting; MobileWorldSafety defensive system prompt; agent-side taint without OS labels (AOHP-like); OS-Sentinel post-hoc detection.

## Terms that must appear in title / abstract / introduction

ProvGuard; origin label (or origin-labeled); perceivability; causal attribution (or causal action attribution); mobile GUI agent; Android; accessibility tree; screenshot; indirect prompt injection; masked re-execution; dispatch-time binding; protected action; window token; no LLM judge in the trusted path (or equivalent phrasing); AgentHazard / MobileWorldSafety / Not-an-A11y as the motivating attack literature.

## Terms that must not dominate the paper unless they appear in the idea PDF

Federated learning; differential privacy; over-the-air computation; Byzantine robustness; mechanism design / incentives / auctions; blockchain / ledger; convergence rate; wireless channel; cloud tool-calling agents as the primary setting; model fine-tuning as the defense; hardware enclaves / TEE as the mechanism; non-interference as the claimed property; AppFunctions as the proposed solution (it appears only as a reviewer objection to be answered with coverage data).

## Venue / format note (derived)

The idea PDF targets ACM MobiSys 2027 (12-page ACM format). The user's instruction for this task is an Elsevier-style ~45-page manuscript (`elsarticle`, preprint, 12pt). The manuscript is therefore written as an extended journal-style version of the same idea, with the understanding that a MobiSys submission would be a compressed version. This is recorded in `TODO_before_submission.md`.
