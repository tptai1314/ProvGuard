package com.provguard.attackkit.overlay;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;

/**
 * PG-Overlay launcher activity (Tier 5 - C18).
 * Starts OverlayService with custom payload/alpha/y_offset and finishes immediately
 * so the target foreground application remains visible underneath the overlay.
 */
public class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        dispatchOverlayIntent(getIntent());
        finish();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        dispatchOverlayIntent(intent);
        finish();
    }

    private void dispatchOverlayIntent(Intent incoming) {
        if (!Settings.canDrawOverlays(this)) {
            return;
        }
        Intent svc = new Intent(this, OverlayService.class);
        if (incoming != null && incoming.getExtras() != null) {
            svc.putExtras(incoming.getExtras());
        }
        startService(svc);
    }
}
