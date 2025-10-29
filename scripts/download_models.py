#!/usr/bin/env python3
"""
Model download script for ComfyUI
Downloads models from models_download.json with parallel processing and progress tracking
"""

import os
import sys
import json
import hashlib
import argparse
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import time

class ModelDownloader:
    """ComfyUI Model Downloader with parallel processing"""
    
    def __init__(self, config_path: str, models_path: str, max_concurrent: int = 3):
        self.config_path = Path(config_path)
        self.models_path = Path(models_path)
        self.max_concurrent = max_concurrent
        self.config = {}
        self.download_stats = {
            'total_files': 0,
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'total_size': 0,
            'downloaded_size': 0
        }
        
    def load_config(self) -> bool:
        """Load model configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Loaded config: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return False
    
    def create_model_directories(self) -> bool:
        """Create necessary model directories"""
        try:
            model_types = ['checkpoints', 'loras', 'vae', 'controlnet', 'upscalers']
            for model_type in model_types:
                dir_path = self.models_path / model_type
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created directory: {dir_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create directories: {e}")
            return False
    
    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate SHA256 hash of a file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"⚠️ Failed to calculate hash for {file_path}: {e}")
            return None
    
    def verify_file(self, file_path: Path, expected_hash: str, expected_size: int) -> bool:
        """Verify downloaded file integrity"""
        if not file_path.exists():
            return False
        
        # Check file size
        actual_size = file_path.stat().st_size
        if actual_size != expected_size:
            print(f"⚠️ Size mismatch for {file_path.name}: expected {expected_size}, got {actual_size}")
            return False
        
        # Check hash if provided
        if expected_hash and expected_hash != "null":
            actual_hash = self.calculate_file_hash(file_path)
            if actual_hash != expected_hash:
                print(f"⚠️ Hash mismatch for {file_path.name}: expected {expected_hash}, got {actual_hash}")
                return False
        
        return True
    
    def get_download_url(self, model_info: Dict) -> str:
        """Get the actual download URL, handling different sources"""
        url = model_info['url']
        
        # Handle CivitAI API downloads
        if 'civitai.com/api/download' in url:
            # For CivitAI, we need to handle the API redirect
            # This is a simplified version - in production you'd want proper API handling
            print(f"⚠️ CivitAI URL detected: {url}")
            print("   Note: CivitAI downloads may require authentication")
        
        return url
    
    async def download_file(self, session: aiohttp.ClientSession, model_info: Dict, 
                          model_type: str, semaphore: asyncio.Semaphore) -> bool:
        """Download a single model file"""
        async with semaphore:
            try:
                name = model_info['name']
                url = self.get_download_url(model_info)
                expected_size = int(model_info.get('size', 0))
                expected_hash = model_info.get('sha256', '')
                
                # Determine file path
                file_path = self.models_path / model_type / name
                
                # Check if file already exists and is valid
                if file_path.exists():
                    if self.verify_file(file_path, expected_hash, expected_size):
                        print(f"✅ {name} already exists and is valid")
                        self.download_stats['skipped'] += 1
                        return True
                    else:
                        print(f"🔄 {name} exists but is invalid, re-downloading...")
                        file_path.unlink()
                
                print(f"📥 Downloading {name} ({expected_size / 1024 / 1024:.1f} MB)...")
                
                # Download with progress tracking
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"❌ Failed to download {name}: HTTP {response.status}")
                        self.download_stats['failed'] += 1
                        return False
                    
                    # Create file and download with progress
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    downloaded_size = 0
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # Show progress every 10MB
                            if downloaded_size % (10 * 1024 * 1024) == 0:
                                progress = (downloaded_size / expected_size) * 100 if expected_size > 0 else 0
                                print(f"   📊 {name}: {downloaded_size / 1024 / 1024:.1f}MB / {expected_size / 1024 / 1024:.1f}MB ({progress:.1f}%)")
                
                # Verify downloaded file
                if self.verify_file(file_path, expected_hash, expected_size):
                    print(f"✅ {name} downloaded and verified successfully")
                    self.download_stats['downloaded'] += 1
                    self.download_stats['downloaded_size'] += downloaded_size
                    return True
                else:
                    print(f"❌ {name} verification failed")
                    file_path.unlink()
                    self.download_stats['failed'] += 1
                    return False
                    
            except Exception as e:
                print(f"❌ Error downloading {model_info.get('name', 'unknown')}: {e}")
                self.download_stats['failed'] += 1
                return False
    
    async def download_models(self, model_types: List[str] = None, 
                            categories: List[str] = None) -> bool:
        """Download models with parallel processing"""
        if not self.config:
            print("❌ No config loaded")
            return False
        
        # Filter models based on criteria
        models_to_download = []
        total_size = 0
        
        for model_type, models in self.config['models'].items():
            if model_types and model_type not in model_types:
                continue
                
            for model in models:
                # Filter by category if specified
                if categories and model.get('category') not in categories:
                    continue
                
                models_to_download.append((model_type, model))
                total_size += int(model.get('size', 0))
        
        if not models_to_download:
            print("❌ No models to download")
            return False
        
        self.download_stats['total_files'] = len(models_to_download)
        self.download_stats['total_size'] = total_size
        
        print(f"🚀 Starting download of {len(models_to_download)} models ({total_size / 1024 / 1024 / 1024:.1f} GB)")
        print(f"📊 Max concurrent downloads: {self.max_concurrent}")
        
        # Create semaphore for concurrent downloads
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Start downloads
        start_time = time.time()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3600),  # 1 hour timeout
            headers={'User-Agent': 'ComfyUI-Model-Downloader/1.0'}
        ) as session:
            tasks = []
            for model_type, model in models_to_download:
                task = asyncio.create_task(
                    self.download_file(session, model, model_type, semaphore)
                )
                tasks.append(task)
            
            # Wait for all downloads to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r is True)
        
        print(f"\n📊 Download Summary:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ⏭️ Skipped: {self.download_stats['skipped']}")
        print(f"   ❌ Failed: {self.download_stats['failed']}")
        print(f"   📁 Total: {self.download_stats['total_files']}")
        print(f"   💾 Downloaded: {self.download_stats['downloaded_size'] / 1024 / 1024 / 1024:.1f} GB")
        print(f"   ⏱️ Time: {elapsed_time:.1f} seconds")
        
        return success_count > 0
    
    def print_available_models(self):
        """Print available models from config"""
        if not self.config:
            print("❌ No config loaded")
            return
        
        print("📋 Available Models:")
        for model_type, models in self.config['models'].items():
            print(f"\n🔹 {model_type.upper()}:")
            for model in models:
                size_mb = int(model.get('size', 0)) / 1024 / 1024
                category = model.get('category', 'unknown')
                print(f"   • {model['name']} ({size_mb:.1f} MB) - {category}")

def main():
    parser = argparse.ArgumentParser(description='ComfyUI Model Downloader')
    parser.add_argument('--config', default='/workspace/models_download.json',
                       help='Path to models config file')
    parser.add_argument('--models-path', default='/workspace/ComfyUI/models',
                       help='Path to ComfyUI models directory')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent downloads')
    parser.add_argument('--types', nargs='+', 
                       choices=['checkpoints', 'loras', 'vae', 'controlnet', 'upscalers'],
                       help='Model types to download')
    parser.add_argument('--categories', nargs='+',
                       help='Categories to download')
    parser.add_argument('--list', action='store_true',
                       help='List available models')
    
    args = parser.parse_args()
    
    # Create downloader
    downloader = ModelDownloader(
        config_path=args.config,
        models_path=args.models_path,
        max_concurrent=args.max_concurrent
    )
    
    # Load config
    if not downloader.load_config():
        sys.exit(1)
    
    # List models if requested
    if args.list:
        downloader.print_available_models()
        return
    
    # Create directories
    if not downloader.create_model_directories():
        sys.exit(1)
    
    # Download models
    success = asyncio.run(downloader.download_models(
        model_types=args.types,
        categories=args.categories
    ))
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()