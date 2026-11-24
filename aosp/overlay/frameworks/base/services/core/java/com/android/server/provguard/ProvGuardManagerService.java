/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.server.provguard;

import android.content.Context;
import android.os.Binder;
import android.os.IBinder;
import android.os.ResultReceiver;
import android.os.ShellCallback;
import android.security.provguard.IProvGuardCallback;
import android.security.provguard.IProvGuardManager;
import android.security.provguard.ProvGuardLattice;
import android.security.provguard.ProvenanceRecord;
import android.security.provguard.TargetBinding;
import android.util.Slog;
import com.android.modules.utils.BasicShellCommandHandler;
import com.android.server.LocalServices;
import com.android.server.SystemService;
import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * ProvGuard SystemService running inside Android system_server (Paper Section 5).
 *
 * Publishes:
 *   - Binder service "provguard" (IProvGuardManager)
 *   - LocalService ProvGuardInternal (for AMS, WMS, NMS, WebView hooks)
 *   - `adb shell cmd provguard <status|set-task|config|provenance|telemetry|reset>`
 */
public final class ProvGuardManagerService extends SystemService {

    public static final String SERVICE_NAME = "provguard";
    private static final String TAG = "ProvGuardService";

    private static final Pattern FIELD_OP = Pattern.compile("\"op\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern FIELD_TARGET =
            Pattern.compile("\"target_region_id\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern FIELD_ARG = Pattern.compile("\"argument\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern FIELD_ROLE =
            Pattern.compile("\"semantic_role\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern FIELD_PKG =
            Pattern.compile("\"target_package\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern FIELD_RES =
            Pattern.compile("\"view_id_resource_name\"\\s*:\\s*\"([^\"]*)\"");

    private final ProvGuardLabelService mLabelService = new ProvGuardLabelService();
    private final ProvGuardSinkPolicy mSinkPolicy = new ProvGuardSinkPolicy();
    private final ProvGuardCausalGate mCausalGate =
            new ProvGuardCausalGate(mLabelService, mSinkPolicy);
    private final ProvGuardDispatchBinder mDispatchBinder =
            new ProvGuardDispatchBinder(mLabelService);

    private volatile IProvGuardCallback mCallback;
    private volatile boolean mEnabled = true;

    public ProvGuardManagerService(Context context) {
        super(context);
    }

    @Override
    public void onStart() {
        Slog.i(TAG, "Starting ProvGuardManagerService inside system_server");
        publishBinderService(SERVICE_NAME, new BinderService());
        LocalServices.addService(ProvGuardInternal.class, new LocalServiceImpl());
    }

    private ProvGuardCausalGate.MaskedReexecutor buildCallbackWrapper() {
        final IProvGuardCallback cb = mCallback;
        if (cb == null) {
            return null;
        }
        return (maskedJson, obsId, seed) -> cb.reexecuteMasked(maskedJson, obsId, seed);
    }

    private String buildTelemetryJson() {
        return "{\"service\":\"provguard\",\"enabled\":"
                + mEnabled
                + ",\"aosp_tcb\":true"
                + ",\"gate_evaluated\":"
                + mCausalGate.getTotalEvaluated()
                + ",\"gate_protected\":"
                + mCausalGate.getProtectedCount()
                + ",\"gate_escalated\":"
                + mCausalGate.getEscalatedCount()
                + ",\"binder_delivered\":"
                + mDispatchBinder.getDeliveredCount()
                + ",\"binder_rejected\":"
                + mDispatchBinder.getRejectedCount()
                + "}";
    }

    private final class LocalServiceImpl extends ProvGuardInternal {
        @Override
        public ProvenanceRecord onNodeObserved(
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
            return mLabelService.recordObservedNode(
                    observationId,
                    regionId,
                    ownerUid,
                    windowToken,
                    windowType,
                    nodeId,
                    className,
                    text,
                    contentDescription,
                    viewIdResourceName,
                    left,
                    top,
                    right,
                    bottom,
                    perceivable,
                    contrastRatio,
                    visibleFraction,
                    developerMarkedThirdParty);
        }

        @Override
        public void onNotificationPosted(
                String notificationKey, String senderPackage, boolean sensitiveOtp) {
            mLabelService.recordNotificationPosted(notificationKey, senderPackage, sensitiveOtp);
        }

        @Override
        public void onNotificationRemoved(String notificationKey) {
            mLabelService.recordNotificationRemoved(notificationKey);
        }

        @Override
        public void onWebViewOriginChanged(IBinder windowToken, String webOrigin) {
            mLabelService.recordWebViewOrigin(windowToken, webOrigin);
        }

        @Override
        public boolean checkAndAuthorizeAction(
                String observationId,
                String op,
                String targetRegionId,
                long nodeId,
                float x,
                float y,
                String argument,
                String targetPackage,
                String viewIdResourceName,
                String semanticRole) {
            if (!mEnabled) {
                return true;
            }
            ProvGuardLabelService.RegionSnapshot snap =
                    mLabelService.findRegion(observationId, targetRegionId, nodeId);
            int targetLabel =
                    snap != null ? snap.provenance.integrityLabel : ProvGuardLattice.LABEL_TOP;
            String nodeText = snap != null ? snap.text : "";

            ProvGuardCausalGate.GateVerdict gate =
                    mCausalGate.evaluate(
                            observationId,
                            op,
                            targetRegionId,
                            argument,
                            targetPackage,
                            viewIdResourceName,
                            semanticRole,
                            nodeText,
                            targetLabel,
                            buildCallbackWrapper(),
                            2026L);
            if (!ProvGuardCausalGate.DECISION_PASS.equals(gate.decision)) {
                Slog.w(TAG, "CausalGate blocked/escalated action: " + gate.toJson());
                return false;
            }

            ProvGuardDispatchBinder.DispatchVerdict binder =
                    mDispatchBinder.verifyBeforeDispatch(
                            observationId, nodeId, x >= 0 && y >= 0, x, y, null);
            if (!binder.delivered) {
                Slog.w(TAG, "DispatchBinder rejected action: " + binder.reason);
                return false;
            }
            mLabelService.recordDispatchedAction(
                    "{\"op\":\""
                            + ProvGuardLabelService.escapeJson(op)
                            + "\",\"target_region_id\":\""
                            + ProvGuardLabelService.escapeJson(targetRegionId)
                            + "\"}");
            return true;
        }

        @Override
        public TargetBinding getExpectedBinding(String observationId, long nodeId) {
            return mLabelService.getTargetBinding(observationId, nodeId);
        }

        @Override
        public void registerWindowLockVerifier(WindowLockVerifier verifier) {
            mDispatchBinder.setWindowLockVerifier(verifier);
        }
    }

    private final class BinderService extends IProvGuardManager.Stub {
        @Override
        public void registerCallback(IProvGuardCallback callback) {
            mCallback = callback;
        }

        @Override
        public List<ProvenanceRecord> getCurrentProvenance() {
            return mLabelService.getLatestProvenance();
        }

        @Override
        public TargetBinding getTargetBinding(String observationId, long nodeId) {
            return mLabelService.getTargetBinding(observationId, nodeId);
        }

        @Override
        public String evaluateAction(String observationId, String proposedActionJson) {
            String op = matchField(FIELD_OP, proposedActionJson, "tap");
            String target = matchField(FIELD_TARGET, proposedActionJson, "");
            String arg = matchField(FIELD_ARG, proposedActionJson, "");
            String role = matchField(FIELD_ROLE, proposedActionJson, "");
            String pkg = matchField(FIELD_PKG, proposedActionJson, "");
            String res = matchField(FIELD_RES, proposedActionJson, "");

            ProvGuardLabelService.RegionSnapshot snap =
                    mLabelService.findRegion(observationId, target, -1L);
            int targetLabel =
                    snap != null ? snap.provenance.integrityLabel : ProvGuardLattice.LABEL_TOP;
            String nodeText = snap != null ? snap.text : "";

            ProvGuardCausalGate.GateVerdict verdict =
                    mCausalGate.evaluate(
                            observationId,
                            op,
                            target,
                            arg,
                            pkg,
                            res,
                            role,
                            nodeText,
                            targetLabel,
                            buildCallbackWrapper(),
                            2026L);
            return verdict.toJson();
        }

        @Override
        public void recordUserEndorsement(
                String observationId, String sinkClass, String targetRegionId, boolean approved) {
            getContext()
                    .enforceCallingOrSelfPermission(
                            android.Manifest.permission.INTERNAL_SYSTEM_WINDOW,
                            "Only trusted SystemUI may record ProvGuard user endorsements");
            mCausalGate.recordEndorsement(observationId, sinkClass, targetRegionId, approved);
        }

        @Override
        public void reportWebViewOrigin(IBinder windowToken, String webOrigin) {
            mLabelService.recordWebViewOrigin(windowToken, webOrigin);
        }

        @Override
        public String getTelemetryJson() {
            return buildTelemetryJson();
        }

        @Override
        public void onShellCommand(
                FileDescriptor in,
                FileDescriptor out,
                FileDescriptor err,
                String[] args,
                ShellCallback callback,
                ResultReceiver resultReceiver) {
            new ShellCmd().exec(this, in, out, err, args, callback, resultReceiver);
        }
    }

    private final class ShellCmd extends BasicShellCommandHandler {
        @Override
        public int onCommand(String cmd) {
            PrintWriter pw = getOutPrintWriter();
            if (cmd == null || "status".equals(cmd) || "telemetry".equals(cmd)) {
                pw.println(buildTelemetryJson());
                return 0;
            }
            if ("enable".equals(cmd)) {
                mEnabled = true;
                pw.println("{\"enabled\":true}");
                return 0;
            }
            if ("disable".equals(cmd)) {
                mEnabled = false;
                pw.println("{\"enabled\":false}");
                return 0;
            }
            if ("set-task".equals(cmd)) {
                String task = getNextArgRequired();
                mLabelService.setCurrentTask(task);
                mCausalGate.clearEndorsements();
                pw.println("{\"task_set\":true}");
                return 0;
            }
            if ("config".equals(cmd)) {
                int trials = Integer.parseInt(getNextArgRequired());
                double theta = Double.parseDouble(getNextArgRequired());
                boolean strict = Boolean.parseBoolean(getNextArgRequired());
                mCausalGate.configure(trials, theta, strict);
                pw.println(
                        "{\"trials\":"
                                + trials
                                + ",\"theta\":"
                                + theta
                                + ",\"strict\":"
                                + strict
                                + "}");
                return 0;
            }
            if ("provenance".equals(cmd)) {
                List<ProvenanceRecord> list = mLabelService.getLatestProvenance();
                StringBuilder sb = new StringBuilder("[");
                for (int i = 0; i < list.size(); i++) {
                    if (i > 0) sb.append(',');
                    ProvenanceRecord r = list.get(i);
                    sb.append("{\"region_id\":\"")
                            .append(ProvGuardLabelService.escapeJson(r.regionId))
                            .append("\",\"uid\":")
                            .append(r.ownerUid)
                            .append(",\"window_type\":")
                            .append(r.windowType)
                            .append(",\"label\":\"")
                            .append(ProvGuardLattice.labelName(r.integrityLabel))
                            .append("\",\"perceivable\":")
                            .append(r.perceivable)
                            .append(",\"contrast\":")
                            .append(r.contrastRatio)
                            .append(",\"visible_fraction\":")
                            .append(r.visibleFraction)
                            .append(",\"digest\":\"")
                            .append(ProvGuardLabelService.escapeJson(r.nodeDigest))
                            .append("\"}");
                }
                sb.append(']');
                pw.println(sb.toString());
                return 0;
            }
            if ("reset".equals(cmd)) {
                mLabelService.setCurrentTask("");
                mCausalGate.clearEndorsements();
                pw.println("{\"reset\":true}");
                return 0;
            }
            return handleDefaultCommands(cmd);
        }

        @Override
        public void onHelp() {
            PrintWriter pw = getOutPrintWriter();
            pw.println("ProvGuard OS service commands (adb shell cmd provguard <subcmd>):");
            pw.println("  status | telemetry                 Print JSON telemetry counters");
            pw.println("  enable | disable                   Toggle OS gate/binder enforcement (B0 vs PG)");
            pw.println("  set-task <task_text>               Start new OS-held transcript for task");
            pw.println("  config <k> <theta> <strict_bool>   Configure CausalGate parameters");
            pw.println("  provenance                         Dump latest OS-owned ProvenanceRecord JSON");
            pw.println("  reset                              Clear transcript and endorsements");
        }
    }

    private static String matchField(Pattern p, String json, String fallback) {
        if (json == null) return fallback;
        Matcher m = p.matcher(json);
        return m.find() ? m.group(1) : fallback;
    }
}
