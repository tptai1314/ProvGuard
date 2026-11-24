/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

/**
 * Stateless re-execution callback exported by the agent SDK in an isolated process
 * (android:isolatedProcess="true"). Implements Paper Section 5.3 and Assumption 5.
 *
 * The callback receives only the OS-constructed trusted projection (masked JSON transcript)
 * and returns a single JSON-encoded proposed action. It has no access to agent memory.
 *
 * @hide
 */
interface IProvGuardCallback {
    /**
     * Evaluate the agent policy on the OS-masked transcript projection.
     *
     * @param maskedTranscriptJson Canonical JSON of Proj_U(xi_t).
     * @param observationId        Identifier of the current masked observation.
     * @param seed                 Deterministic or per-trial seed.
     * @return JSON-encoded action: {"op":..., "target_region_id":..., "argument":...}.
     */
    String reexecuteMasked(String maskedTranscriptJson, String observationId, long seed);

    /**
     * Return pinned agent/model identity metadata (version, digest, provider).
     */
    String getAgentIdentityJson();
}
