#!/usr/bin/env bash
# Compile patched AOSP for Cuttlefish (default) or Android SDK Emulator.
# Usage:
#   ./build_cuttlefish.sh /path/to/aosp-provguard cuttlefish
#   ./build_cuttlefish.sh /path/to/aosp-provguard emulator
set -euo pipefail

AOSP_ROOT="${1:-$HOME/aosp-provguard}"
TARGET_KIND="${2:-cuttlefish}"

cd "$AOSP_ROOT"
set +u
source build/envsetup.sh
if [ "$TARGET_KIND" = "emulator" ]; then
  LUNCH_TARGET="sdk_phone64_x86_64-trunk_staging-userdebug"
else
  LUNCH_TARGET="aosp_cf_x86_64_phone-trunk_staging-userdebug"
fi
echo "Selecting lunch target: $LUNCH_TARGET"
lunch "$LUNCH_TARGET"
set -u

echo "Building ProvGuard-patched AOSP image with $(nproc) cores..."
m -j"$(nproc)"

if [ "$TARGET_KIND" = "emulator" ]; then
  echo "Packaging AVD zip for Windows/Linux Android Studio Emulator..."
  m emu_img_zip
  echo "Done! Transfer out/target/product/emu64x/sdk-repo-linux-system-images-*.zip to your Emulator SDK."
else
  echo "Done! Launch Cuttlefish with ./launch_cuttlefish.sh $AOSP_ROOT"
fi
