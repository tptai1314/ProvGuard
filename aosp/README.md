# ProvGuard Real AOSP Patches (Cuttlefish / Android Emulator)

This directory contains the real AOSP implementation of **ProvGuard** targeting **Android 15 (`android-15.0.0_r14`)** running 100% on **Cuttlefish (`aosp_cf_x86_64_phone-trunk_staging-userdebug`)** or **Android SDK Emulator (`sdk_phone64_x86_64-trunk_staging-userdebug`)** — no physical Pixel or unlocked Xiaomi handset is required.

## Architecture Mapping (Paper Section 5 -> AOSP Tree)

| Paper Component | AOSP Path (`aosp/overlay/...`) | Role in TCB |
| :--- | :--- | :--- |
| **AIDL & Core Lattice** | `frameworks/base/core/java/android/security/provguard/` | `IProvGuardManager.aidl`, `IProvGuardCallback.aidl`, `ProvenanceRecord`, `TargetBinding`, `ProvGuardLattice`, `ProvGuardDigest` |
| **Label Service, Sink Policy, Causal Gate, Dispatch Binder** | `frameworks/base/services/core/java/com/android/server/provguard/` | `ProvGuardManagerService` (`system_server`), `ProvGuardLabelService`, `ProvGuardSinkPolicy`, `ProvGuardCausalGate`, `ProvGuardDispatchBinder`, `ProvGuardInternal`, `adb shell cmd provguard` |
| **Trusted Endorsement UI** | `frameworks/base/packages/SystemUI/src/com/android/systemui/provguard/` | `ProvGuardEndorsementActivity` with `SYSTEM_FLAG_HIDE_NON_SYSTEM_OVERLAY_WINDOWS` |
| **SurfaceFlinger Perceivability (P1–P4)** | `frameworks/native/services/surfaceflinger/ProvGuard/` | `ProvGuardPerceivability.{h,cpp}` (on-screen fraction, Porter-Duff occlusion, WCAG 1%/99% contrast, effective alpha) |
| **InputDispatcher Atomic Lock Hook** | `frameworks/native/services/inputflinger/dispatcher/ProvGuard/` | `ProvGuardInputHook.{h,cpp}` (verified under `InputDispatcher::mLock`, Assumption 6) |
| **SELinux Policy** | `system/sepolicy/private/` | `provguard_service.te` + `service_contexts` hook |
| **Surgical Framework Hooks** | `aosp/patches/hooks_manifest.json` + `apply_hooks.py` | Anchor-verified, idempotent hooks into `SystemServer`, `WindowManagerService`, `AccessibilityWindowManager`, `AccessibilityInteractionController`, `NotificationManagerService`, `WebView`, `Android.bp`, `service_contexts` |

## Local Verification (Windows / Linux without full 300 GB AOSP tree)

Even before spinning up a Linux build host, you can verify AIDL compilation, Java compilation against `android.jar`, core logic unit tests, and the anchor patcher:

```powershell
# 1. Verify Java/AIDL compilation and run ProvGuardCoreHostTest (Lattice, Digest, SinkPolicy, CausalGate, DispatchBinder)
.\ProvGuard\.venv\Scripts\python.exe -m pytest ProvGuard\tests\test_aosp_bridge.py -q
```

## Building & Running on Ubuntu EC2 (100% Virtual Device)

1. **Provision Linux host** (Ubuntu 22.04/24.04, 64 GB RAM, 400 GB SSD):
   ```bash
   bash aosp/scripts/ec2_setup.sh
   ```
2. **Sync AOSP & apply ProvGuard overlay + hooks**:
   ```bash
   bash aosp/scripts/sync_and_apply.sh "$HOME/aosp-provguard"
   ```
3. **Compile for Cuttlefish (or `emulator` to export an AVD zip for Windows)**:
   ```bash
   bash aosp/scripts/build_cuttlefish.sh "$HOME/aosp-provguard" cuttlefish
   # Or: bash aosp/scripts/build_cuttlefish.sh "$HOME/aosp-provguard" emulator
   ```
4. **Boot Cuttlefish & verify `system_server` service**:
   ```bash
   bash aosp/scripts/launch_cuttlefish.sh "$HOME/aosp-provguard"
   ```
5. **Connect Python Evaluation Harness**:
   Use `provguard.aosp_bridge.AospProvGuardBridge` (automatically queries `adb shell cmd provguard status|provenance|config|set-task|telemetry`).
