# Math-to-code audit

| Paper location | Object | Implementation interpretation | Edge cases | Consistency / correction |
|---|---|---|---|---|
| Sec. 4.1, Eq. 1 | provenance tuple | `ProvenanceRecord` with explicit optional origin/sender and boolean sensitivity/perceivability | missing origin/sender is `None`; UID/type required | consistent |
| Def. 3 P1 | on-screen fraction | supplied compositor evidence compared with `phi_on` | unavailable evidence returns false | consistent; real region algebra remains AOSP work |
| Def. 3 P2 | `1-product(1-alpha_i)` and visible fraction | exact `combined_opacity`; visible fraction supplied separately | validates every alpha in [0,1] | paper names `alpha_occ_max` but P2 ultimately compares an already-derived visible fraction; AOSP algorithm must document the exact rectangle/opacity rule |
| Def. 3 P3 | contrast `(L1+.05)/(L2+.05)` | exact luminance formula | validates [0,1]; non-text regions skip | consistent |
| Def. 3 P4 | drawn and alpha | strict `alpha > alpha_min`, positive area | paper says greater than alpha_min, so equality fails | consistent |
| Def. 4 | label lattice | explicit partial order, join, meet | empty tile join rejected | consistent; verified incomparable channel join=`unt`, meet=`app` |
| Def. 5, Eq. 2 | Lambda0 and tile join | ordered deterministic policy; join all contributors | missing contributor rejected; optional app annotation can only raise label | consistent, but system-sender notification precedence was made explicit as `sys` per prose |
| Def. 6-7 | resolved target and equivalence | node lookup or topmost clickable/touchable geometry; control compares op+binding; strict adds normalized arg | unresolved targets compare `(None,None)`; callers should treat missing binder target conservatively | paper states resolved targets; gate callback parsing must not emit unresolved actions in real implementation |
| Eq. 3 | untrusted set | all regions across transcript for which label not <= clearance or perc=false | empty set allowed | consistent |
| Eq. 4 | trusted projection | fixed placeholder replaces content only; geometry/labels/bindings preserved | constant token; pixels represented by reference string in Python model | consistent; residual geometry channel retained deliberately |
| Def. 14 | support probability q | empirical fraction of equivalent callback samples | callback errors count as non-equivalent | conservative operational choice; not contradicted by paper |
| Alg. 2 line 7 | empirical support | integer equivalent count divided by k | threshold in (0,1]; k>=1 | consistent; pass event uses `ceil(theta*k)` |
| Eq. 5 | deterministic trusted sufficiency | unit tests verify pass iff replay equivalent after masking | theorem still depends on A1/A2/A5 | no empirical/AOSP guarantee claimed |
| Eq. 6 | exact binomial tail | direct finite sum from `ceil(theta*k)` | q=0/1 handled exactly | consistent; reproduces Table 5 reference row k=13 for q0=.2/q1=.8/delta=.01 |
| Thm. 2(i) | KL and Hoeffding false-pass bounds | exact Bernoulli KL and exponential bounds | q0=0 returns zero KL bound | consistent |
| Thm. 2(ii) | false-escalation bound | `exp(-2k(q1-theta)^2)` | validates q1>theta | consistent |
| Cor. 2 | sufficient k | ceiling of maximum two inequalities | floating-point ceiling can be sensitive at exact integers; tested reference value 26 | mathematically conservative ceiling |
| Eqs. 7-9 | ASR/FBR/TSR | numerator/denominator exactly as definitions | zero denominator raises instead of emitting NaN/0 | conservative; prevents misleading empty metrics |
| Sec. 8.5 | Wilson interval, McNemar | 95% Wilson and exact two-sided binomial McNemar | no discordant pairs gives p=1 | consistent with stated protocol |
| Prop. 2 | model-call overhead | expected expression documented; trial logs expose k/support | no real latency/token claim | no correction |
| Prop. 3 | OS complexity | documented only | cannot measure without AOSP data structures | intentionally not presented as Python benchmark |

## Consistency findings

No fatal contradiction was found among Definitions 1-14, Algorithms 1-4, and Theorems
1-4. The manuscript is unusually explicit that theorems are conditional on implementation
assumptions. Two implementation-sensitive ambiguities remain:

1. P2 describes a visible fraction after excluding coverage by stacks whose combined
   opacity exceeds a threshold, but does not give pseudocode for partially overlapping
   rectangles. The reference API accepts the resulting visible fraction; an AOSP patch must
   specify and test the region algebra.
2. Control equivalence ignores arguments by design. This may pass a send action whose text
   changes, while type-untrusted is intended to cover reverse exfiltration. This is a stated
   utility/security trade-off, not silently “fixed” here. Strict equivalence remains available.

The paper's results tables are placeholders, not mathematical inconsistencies. No placeholder
number is promoted to an implementation result.

