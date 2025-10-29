"""
Runtime performance tuning for PyTorch/ComfyUI.

This module is imported automatically via sitecustomize.py when Python starts
inside the container. It configures:
- TF32 usage on Ampere+ GPUs
- cuDNN benchmarking
- Memory allocator tuning
- Optional torch.compile when enabled

Control via environment variables (all optional):
- ENABLE_TORCH_COMPILE: "1" to enable torch.compile (default: off)
- TORCH_COMPILE_MODE: one of {"default", "reduce-overhead", "max-autotune"}
- TORCH_COMPILE_BACKEND: e.g., "inductor" (default)
- TORCH_COMPILE_FULLGRAPH: "1" for fullgraph=True (default: off)
- TORCH_COMPILE_DYNAMIC: "1" for dynamic=True (default: off)
- ENABLE_TF32: "1" to allow TF32 (default: on)
- ENABLE_CUDNN_BENCHMARK: "1" to enable cudnn.benchmark (default: on)
- MATMUL_PRECISION: one of {"highest", "high", "medium"} (default: high)
"""
from __future__ import annotations

import os
import warnings
from typing import Any, Callable


def _env_flag(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val.strip() != "" else default


def _apply_backend_flags() -> None:
    try:
        import torch
        # TF32
        if _env_flag("ENABLE_TF32", True):
            try:
                torch.backends.cuda.matmul.allow_tf32 = True  # type: ignore[attr-defined]
                torch.backends.cudnn.allow_tf32 = True  # type: ignore[attr-defined]
            except Exception:
                pass
        # cuDNN autotune
        if _env_flag("ENABLE_CUDNN_BENCHMARK", True):
            try:
                torch.backends.cudnn.benchmark = True  # type: ignore[attr-defined]
            except Exception:
                pass
        # Matmul precision (PyTorch 2.0+)
        try:
            precision = _env_str("MATMUL_PRECISION", "high")
            torch.set_float32_matmul_precision(precision)  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        # Torch may not be available in some contexts
        return


def _wrap_torch_compile() -> None:
    """Optionally enable torch.compile with conservative defaults.

    We avoid aggressive graph capture to minimize breakages.
    """
    if not _env_flag("ENABLE_TORCH_COMPILE", False) and not _env_flag("COMFY_ENABLE_COMPILE", False):
        return

    try:
        import torch
        compile_backend = _env_str("TORCH_COMPILE_BACKEND", "inductor")
        compile_mode = _env_str("TORCH_COMPILE_MODE", "reduce-overhead")
        fullgraph = _env_flag("TORCH_COMPILE_FULLGRAPH", False)
        dynamic = _env_flag("TORCH_COMPILE_DYNAMIC", False)

        # Expose a helper for libraries to use if they want
        def compile_module_fn(module_forward: Callable[..., Any]) -> Callable[..., Any]:
            return torch.compile(
                module_forward,
                backend=compile_backend,
                mode=compile_mode,
                fullgraph=fullgraph,
                dynamic=dynamic,
            )

        # Register globally for optional usage by downstream code
        import builtins  # type: ignore
        setattr(builtins, "COMFY_TORCH_COMPILE", compile_module_fn)

        # Soft log
        print(
            f"⚙️  torch.compile enabled (backend={compile_backend}, mode={compile_mode}, fullgraph={fullgraph}, dynamic={dynamic})"
        )
    except Exception as e:
        warnings.warn(f"Failed to enable torch.compile: {e}")


def apply_global_torch_optimizations() -> None:
    _apply_backend_flags()
    _wrap_torch_compile()


# Auto-apply when imported
try:
    apply_global_torch_optimizations()
except Exception:
    pass
