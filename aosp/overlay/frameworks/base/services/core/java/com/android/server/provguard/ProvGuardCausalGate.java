/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Causal Gate: masked re-execution of protected GUI actions (Paper Algorithm 2, Section 5.3).
 *
 * Fail-closed by design: any callback error, timeout, or unparseable replay reduces support
 * rather than allowing an unverified protected action to pass.
 */
public final class ProvGuardCausalGate {

    public static final String DECISION_PASS = "pass";
    public static final String DECISION_ESCALATE = "escalate";
    public static final String DECISION_DENY = "deny";

    /** Functional abstraction over IProvGuardCallback so both Binder and host unit tests run identically. */
    public interface MaskedReexecutor {
        String reexecuteMasked(String maskedTranscriptJson, String observationId, long seed)
                throws Exception;
    }

    public static final class GateVerdict {
        public final String decision;
        public final boolean isProtected;
        public final String sinkClass;
        public final double support;
        public final int equivalentTrials;
        public final int totalTrials;
        public final long latencyNs;
        public final String reason;

        public GateVerdict(
                String decision,
                boolean isProtected,
                String sinkClass,
                double support,
                int equivalentTrials,
                int totalTrials,
                long latencyNs,
                String reason) {
            this.decision = decision;
            this.isProtected = isProtected;
            this.sinkClass = sinkClass;
            this.support = support;
            this.equivalentTrials = equivalentTrials;
            this.totalTrials = totalTrials;
            this.latencyNs = latencyNs;
            this.reason = reason;
        }

        public String toJson() {
            return "{\"decision\":\""
                    + decision
                    + "\",\"protected\":"
                    + isProtected
                    + ",\"sink_class\":"
                    + (sinkClass == null ? "null" : "\"" + sinkClass + "\"")
                    + ",\"support\":"
                    + support
                    + ",\"equivalent\":"
                    + equivalentTrials
                    + ",\"trials\":"
                    + totalTrials
                    + ",\"latency_ms\":"
                    + (latencyNs / 1_000_000.0)
                    + ",\"reason\":\""
                    + ProvGuardLabelService.escapeJson(reason)
                    + "\"}";
        }
    }

    private static final Pattern JSON_OP_RE =
            Pattern.compile("\"(?:op|action)\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern JSON_TARGET_RE =
            Pattern.compile("\"(?:target_region_id|region_id|target)\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern JSON_ARG_RE =
            Pattern.compile("\"(?:argument|text)\"\\s*:\\s*\"([^\"]*)\"");

    private final ProvGuardLabelService mLabelService;
    private final ProvGuardSinkPolicy mSinkPolicy;
    private final Map<String, Boolean> mEndorsements = new ConcurrentHashMap<>();

    private volatile int mTrials = 1;
    private volatile double mThreshold = 0.5;
    private volatile boolean mStrictEquivalence = false; // false = control equiv, true = strict equiv

    private final AtomicLong mTotalEvaluated = new AtomicLong();
    private final AtomicLong mProtectedCount = new AtomicLong();
    private final AtomicLong mEscalatedCount = new AtomicLong();

    public ProvGuardCausalGate(
            ProvGuardLabelService labelService, ProvGuardSinkPolicy sinkPolicy) {
        this.mLabelService = labelService;
        this.mSinkPolicy = sinkPolicy;
    }

    public void configure(int trials, double threshold, boolean strictEquivalence) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1");
        }
        if (threshold <= 0.0 || threshold > 1.0) {
            throw new IllegalArgumentException("threshold must be in (0, 1]");
        }
        mTrials = trials;
        mThreshold = threshold;
        mStrictEquivalence = strictEquivalence;
    }

    public void recordEndorsement(
            String observationId, String sinkClass, String targetRegionId, boolean approved) {
        String key = endorsementKey(sinkClass, targetRegionId);
        mEndorsements.put(key, approved);
    }

    public void clearEndorsements() {
        mEndorsements.clear();
    }

    public GateVerdict evaluate(
            String observationId,
            String op,
            String targetRegionId,
            String argument,
            String targetPackage,
            String viewIdResourceName,
            String semanticRole,
            String nodeText,
            int targetLabel,
            MaskedReexecutor callback,
            long baseSeed) {
        long startNs = System.nanoTime();
        mTotalEvaluated.incrementAndGet();

        String sinkClass =
                mSinkPolicy.classify(
                        op, targetPackage, viewIdResourceName, semanticRole, nodeText, targetLabel);
        if (sinkClass == null) {
            return new GateVerdict(
                    DECISION_PASS,
                    false,
                    null,
                    1.0,
                    0,
                    0,
                    System.nanoTime() - startNs,
                    "unprotected action; gate bypassed");
        }
        mProtectedCount.incrementAndGet();

        // Check task-scoped SystemUI user endorsement first
        Boolean endorsed = mEndorsements.get(endorsementKey(sinkClass, targetRegionId));
        if (endorsed != null) {
            return new GateVerdict(
                    endorsed ? DECISION_PASS : DECISION_DENY,
                    true,
                    sinkClass,
                    endorsed ? 1.0 : 0.0,
                    0,
                    0,
                    System.nanoTime() - startNs,
                    endorsed ? "approved via SystemUI endorsement" : "denied by user");
        }

        if (callback == null) {
            mEscalatedCount.incrementAndGet();
            return new GateVerdict(
                    DECISION_ESCALATE,
                    true,
                    sinkClass,
                    0.0,
                    0,
                    mTrials,
                    System.nanoTime() - startNs,
                    "no isolated re-execution callback registered (fail-closed)");
        }

        int clearance = mSinkPolicy.clearanceForSink(sinkClass);
        String maskedJson = mLabelService.buildMaskedTranscriptJson(clearance);
        int k = mTrials;
        int equivalent = 0;

        for (int i = 0; i < k; i++) {
            try {
                String replayJson = callback.reexecuteMasked(maskedJson, observationId, baseSeed + i);
                if (actionsEquivalent(op, targetRegionId, argument, replayJson, mStrictEquivalence)) {
                    equivalent++;
                }
            } catch (Exception ignored) {
                // Fail-closed: callback exception counts as non-equivalent trial.
            }
        }

        double support = (double) equivalent / (double) k;
        boolean pass = support >= mThreshold;
        if (!pass) {
            mEscalatedCount.incrementAndGet();
        }
        return new GateVerdict(
                pass ? DECISION_PASS : DECISION_ESCALATE,
                true,
                sinkClass,
                support,
                equivalent,
                k,
                System.nanoTime() - startNs,
                pass
                        ? "empirical trusted support meets threshold"
                        : "empirical trusted support below threshold");
    }

    /** Paper Definition 13: control equivalence (op + target) vs strict equivalence (+ argument). */
    public static boolean actionsEquivalent(
            String proposedOp,
            String proposedTarget,
            String proposedArg,
            String replayJson,
            boolean strict) {
        if (replayJson == null || replayJson.isEmpty()) {
            return false;
        }
        String replayOp = extract(JSON_OP_RE, replayJson);
        String replayTarget = extract(JSON_TARGET_RE, replayJson);
        if (replayOp == null || !replayOp.equalsIgnoreCase(nonNull(proposedOp))) {
            return false;
        }
        if (!nonNull(proposedTarget).equalsIgnoreCase(nonNull(replayTarget))) {
            return false;
        }
        if (strict) {
            String replayArg = extract(JSON_ARG_RE, replayJson);
            return nonNull(proposedArg).equals(nonNull(replayArg));
        }
        return true;
    }

    public long getTotalEvaluated() {
        return mTotalEvaluated.get();
    }

    public long getProtectedCount() {
        return mProtectedCount.get();
    }

    public long getEscalatedCount() {
        return mEscalatedCount.get();
    }

    private static String endorsementKey(String sinkClass, String targetRegionId) {
        return nonNull(sinkClass) + "::" + nonNull(targetRegionId);
    }

    private static String extract(Pattern p, String text) {
        Matcher m = p.matcher(text);
        return m.find() ? m.group(1) : null;
    }

    private static String nonNull(String s) {
        return s == null ? "" : s;
    }
}
