/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import android.security.provguard.ProvGuardLattice;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Deterministic protected sink classifier and clearance policy (Paper Section 5.5, Table 2).
 */
public final class ProvGuardSinkPolicy {

    public static final String SINK_GRANT = "grant";
    public static final String SINK_INSTALL = "install";
    public static final String SINK_SHARE = "share";
    public static final String SINK_SEND = "send";
    public static final String SINK_PAY = "pay";
    public static final String SINK_DELETE = "delete";
    public static final String SINK_TYPE_UNTRUSTED = "type-untrusted";

    private static final Set<String> PERMISSION_CONTROLLER_PKGS =
            new HashSet<>(
                    Arrays.asList(
                            "com.google.android.permissioncontroller",
                            "com.android.permissioncontroller",
                            "com.android.packageinstaller"));

    private static final Set<String> SHARE_SHEET_PKGS =
            new HashSet<>(Arrays.asList("android", "com.android.intentresolver"));

    private volatile int mSendClearance = ProvGuardLattice.LABEL_APP;

    /** Allow sensitivity sweep of send clearance (APP vs SYS; Paper Table 7). */
    public void setSendClearance(int clearance) {
        mSendClearance = clearance;
    }

    /**
     * Classify a proposed action against OS-surface and per-app rules.
     *
     * @return sink class name or {@code null} if the action is unprotected.
     */
    public String classify(
            String op,
            String targetPackage,
            String viewIdResourceName,
            String semanticRole,
            String nodeText,
            int targetLabel) {
        String opLow = lower(op);
        String pkgLow = lower(targetPackage);
        String resLow = lower(viewIdResourceName);
        String roleLow = lower(semanticRole);
        String txtLow = lower(nodeText);

        // 1. Exfiltration via typing into any untrusted / web / SDK / notification field
        if ("type".equals(opLow)
                && !ProvGuardLattice.leq(targetLabel, ProvGuardLattice.LABEL_APP)) {
            return SINK_TYPE_UNTRUSTED;
        }

        // 2. OS-owned surfaces (grant, install, share)
        if (PERMISSION_CONTROLLER_PKGS.contains(pkgLow)) {
            if (resLow.contains("permission_allow")
                    || txtLow.contains("allow")
                    || "grant".equals(roleLow)) {
                return SINK_GRANT;
            }
            if (resLow.contains("install")
                    || txtLow.contains("install")
                    || "install".equals(roleLow)) {
                return SINK_INSTALL;
            }
        }
        if (SHARE_SHEET_PKGS.contains(pkgLow)
                && (resLow.contains("resolver") || resLow.contains("chooser"))) {
            return SINK_SHARE;
        }

        // 3. Semantic role or per-app view-id / text rules
        if ("grant".equals(roleLow) || resLow.contains("permission_allow")) {
            return SINK_GRANT;
        }
        if ("install".equals(roleLow) || resLow.contains("install_button")) {
            return SINK_INSTALL;
        }
        if ("share".equals(roleLow)
                || resLow.contains("btn_share")
                || resLow.contains("share_button")) {
            return SINK_SHARE;
        }
        if ("pay".equals(roleLow)
                || resLow.contains("btn_pay")
                || resLow.contains("confirm_payment")
                || txtLow.contains("confirm payment")) {
            return SINK_PAY;
        }
        if ("delete".equals(roleLow)
                || resLow.contains("btn_delete")
                || resLow.contains("delete_button")) {
            return SINK_DELETE;
        }
        if ("send".equals(roleLow)
                || resLow.contains("send_button")
                || resLow.contains("btn_send")) {
            return SINK_SEND;
        }
        return null;
    }

    /** Return default integrity clearance clr(s) from Paper Table 2. */
    public int clearanceForSink(String sinkClass) {
        if (SINK_GRANT.equals(sinkClass) || SINK_INSTALL.equals(sinkClass)) {
            return ProvGuardLattice.LABEL_SYS;
        }
        if (SINK_SEND.equals(sinkClass)) {
            return mSendClearance;
        }
        return ProvGuardLattice.LABEL_APP;
    }

    private static String lower(String s) {
        return s == null ? "" : s.trim().toLowerCase(Locale.ROOT);
    }
}
