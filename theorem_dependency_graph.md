# Theorem Dependency Graph

Rendered as Figure 6 in the manuscript (`figures/tikz_theory_diagram.tex`).

```
Assumptions
  A1 TCB integrity           ─┬─> Thm 1, Thm 2, Thm 3, Cor 3, Thm 4
  A2 complete mediation      ─┼─> Thm 1, Thm 2, Thm 3, Thm 4
  A3 one-sided label error   ─┼─> Lemma 2 ─> Thm 1 (part 2) ─> Thm 4
  A4 task authenticity       ─┼─> Thm 4
  A5 callback fidelity       ─┼─> Thm 1 (det.), Thm 2 (stoch.)
  A6 atomic check/delivery   ─┼─> Thm 3
  A7 framework node check    ─┴─> Thm 3 (ii), Thm 4

Lemmas
  Lemma A.1 Chernoff, Lemma A.2 Pinsker-type ─> Thm 2 ─> Cor 2 ─> Table 5, Fig 7
  Lemma 1 (lattice, monotonicity) ─> Lemma 2
  Lemma 3 (projection reveals only geometry of S) ─> Cor 1; residual channel G3

Theorems -> corollaries
  Thm 1 ─> Cor 1 (step-local NI for gated actions)
  Thm 2 ─> Cor 2 (number of trials)
  Thm 3 ─> Cor 3 (rebinding rejected)
  Thm 1 + Thm 2 + Thm 3 ─> Thm 4 (end-to-end)
  Thm 4 limits ─> Prop 1 (separation; residual channel G2)
  Props 2-3 (overhead) stand alone

Results -> experiments (Section 8)
  Thm 1, Cor 1  ─> RQ1 (security per channel), RQ3 (label quality tests A3)
  Thm 2, Cor 2  ─> RQ4 (trusted-support distributions, choice of k, θ)
  Thm 3, Cor 3  ─> RQ2 (binding, rebinding)
  Prop 1, G1-G3 ─> RQ5 (adaptive attacks)
  Props 2-3     ─> RQ6 (latency, tokens)
  all mechanisms ─> RQ7 (ablations)
```

No cycles. Every theorem's hypotheses are stated before it in Section 7.
