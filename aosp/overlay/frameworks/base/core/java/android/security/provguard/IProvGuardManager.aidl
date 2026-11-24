/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

import android.os.IBinder;
import android.security.provguard.IProvGuardCallback;
import android.security.provguard.ProvenanceRecord;
import android.security.provguard.TargetBinding;

/**
 * System service Binder interface for ProvGuard (runs inside system_server).
 * Exposes OS-owned provenance records, Causal Gate evaluation, and Dispatch Binder checks.
 *
 * @hide
 */
interface IProvGuardManager {
    /** Register or update the isolated-process re-execution callback for the calling agent. */
    void registerCallback(IProvGuardCallback callback);

    /** Return the current observation ID and provenance records for all active accessibility windows. */
    List<ProvenanceRecord> getCurrentProvenance();

    /** Retrieve the recorded target binding for a specific (observationId, nodeId). */
    TargetBinding getTargetBinding(String observationId, long nodeId);

    /**
     * Evaluate Causal Gate (Algorithm 2) on a proposed action JSON before dispatch.
     * Returns JSON verdict: {"decision":"pass"|"escalate"|"deny","protected":bool,"support":double,"sink_class":str}.
     */
    String evaluateAction(String observationId, String proposedActionJson);

    /**
     * Record a trusted SystemUI user endorsement for the given action/sink scope.
     * Caller must hold android.permission.INTERNAL_SYSTEM_WINDOW (SystemUI only).
     */
    void recordUserEndorsement(String observationId, String sinkClass, String targetRegionId, boolean approved);

    /**
     * Report the top-level document origin of a WebView bound to the given window token.
     * Called by the WebView provider hook (Paper Section 5.1).
     */
    void reportWebViewOrigin(IBinder windowToken, String webOrigin);

    /** Return JSON telemetry summary (counters, latencies, binder rejects, build metadata). */
    String getTelemetryJson();
}
