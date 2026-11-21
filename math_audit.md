# Math Audit

Scope: every lemma, theorem, proposition, and corollary in Section 7 and Appendix A. All proofs were re-read after the audit revisions listed at the end. "Complete" means complete within the abstract model of Section 4; whether an implementation realizes the model is captured by Assumptions 1, 2, 6, and 7 and is not a mathematical claim.

| Label | Statement (short) | Assumptions | Proof status | External theorem used | Possible gap | Dimensions / constants | Too strong? | Revision made |
|---|---|---|---|---|---|---|---|---|
| Lemma A.1 (Chernoff) | P[Bin(k,q) >= xk] <= exp(-k D(x‖q)) for x>q | independence of trials | complete (derived via MGF + Markov) | none (derived) | none | x,q in (0,1); D in nats | no | added to make App. A self-contained instead of citing an unverified reference |
| Lemma A.2 (Pinsker-type) | D(x‖y) >= 2(x-y)^2 | none | complete (calculus) | none | convention 0 ln 0 = 0 stated | dimensionless | no | added |
| Lemma 1 | lattice; tile join monotone; U monotone in labels, anti-monotone in perc | Def. 4, Def. 5 | complete | none | needed a catch-all rule for totality of Λ0 | n/a | no | catch-all `unt` rule added to Def. 5 |
| Lemma 2 | U* ⊆ U | A3 | complete | none | A3 is relative to the producing process (stated) | n/a | no | none |
| Lemma 3 | projection depends on S only via geometry | Def. 12 | complete | none | requires identical region sets across transcripts (stated) | n/a | no | geometry channel made explicit in text |
| Theorem 1 | dispatched unendorsed protected a satisfies f(Π_U(ξ_t)) ≈ a; projection has only truly trusted content | A1, A2, A5 (det.), A3 for part 2 | complete | none | original Alg. 2 had a shortcut "U = ∅ ⇒ PASS" that broke the proof (agent's action may come from internal state) | θ in (0,1], k >= 1 | no | shortcut removed from Alg. 2 |
| Corollary 1 | step-local NI for gated actions with equal clearance | Thm 1, Lemma 3 | complete | none | requires same untrusted set and same geometry (stated) | n/a | no ("non-interference" qualified as step-local and gated-only) | none |
| Theorem 2 | P_pass = P[Bin(k,q) >= ⌈θk⌉], monotone in q; Chernoff/Hoeffding bounds | A1, A2, A5 (iid) | complete | Lemmas A.1, A.2 | iid sampling assumption may fail for real APIs (stated in G7, A5) | k integer >= 1; q0 < θ < q1 | no | conditional on ξ_t made explicit |
| Corollary 2 | k >= ln(1/δ)/(2(θ-q0)^2) etc. | Thm 2 | complete | none | Hoeffding is loose; exact k table provided | k dimensionless | no | exact table added (Table 5) |
| Theorem 3 | (i) window-level binding; (ii) node-level binding | A1, A2, A6; A7 for (ii) | complete | none | original version claimed node digest check in system_server under the WM lock, which would require IPC to an untrusted process under a global lock | n/a | original was too strong | split into (i) and (ii); node check moved to framework code in the target process with new Assumption 7 |
| Corollary 3 | rebinding never delivers to the new foreground window | Thm 3(i), A1 | complete | none | none | n/a | no | none |
| Theorem 4 | end-to-end composition | A1-A7 | complete | Thms 1-3, Lemma 2 | none | n/a | no | Assumption 7 added to the list |
| Proposition 1 | (a) more permissive than context taint; (b) trajectory NI fails | constructions | complete (existence by construction) | none | original title "strictly between taint tracking and NI" implied a total order that was not proven | n/a | original title too strong | retitled "Separation from taint tracking and from non-interference"; intro wording changed |
| Proposition 2 | calls c + πkc'; token bound | agent issues c calls per step | complete | none | original assumed single-call agents | tokens, calls | original too narrow | generalized to c, c' |
| Proposition 3 | Label Service O((n+N) m r + P); binder O(|W| r) + O(1) node check | rectangle-union region model, hashing | complete under the stated data-structure model | none | original claimed O(log|W|) for the topmost-window query, not justified | counts | original too strong | corrected to O(|W| r) |
| Remark 1 | early escalation preserves Thms 1-2; attribution-only has no guarantee | Alg. 2 | argument complete (one line) | Jain & Wallace cited only for the empirical observation that attention is not explanation | none | n/a | no | none |

## Classical results and whether their assumptions hold

- Chernoff/Hoeffding: proved in-paper (Lemmas A.1, A.2) for i.i.d. Bernoulli trials; i.i.d. follows from Assumption 5.
- Structural causal model framing (Pearl): used only as interpretation ("but-for test under an intervention"); no theorem of Pearl is invoked.
- Lattice model (Denning) and integrity ordering (Biba): used for terminology and orientation; Lemma 1 proves the lattice facts needed.
- Non-interference (Goguen and Meseguer): only the informal notion is used to state what is NOT guaranteed (Prop. 1b); no theorem relies on it.

## Words checked

No result uses "optimal", "tight", "sharp", "matching", or "first". "Provable" appears only when describing MELON's own claim, with its meaning stated.
