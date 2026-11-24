#!/usr/bin/env bash
# Provision Python environment and all 5 external benchmarks (Table 6) on a fresh EC2 clone.
# Idempotent: skips any repository or archive already downloaded.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXT_DIR="$REPO_ROOT/datasets_external"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$EXT_DIR"

echo "[1/3] Installing ProvGuard package and py7zr..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -e "$REPO_ROOT/ProvGuard[dev]"

echo "[2/3] Cloning external benchmark repositories into $EXT_DIR..."
if [ ! -d "$EXT_DIR/AgentHazard" ]; then
  git clone --depth 1 https://github.com/aron00017/AgentHazard.git "$EXT_DIR/AgentHazard"
fi
if [ ! -d "$EXT_DIR/Ghost-EI" ]; then
  git clone --depth 1 https://github.com/cswjl/Ghost-EI.git "$EXT_DIR/Ghost-EI"
fi
if [ ! -d "$EXT_DIR/Not-An-A11y" ]; then
  git clone --depth 1 https://github.com/Trusted-System-Lab/Not-An-A11y.git "$EXT_DIR/Not-An-A11y"
fi
if [ ! -d "$EXT_DIR/android_world" ]; then
  git clone --depth 1 https://github.com/google-research/android_world.git "$EXT_DIR/android_world"
fi
if [ ! -d "$EXT_DIR/Android-Lab" ]; then
  git clone --depth 1 https://github.com/THUDM/Android-Lab.git "$EXT_DIR/Android-Lab"
fi

echo "[3/3] Checking AgentHazard static scenarios archive (Tsinghua Cloud exp.7z)..."
AH_STATIC="$EXT_DIR/AgentHazard/data/data/static"
if [ ! -d "$AH_STATIC" ]; then
  mkdir -p "$EXT_DIR/AgentHazard/data"
  ARCHIVE="$EXT_DIR/AgentHazard/data/exp.7z"
  if [ ! -f "$ARCHIVE" ]; then
    echo "  Downloading exp.7z (~398 MB) from Tsinghua Cloud..."
    curl -fL "https://cloud.tsinghua.edu.cn/f/b918dc92c8084bf6ab95/?dl=1" -o "$ARCHIVE"
  fi
  echo "  Extracting exp.7z with py7zr..."
  "$PYTHON_BIN" -c "import py7zr; py7zr.SevenZipFile(r'$ARCHIVE', mode='r').extractall(path=r'$EXT_DIR/AgentHazard/data')"
fi

echo "All 5 external benchmarks and ProvGuard Python package are ready."
