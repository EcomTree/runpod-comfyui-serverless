#!/usr/bin/env python3
"""
Performance optimization script for ComfyUI
Implements PyTorch 2.0+ optimizations including torch.compile
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional

class PerformanceOptimizer:
    """ComfyUI Performance Optimizer"""
    
    def __init__(self, comfyui_path: Path):
        self.comfyui_path = comfyui_path
        self.optimizations_applied = []
        
    def check_pytorch_version(self) -> bool:
        """Check if PyTorch version supports optimizations"""
        try:
            import torch
            version = torch.__version__
            major, minor = map(int, version.split('.')[:2])
            
            if major >= 2:
                print(f"✅ PyTorch {version} detected - optimizations supported")
                return True
            else:
                print(f"⚠️ PyTorch {version} detected - some optimizations may not be available")
                return False
        except ImportError:
            print("❌ PyTorch not found - optimizations cannot be applied")
            return False
    
    def apply_torch_compile(self, enable: bool = True) -> bool:
        """Apply torch.compile optimizations"""
        if not enable:
            return True
            
        try:
            # Check if torch.compile is available
            import torch
            if not hasattr(torch, 'compile'):
                print("⚠️ torch.compile not available in this PyTorch version")
                return False
                
            # Create optimization config
            config = {
                "torch_compile": {
                    "enabled": True,
                    "mode": "default",  # Can be "default", "reduce-overhead", "max-autotune"
                    "backend": "inductor",
                    "fullgraph": False,
                    "dynamic": None
                }
            }
            
            config_path = self.comfyui_path / "torch_compile_config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            print("✅ torch.compile configuration created")
            self.optimizations_applied.append("torch_compile")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply torch.compile: {e}")
            return False
    
    def apply_cudnn_optimizations(self) -> bool:
        """Apply CUDNN optimizations"""
        try:
            # Set CUDNN environment variables
            optimizations = {
                "CUDNN_BENCHMARK": "1",
                "CUDNN_DETERMINISTIC": "0",
                "CUDNN_CONV_ALGO_WORKSPACE_LIMIT": "1024"
            }
            
            for key, value in optimizations.items():
                os.environ[key] = value
                
            print("✅ CUDNN optimizations applied")
            self.optimizations_applied.append("cudnn")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply CUDNN optimizations: {e}")
            return False
    
    def apply_memory_optimizations(self) -> bool:
        """Apply memory management optimizations"""
        try:
            # PyTorch memory optimizations
            memory_config = {
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:1024,expandable_segments:True",
                "TORCH_ALLOW_TF32_CUBLAS_OVERRIDE": "1",
                "TORCH_CUDNN_V8_API_ENABLED": "1"
            }
            
            for key, value in memory_config.items():
                os.environ[key] = value
                
            print("✅ Memory optimizations applied")
            self.optimizations_applied.append("memory")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply memory optimizations: {e}")
            return False
    
    def create_optimized_startup_script(self) -> bool:
        """Create optimized ComfyUI startup script"""
        try:
            script_content = '''#!/bin/bash
# Optimized ComfyUI startup script

# Set performance environment variables
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True
export TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1
export TORCH_CUDNN_V8_API_ENABLED=1
export CUDNN_BENCHMARK=1
export CUDNN_DETERMINISTIC=0
export CUDNN_CONV_ALGO_WORKSPACE_LIMIT=1024

# Enable torch.compile if available
export TORCH_COMPILE_ENABLED=1

# Start ComfyUI with optimizations
exec python main.py "$@"
'''
            
            script_path = self.comfyui_path / "start_optimized.sh"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_path, 0o755)
            
            print(f"✅ Optimized startup script created: {script_path}")
            self.optimizations_applied.append("startup_script")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create startup script: {e}")
            return False
    
    def apply_all_optimizations(self, enable_compile: bool = True) -> Dict[str, bool]:
        """Apply all performance optimizations"""
        results = {}
        
        print("🚀 Applying ComfyUI performance optimizations...")
        
        # Check PyTorch version
        results['pytorch_compatible'] = self.check_pytorch_version()
        
        # Apply optimizations
        results['torch_compile'] = self.apply_torch_compile(enable_compile)
        results['cudnn'] = self.apply_cudnn_optimizations()
        results['memory'] = self.apply_memory_optimizations()
        results['startup_script'] = self.create_optimized_startup_script()
        
        # Summary
        successful = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\n📊 Optimization Summary: {successful}/{total} optimizations applied")
        print(f"✅ Applied: {', '.join(self.optimizations_applied)}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='ComfyUI Performance Optimizer')
    parser.add_argument('--comfyui-path', type=str, default='/workspace/ComfyUI',
                       help='Path to ComfyUI installation')
    parser.add_argument('--enable-compile', action='store_true', default=True,
                       help='Enable torch.compile optimizations')
    parser.add_argument('--disable-compile', action='store_true',
                       help='Disable torch.compile optimizations')
    
    args = parser.parse_args()
    
    comfyui_path = Path(args.comfyui_path)
    if not comfyui_path.exists():
        print(f"❌ ComfyUI path does not exist: {comfyui_path}")
        sys.exit(1)
    
    # Determine if compile should be enabled
    enable_compile = args.enable_compile and not args.disable_compile
    
    optimizer = PerformanceOptimizer(comfyui_path)
    results = optimizer.apply_all_optimizations(enable_compile)
    
    # Exit with error if critical optimizations failed
    if not results.get('pytorch_compatible', False):
        print("❌ Critical: PyTorch compatibility check failed")
        sys.exit(1)
    
    print("🎉 Performance optimization complete!")

if __name__ == "__main__":
    main()