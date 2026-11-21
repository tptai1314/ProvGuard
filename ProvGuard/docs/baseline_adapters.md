# Baseline adapters

## Implemented local components

- B0 (`NoDefenseBaseline`) always allows the proposed action.
- B1 (`SpotlightingDelimiter`) wraps regions above `app` in advisory delimiters. It is a
  prompt transform, not an enforcement mechanism.
- B2 (`DefensivePromptBaseline`) implements only the manuscript's published description.
  The exact MobileWorldSafety defense text is unavailable, so this class is explicitly
  named description-based and must not be reported as the original artifact.
- B3 (`AgentSideTaintBaseline`) approximates an AOHP/Aura-style conservative no-write-down
  rule with client-visible labels.

## External wrapper

B4 OS-Sentinel requires its formal verifier and VLM judge. `OSSentinelAdapter` intentionally
raises until a pinned external artifact is installed and the released API is known. Expected
input is the current normalized transcript plus proposed action; expected output is an
allow/block decision, detector evidence, latency, and exact artifact identity.

The four agent callback adapters have the common contract `decide(Transcript)->Action`
and `identity()->metadata`. Real callbacks must use the same prompt construction, model,
checkpoint, action parser, and decoding parameters as the main agent; must be stateless;
and must record enough identity information to audit paper Assumption 5.

