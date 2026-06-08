#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/home/kotori9/models/qwen3_6_35b_a3b_ojgen_text_vllm}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-ojgen-qwen3-35b}"
PORT="${PORT:-8080}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-12288}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.50}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-4}"

exec env PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
  vllm serve "$MODEL_PATH" \
    --served-model-name "$SERVED_MODEL_NAME" \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-model-len "$MAX_MODEL_LEN" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    --language-model-only \
    --trust-remote-code \
    --enforce-eager \
    --quantization fp8 \
    --kv-cache-dtype fp8 \
    --mamba-block-size 128 \
    --port "$PORT"
