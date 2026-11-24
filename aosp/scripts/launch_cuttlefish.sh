#!/usr/bin/env bash
# Boot ProvGuard-patched Cuttlefish virtual device and verify `cmd provguard status`.
set -euo pipefail

AOSP_ROOT="${1:-$HOME/aosp-provguard}"
cd "$AOSP_ROOT"
set +u
source build/envsetup.sh
lunch aosp_cf_x86_64_phone-trunk_staging-userdebug
set -u

echo "[1/3] Starting Cuttlefish virtual device (headless daemon)..."
launch_cvd --daemon --start_webrtc=false --cpus=4 --memory_mb=6144

echo "[2/3] Waiting for ADB boot completion..."
adb wait-for-device
until [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = "1" ]; do
  sleep 2
done

echo "[3/3] Verifying ProvGuard system_server service inside AOSP..."
STATUS_JSON="$(adb shell cmd provguard status | tr -d '\r')"
echo "ProvGuard OS status: $STATUS_JSON"
if ! echo "$STATUS_JSON" | grep -q '"aosp_tcb":true'; then
  echo "ERROR: ProvGuardManagerService did not report aosp_tcb=true!" >&2
  exit 1
fi
echo "SUCCESS: ProvGuard AOSP TCB is live on Cuttlefish!"
