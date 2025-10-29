# Auto-applied performance tuning hooks
# This file is imported automatically by Python when present on sys.path.
# It enables TF32, cuDNN benchmarking and optional torch.compile.

try:
    from scripts.optimize_performance import apply_global_torch_optimizations  # type: ignore
    apply_global_torch_optimizations()
except Exception:
    # Never block startup on optimization errors
    pass
