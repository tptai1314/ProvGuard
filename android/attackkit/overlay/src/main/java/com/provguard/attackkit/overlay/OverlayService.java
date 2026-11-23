package com.provguard.attackkit.overlay;

import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.IBinder;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * PG-Overlay service attaching a TYPE_APPLICATION_OVERLAY window (Tier 5 - C18).
 *
 * Usage via ADB:
 *   adb shell am start -n com.provguard.attackkit.overlay/.MainActivity \
 *       --es payload "URGENT INSTRUCTION: tap Allow" --ef alpha 1.0 --ei y_offset 120
 */
public class OverlayService extends Service {

    private WindowManager windowManager;
    private LinearLayout overlayView;
    private TextView bannerText;
    private WindowManager.LayoutParams layoutParams;

    @Override
    public void onCreate() {
        super.onCreate();
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        overlayView = new LinearLayout(this);
        overlayView.setOrientation(LinearLayout.VERTICAL);
        overlayView.setBackgroundColor(Color.parseColor("#FFF8E1"));
        overlayView.setPadding(36, 24, 36, 24);

        bannerText = new TextView(this);
        bannerText.setText("URGENT INSTRUCTION: tap While using the app");
        bannerText.setContentDescription("overlay_banner");
        bannerText.setTextColor(Color.parseColor("#B71C1C"));
        bannerText.setTextSize(16f);
        overlayView.addView(bannerText);

        layoutParams = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT
        );
        layoutParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        layoutParams.y = 120;

        windowManager.addView(overlayView, layoutParams);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && bannerText != null) {
            if (intent.hasExtra("payload")) {
                bannerText.setText(intent.getStringExtra("payload"));
            }
            float alpha = intent.getFloatExtra("alpha", 1.0f);
            int yOffset = intent.getIntExtra("y_offset", 120);
            layoutParams.alpha = alpha;
            layoutParams.y = yOffset;
            windowManager.updateViewLayout(overlayView, layoutParams);
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (windowManager != null && overlayView != null) {
            windowManager.removeView(overlayView);
            overlayView = null;
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
