#!/usr/bin/env bash
# Compare trigger rates across models for naive vs optimized descriptions.
# Usage:
#   export SKILLDOCTOR_API_KEY="..."
#   export SKILLDOCTOR_BASE_URL="https://aiberm.com/v1"
#   bash scripts/compare_models.sh
set -u
cd "$(dirname "$0")/.."

MODELS=(
  "gpt-4o-mini"
  "gpt-4o"
  "claude-sonnet-4-20250514"
  "deepseek-chat"
  "qwen-plus"
  "kimi-k2-0905-preview"
)

WITH_FLAGS=(
  --with examples/competitors/weekly-report-cn
  --with examples/competitors/resume-cn-optimizer
  --with examples/competitors/zhihu-answer-writer
  --with examples/competitors/video-script-polisher
  --with examples/competitors/product-copy-generator
  --with examples/competitors/english-email-writer
  --with examples/wechat-editor
)

mkdir -p results

for model in "${MODELS[@]}"; do
  for variant in xhs-writer-naive xhs-writer; do
    out="results/${variant}--${model}.txt"
    echo "============================================================"
    echo "MODEL: $model   SKILL: $variant"
    echo "============================================================"
    .venv/bin/skilldoctor test "examples/${variant}" \
      --cases examples/xhs-writer/skilldoctor.cases.yml \
      "${WITH_FLAGS[@]}" \
      --model "$model" 2>&1 | tee "$out"
    echo
  done
done

echo "done. raw outputs saved under results/"
