#!/usr/bin/env python3
"""
ComfyUI Model Link Verification Script
Verifies that all model download URLs are accessible
"""

import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class LinkVerifier:
    """Verify model download links"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.results = {
            'valid': [],
            'invalid': [],
            'timeout': [],
            'redirect': []
        }
    
    def _load_config(self) -> Dict:
        """Load model configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _check_url(self, url: str, timeout: int = 10) -> Tuple[str, int, str]:
        """
        Check if URL is accessible
        Returns: (status, status_code, message)
        """
        try:
            response = requests.head(
                url, 
                allow_redirects=True, 
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            # Check for redirects
            if response.history:
                final_url = response.url
                if final_url != url:
                    return 'redirect', response.status_code, f"Redirects to {final_url}"
            
            if response.status_code == 200:
                size = response.headers.get('content-length', 'unknown')
                return 'valid', response.status_code, f"Size: {size} bytes"
            elif response.status_code == 405:
                # HEAD not allowed, try GET with minimal range
                try:
                    response = requests.get(
                        url,
                        headers={'Range': 'bytes=0-0'},
                        timeout=timeout
                    )
                    if response.status_code in [200, 206]:
                        return 'valid', response.status_code, "GET verified"
                except:
                    pass
                return 'invalid', response.status_code, "Method not allowed"
            else:
                return 'invalid', response.status_code, response.reason
                
        except requests.exceptions.Timeout:
            return 'timeout', 0, f"Timeout after {timeout}s"
        except requests.exceptions.ConnectionError as e:
            return 'invalid', 0, f"Connection error: {str(e)[:50]}"
        except Exception as e:
            return 'invalid', 0, f"Error: {str(e)[:50]}"
    
    def verify_model(self, category: str, model: Dict, verbose: bool = False) -> Dict:
        """Verify a single model"""
        name = model['name']
        url = model['url']
        
        if verbose:
            print(f"🔍 Checking: {category}/{name}")
        
        status, code, message = self._check_url(url)
        
        result = {
            'category': category,
            'name': name,
            'url': url,
            'status': status,
            'status_code': code,
            'message': message,
            'size': model.get('size', 'unknown'),
            'type': model.get('type', 'unknown')
        }
        
        self.results[status].append(result)
        
        # Print status
        status_symbols = {
            'valid': '✅',
            'invalid': '❌',
            'timeout': '⏱️',
            'redirect': '🔄'
        }
        symbol = status_symbols.get(status, '❓')
        
        if verbose or status != 'valid':
            print(f"{symbol} {category}/{name}: {message}")
        
        return result
    
    def verify_all(self, parallel: bool = True, max_workers: int = 10, verbose: bool = False):
        """Verify all models in configuration"""
        print("🔍 Verifying model download links...")
        print("=" * 60)
        
        all_models = []
        for category, data in self.config['model_categories'].items():
            for model in data['models']:
                all_models.append((category, model))
        
        print(f"📊 Total models to verify: {len(all_models)}\n")
        
        if parallel and len(all_models) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.verify_model, cat, model, verbose): (cat, model['name'])
                    for cat, model in all_models
                }
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        cat, name = futures[future]
                        print(f"❌ Exception verifying {cat}/{name}: {e}")
        else:
            for category, model in all_models:
                self.verify_model(category, model, verbose)
        
        self._print_summary()
    
    def verify_category(self, category: str, verbose: bool = False):
        """Verify all models in a specific category"""
        if category not in self.config['model_categories']:
            print(f"❌ Category '{category}' not found")
            return
        
        print(f"🔍 Verifying category: {category}")
        print("=" * 60)
        
        models = self.config['model_categories'][category]['models']
        print(f"📊 Models to verify: {len(models)}\n")
        
        for model in models:
            self.verify_model(category, model, verbose)
        
        self._print_summary()
    
    def verify_pack(self, pack_name: str, verbose: bool = False):
        """Verify all models in a pack"""
        if pack_name not in self.config['model_packs']:
            print(f"❌ Pack '{pack_name}' not found")
            return
        
        pack_data = self.config['model_packs'][pack_name]
        print(f"🔍 Verifying pack: {pack_name}")
        print(f"📝 {pack_data['description']}")
        print("=" * 60)
        
        for model_path in pack_data['models']:
            category, model_name = model_path.split('/', 1)
            
            # Find model
            category_data = self.config['model_categories'][category]
            for model in category_data['models']:
                if model['name'] == model_name:
                    self.verify_model(category, model, verbose)
                    break
        
        self._print_summary()
    
    def _print_summary(self):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("📊 Verification Summary")
        print("=" * 60)
        
        total = sum(len(v) for v in self.results.values())
        valid_count = len(self.results['valid'])
        invalid_count = len(self.results['invalid'])
        timeout_count = len(self.results['timeout'])
        redirect_count = len(self.results['redirect'])
        
        print(f"✅ Valid:     {valid_count:3d} ({valid_count/total*100:.1f}%)")
        print(f"❌ Invalid:   {invalid_count:3d} ({invalid_count/total*100:.1f}%)")
        print(f"⏱️ Timeout:   {timeout_count:3d} ({timeout_count/total*100:.1f}%)")
        print(f"🔄 Redirect:  {redirect_count:3d} ({redirect_count/total*100:.1f}%)")
        print(f"📊 Total:     {total}")
        
        # Show invalid links
        if self.results['invalid']:
            print("\n❌ Invalid Links:")
            for result in self.results['invalid']:
                print(f"  - {result['category']}/{result['name']}")
                print(f"    URL: {result['url']}")
                print(f"    Error: {result['message']}")
        
        # Show timeouts
        if self.results['timeout']:
            print("\n⏱️ Timeout Links:")
            for result in self.results['timeout']:
                print(f"  - {result['category']}/{result['name']}")
                print(f"    URL: {result['url']}")
        
        # Show redirects
        if self.results['redirect']:
            print("\n🔄 Redirected Links:")
            for result in self.results['redirect']:
                print(f"  - {result['category']}/{result['name']}")
                print(f"    {result['message']}")
    
    def export_results(self, output_path: str):
        """Export verification results to JSON"""
        output = Path(output_path)
        
        export_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config_file': str(self.config_path),
            'summary': {
                'total': sum(len(v) for v in self.results.values()),
                'valid': len(self.results['valid']),
                'invalid': len(self.results['invalid']),
                'timeout': len(self.results['timeout']),
                'redirect': len(self.results['redirect'])
            },
            'results': self.results
        }
        
        with open(output, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n💾 Results exported to: {output}")


def main():
    parser = argparse.ArgumentParser(description='Verify ComfyUI Model Download Links')
    parser.add_argument('--config', type=str, default='/workspace/models_download.json',
                       help='Path to model configuration JSON')
    parser.add_argument('--category', type=str, help='Verify specific category only')
    parser.add_argument('--pack', type=str, help='Verify specific pack only')
    parser.add_argument('--sequential', action='store_true', help='Disable parallel verification')
    parser.add_argument('--workers', type=int, default=10, help='Max parallel workers')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--export', type=str, help='Export results to JSON file')
    
    args = parser.parse_args()
    
    try:
        verifier = LinkVerifier(args.config)
        
        if args.category:
            verifier.verify_category(args.category, args.verbose)
        elif args.pack:
            verifier.verify_pack(args.pack, args.verbose)
        else:
            parallel = not args.sequential
            verifier.verify_all(parallel, args.workers, args.verbose)
        
        if args.export:
            verifier.export_results(args.export)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
