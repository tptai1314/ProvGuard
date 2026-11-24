/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

/**
 * ProvGuard Integrity Lattice (Paper Section 3 / Eq. 1-3).
 *
 * Partial order (lower = more trusted):
 *   SYS < APP < {WEB, SDK, NTF} < TOP
 *
 * WEB, SDK, and NTF are mutually incomparable; their join is TOP.
 *
 * @hide
 */
public final class ProvGuardLattice {

    public static final int LABEL_SYS = 0;
    public static final int LABEL_APP = 1;
    public static final int LABEL_WEB = 2;
    public static final int LABEL_SDK = 3;
    public static final int LABEL_NTF = 4;
    public static final int LABEL_TOP = 5;

    /** Window type constants aligned with ProvGuard formal semantics. */
    public static final int WTYPE_SYSTEM = 0;
    public static final int WTYPE_APPLICATION = 1;
    public static final int WTYPE_OVERLAY = 2;
    public static final int WTYPE_SHADE = 3;
    public static final int WTYPE_SDK_SURFACE = 4;
    public static final int WTYPE_INPUT_METHOD = 5;

    private ProvGuardLattice() {}

    /** Return true iff {@code a <= b} in the integrity lattice (a is at least as trusted as b). */
    public static boolean leq(int a, int b) {
        if (a == b) {
            return true;
        }
        if (a == LABEL_SYS || b == LABEL_TOP) {
            return true;
        }
        if (a == LABEL_APP && (b == LABEL_WEB || b == LABEL_SDK || b == LABEL_NTF)) {
            return true;
        }
        return false;
    }

    /** Least upper bound (join) in the lattice. */
    public static int join(int a, int b) {
        if (leq(a, b)) {
            return b;
        }
        if (leq(b, a)) {
            return a;
        }
        // Incomparable pair among {WEB, SDK, NTF} joins to TOP.
        return LABEL_TOP;
    }

    /**
     * Paper Eq. (3): a region belongs to the untrusted set U_t(a) iff
     * its label is not <= clearance OR it fails the SurfaceFlinger perceivability predicate.
     */
    public static boolean isUntrusted(int label, boolean perceivable, int clearance) {
        return !leq(label, clearance) || !perceivable;
    }

    /**
     * Default OS labeling policy Lambda_0 (Paper Section 5.1).
     * Computed strictly from system_server / SurfaceFlinger metadata (never app text).
     */
    public static int classifyOrigin(
            int ownerUid,
            int windowType,
            String webOrigin,
            String senderPackage,
            boolean developerMarkedThirdParty) {
        if (developerMarkedThirdParty) {
            // Optional developer annotation can only raise the label to TOP (Section 5.1).
            return LABEL_TOP;
        }
        if (windowType == WTYPE_OVERLAY) {
            return LABEL_TOP;
        }
        if (windowType == WTYPE_SHADE || (senderPackage != null && !senderPackage.isEmpty())) {
            return LABEL_NTF;
        }
        if (windowType == WTYPE_SDK_SURFACE) {
            return LABEL_SDK;
        }
        if (webOrigin != null && !webOrigin.isEmpty()) {
            return LABEL_WEB;
        }
        if (windowType == WTYPE_SYSTEM || ownerUid == 1000) {
            return LABEL_SYS;
        }
        return LABEL_APP;
    }

    public static String labelName(int label) {
        switch (label) {
            case LABEL_SYS:
                return "sys";
            case LABEL_APP:
                return "app";
            case LABEL_WEB:
                return "web";
            case LABEL_SDK:
                return "sdk";
            case LABEL_NTF:
                return "ntf";
            case LABEL_TOP:
            default:
                return "unt";
        }
    }

    public static int parseLabel(String name) {
        if (name == null) {
            return LABEL_TOP;
        }
        switch (name.trim().toLowerCase()) {
            case "sys":
            case "system":
                return LABEL_SYS;
            case "app":
            case "application":
                return LABEL_APP;
            case "web":
                return LABEL_WEB;
            case "sdk":
                return LABEL_SDK;
            case "ntf":
            case "notification":
                return LABEL_NTF;
            case "unt":
            case "top":
            case "untrusted":
            default:
                return LABEL_TOP;
        }
    }
}
