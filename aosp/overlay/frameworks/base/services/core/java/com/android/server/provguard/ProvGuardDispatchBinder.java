/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import android.security.provguard.TargetBinding;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Dispatch Binder: atomic window identity + owner UID + topmost touchable window + node digest
 * verification at dispatch time (Paper Algorithm 3, Section 5.4, Assumptions 6 & 7).
 */
public final class ProvGuardDispatchBinder {

    public static final class DispatchVerdict {
        public final boolean delivered;
        public final String reason;

        public DispatchVerdict(boolean delivered, String reason) {
            this.delivered = delivered;
            this.reason = reason;
        }
    }

    private final ProvGuardLabelService mLabelService;
    private volatile ProvGuardInternal.WindowLockVerifier mWindowLockVerifier;
    private volatile boolean mVerifyWindowToken = true;
    private volatile boolean mVerifyNodeDigest = true;

    private final AtomicLong mDeliveredCount = new AtomicLong();
    private final AtomicLong mRejectedCount = new AtomicLong();

    public ProvGuardDispatchBinder(ProvGuardLabelService labelService) {
        this.mLabelService = labelService;
    }

    public void setWindowLockVerifier(ProvGuardInternal.WindowLockVerifier verifier) {
        this.mWindowLockVerifier = verifier;
    }

    public void configure(boolean verifyWindowToken, boolean verifyNodeDigest) {
        this.mVerifyWindowToken = verifyWindowToken;
        this.mVerifyNodeDigest = verifyNodeDigest;
    }

    /**
     * Verify window binding atomically (Check i) and expected node digest (Check ii).
     *
     * @param currentLiveNodeDigest Optional live digest from AccessibilityInteractionController
     *                              (null if checked at target process boundary instead).
     */
    public DispatchVerdict verifyBeforeDispatch(
            String observationId,
            long nodeId,
            boolean hasCoords,
            float x,
            float y,
            String currentLiveNodeDigest) {
        TargetBinding binding = mLabelService.getTargetBinding(observationId, nodeId);
        if (binding == null) {
            mRejectedCount.incrementAndGet();
            return new DispatchVerdict(false, "missing observation target binding (re-observe)");
        }

        if (mVerifyWindowToken) {
            ProvGuardInternal.WindowLockVerifier verifier = mWindowLockVerifier;
            if (verifier == null) {
                mRejectedCount.incrementAndGet();
                return new DispatchVerdict(
                        false, "window lock verifier uninitialized (fail-closed)");
            }
            float checkX = hasCoords ? x : binding.centerX();
            float checkY = hasCoords ? y : binding.centerY();
            boolean ok =
                    verifier.verifyWindowAtomicLocked(
                            binding.windowToken, binding.ownerUid, true, checkX, checkY);
            if (!ok) {
                mRejectedCount.incrementAndGet();
                return new DispatchVerdict(
                        false,
                        "window token/owner/topmost check failed under WM lock (action rebinding blocked)");
            }
        }

        if (mVerifyNodeDigest && currentLiveNodeDigest != null) {
            if (!currentLiveNodeDigest.equals(binding.nodeDigest)) {
                mRejectedCount.incrementAndGet();
                return new DispatchVerdict(
                        false, "node digest mismatch at dispatch time (in-window target swap blocked)");
            }
        }

        mDeliveredCount.incrementAndGet();
        return new DispatchVerdict(true, "binding verified");
    }

    public long getDeliveredCount() {
        return mDeliveredCount.get();
    }

    public long getRejectedCount() {
        return mRejectedCount.get();
    }
}
