/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import android.os.IBinder;
import android.security.provguard.ProvGuardDigest;
import android.security.provguard.ProvGuardLattice;
import android.security.provguard.ProvenanceRecord;
import android.security.provguard.TargetBinding;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * OS-owned Label Service and tamper-proof transcript store (Paper Section 5.1, Eq. 1-4).
 *
 * Maintains:
 *   - Window -> WebView origin registry (populated by WebView provider hook)
 *   - NotificationKey -> (senderPackage, sensitiveOtp) registry (from NotificationManagerService)
 *   - Bounded OS-held transcript of observations and target bindings
 *   - Trusted projection builder Proj_U(xi_t) replacing untrusted content with <MASKED_BY_PROVGUARD>
 */
public final class ProvGuardLabelService {

    public static final String MASK_PLACEHOLDER = "<MASKED_BY_PROVGUARD>";
    private static final int MAX_OBSERVATIONS = 32;

    public static final class RegionSnapshot {
        public final ProvenanceRecord provenance;
        public final TargetBinding binding;
        public final String className;
        public final String text;
        public final String contentDescription;
        public final String viewIdResourceName;

        public RegionSnapshot(
                ProvenanceRecord provenance,
                TargetBinding binding,
                String className,
                String text,
                String contentDescription,
                String viewIdResourceName) {
            this.provenance = provenance;
            this.binding = binding;
            this.className = className;
            this.text = text;
            this.contentDescription = contentDescription;
            this.viewIdResourceName = viewIdResourceName;
        }
    }

    public static final class NotificationMeta {
        public final String senderPackage;
        public final boolean sensitiveOtp;

        public NotificationMeta(String senderPackage, boolean sensitiveOtp) {
            this.senderPackage = senderPackage;
            this.sensitiveOtp = sensitiveOtp;
        }
    }

    private final Object mLock = new Object();
    private final Map<IBinder, String> mWebViewOrigins = new ConcurrentHashMap<>();
    private final Map<String, NotificationMeta> mNotifications = new ConcurrentHashMap<>();
    private final Map<String, List<RegionSnapshot>> mObservations =
            new LinkedHashMap<String, List<RegionSnapshot>>(MAX_OBSERVATIONS + 1, 0.75f, false) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, List<RegionSnapshot>> eldest) {
                    return size() > MAX_OBSERVATIONS;
                }
            };
    private final Map<String, Map<Long, TargetBinding>> mBindingsByObs = new ConcurrentHashMap<>();
    private final List<String> mDispatchedActionLog = new ArrayList<>();
    private volatile String mCurrentTask = "";
    private volatile String mLatestObservationId = "";

    public void setCurrentTask(String task) {
        synchronized (mLock) {
            mCurrentTask = task == null ? "" : task;
            mObservations.clear();
            mBindingsByObs.clear();
            mDispatchedActionLog.clear();
            mLatestObservationId = "";
        }
    }

    public void recordWebViewOrigin(IBinder windowToken, String webOrigin) {
        if (windowToken == null) {
            return;
        }
        if (webOrigin == null || webOrigin.isEmpty()) {
            mWebViewOrigins.remove(windowToken);
        } else {
            mWebViewOrigins.put(windowToken, webOrigin);
        }
    }

    public void recordNotificationPosted(
            String key, String senderPackage, boolean sensitiveOtp) {
        if (key != null) {
            mNotifications.put(key, new NotificationMeta(senderPackage, sensitiveOtp));
        }
    }

    public void recordNotificationRemoved(String key) {
        if (key != null) {
            mNotifications.remove(key);
        }
    }

    public void recordDispatchedAction(String actionJson) {
        synchronized (mLock) {
            if (actionJson != null) {
                mDispatchedActionLog.add(actionJson);
            }
        }
    }

    /** Compute OS-owned ProvenanceRecord and TargetBinding for an observed node. */
    public ProvenanceRecord recordObservedNode(
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
            boolean developerMarkedThirdParty) {
        String webOrigin = windowToken != null ? mWebViewOrigins.get(windowToken) : null;
        String senderPackage = null;
        if (windowType == ProvGuardLattice.WTYPE_SHADE && !mNotifications.isEmpty()) {
            NotificationMeta latest = mNotifications.values().iterator().next();
            senderPackage = latest.senderPackage;
        }
        int label =
                ProvGuardLattice.classifyOrigin(
                        ownerUid,
                        windowType,
                        webOrigin,
                        senderPackage,
                        developerMarkedThirdParty);

        // Conservative perceivability: zero-area or non-rendered bounds force perceivable = false.
        boolean effPerceivable = perceivable && (right > left) && (bottom > top);
        String digest =
                ProvGuardDigest.computeNodeDigest(
                        className,
                        text,
                        contentDescription,
                        viewIdResourceName,
                        left,
                        top,
                        right,
                        bottom);

        ProvenanceRecord rec =
                new ProvenanceRecord(
                        observationId,
                        regionId,
                        ownerUid,
                        windowToken,
                        windowType,
                        webOrigin,
                        senderPackage,
                        effPerceivable,
                        contrastRatio,
                        visibleFraction,
                        label,
                        digest);
        TargetBinding bind =
                new TargetBinding(
                        observationId, windowToken, nodeId, digest, ownerUid, left, top, right, bottom);
        RegionSnapshot snap =
                new RegionSnapshot(rec, bind, className, text, contentDescription, viewIdResourceName);

        synchronized (mLock) {
            mLatestObservationId = observationId;
            List<RegionSnapshot> list =
                    mObservations.computeIfAbsent(observationId, k -> new ArrayList<>());
            list.add(snap);
            mBindingsByObs
                    .computeIfAbsent(observationId, k -> new ConcurrentHashMap<>())
                    .put(nodeId, bind);
        }
        return rec;
    }

    public List<ProvenanceRecord> getLatestProvenance() {
        synchronized (mLock) {
            List<RegionSnapshot> snaps = mObservations.get(mLatestObservationId);
            if (snaps == null) {
                return Collections.emptyList();
            }
            List<ProvenanceRecord> out = new ArrayList<>(snaps.size());
            for (RegionSnapshot s : snaps) {
                out.add(s.provenance);
            }
            return out;
        }
    }

    public TargetBinding getTargetBinding(String observationId, long nodeId) {
        Map<Long, TargetBinding> map = mBindingsByObs.get(observationId);
        return map == null ? null : map.get(nodeId);
    }

    public RegionSnapshot findRegion(String observationId, String regionId, long nodeId) {
        synchronized (mLock) {
            List<RegionSnapshot> snaps = mObservations.get(observationId);
            if (snaps == null) {
                return null;
            }
            for (RegionSnapshot s : snaps) {
                if (regionId != null && regionId.equals(s.provenance.regionId)) {
                    return s;
                }
                if (nodeId >= 0 && s.binding.nodeId == nodeId) {
                    return s;
                }
            }
            return null;
        }
    }

    /**
     * Build canonical JSON for the trusted projection Proj_{U_t(a)}(xi_t) (Paper Eq. 4).
     * Replaces content of every untrusted or imperceptible region with MASK_PLACEHOLDER
     * while preserving geometry and region identifiers.
     */
    public String buildMaskedTranscriptJson(int clearance) {
        synchronized (mLock) {
            StringBuilder sb = new StringBuilder(1024);
            sb.append("{\"task\":\"").append(escapeJson(mCurrentTask)).append("\",");
            sb.append("\"clearance\":\"")
                    .append(ProvGuardLattice.labelName(clearance))
                    .append("\",\"actions\":[");
            for (int i = 0; i < mDispatchedActionLog.size(); i++) {
                if (i > 0) sb.append(',');
                sb.append(mDispatchedActionLog.get(i));
            }
            sb.append("],\"observations\":[");
            int obsIdx = 0;
            for (Map.Entry<String, List<RegionSnapshot>> entry : mObservations.entrySet()) {
                if (obsIdx++ > 0) sb.append(',');
                sb.append("{\"observation_id\":\"")
                        .append(escapeJson(entry.getKey()))
                        .append("\",\"regions\":[");
                List<RegionSnapshot> snaps = entry.getValue();
                for (int j = 0; j < snaps.size(); j++) {
                    if (j > 0) sb.append(',');
                    RegionSnapshot s = snaps.get(j);
                    boolean untrusted =
                            ProvGuardLattice.isUntrusted(
                                    s.provenance.integrityLabel,
                                    s.provenance.perceivable,
                                    clearance);
                    String content = untrusted ? MASK_PLACEHOLDER : nonNull(s.text);
                    sb.append("{\"region_id\":\"")
                            .append(escapeJson(s.provenance.regionId))
                            .append("\",\"label\":\"")
                            .append(ProvGuardLattice.labelName(s.provenance.integrityLabel))
                            .append("\",\"perceivable\":")
                            .append(s.provenance.perceivable)
                            .append(",\"masked\":")
                            .append(untrusted)
                            .append(",\"content\":\"")
                            .append(escapeJson(content))
                            .append("\",\"bounds\":[")
                            .append(s.binding.boundsLeft)
                            .append(',')
                            .append(s.binding.boundsTop)
                            .append(',')
                            .append(s.binding.boundsRight)
                            .append(',')
                            .append(s.binding.boundsBottom)
                            .append("]}");
                }
                sb.append("]}");
            }
            sb.append("]}");
            return sb.toString();
        }
    }

    private static String nonNull(String s) {
        return s == null ? "" : s;
    }

    public static String escapeJson(String s) {
        if (s == null) return "";
        StringBuilder out = new StringBuilder(s.length() + 8);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':
                    out.append("\\\"");
                    break;
                case '\\':
                    out.append("\\\\");
                    break;
                case '\n':
                    out.append("\\n");
                    break;
                case '\r':
                    out.append("\\r");
                    break;
                case '\t':
                    out.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        return out.toString();
    }
}
