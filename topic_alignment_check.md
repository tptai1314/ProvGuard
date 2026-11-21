# Topic Alignment Check

Compared against `idea_fidelity_report.md` (LOCKED PAPER SPECIFICATION) and `topic_signature.json`.

| Item | Idea PDF | Manuscript | Status |
|---|---|---|---|
| Title | "ProvGuard: Origin-Labeled Perception and Causal Action Attribution for Mobile GUI Agents" | identical | PASS |
| Field | mobile systems security; Android OS mechanism for GUI agents | same (Sections 1, 3, 5) | PASS |
| Keywords | origin label, perceivability, causal attribution, masked re-execution, dispatch binding, accessibility tree, screenshot, indirect prompt injection, protected action, no LLM judge | all appear in title/abstract/intro; keyword list contains 10 of them | PASS |
| System entities | system_server (WindowManager, AccessibilityManagerService, NotificationManager, SurfaceFlinger); Label Service, Perception Adapter, Causal Gate, Dispatch Binder; untrusted agent, apps, WebViews, ad SDKs, notification senders, repackaged apps | Section 3.1, 3.2, 5, Fig. 4 | PASS |
| Mathematical objects | provenance record; perceivability bit; lattice {user, system, app, web, ad/SDK, notification-untrusted}; sink list; causal dependency set; masked re-execution; window token and node id | Defs. 1-14, Eq. (1)-(5); lattice adds a top element `unt` needed for joins (derived, stated) | PASS (one derived addition, explained) |
| Algorithm | ProvGuard; Label Service, Perception Adapter, Causal Gate (MELON-style masked re-execution adapted to GUI steps; cheaper attention attribution as alternative), Dispatch Binder | Algorithms 1-4; attention used only for early escalation, attribution-only variant as ablation | PASS |
| Theorem directions | integrity of protected actions; binding closes observe-to-act window; stochastic confidence rule; weaker-than-IFC property; cost | Thm 1 + Cor 1; Thm 3 + Cor 3; Thm 2 + Cor 2 + Table 5; Prop. 1; Props. 2-3 | PASS |
| Experiment plan | AOSP on Pixel; AgentHazard (AWAttackerApplier), MobileWorldSafety, GhostEI-Bench, Not-an-A11y nine vectors, UI desync, 2510.27140 channel attacks, rebinding, adaptive paraphrase; Mobile-Agent-v3, DroidRun, AutoGLM/Open-AutoGLM, UI-TARS; metrics ASR per channel, false block rate, task success on AndroidWorld/AndroidLab, gate latency, token cost; ablations labels only, gate only, binding only, perceivability on/off, cheap attribution vs masked re-execution; killer experiment | Section 8 contains every item; killer experiment is the decisive experiment of Sec. 1 and 8.7 with the same thresholds (10 points, 10% false blocks) | PASS |
| Baselines | no defense; Spotlighting-style delimiting; MobileWorldSafety defensive prompt; AOHP-like agent-side taint; OS-Sentinel | B0-B4, same | PASS |
| Seed references | 30+ named works | all resolved; all cited except MATE (unverifiable author list, in citation_todo.md) | PASS with one TODO |
| Not about | cloud tool agents, fine-tuning defenses, OS-side LLM judge, hardware, non-interference claims, FL/DP/wireless/mechanism design | tool-agent IFC appears only as related work and contrast; fine-tuning only as complementary related work; NI only as what is NOT achieved; no FL/DP/wireless/mechanism-design content | PASS |

## Section-level checklist against `topic_signature.json`

| Section | Required objects present | Forbidden drift present |
|---|---|---|
| Abstract | ProvGuard, origin label, perceivability, masked re-execution, dispatch binding, window token, protected actions, agents, suites | none |
| 1 Introduction | all core terms; contributions mirror the idea's five contributions plus the formal property | none |
| 2 Related work | seed references organized around mobile GUI agent security | none |
| 3 System/threat model | trusted/untrusted split, attacker capabilities and limits, assets, goal exactly as the idea | none |
| 4 Formulation | record, perceivability, lattice, sinks, untrusted set, masking, causal dependence | none |
| 5-6 Design and algorithms | four components, policy, sink list | none |
| 7 Theory | theorem directions above | none |
| 8 Evaluation | full experiment plan, placeholders only | none |
| 9-11 | AppFunctions question, endorsement UX, WebView granularity, collision risk (all listed as risks in the idea) | none |

## Deviations from the idea, with reasons

1. Venue format: the idea targets MobiSys 2027 (12 pages); the user requested a ~45-page Elsevier manuscript. Recorded in Limitations and TODO.
2. Optional developer annotation for in-app third-party content (Section 5.1): not in the idea, added because the idea's own threat model lists in-app content and AgentHazard (a seed) asks for exactly this API. It can only raise labels.
3. Stochastic analysis made quantitative (Theorem 2, Table 5): the idea asks for "repeated trials and a confidence rule"; the theorem provides it.
4. MobileWorldSafety's "source labeling as future work" claim dropped (not supported by the paper).
