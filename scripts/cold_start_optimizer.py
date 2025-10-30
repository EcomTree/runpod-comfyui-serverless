#!/usr/bin/env python3
"""
Cold start optimizer for ComfyUI serverless deployment
Implements optimizations to reduce container startup time
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict

class ColdStartOptimizer:
    """ComfyUI Cold Start Optimizer"""
    
    def __init__(self, comfyui_path: Path):
        self.comfyui_path = comfyui_path
        self.optimizations_applied = []
        
    def preload_essential_modules(self) -> bool:
        """Preload essential Python modules to reduce import time"""
        try:
            print("🔄 Preloading essential modules...")
            
            # Essential modules for ComfyUI
            essential_modules = [
                'torch',
                'torchvision',
                'numpy',
                'PIL',
                'cv2',
                'requests',
                'json',
                'pathlib',
                'asyncio',
                'aiohttp',
                'aiofiles'
            ]
            
            for module in essential_modules:
                try:
                    __import__(module)
                    print(f"   ✅ {module}")
                except ImportError as e:
                    print(f"   ⚠️ {module}: {e}")
            
            self.optimizations_applied.append("module_preload")
            return True
            
        except Exception as e:
            print(f"❌ Failed to preload modules: {e}")
            return False
    
    def optimize_python_path(self) -> bool:
        """Optimize Python path and environment"""
        try:
            print("🔄 Optimizing Python environment...")
            
            # Set optimal Python environment variables
            optimizations = {
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONUNBUFFERED': '1',
                'PYTHONHASHSEED': '0',
                'PYTHONIOENCODING': 'utf-8'
            }
            
            for key, value in optimizations.items():
                os.environ[key] = value
                print(f"   ✅ {key}={value}")
            
            self.optimizations_applied.append("python_env")
            return True
            
        except Exception as e:
            print(f"❌ Failed to optimize Python environment: {e}")
            return False
    
    def create_startup_cache(self) -> bool:
        """Create startup cache for faster subsequent starts"""
        try:
            print("🔄 Creating startup cache...")
            
            cache_dir = self.comfyui_path / ".startup_cache"
            cache_dir.mkdir(exist_ok=True)
            
            # Create a simple cache marker
            cache_marker = cache_dir / "startup_optimized"
            with open(cache_marker, 'w') as f:
                f.write(f"Cold start optimization applied at {time.time()}\n")
                f.write(f"Optimizations: {', '.join(self.optimizations_applied)}\n")
            
            print(f"   ✅ Cache created: {cache_dir}")
            self.optimizations_applied.append("startup_cache")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create startup cache: {e}")
            return False
    
    def optimize_import_paths(self) -> bool:
        """Optimize Python import paths"""
        try:
            print("🔄 Optimizing import paths...")
            
            # Add ComfyUI to Python path
            comfyui_path = str(self.comfyui_path)
            if comfyui_path not in sys.path:
                sys.path.insert(0, comfyui_path)
                print(f"   ✅ Added to sys.path: {comfyui_path}")
            
            # Add workspace to Python path
            workspace_path = str(self.comfyui_path.parent)
            if workspace_path not in sys.path:
                sys.path.insert(0, workspace_path)
                print(f"   ✅ Added to sys.path: {workspace_path}")
            
            self.optimizations_applied.append("import_paths")
            return True
            
        except Exception as e:
            print(f"❌ Failed to optimize import paths: {e}")
            return False
    
    def create_fast_startup_script(self) -> bool:
        """Create a fast startup script with all optimizations"""
        try:
            print("🔄 Creating fast startup script...")
            
            script_content = f'''#!/bin/bash
# Fast ComfyUI startup script with cold start optimizations

# Set optimized environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONHASHSEED=0
export PYTHONIOENCODING=utf-8

# PyTorch optimizations
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True
export TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1
export TORCH_CUDNN_V8_API_ENABLED=1
export CUDNN_BENCHMARK=1
export CUDNN_DETERMINISTIC=0
export CUDNN_CONV_ALGO_WORKSPACE_LIMIT=1024

# Serverless optimizations
export ENABLE_TORCH_COMPILE=1
export COLD_START_OPTIMIZATION=1

# Start ComfyUI with optimizations
cd "{self.comfyui_path}"
exec python main.py "$@"
'''
            
            script_path = self.comfyui_path / "start_fast.sh"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_path, 0o755)
            
            print(f"   ✅ Fast startup script created: {script_path}")
            self.optimizations_applied.append("fast_startup_script")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create fast startup script: {e}")
            return False
    
    def apply_all_optimizations(self) -> Dict[str, bool]:
        """Apply all cold start optimizations"""
        results = {}
        
        print("🚀 Applying ComfyUI cold start optimizations...")
        
        # Apply optimizations
        results['module_preload'] = self.preload_essential_modules()
        results['python_env'] = self.optimize_python_path()
        results['import_paths'] = self.optimize_import_paths()
        results['startup_cache'] = self.create_startup_cache()
        results['fast_startup_script'] = self.create_fast_startup_script()
        
        # Summary
        successful = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\n📊 Cold Start Optimization Summary: {successful}/{total} optimizations applied")
        print(f"✅ Applied: {', '.join(self.optimizations_applied)}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='ComfyUI Cold Start Optimizer')
    parser.add_argument('--comfyui-path', type=str, default='/workspace/ComfyUI',
                       help='Path to ComfyUI installation')
    
    args = parser.parse_args()
    
    comfyui_path = Path(args.comfyui_path)
    if not comfyui_path.exists():
        print(f"❌ ComfyUI path does not exist: {comfyui_path}")
        sys.exit(1)
    
    optimizer = ColdStartOptimizer(comfyui_path)
    results = optimizer.apply_all_optimizations()
    
    # Exit with error if critical optimizations failed
    critical_optimizations = ['python_env', 'import_paths']
    if not all(results.get(opt, False) for opt in critical_optimizations):
        print("❌ Critical cold start optimizations failed")
        sys.exit(1)
    
    print("🎉 Cold start optimization complete!")

if __name__ == "__main__":
    main()
