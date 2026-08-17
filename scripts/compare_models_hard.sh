#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."

MODELS=(
  "gpt-4o-mini"
  "gpt-4o"
  "gpt-5"
  "gpt-5.1"
  "claude-haiku-4-5"
  "claude-sonnet-4-6"
  "claude-opus-4-6"
  "gemini-2.5-flash"
  "gemini-2.5-pro"
  "qwen3.7-plus"
  "qwen3.7-max"
  "deepseek-v4-flash"
  "deepseek-v4-pro"
  "kimi-k2.5"
)

WITH_FLAGS=(
  --with examples/competitors/weekly-report-cn
  --with examples/competitors/resume-cn-optimizer
  --with examples/competitors/zhihu-answer-writer
  --with examples/competitors/video-script-polisher
  --with examples/competitors/product-copy-generator
  --with examples/competitors/english-email-writer
  --with examples/competitors/universal-copywriter
  --with examples/wechat-editor
)

mkdir -p results/hard

for model in "$@"; do
  for variant in xhs-writer-naive xhs-writer; do
    out="results/hard/${variant}--${model}.txt"
    echo "MODEL: $model   SKILL: $variant"
    .venv/bin/skilldoctor test "examples/${variant}" \
      --cases examples/xhs-writer/skilldoctor.cases-hard.yml \
      "${WITH_FLAGS[@]}" \
      --model "$model" 2>&1 | tee "$out"
    echo
  done
done
