# AOSP integration boundary

The paper's security property ultimately requires Android framework changes. This Python
repository is a formal reference implementation and evaluation harness; it is not an AOSP
patch. The following integration points must be implemented against a pinned AOSP release:

- `AccessibilityManagerService`: attach provenance records, labels, observation IDs, and
  bindings to accessibility nodes.
- `WindowManagerService` and input dispatch: expose owner UID/type/token to the Label
  Service and perform Algorithm 3's check-and-enqueue under the dispatch lookup lock.
- `SurfaceFlinger`: compute P1/P2/P4, tile contributors, and frame samples for P3.
- WebView provider: export top-level document origins.
- `NotificationManagerService`: export posting package and sensitivity class.
- new `system_server` services: Causal Gate, transcript store, isolated callback broker,
  and SystemUI endorsement flow.
- target app framework: validate node identity and digest before a node action.

Place reviewed patches in `aosp/patches/` and record the exact AOSP tag, device, kernel,
build fingerprint, and patch hashes in every real run. No patch is fabricated here because
the manuscript does not specify concrete AOSP classes/method signatures for a pinned tag.

