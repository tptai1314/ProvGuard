#!/usr/bin/env bash
# One-command EC2 batch evaluation script for the full ProvGuard international paper matrix.
#
# Runs:
#   1. All 10 Table-8 configurations (B0, B1, B2, B3, B4, labels, gate, binder, no_perc, full)
#   2. All 6 external & adaptive suites (AgentHazard, GhostEI-Bench, Not-An-A11y, Adaptive, AndroidWorld, AndroidLab)
#   3. All 4 paper agents (droidrun, ui-tars, open-autoglm, mobile-agent-v3)
#   4. RQ4 (k, theta) sensitivity sweep (k in {1,3,5,9}, theta in {0.3,0.5,0.7})
#
# Usage on EC2 GPU instance (with vLLM serving on localhost:8000):
#   VLLM_BASE_URL=http://localhost:8000/v1 VLLM_MODEL=ByteDance-Seed/UI-TARS-7B-DPO \
#     bash aosp/scripts/run_ec2_paper_eval.sh
set -euo pipefail

PROVIDER="${PROVIDER:-openai}"
VLLM_BASE_URL="${VLLM_BASE_URL:-http://localhost:8000/v1}"
VLLM_API_KEY="${VLLM_API_KEY:-EMPTY}"
VLLM_MODEL="${VLLM_MODEL:-ByteDance-Seed/UI-TARS-7B-DPO}"
REPS="${REPS:-5}"
OUT_ROOT="${OUT_ROOT:-results_paper_ec2}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "================================================================"
echo "ProvGuard Full Paper Evaluation"
echo "  Provider : $PROVIDER"
echo "  Base URL : $VLLM_BASE_URL"
echo "  Model    : $VLLM_MODEL"
echo "  Reps     : $REPS"
echo "  Out Root : $OUT_ROOT"
echo "================================================================"

if command -v adb >/dev/null 2>&1 && adb get-state >/dev/null 2>&1; then
  echo "[AOSP TCB Check] Querying connected Cuttlefish / Emulator..."
  adb shell cmd provguard status || true
fi

for AGENT in droidrun ui-tars open-autoglm mobile-agent-v3; do
  echo ""
  echo ">>> [1/2] Running 10-config Table 8 matrix for agent=$AGENT..."
  "$PYTHON_BIN" ProvGuard/scripts/run_trials.py \
    --provider "$PROVIDER" \
    --model "$VLLM_MODEL" \
    --agent "$AGENT" \
    --base-url "$VLLM_BASE_URL" \
    --api-key "$VLLM_API_KEY" \
    --configs "B0,B1,B2,B3,B4,labels,gate,binder,no_perc,full" \
    --reps "$REPS" \
    --trials 1 \
    --out "$OUT_ROOT/table8_${AGENT}" \
    --freeze

  echo ">>> [2/2] Running External + Adaptive + AndroidWorld + AndroidLab suites for agent=$AGENT..."
  "$PYTHON_BIN" ProvGuard/scripts/run_external_suites.py \
    --provider "$PROVIDER" \
    --model "$VLLM_MODEL" \
    --agent "$AGENT" \
    --base-url "$VLLM_BASE_URL" \
    --api-key "$VLLM_API_KEY" \
    --out "$OUT_ROOT/external_${AGENT}" \
    --freeze
done

echo ""
echo ">>> Running RQ4 (k, theta) sensitivity sweep (k=1,3,5,9 x theta=0.3,0.5,0.7)..."
"$PYTHON_BIN" ProvGuard/scripts/run_rq4_sweep.py \
  --provider "$PROVIDER" \
  --model "$VLLM_MODEL" \
  --agent "ui-tars" \
  --base-url "$VLLM_BASE_URL" \
  --api-key "$VLLM_API_KEY" \
  --k-values "1,3,5,9" \
  --theta-values "0.3,0.5,0.7" \
  --temperature 0.3 \
  --out "$OUT_ROOT/rq4_sweep"

echo ""
echo "ALL EC2 evaluations finished cleanly. Results written to: $OUT_ROOT"
