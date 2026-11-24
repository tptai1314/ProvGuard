/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Deterministic SHA-256 node digest for DispatchBinder verification
 * (Paper Section 5.4 & Assumption 7).
 *
 * Canonical tuple: (className, text, contentDescription, viewIdResourceName, left, top, right, bottom).
 */
public final class ProvGuardDigest {

    private ProvGuardDigest() {}

    public static String computeNodeDigest(
            String className,
            String text,
            String contentDescription,
            String viewIdResourceName,
            int left,
            int top,
            int right,
            int bottom) {
        String payload =
                safe(className)
                        + "|"
                        + safe(text)
                        + "|"
                        + safe(contentDescription)
                        + "|"
                        + safe(viewIdResourceName)
                        + "|"
                        + left
                        + ","
                        + top
                        + ","
                        + right
                        + ","
                        + bottom;
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(payload.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(Character.forDigit((b >>> 4) & 0xF, 16));
                hex.append(Character.forDigit(b & 0xF, 16));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable in Android runtime", e);
        }
    }

    private static String safe(String s) {
        return s == null ? "" : s;
    }
}
