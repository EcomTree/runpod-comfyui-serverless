#!/usr/bin/env python3
"""
Link verification script for model downloads
Checks if all URLs in models_download.json are accessible
"""

import json
import argparse
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple
import time

class LinkVerifier:
    """Verify model download links"""
    
    def __init__(self, config_path: str, max_concurrent: int = 10):
        self.config_path = Path(config_path)
        self.max_concurrent = max_concurrent
        self.config = {}
        self.verification_results = {
            'total': 0,
            'accessible': 0,
            'inaccessible': 0,
            'timeout': 0,
            'error': 0
        }
    
    def load_config(self) -> bool:
        """Load model configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Loaded config: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return False
    
    async def verify_url(self, session: aiohttp.ClientSession, 
                        model_type: str, model_name: str, url: str) -> Tuple[str, str, bool, str]:
        """Verify a single URL"""
        try:
            async with session.head(url, allow_redirects=True) as response:
                if response.status == 200:
                    return model_type, model_name, True, f"OK (HTTP {response.status})"
                else:
                    return model_type, model_name, False, f"HTTP {response.status}"
        except asyncio.TimeoutError:
            return model_type, model_name, False, "Timeout"
        except Exception as e:
            return model_type, model_name, False, f"Error: {str(e)[:50]}"
    
    async def verify_all_links(self) -> bool:
        """Verify all model download links"""
        if not self.config:
            print("❌ No config loaded")
            return False
        
        # Collect all URLs
        urls_to_verify = []
        for model_type, models in self.config['models'].items():
            for model in models:
                urls_to_verify.append((
                    model_type,
                    model['name'],
                    model['url']
                ))
        
        if not urls_to_verify:
            print("❌ No URLs found in config")
            return False
        
        self.verification_results['total'] = len(urls_to_verify)
        print(f"🔍 Verifying {len(urls_to_verify)} URLs...")
        
        # Create semaphore for concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def verify_with_semaphore(session, model_type, model_name, url):
            async with semaphore:
                return await self.verify_url(session, model_type, model_name, url)
        
        # Start verification
        start_time = time.time()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'ComfyUI-Link-Verifier/1.0'}
        ) as session:
            tasks = []
            for model_type, model_name, url in urls_to_verify:
                task = asyncio.create_task(
                    verify_with_semaphore(session, model_type, model_name, url)
                )
                tasks.append(task)
            
            # Process results as they complete
            for task in asyncio.as_completed(tasks):
                model_type, model_name, success, message = await task
                
                if success:
                    print(f"✅ {model_type}/{model_name}: {message}")
                    self.verification_results['accessible'] += 1
                else:
                    print(f"❌ {model_type}/{model_name}: {message}")
                    if "Timeout" in message:
                        self.verification_results['timeout'] += 1
                    else:
                        self.verification_results['error'] += 1
                    self.verification_results['inaccessible'] += 1
        
        # Print summary
        elapsed_time = time.time() - start_time
        print(f"\n📊 Verification Summary:")
        print(f"   ✅ Accessible: {self.verification_results['accessible']}")
        print(f"   ❌ Inaccessible: {self.verification_results['inaccessible']}")
        print(f"   ⏱️ Timeouts: {self.verification_results['timeout']}")
        print(f"   🚫 Errors: {self.verification_results['error']}")
        print(f"   📁 Total: {self.verification_results['total']}")
        print(f"   ⏱️ Time: {elapsed_time:.1f} seconds")
        
        return self.verification_results['inaccessible'] == 0
    
    def generate_report(self, output_file: str = None):
        """Generate verification report"""
        if not output_file:
            output_file = f"link_verification_report_{int(time.time())}.json"
        
        report = {
            'timestamp': time.time(),
            'config_file': str(self.config_path),
            'results': self.verification_results,
            'summary': {
                'success_rate': (self.verification_results['accessible'] / self.verification_results['total']) * 100,
                'all_accessible': self.verification_results['inaccessible'] == 0
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Report saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='ComfyUI Link Verifier')
    parser.add_argument('--config', default='/workspace/models_download.json',
                       help='Path to models config file')
    parser.add_argument('--max-concurrent', type=int, default=10,
                       help='Maximum concurrent verifications')
    parser.add_argument('--report', type=str,
                       help='Output file for verification report')
    
    args = parser.parse_args()
    
    # Create verifier
    verifier = LinkVerifier(
        config_path=args.config,
        max_concurrent=args.max_concurrent
    )
    
    # Load config
    if not verifier.load_config():
        return 1
    
    # Verify links
    success = asyncio.run(verifier.verify_all_links())
    
    # Generate report
    verifier.generate_report(args.report)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())