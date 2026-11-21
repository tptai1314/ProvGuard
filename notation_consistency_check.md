# Notation Consistency Check

Notation is defined in `sections/macros.tex` and summarized in Table 3 of the manuscript.

## Conflicts found and fixed

| Symbol | Conflict | Fix |
|---|---|---|
| `λ` | label function vs. MGF parameter in the Chernoff proof | MGF parameter renamed `ζ` (Lemma A.1) |
| `S` | region set in Lemma 3 / masking vs. binomial sum in Theorem 2 proof | binomial sum renamed `Z` |
| `r` | provenance record `𝗋(ρ)` vs. rectangles per region in Prop. 3 | rectangles renamed `b` |
| `c` | content `𝖼(ρ)` and `c_min` vs. calls per step in Prop. 2 | calls renamed `μ`, `μ'` |
| `𝟙` | `\mathbb{1}` unavailable (rendered wrongly in a figure) | `\ind` defined as `\mathbf{1}` |

## Remaining overloads (intentional, documented)

- `W` (display width, Section 6.1) vs. `𝒲` (window set): different fonts, both local.
- `T` (task) vs. `T_o`, `T_a` (observation and action times, only in prose about Qian et al.): context-distinct.
- `π` (fraction of protected steps) vs. `Π` (projection): different symbols.

## All symbols in theorem statements are defined before use

| Symbol | Defined in |
|---|---|
| `ρ, ℛ_t, 𝖼, 𝗀` | Def. 1 |
| `𝗋(ρ)`, `uid, wtype, org, snd, sens, perc` | Def. 2, Eq. (1) |
| `φ_on, φ_vis, c_min, α_min, α^occ_max` | Def. 3 |
| `ℒ, ⊑, ⊔`, label names | Def. 4 |
| `Λ, λ` | Def. 5 |
| `a=(op,tgt,arg)`, resolved target | Def. 6 |
| `≈_c, ≈_s` | Def. 7 |
| `ξ_t` | Def. 8 |
| `f` | Def. 9 |
| `prot, Σ, κ` | Def. 10 |
| `U_t(a)` | Def. 11, Eq. (3) |
| `𝖬_S, Π_S, ◇` | Def. 12, Eq. (4) |
| `q_t(a)` | Def. 14 |
| `k, θ` | Alg. 2, Table 3 |
| `τ, ν, γ, β` | Section 5.4, Table 3 |
| `D(x‖y)` | Theorem 2 statement |
| `π, μ, μ'` | Prop. 2, Table 3 |
| `n_t, m_t, N_t, b, P_t` | Section 6.1, Prop. 3, Table 3 |

## Labels and references

- `latexmk` build: no undefined references, no multiply defined labels, no `??` in the PDF text.
- Theorem variables match the system model: the transcript, labels, and bindings in Section 7 are exactly the objects produced by Algorithms 1 to 3.
- No undefined constants in final theorem statements; all thresholds are inputs (`θ, q_0, q_1, δ`).
