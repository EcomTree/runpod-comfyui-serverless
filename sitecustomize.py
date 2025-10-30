# Auto-applied performance tuning hooks
# This file is imported automatically by Python when present on sys.path.
# It enables TF32, cuDNN benchmarking and optional torch.compile.

import sys
import os

try:
    # Allow callers to defer torch-related optimizations to avoid early import of torch
    if os.getenv("SKIP_TORCH_OPTIMIZATIONS", "0").strip().lower() not in ("1", "true", "yes"):
        # Ensure workspace is on sys.path before importing
        workspace_dir = os.path.dirname(os.path.abspath(__file__))
        if workspace_dir not in sys.path:
            sys.path.insert(0, workspace_dir)

        from scripts.optimize_performance import apply_global_torch_optimizations

        apply_global_torch_optimizations()
except Exception:
    # Never block startup on optimization errors
    pass
