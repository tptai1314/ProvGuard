"""Tests for AOSP ProvGuard bridge, anchor-verified hook patcher, and Java/AIDL compilation."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from provguard.aosp_bridge import AospProvGuardBridge

REPO_ROOT = Path(__file__).resolve().parents[2]
AOSP_DIR = REPO_ROOT / "aosp"


def _load_apply_hooks_module():
    spec = importlib.util.spec_from_file_location(
        "apply_hooks", AOSP_DIR / "patches" / "apply_hooks.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_aosp_bridge_parses_telemetry_and_provenance() -> None:
    calls: list[list[str]] = []

    def fake_runner(argv: list[str]) -> str:
        calls.append(argv)
        sub = argv[-1]
        if sub == "status":
            return json.dumps(
                {
                    "service": "provguard",
                    "enabled": True,
                    "aosp_tcb": True,
                    "gate_evaluated": 12,
                    "gate_protected": 5,
                    "gate_escalated": 2,
                    "binder_delivered": 10,
                    "binder_rejected": 1,
                }
            )
        if sub == "provenance":
            return json.dumps(
                [
                    {
                        "region_id": "r0.1",
                        "uid": 10200,
                        "window_type": 1,
                        "label": "app",
                        "perceivable": True,
                        "contrast": 7.5,
                        "visible_fraction": 1.0,
                        "digest": "abc123",
                    }
                ]
            )
        if "config" in argv:
            return json.dumps({"trials": 5, "theta": 0.5, "strict": False})
        if "set-task" in argv:
            return json.dumps({"task_set": True})
        if sub == "disable":
            return json.dumps({"enabled": False})
        return json.dumps({"reset": True})

    bridge = AospProvGuardBridge(serial="0.0.0.0:6520", runner=fake_runner)
    assert bridge.is_available() is True
    tel = bridge.status()
    assert tel.gate_escalated == 2
    assert tel.binder_rejected == 1
    assert bridge.set_enabled(False) is False
    assert bridge.set_task("Pay invoice") is True
    assert bridge.configure_gate(trials=5, theta=0.5)["trials"] == 5
    prov = bridge.get_provenance()
    assert len(prov) == 1 and prov[0].label == "app" and prov[0].perceivable is True
    assert bridge.reset() is True
    assert any(c[:5] == ["adb", "-s", "0.0.0.0:6520", "shell", "cmd"] for c in calls)


def test_apply_hooks_check_apply_idempotent_and_revert(tmp_path: Path) -> None:
    apply_hooks = _load_apply_hooks_module()
    manifest_path = AOSP_DIR / "patches" / "hooks_manifest.json"
    overlay_dir = AOSP_DIR / "overlay"

    # Create realistic skeleton target files matching Android 15 anchors
    skeletons = {
        "frameworks/base/services/java/com/android/server/SystemServer.java": (
            "class SystemServer {\n"
            "  void startOtherServices() {\n"
            "    mSystemServiceManager.startService(AccessibilityManagerService.Lifecycle.class);\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java": (
            "class WindowManagerService {\n"
            "  public void systemReady() {\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityWindowManager.java": (
            "class AccessibilityWindowManager {\n"
            "  public AccessibilityWindowInfo findA11yWindowInfoByIdLocked(int windowId) {\n"
            "    return null;\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/base/core/java/android/view/AccessibilityInteractionController.java": (
            "class AccessibilityInteractionController {\n"
            "  private void performAccessibilityActionUiThread(SomeArgs args) {\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java": (
            "class NotificationManagerService {\n"
            "  void enqueueNotificationInternal(String pkg, int id) {\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/base/core/java/android/webkit/WebView.java": (
            "class WebView {\n"
            "  public void loadUrl(String url) {\n"
            "  }\n"
            "}\n"
        ),
        "frameworks/native/services/inputflinger/dispatcher/Android.bp": (
            'srcs: [\n    "InputDispatcher.cpp",\n]\n'
        ),
        "frameworks/native/services/surfaceflinger/Android.bp": (
            'srcs: [\n    "SurfaceFlinger.cpp",\n]\n'
        ),
        "system/sepolicy/private/service_contexts": (
            "activity                                  u:object_r:activity_service:s0\n"
        ),
    }
    for rel, content in skeletons.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    chk = apply_hooks.run(tmp_path, manifest_path, mode="check")
    assert chk["passed"] is True

    res1 = apply_hooks.run(tmp_path, manifest_path, mode="apply", overlay_dir=overlay_dir)
    assert res1["passed"] is True
    assert res1["overlay_copied"] >= 15
    assert all(h["status"] == "applied" for h in res1["hooks"])
    assert (
        tmp_path
        / "frameworks/base/services/core/java/com/android/server/provguard/ProvGuardManagerService.java"
    ).exists()

    # Second apply must be idempotent
    res2 = apply_hooks.run(tmp_path, manifest_path, mode="apply", overlay_dir=overlay_dir)
    assert res2["passed"] is True
    assert all(h["status"] == "already_present" for h in res2["hooks"])

    # Revert strips every hook cleanly
    rev = apply_hooks.run(tmp_path, manifest_path, mode="revert")
    assert rev["passed"] is True
    assert all(h["status"] == "reverted" for h in rev["hooks"])


def test_aidl_and_java_core_compile_and_run_host_tests(tmp_path: Path) -> None:
    javac = shutil.which("javac")
    java = shutil.which("java")
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not (javac and java and android_home):
        pytest.skip("JDK or ANDROID_HOME unavailable for host AIDL/Java compile check")

    sdk_root = Path(android_home)
    android_jars = sorted((sdk_root / "platforms").glob("android-*/android.jar"))
    aidl_bins = sorted((sdk_root / "build-tools").glob("*/aidl*"))
    if not android_jars or not aidl_bins:
        pytest.skip("android.jar or aidl binary not installed in ANDROID_HOME")

    android_jar = android_jars[-1]
    aidl_bin = aidl_bins[-1]

    gen_dir = tmp_path / "gen"
    cls_dir = tmp_path / "classes"
    gen_dir.mkdir()
    cls_dir.mkdir()

    core_java_root = AOSP_DIR / "overlay/frameworks/base/core/java"
    svc_java_root = AOSP_DIR / "overlay/frameworks/base/services/core/java"

    # 1. Compile all .aidl interfaces with real Android SDK aidl tool
    for aidl_name in ("IProvGuardCallback.aidl", "IProvGuardManager.aidl"):
        aidl_file = core_java_root / "android/security/provguard" / aidl_name
        proc = subprocess.run(
            [str(aidl_bin), f"-I{core_java_root}", f"-o{gen_dir}", str(aidl_file)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"aidl failed for {aidl_name}: {proc.stderr}"

    # 2. Compile generated AIDL stubs + ProvGuard core & service logic + Host test against android.jar
    java_sources = [
        *sorted(gen_dir.rglob("*.java")),
        *sorted((core_java_root / "android/security/provguard").glob("*.java")),
        svc_java_root / "com/android/server/provguard/ProvGuardInternal.java",
        svc_java_root / "com/android/server/provguard/ProvGuardSinkPolicy.java",
        svc_java_root / "com/android/server/provguard/ProvGuardLabelService.java",
        svc_java_root / "com/android/server/provguard/ProvGuardCausalGate.java",
        svc_java_root / "com/android/server/provguard/ProvGuardDispatchBinder.java",
        AOSP_DIR / "tests/java/ProvGuardCoreHostTest.java",
    ]
    comp = subprocess.run(
        [
            javac,
            "-cp",
            str(android_jar),
            "-d",
            str(cls_dir),
            *[str(p) for p in java_sources],
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert comp.returncode == 0, f"javac failed:\n{comp.stderr}"

    # 3. Execute ProvGuardCoreHostTest on JVM
    run_res = subprocess.run(
        [java, "-cp", f"{cls_dir}{os.pathsep}{android_jar}", "ProvGuardCoreHostTest"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_res.returncode == 0, f"ProvGuardCoreHostTest failed:\n{run_res.stderr}\n{run_res.stdout}"
    assert "ALL CHECKS PASSED" in run_res.stdout
