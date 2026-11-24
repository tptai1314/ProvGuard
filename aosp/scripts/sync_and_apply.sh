#!/usr/bin/env bash
# Sync AOSP android-15.0.0_r14 and apply ProvGuard overlay + verified framework hooks.
set -euo pipefail

AOSP_ROOT="${1:-$HOME/aosp-provguard}"
AOSP_BRANCH="${AOSP_BRANCH:-android-15.0.0_r14}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVGUARD_AOSP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$AOSP_ROOT"
cd "$AOSP_ROOT"

if [ ! -d ".repo" ]; then
  echo "[1/3] Initializing AOSP repo ($AOSP_BRANCH, shallow depth=1)..."
  repo init -u https://android.googlesource.com/platform/manifest -b "$AOSP_BRANCH" --depth=1
fi

echo "[2/3] Syncing AOSP source tree..."
repo sync -c -j"$(nproc)" --no-tags --no-clone-bundle

echo "[3/3] Checking hook anchors and applying ProvGuard overlay + patches..."
python3 "$PROVGUARD_AOSP_DIR/patches/apply_hooks.py" \
  --aosp-root "$AOSP_ROOT" \
  --overlay-dir "$PROVGUARD_AOSP_DIR/overlay" \
  --check

python3 "$PROVGUARD_AOSP_DIR/patches/apply_hooks.py" \
  --aosp-root "$AOSP_ROOT" \
  --overlay-dir "$PROVGUARD_AOSP_DIR/overlay" \
  --apply

echo "ProvGuard AOSP patches applied cleanly to $AOSP_ROOT."
