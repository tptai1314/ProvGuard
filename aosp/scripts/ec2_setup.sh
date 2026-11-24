#!/usr/bin/env bash
# Provision Ubuntu 22.04 / 24.04 EC2 instance for building AOSP + running Cuttlefish.
# Recommended AWS instance:
#   - Build host (compile only): c7i.8xlarge or r6i.4xlarge (64 GB RAM, 400 GB gp3 EBS)
#   - Cuttlefish KVM host:       c7i.metal-24xl / i3en.metal, OR any Linux host with /dev/kvm
set -euo pipefail

echo "[1/4] Installing AOSP build dependencies..."
sudo apt-get update
sudo apt-get install -y \
  git-core gnupg flex bison build-essential zip curl zlib1g-dev \
  libc6-dev-i386 x11proto-core-dev libx11-dev lib32z1-dev libgl1-mesa-dev \
  libxml2-utils xsltproc unzip fontconfig python3 python3-pip rsync \
  openjdk-17-jdk adb fastboot qemu-kvm libvirt-daemon-system

echo "[2/4] Installing Google repo tool..."
mkdir -p "$HOME/.local/bin"
curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo -o "$HOME/.local/bin/repo"
chmod a+x "$HOME/.local/bin/repo"
export PATH="$HOME/.local/bin:$PATH"

echo "[3/4] Installing Cuttlefish host packages (if supported on this kernel)..."
if [ -e /dev/kvm ]; then
  echo "  /dev/kvm detected! Adding $USER to kvm/cvdnetwork groups."
  sudo usermod -aG kvm "$USER" || true
  if ! command -v launch_cvd >/dev/null 2>&1; then
    echo "  Build/install android-cuttlefish host debian packages from github.com/google/android-cuttlefish:"
    echo "    git clone https://github.com/google/android-cuttlefish && cd android-cuttlefish"
    echo "    tools/buildutils/build_packages.sh && sudo dpkg -i ./cuttlefish-base_*.deb ./cuttlefish-user_*.deb"
  fi
else
  echo "  WARNING: /dev/kvm not found on this VM (normal on non-metal AWS EC2)."
  echo "  You can STILL compile AOSP Cuttlefish / Emulator images here, then transfer"
  echo "  out/target/product/emulator_x86_64/ images to a KVM Linux or Windows Android Emulator host."
fi

echo "[4/4] Verifying disk & RAM..."
df -h .
free -h
echo "EC2 AOSP build environment setup complete."
