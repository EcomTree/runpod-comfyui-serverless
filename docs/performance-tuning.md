# Performance Tuning

This image includes multiple runtime optimizations for PyTorch and ComfyUI. You can enable or tweak them using environment variables.

## Torch compile (PyTorch 2.x)

Enable ahead-of-time graph compilation for select workloads. This can provide 10–30% speedups depending on the workflow and GPU.

- ENABLE_TORCH_COMPILE: "1" to enable optimization hooks
- TORCH_COMPILE_BACKEND: Backend name (default: "inductor")
- TORCH_COMPILE_MODE: "default", "reduce-overhead" (default), or "max-autotune"
- TORCH_COMPILE_FULLGRAPH: "1" to require full graph capture (default: "0")
- TORCH_COMPILE_DYNAMIC: "1" to allow dynamic shapes (default: "0")

Example (RunPod env):

```bash
ENABLE_TORCH_COMPILE=1
TORCH_COMPILE_BACKEND=inductor
TORCH_COMPILE_MODE=reduce-overhead
TORCH_COMPILE_FULLGRAPH=0
TORCH_COMPILE_DYNAMIC=0
```

Note: The container ships with a lightweight optimization shim that is auto-imported via `sitecustomize.py`. When compilation is enabled, it exposes a global helper `COMFY_TORCH_COMPILE` which downstream modules can call to compile their heavy kernels.

## CUDA / cuDNN

Enabled by default unless overridden:

- ENABLE_TF32=1: allow TF32 on Ampere+ (throughput win, minor precision loss)
- ENABLE_CUDNN_BENCHMARK=1: cudnn autotuning for best kernels per shape
- MATMUL_PRECISION=high: set matmul precision policy ("highest" | "high" | "medium")
- PYTORCH_CUDA_ALLOC_CONF: uses `max_split_size_mb:1024,expandable_segments:True`

You can disable or change them by setting these variables to 0 or to your preferred values.

## Extra ComfyUI args

Use `COMFY_EXTRA_ARGS` to pass additional flags to ComfyUI startup (space-separated).

```bash
COMFY_EXTRA_ARGS="--listen 0.0.0.0 --auto-launch --cache-lru 4"
```

## Warmup

On startup, the manager optionally issues a lightweight request to `/object_info` to warm caches and speed up the first prompt. Toggle via:

- ENABLE_STARTUP_WARMUP=1 (default)

## GPU diagnostics

When starting, the runtime logs detected GPU name, VRAM and compute capability to help with capacity and debugging in serverless environments.
