# Claim Strength Audit

Search terms: first, optimal, sharp, tight, matching, exact, no efficiency loss, state-of-the-art, superior, universal, guarantee, provable, prevent, eliminate, always, never.

| Phrase / claim | Location | Verdict | Action |
|---|---|---|---|
| "first" | nowhere in the manuscript as a novelty claim (appears only in quotes such as "first unsafe step" and Sec. 6 algorithm prose) | n/a | Novelty stated as "to the best of our knowledge, within the literature verified for this manuscript" (Sec. 2.7), with an explicit TODO for a collision check |
| "optimal", "sharp", "tight", "matching" | absent | n/a | none |
| "exact" | "computed exactly from Eq. (5)" (Table 5, Fig. 7) | justified: values are exact binomial tails computed by script | kept |
| "state-of-the-art", "superior" | absent | n/a | none |
| "Provable" | only when quoting MELON's title and describing what it means | justified | kept with explanation |
| "strictly between taint tracking and non-interference" | Prop. 1 title and intro C4 (first draft) | too strong: no total order was proven | weakened to "separation from taint tracking and from trajectory-level non-interference" |
| "non-interference" for ProvGuard | Cor. 1 | qualified as "step-local", "for gated actions", "with equal clearance" | kept with qualifiers |
| "no LLM judge in the trusted path" | abstract, intro, design | justified by construction of Alg. 2 (deterministic comparison) | kept |
| "dispatch binding closes the rebinding window" | intro, design | weakened in Thm 3: window-level binding is in system_server; node-level depends on Assumption 7 | node-level claim made conditional |
| "Real Android" for ProvGuard in Table 1 | first draft had a checkmark | too strong: not implemented | changed to "partial, planned" with footnote |
| Any experimental number for ProvGuard | none | n/a | All result tables empty and labeled; conceptual plots carry no numeric axes and a PLACEHOLDER tag |
| "labels never depend on what a region says" | Sec. 3.2 | justified for all fields except the optional developer annotation, which can only raise a label (stated) | kept |
| MobileWorldSafety "names source labeling as future work" | idea document | unsupported | removed |
| UI desync "deployed apps" | idea document | inaccurate | reworded to repackaged APKs of 13 open-source apps |
| "the thesis holds if labels alone move ASR by < 10 points ..." | intro, Sec. 8.7 | stated as a falsifiable hypothesis, with the alternative outcome described | kept |
| MELON "would flag benign navigation" | Sec. 9 (first draft) | speculative | weakened to "could also flag" |
