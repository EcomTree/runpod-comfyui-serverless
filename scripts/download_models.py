#!/usr/bin/env python3
"""
ComfyUI Model Download Manager
Downloads models from various sources with progress tracking and validation
"""

import os
import sys
import json
import argparse
import requests
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time


class ModelDownloader:
    """Download and manage ComfyUI models"""
    
    def __init__(self, config_path: str, comfyui_path: str = "/workspace/ComfyUI"):
        self.config_path = Path(config_path)
        self.comfyui_path = Path(comfyui_path)
        self.config = self._load_config()
        self.download_settings = self.config.get('download_settings', {})
        
    def _load_config(self) -> Dict:
        """Load model configuration from JSON"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _get_file_size(self, url: str) -> Optional[int]:
        """Get file size from URL headers"""
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            if 'content-length' in response.headers:
                return int(response.headers['content-length'])
        except Exception as e:
            print(f"⚠️ Could not get file size: {e}")
        return None
    
    def _download_file(self, url: str, dest_path: Path, resume: bool = True) -> bool:
        """Download a file with progress tracking and resume support"""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists
        if dest_path.exists():
            print(f"✓ File already exists: {dest_path.name}")
            return True
        
        # Setup resume
        headers = {}
        mode = 'wb'
        initial_pos = 0
        
        if resume and dest_path.with_suffix('.part').exists():
            initial_pos = dest_path.with_suffix('.part').stat().st_size
            headers['Range'] = f'bytes={initial_pos}-'
            mode = 'ab'
            print(f"📥 Resuming download from {self._format_size(initial_pos)}")
        
        temp_path = dest_path.with_suffix('.part')
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=self.download_settings.get('timeout', 3600)
            )
            
            # Check if resume is supported
            if initial_pos > 0 and response.status_code not in [206, 200]:
                print(f"⚠️ Resume not supported, starting fresh")
                temp_path.unlink()
                initial_pos = 0
                mode = 'wb'
                response = requests.get(url, stream=True, timeout=3600)
            
            total_size = int(response.headers.get('content-length', 0))
            if initial_pos > 0:
                total_size += initial_pos
            
            chunk_size = self.download_settings.get('chunk_size', 8192)
            downloaded = initial_pos
            
            print(f"📥 Downloading: {dest_path.name}")
            print(f"📦 Size: {self._format_size(total_size)}")
            
            start_time = time.time()
            last_print_time = start_time
            
            with open(temp_path, mode) as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Print progress every 2 seconds
                        current_time = time.time()
                        if current_time - last_print_time >= 2:
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                speed = downloaded / (current_time - start_time)
                                eta = (total_size - downloaded) / speed if speed > 0 else 0
                                print(f"  Progress: {percent:.1f}% | "
                                      f"{self._format_size(downloaded)}/{self._format_size(total_size)} | "
                                      f"Speed: {self._format_size(speed)}/s | "
                                      f"ETA: {int(eta)}s")
                            last_print_time = current_time
            
            # Move completed file
            temp_path.rename(dest_path)
            
            elapsed = time.time() - start_time
            avg_speed = downloaded / elapsed if elapsed > 0 else 0
            print(f"✅ Downloaded: {dest_path.name}")
            print(f"   Time: {int(elapsed)}s | Avg speed: {self._format_size(avg_speed)}/s")
            
            return True
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False
    
    def _download_with_retry(self, url: str, dest_path: Path) -> bool:
        """Download with retry logic"""
        max_retries = self.download_settings.get('retry_attempts', 3)
        retry_delay = self.download_settings.get('retry_delay', 5)
        resume = self.download_settings.get('resume_downloads', True)
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"🔄 Retry attempt {attempt + 1}/{max_retries}")
                time.sleep(retry_delay)
            
            if self._download_file(url, dest_path, resume):
                return True
        
        print(f"❌ Failed after {max_retries} attempts")
        return False
    
    def list_categories(self):
        """List all available model categories"""
        print("\n📂 Available Model Categories:")
        print("=" * 60)
        
        for category, data in self.config['model_categories'].items():
            model_count = len(data['models'])
            total_size = sum([self._parse_size(m.get('size', '0')) for m in data['models']])
            print(f"\n{category.upper()}")
            print(f"  Description: {data['description']}")
            print(f"  Models: {model_count}")
            print(f"  Estimated size: {self._format_size(total_size)}")
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        if not size_str:
            return 0
        
        size_str = size_str.strip().upper()
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        for unit, multiplier in units.items():
            if unit in size_str:
                try:
                    number = float(size_str.split(unit)[0].strip())
                    return int(number * multiplier)
                except ValueError:
                    return 0
        return 0
    
    def list_packs(self):
        """List all available model packs"""
        print("\n📦 Available Model Packs:")
        print("=" * 60)
        
        for pack_name, pack_data in self.config['model_packs'].items():
            print(f"\n{pack_name.upper()}")
            print(f"  Description: {pack_data['description']}")
            print(f"  Models: {len(pack_data['models'])}")
            print(f"  Contents:")
            for model_path in pack_data['models']:
                print(f"    - {model_path}")
    
    def download_category(self, category: str, parallel: bool = True) -> Tuple[int, int]:
        """Download all models in a category"""
        if category not in self.config['model_categories']:
            print(f"❌ Category '{category}' not found")
            return 0, 0
        
        category_data = self.config['model_categories'][category]
        models = category_data['models']
        base_path = self.comfyui_path / category_data['path']
        
        print(f"\n📂 Downloading category: {category}")
        print(f"📍 Destination: {base_path}")
        print(f"📊 Models: {len(models)}")
        
        success_count = 0
        failed_count = 0
        
        if parallel and len(models) > 1:
            max_workers = min(self.download_settings.get('parallel_downloads', 3), len(models))
            print(f"🔄 Parallel downloads: {max_workers}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for model in models:
                    dest_path = base_path / model['name']
                    future = executor.submit(self._download_with_retry, model['url'], dest_path)
                    futures[future] = model['name']
                
                for future in as_completed(futures):
                    model_name = futures[future]
                    try:
                        if future.result():
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        print(f"❌ Error downloading {model_name}: {e}")
                        failed_count += 1
        else:
            for model in models:
                dest_path = base_path / model['name']
                if self._download_with_retry(model['url'], dest_path):
                    success_count += 1
                else:
                    failed_count += 1
        
        print(f"\n✅ Category '{category}' complete: {success_count} success, {failed_count} failed")
        return success_count, failed_count
    
    def download_pack(self, pack_name: str) -> Tuple[int, int]:
        """Download a model pack"""
        if pack_name not in self.config['model_packs']:
            print(f"❌ Pack '{pack_name}' not found")
            return 0, 0
        
        pack_data = self.config['model_packs'][pack_name]
        print(f"\n📦 Downloading pack: {pack_name}")
        print(f"📝 {pack_data['description']}")
        
        success_count = 0
        failed_count = 0
        
        for model_path in pack_data['models']:
            category, model_name = model_path.split('/', 1)
            
            # Find model in category
            category_data = self.config['model_categories'][category]
            model_info = None
            for m in category_data['models']:
                if m['name'] == model_name:
                    model_info = m
                    break
            
            if not model_info:
                print(f"⚠️ Model not found: {model_path}")
                failed_count += 1
                continue
            
            dest_path = self.comfyui_path / category_data['path'] / model_name
            if self._download_with_retry(model_info['url'], dest_path):
                success_count += 1
            else:
                failed_count += 1
        
        print(f"\n✅ Pack '{pack_name}' complete: {success_count} success, {failed_count} failed")
        return success_count, failed_count
    
    def download_model(self, category: str, model_name: str) -> bool:
        """Download a specific model"""
        if category not in self.config['model_categories']:
            print(f"❌ Category '{category}' not found")
            return False
        
        category_data = self.config['model_categories'][category]
        model_info = None
        
        for m in category_data['models']:
            if m['name'] == model_name:
                model_info = m
                break
        
        if not model_info:
            print(f"❌ Model '{model_name}' not found in category '{category}'")
            return False
        
        dest_path = self.comfyui_path / category_data['path'] / model_name
        return self._download_with_retry(model_info['url'], dest_path)
    
    def verify_downloads(self) -> Dict[str, List[str]]:
        """Verify all downloaded models"""
        print("\n🔍 Verifying downloaded models...")
        
        results = {
            'present': [],
            'missing': [],
            'corrupt': []
        }
        
        for category, data in self.config['model_categories'].items():
            base_path = self.comfyui_path / data['path']
            
            for model in data['models']:
                model_path = base_path / model['name']
                
                if model_path.exists():
                    # Check file size if available
                    actual_size = model_path.stat().st_size
                    expected_size = self._parse_size(model.get('size', '0'))
                    
                    if expected_size > 0 and abs(actual_size - expected_size) > expected_size * 0.1:
                        results['corrupt'].append(f"{category}/{model['name']}")
                        print(f"⚠️ Size mismatch: {model['name']}")
                    else:
                        results['present'].append(f"{category}/{model['name']}")
                        print(f"✓ {category}/{model['name']}")
                else:
                    results['missing'].append(f"{category}/{model['name']}")
        
        print(f"\n📊 Verification Results:")
        print(f"  ✅ Present: {len(results['present'])}")
        print(f"  ❌ Missing: {len(results['missing'])}")
        print(f"  ⚠️ Corrupt: {len(results['corrupt'])}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='ComfyUI Model Download Manager')
    parser.add_argument('--config', type=str, default='/workspace/models_download.json',
                       help='Path to model configuration JSON')
    parser.add_argument('--comfyui-path', type=str, default='/workspace/ComfyUI',
                       help='Path to ComfyUI installation')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List commands
    subparsers.add_parser('list-categories', help='List all model categories')
    subparsers.add_parser('list-packs', help='List all model packs')
    
    # Download commands
    download_cat = subparsers.add_parser('download-category', help='Download a category')
    download_cat.add_argument('category', help='Category name')
    download_cat.add_argument('--sequential', action='store_true', help='Disable parallel downloads')
    
    download_pack = subparsers.add_parser('download-pack', help='Download a model pack')
    download_pack.add_argument('pack', help='Pack name')
    
    download_model = subparsers.add_parser('download-model', help='Download a specific model')
    download_model.add_argument('category', help='Category name')
    download_model.add_argument('model', help='Model filename')
    
    # Verify command
    subparsers.add_parser('verify', help='Verify downloaded models')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        downloader = ModelDownloader(args.config, args.comfyui_path)
        
        if args.command == 'list-categories':
            downloader.list_categories()
        
        elif args.command == 'list-packs':
            downloader.list_packs()
        
        elif args.command == 'download-category':
            parallel = not args.sequential
            downloader.download_category(args.category, parallel)
        
        elif args.command == 'download-pack':
            downloader.download_pack(args.pack)
        
        elif args.command == 'download-model':
            downloader.download_model(args.category, args.model)
        
        elif args.command == 'verify':
            downloader.verify_downloads()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
