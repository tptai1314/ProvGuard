# Reviewer-Style Self-Audit

**Locked topic.** OS-level origin and perceivability labels for everything a mobile GUI agent perceives on Android, a judge-free causal gate based on masked re-execution, and dispatch-time binding to observed window and node.

**Matches idea.pdf?** Yes (see `topic_alignment_check.md`; one TODO: MATE citation).

## Contributions and evidence

| Contribution | What is new | Why prior work does not solve it | Evidence in this manuscript | Boundary references |
|---|---|---|---|---|
| C1 OS-computed labels | provenance attached by the OS to a11y nodes and screenshot tiles, including compositor perceivability | a11y window object has no owner; node flags are app-side; prior mobile designs simulate (Aura) or protect confidentiality (AOHP) | design (Sec. 5.1), Lemma 1-2; label accuracy is RQ3, not yet measured | android_accessibilitywindowinfo, android_accessibilitynodeinfo, zou2026aura, zhao2026aohp, yan2019overlay |
| C2 causal gate without LLM judge | masked re-execution of GUI steps on untrusted regions selected by OS labels | MELON masks the user prompt in tool agents; CaMeL/ACE fix control flow, impossible for GUI; NeuroTaint and OS-Sentinel use LLM/VLM judges | Thm 1, Cor 1, Thm 2, Table 5 (analytical); efficacy is RQ1/RQ4, not yet measured | zhu2025melon, debenedetti2025camel, li2026ace, cai2026neurotaint, sun2026ossentinel |
| C3 dispatch binding | binding to window token, owner, node digest under the dispatch lock | GUI agents lack binding (Qian et al.); PUSV compares pixels on desktop | Thm 3, Cor 3; RQ2 | qian2026zeropermission, xu2026pusv |
| C4 formal property | trusted sufficiency, with explicit gaps G1-G7 and a separation result | prior agent IFC either fixes control flow or claims NI for tool agents | Sec. 7, App. A (complete proofs within the model) | costa2025fides, goguen1982noninterference |
| C5 evaluation methodology | protocol over four agents and six suites with decisive experiment | n/a | Sec. 8; placeholders only | suites as cited |

## Likely reviewer objections and current answers

1. **"There is no implementation or evaluation."** Correct. This is the dominant weakness for MobiSys, where working implementations are expected. The manuscript states it in the abstract, Sec. 6.2, Sec. 8, and Sec. 10. It cannot be submitted to a systems venue in this state.
2. **"In-app third-party content (AgentHazard's main channel) is labeled as the app's own."** Acknowledged as G1; mitigations are developer annotation and lower clearance; expected to be the most informative measurement (H3).
3. **"Re-execution doubles cost and latency."** Only on protected actions (Prop. 2); measured in RQ6. Reviewers will want numbers.
4. **"The agent can lie in the callback."** Out of scope (malicious developer); Assumption 5 is checkable for on-device models.
5. **"History steering defeats it."** Prop. 1(b) concedes this formally; `grant`/`install` clearance of `sys` reduces it; RQ5.
6. **"Why not AppFunctions?"** Discussion gives the argument and a planned coverage measurement.
7. **"Sink rules are incomplete."** Stated as scope; sink coverage is a metric.
8. **"Novelty versus concurrent work."** The area moved fast in Aug-Sep 2026 (Not an A11y, UI desync, FlowSeal, APPA, MATE). A fresh collision check is required, especially for any GUI adaptation of MELON by its authors (risk named in the idea).
9. **"Perceivability is not per-user."** Acknowledged in Limitations.
10. **"Theorem 1 is close to definitional."** True by design: the contribution is making the property precise and checkable and stating exactly what it excludes. The non-trivial parts are the projection construction (no agent memory), the over-approximation lemma, the stochastic bounds, and the separation result.

## Overclaiming risks (checked)

See `claim_strength_audit.md`. No "first", "optimal", "state-of-the-art" claims; Table 1 marks ProvGuard's Android implementation as planned.

## Status

| Item | Status |
|---|---|
| TikZ/figure readability | 9 figures, all PASS after rendering and inspection (`figure_quality_audit.md`) |
| LaTeX compilation | `latexmk -pdf main.tex` succeeds; 51 pages; no undefined references or citations; 3 overfull boxes under 3.4pt; font-shape substitution warnings for bold small caps (cosmetic) |
| Citation verification | 90 cited references, all verified; 1 claim marked `[Citation needed]`; 1 seed unverifiable (MATE) |
| Proofs | all results have complete proofs within the model; no proof sketches remain |
| Experiments | none run; all result tables empty; conceptual plots labeled |

## Verdict as a reviewer would see it today

Strong problem framing, precise threat model, and a careful, honest formal core; well-positioned against verified prior work. Not acceptable at MobiSys until the AOSP prototype exists and the decisive experiment plus RQ1, RQ2, RQ6 are run. The paper should not be described as submission-ready.
