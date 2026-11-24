/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import android.os.IBinder;
import android.security.provguard.ProvenanceRecord;
import android.security.provguard.TargetBinding;

/**
 * In-process LocalService interface inside system_server for hooks in:
 *   - AccessibilityManagerService / AccessibilityWindowManager
 *   - WindowManagerService / InputDispatcher
 *   - NotificationManagerService
 *   - WebView provider
 */
public abstract class ProvGuardInternal {

    /** Hook from WindowManager / AccessibilityWindowManager when serving an observation. */
    public abstract ProvenanceRecord onNodeObserved(
            String observationId,
            String regionId,
            int ownerUid,
            IBinder windowToken,
            int windowType,
            long nodeId,
            String className,
            String text,
            String contentDescription,
            String viewIdResourceName,
            int left,
            int top,
            int right,
            int bottom,
            boolean perceivable,
            float contrastRatio,
            float visibleFraction,
            boolean developerMarkedThirdParty);

    /** Hook from NotificationManagerService when a notification is posted or updated. */
    public abstract void onNotificationPosted(
            String notificationKey, String senderPackage, boolean sensitiveOtp);

    /** Hook from NotificationManagerService when a notification is removed. */
    public abstract void onNotificationRemoved(String notificationKey);

    /** Hook from WebView provider when top-level document origin changes. */
    public abstract void onWebViewOriginChanged(IBinder windowToken, String webOrigin);

    /**
     * Hook from AccessibilityManagerService before executing performAction or dispatchGesture.
     * Runs CausalGate (if protected) and DispatchBinder verification.
     *
     * @return true iff action is permitted to proceed to InputDispatcher / target process.
     */
    public abstract boolean checkAndAuthorizeAction(
            String observationId,
            String op,
            String targetRegionId,
            long nodeId,
            float x,
            float y,
            String argument,
            String targetPackage,
            String viewIdResourceName,
            String semanticRole);

    /** Retrieve expected digest for AccessibilityInteractionController verification (Assumption 7). */
    public abstract TargetBinding getExpectedBinding(String observationId, long nodeId);

    /** Atomic WindowManager lock verifier interface registered by WindowManagerService. */
    public interface WindowLockVerifier {
        /**
         * Must execute under WindowManagerGlobalLock / InputDispatcher::mLock.
         * Returns true iff token exists, is owned by expectedUid, and (when checkCoords is true)
         * is the topmost touchable window at (x, y).
         */
        boolean verifyWindowAtomicLocked(
                IBinder token, int expectedUid, boolean checkCoords, float x, float y);
    }

    /** Register the atomic WindowManagerService/InputDispatcher lock callback at boot. */
    public abstract void registerWindowLockVerifier(WindowLockVerifier verifier);
}
