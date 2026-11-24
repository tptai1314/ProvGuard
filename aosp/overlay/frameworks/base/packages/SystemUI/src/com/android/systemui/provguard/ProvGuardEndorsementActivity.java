/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package com.android.systemui.provguard;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.IBinder;
import android.os.ServiceManager;
import android.security.provguard.IProvGuardManager;
import android.util.Log;
import android.view.WindowManager;

/**
 * Trusted SystemUI user endorsement dialog (Paper Section 5.3).
 *
 * Sets SYSTEM_FLAG_HIDE_NON_SYSTEM_OVERLAY_WINDOWS so untrusted TYPE_APPLICATION_OVERLAY
 * windows cannot obscure or clickjack the user's approval decision.
 */
public final class ProvGuardEndorsementActivity extends Activity {

    private static final String TAG = "ProvGuardEndorseUI";
    public static final String EXTRA_OBS_ID = "provguard.obs_id";
    public static final String EXTRA_SINK_CLASS = "provguard.sink_class";
    public static final String EXTRA_TARGET_REGION = "provguard.target_region";
    public static final String EXTRA_SUMMARY = "provguard.summary";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Prevent any third-party overlay from covering this SystemUI endorsement dialog.
        getWindow().addSystemFlags(
                WindowManager.LayoutParams.SYSTEM_FLAG_HIDE_NON_SYSTEM_OVERLAY_WINDOWS);

        final String obsId = getIntent().getStringExtra(EXTRA_OBS_ID);
        final String sinkClass = getIntent().getStringExtra(EXTRA_SINK_CLASS);
        final String targetRegion = getIntent().getStringExtra(EXTRA_TARGET_REGION);
        final String summary = getIntent().getStringExtra(EXTRA_SUMMARY);

        new AlertDialog.Builder(this)
                .setTitle("ProvGuard Security Check (" + sinkClass + ")")
                .setMessage(
                        "An agent requested a protected action that depends on untrusted screen content.\n\n"
                                + "Action summary: "
                                + (summary == null ? targetRegion : summary)
                                + "\n\nApprove this action for the current task?")
                .setCancelable(false)
                .setPositiveButton(
                        "Approve",
                        (d, w) -> {
                            sendDecision(obsId, sinkClass, targetRegion, true);
                            finish();
                        })
                .setNegativeButton(
                        "Deny",
                        (d, w) -> {
                            sendDecision(obsId, sinkClass, targetRegion, false);
                            finish();
                        })
                .show();
    }

    private void sendDecision(
            String obsId, String sinkClass, String targetRegion, boolean approved) {
        try {
            IBinder b = ServiceManager.getService("provguard");
            if (b != null) {
                IProvGuardManager mgr = IProvGuardManager.Stub.asInterface(b);
                mgr.recordUserEndorsement(obsId, sinkClass, targetRegion, approved);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to report endorsement decision to ProvGuardManagerService", e);
        }
    }
}
