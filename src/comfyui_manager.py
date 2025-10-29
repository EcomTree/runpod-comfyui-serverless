"""
ComfyUI server management for RunPod Serverless
"""
import os
import shutil
import subprocess
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

import requests

from .config import config


class ComfyUIManager:
    """Manage ComfyUI server lifecycle and operations"""

    def __init__(self):
        self._comfyui_process = None
        self._comfyui_path = config.get_workspace_config()['comfyui_path']
        self._comfyui_logs_path = config.get_workspace_config()['comfyui_logs_path']

    def _wait_for_path(self, path: Path, timeout: int = 20, poll_interval: float = 1.0) -> bool:
        """Wait until a path exists or timeout is reached"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if path.exists():
                return True
            time.sleep(poll_interval)
        return path.exists()

    def _get_volume_base(self) -> Path:
        """Determine the base mount path for the Network Volume"""
        volume_config = config.get_volume_config()
        timeout = volume_config['network_volume_timeout']

        volume_path = volume_config['runpod_volume_path']
        if self._wait_for_path(volume_path, timeout=timeout):
            print(f"📦 Detected Serverless Network Volume at {volume_path}")
            return volume_path

        workspace_path = config.get_workspace_config()['workspace_path']
        print(f"📦 Using {workspace_path} as volume base (no {volume_path} detected)")
        return workspace_path

    def _setup_volume_models(self) -> bool:
        """Setup Volume Models with symlinks"""
        print("📦 Setting up Volume Models with symlinks...")

        try:
            volume_base = self._get_volume_base()
            print(f"🔍 Volume Base: {volume_base}")

            # Check the most common Volume Model structures
            possible_volume_model_dirs = [
                volume_base / "ComfyUI" / "models",
                volume_base / "models",
                volume_base / "comfyui_models",
            ]

            volume_models_dir = None
            for path in possible_volume_model_dirs:
                if path.exists():
                    print(f"✅ Volume Models Directory found: {path}")
                    volume_models_dir = path
                    break

            if not volume_models_dir:
                print(f"⚠️ No Volume Models found in: {[str(p) for p in possible_volume_model_dirs]}")
                return False

            # ComfyUI Models Directory
            comfy_models_dir = config.get_workspace_config()['comfyui_models_path']
            comfy_models_parent = comfy_models_dir.parent
            comfy_models_parent.mkdir(parents=True, exist_ok=True)

            # Check for self-referential symlink
            try:
                volume_resolved = volume_models_dir.resolve()
                comfy_resolved = comfy_models_dir.resolve() if comfy_models_dir.exists() else comfy_models_dir

                if volume_resolved == comfy_resolved:
                    print(f"✅ Volume models directory is already at the expected location: {comfy_models_dir}")
                    print(f"⚠️ Skipping symlink creation (would be self-referential)")
                    return True

                # Also check if both are under WORKSPACE_PATH
                if volume_base == config.get_workspace_config()['workspace_path']:
                    print(f"⚠️ No network volume detected (using {volume_base} as fallback)")
                    print(f"✅ Using local models directory: {comfy_models_dir}")
                    comfy_models_dir.mkdir(parents=True, exist_ok=True)
                    return True
            except (FileNotFoundError, OSError) as e:
                print(f"⚠️ Path resolution warning: {e}")

            # Handle existing symlinks or directories
            symlink_needed = True

            if comfy_models_dir.is_symlink():
                try:
                    current_target = comfy_models_dir.resolve()
                    if current_target == volume_models_dir.resolve():
                        print("🔗 Symlink already exists and points to the volume.")
                        symlink_needed = False
                    else:
                        print(f"🗑️ Removing existing symlink: {comfy_models_dir} → {current_target}")
                        comfy_models_dir.unlink()
                except (FileNotFoundError, OSError):
                    print("🗑️ Removing broken symlink")
                    comfy_models_dir.unlink()
            elif comfy_models_dir.exists():
                print(f"🗑️ Removing local models directory: {comfy_models_dir}")
                shutil.rmtree(comfy_models_dir)

            # Create symlink if needed
            if symlink_needed:
                print(f"🔗 Creating symlink: {comfy_models_dir} → {volume_models_dir}")
                try:
                    comfy_models_dir.symlink_to(volume_models_dir, target_is_directory=True)
                except FileExistsError:
                    print(f"⚠️ Symlink already exists (race condition)")
                    if comfy_models_dir.is_symlink():
                        try:
                            current_target = comfy_models_dir.resolve()
                            if current_target == volume_models_dir.resolve():
                                print("🔗 Symlink is correct")
                            else:
                                print(f"❌ Symlink points to wrong target: {current_target}")
                                return False
                        except (FileNotFoundError, OSError):
                            print("❌ Symlink is broken")
                            return False
                    else:
                        print("❌ Path is blocked by file/directory")
                        return False

            # Verify the symlink
            if comfy_models_dir.is_symlink() and comfy_models_dir.exists():
                print(f"✅ Symlink successfully created and verified!")

                # Show available model types
                model_subdirs = ["checkpoints", "vae", "loras", "unet", "clip", "clip_vision", "text_encoders", "diffusion_models"]
                found_types = []

                for subdir in model_subdirs:
                    subdir_path = comfy_models_dir / subdir
                    if subdir_path.exists():
                        model_files = list(subdir_path.glob("*.safetensors")) + list(subdir_path.glob("*.ckpt"))
                        if model_files:
                            print(f"   📂 {subdir}: {len(model_files)} Models")
                            found_types.append(subdir)
                        else:
                            print(f"   📂 {subdir}: Directory exists, but empty")

                if found_types:
                    print(f"🎯 Models available in: {', '.join(found_types)}")
                    return True
                else:
                    print(f"⚠️ Symlink created, but no models found!")
                    return False
            else:
                print(f"❌ Symlink creation failed!")
                return False

        except Exception as e:
            print(f"❌ Volume Model Setup Error: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def _is_comfyui_running(self) -> bool:
        """Check if ComfyUI is already running"""
        try:
            base_url = config.get_comfyui_base_url()
            response = requests.get(f"{base_url}/system_stats", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        return False

    def _wait_for_comfyui(self, max_retries: int = None, delay: int = 2) -> bool:
        """Wait until ComfyUI is ready"""
        # Use configured timeout or default
        if max_retries is None:
            timeout_seconds = config.get('comfy_startup_timeout', 600)
            max_retries = timeout_seconds // delay
        
        base_url = config.get_comfyui_base_url()
        print(f"⏳ Waiting for ComfyUI to start (timeout: {max_retries * delay}s = {max_retries * delay / 60:.1f} min)...")

        for i in range(max_retries):
            try:
                response = requests.get(f"{base_url}/system_stats", timeout=5)
                if response.status_code == 200:
                    elapsed = (i + 1) * delay
                    print(f"✅ ComfyUI is running (started after ~{elapsed}s = {elapsed / 60:.1f} min)")
                    return True
            except requests.exceptions.RequestException:
                pass

            if i < max_retries - 1:
                if (i + 1) % 5 == 0:
                    elapsed = (i + 1) * delay
                    print(f"⏳ Still waiting for ComfyUI... ({elapsed}s / {max_retries * delay}s)")
                time.sleep(delay)

        print(f"❌ ComfyUI failed to start after {max_retries * delay}s ({max_retries * delay / 60:.1f} min)!")
        return False

    def _force_model_refresh(self) -> bool:
        """Attempt model refresh via manager endpoint, fallback to direct scan"""
        print("🔄 Force Model Refresh after symlink creation...")
        base_url = config.get_comfyui_base_url()
        manager_root = f"{base_url}/manager"

        try:
            discovery_response = requests.get(manager_root, timeout=5)
            print(f"📋 Manager Discovery Status: {discovery_response.status_code}")
        except requests.exceptions.RequestException as discovery_error:
            print(f"⚠️ Manager Endpoint Discovery failed: {discovery_error}")
            return self._direct_model_refresh()

        if discovery_response.status_code == 404:
            print("⚠️ Manager Plugin not available (404)")
            return self._direct_model_refresh()

        if discovery_response.status_code >= 500:
            print(f"⚠️ Manager Discovery error code {discovery_response.status_code}, using fallback")
            return self._direct_model_refresh()

        try:
            refresh_response = requests.post(f"{manager_root}/reboot", timeout=10)
            print(f"📋 Manager Refresh Status: {refresh_response.status_code}")
            if refresh_response.status_code == 200:
                time.sleep(3)
                if not self._wait_for_comfyui():
                    print("⚠️ ComfyUI restart after Model Refresh failed")
                    return False
                print("✅ Model Refresh successful!")
                return True
            print("⚠️ Manager Refresh not successful, trying Direct Scan")
        except requests.exceptions.RequestException as refresh_error:
            print(f"⚠️ Manager Refresh failed: {refresh_error}")

        return self._direct_model_refresh()

    def _direct_model_refresh(self) -> bool:
        """Trigger a direct model refresh via the object_info endpoint"""
        try:
            print("🔄 Alternative: Direct Model Scan...")
            base_url = config.get_comfyui_base_url()
            refresh_response = requests.get(
                f"{base_url}/object_info/CheckpointLoaderSimple",
                params={"refresh": "true"},
                timeout=10,
            )
            print(f"📋 Direct Refresh Response: {refresh_response.status_code}")
            return refresh_response.status_code == 200
        except requests.exceptions.RequestException as error:
            print(f"⚠️ Direct refresh failed: {error}")
            return False

    def _start_comfyui_if_needed(self) -> bool:
        """Start ComfyUI if it's not already running"""
        # Check if ComfyUI is already running
        if self._is_comfyui_running():
            print("✅ ComfyUI is already running, skipping startup")
            if self._comfyui_process and self._comfyui_process.poll() is None:
                print(f"📋 Using existing ComfyUI process (PID: {self._comfyui_process.pid})")
            return True

        # If we have a stale process reference, clear it
        if self._comfyui_process and self._comfyui_process.poll() is not None:
            print("🔄 Clearing stale ComfyUI process reference")
            self._comfyui_process = None

        print("🚀 Starting ComfyUI in background with optimal settings...")
        comfy_cmd = [
            "python", str(self._comfyui_path / "main.py"),
            "--listen", config.get('comfy_host', '127.0.0.1'),
            "--port", str(config.get('comfy_port', 8188)),
            "--normalvram",
            "--preview-method", "auto",
            "--verbose",
            "--cache-lru", "3"
        ]
        
        # Add performance optimizations if enabled
        if config.get('enable_torch_compile', False):
            comfy_cmd.append("--enable-compile")
            print("⚡ torch.compile enabled for 20-30% speed boost")
        
        # Add fast startup flag for serverless
        if config.get('fast_startup', True):
            comfy_cmd.append("--fast")
            print("🚀 Fast startup mode enabled for serverless")
        # Serverless optimization: Pre-warm CUDA
        if config.get('prewarm_cuda', True):
            self._prewarm_cuda()
        
        print(f"🎯 ComfyUI Start Command: {' '.join(comfy_cmd)}")

        # Create log files for debugging
        self._comfyui_logs_path.mkdir(exist_ok=True)
        stdout_log = self._comfyui_logs_path / "comfyui_stdout.log"
        stderr_log = self._comfyui_logs_path / "comfyui_stderr.log"

        try:
            with open(stdout_log, "a") as stdout_file, open(stderr_log, "a") as stderr_file:

                self._comfyui_process = subprocess.Popen(
                    comfy_cmd,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd=str(self._comfyui_path)
                )

                print(f"📋 ComfyUI process started (PID: {self._comfyui_process.pid})")
                print(f"📝 Logs: stdout={stdout_log}, stderr={stderr_log}")

                # Wait until ComfyUI is ready
                if not self._wait_for_comfyui():
                    print("❌ ComfyUI failed to start, check logs for details")

                    try:
                        with open(stderr_log, "r") as f:
                            lines = f.readlines()
                            last_lines = lines[-50:] if len(lines) > 50 else lines
                            print("=" * 60)
                            print("📋 Last 50 lines of ComfyUI stderr:")
                            print("=" * 60)
                            for line in last_lines:
                                print(line.rstrip())
                            print("=" * 60)
                    except Exception as e:
                        print(f"⚠️ Could not read stderr log: {e}")

                    return False

                return True

        except Exception as e:
            print(f"❌ Failed to start ComfyUI: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            return False

    def run_workflow(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute ComfyUI workflow"""
        from .workflow_processor import workflow_processor

        base_url = config.get_comfyui_base_url()
        client_id = str(uuid.uuid4())
        workflow_start_time = time.time()

        try:
            print(f"📤 Sending workflow to ComfyUI API...")
            print(f"🔗 URL: {base_url}/prompt")
            print(f"🆔 Client ID: {client_id}")
            print(f"📋 Workflow Node Count: {workflow_processor.count_workflow_nodes(workflow)}")
            print(f"🔍 Workflow Nodes: {workflow_processor.get_workflow_node_ids(workflow)}")

            # Test system stats
            print(f"🔄 Testing ComfyUI System Stats...")
            stats_response = requests.get(f"{base_url}/system_stats", timeout=10)
            print(f"✅ System Stats: {stats_response.status_code}")

            # Test available models
            print(f"🔄 Testing available models...")
            models_response = requests.get(f"{base_url}/object_info", timeout=10)
            if models_response.status_code == 200:
                object_info = models_response.json()
                checkpoints = workflow_processor.extract_checkpoint_names(object_info)
                print(f"📋 Available Checkpoints: {checkpoints}")
                if not checkpoints:
                    print("⚠️ No checkpoints found!")

            # Check output directory
            output_dir = config.get_workspace_config()['comfyui_output_path']
            print(f"📁 Output Dir: {output_dir}, exists: {output_dir.exists()}, writable: {os.access(output_dir, os.W_OK) if output_dir.exists() else False}")

            # Count SaveImage nodes
            save_nodes = workflow_processor.find_save_nodes(workflow)
            print(f"💾 SaveImage Nodes found: {len(save_nodes)}")

            print(f"🚀 Sending workflow with client_id...")

            response = requests.post(
                f"{base_url}/prompt",
                json={"prompt": workflow, "client_id": client_id},
                timeout=30
            )

            print(f"📤 Response Status: {response.status_code}")
            print(f"📤 Response Headers: {dict(response.headers)}")

            if response.status_code != 200:
                print(f"📜 Response Body: {response.text}")
                return None

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                print(f"❌ No prompt_id received: {result}")
                return None

            print(f"✅ Workflow sent. Prompt ID: {prompt_id}")

            # Wait for completion
            workflow_config = config.get_workflow_config()
            max_wait = workflow_config['max_wait_time']
            poll_interval = workflow_config['poll_interval']
            print(f"⏳ Workflow execution timeout: {max_wait}s ({max_wait / 60:.0f} min)")

            start_time = time.monotonic()
            while True:
                elapsed = time.monotonic() - start_time

                try:
                    history_response = requests.get(f"{base_url}/history/{prompt_id}", timeout=10)
                    if history_response.status_code == 200:
                        history = history_response.json()
                        if prompt_id in history:
                            prompt_history = history[prompt_id]
                            status = prompt_history.get("status", {})

                            if status.get("status_str") == "success":
                                print(f"✅ Workflow completed successfully!")
                                prompt_history["_workflow_start_time"] = workflow_start_time
                                return prompt_history
                            elif status.get("status_str") == "error":
                                print(f"❌ Workflow Error: {status}")
                                return None

                except requests.exceptions.RequestException as e:
                    print(f"⚠️ History API Error: {e}")

                if elapsed >= max_wait:
                    print(f"⏰ Workflow Timeout after {int(elapsed)}s (max: {max_wait}s)")
                    return None

                remaining = max_wait - elapsed
                sleep_time = min(poll_interval, remaining)
                print(f"⏳ Workflow running... ({int(elapsed)}s / {max_wait}s)")
                time.sleep(sleep_time)

        except requests.exceptions.RequestException as e:
            print(f"❌ ComfyUI API Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Workflow Error: {e}")
            return None

    def find_generated_images(self, result: Dict[str, Any], workflow_start_time: float) -> List[Path]:
        """Find generated images from workflow result"""

        image_paths = []
        outputs = result.get("outputs", {})

        # Search all output nodes for images
        expected_files = []
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    filename = img_info.get("filename")
                    subfolder = img_info.get("subfolder", "")
                    if filename:
                        if subfolder:
                            full_path = config.get_workspace_config()['comfyui_output_path'] / subfolder / filename
                        else:
                            full_path = config.get_workspace_config()['comfyui_output_path'] / filename

                        expected_files.append(full_path)
                        if full_path.exists():
                            image_paths.append(full_path)
                            print(f"🖼️ Found: {full_path.name}")

        # Fallback: Search output directory recursively for new images
        if not image_paths:
            print("🔍 Fallback: Recursively searching output directory for images created after workflow start...")
            output_dir = config.get_workspace_config()['comfyui_output_path']
            if output_dir.exists():
                supported_extensions = config.get_supported_extensions()
                cutoff_time = workflow_start_time

                for ext in supported_extensions['image']:
                    for img_path in output_dir.rglob(ext):
                        if img_path.stat().st_mtime > cutoff_time:
                            image_paths.append(img_path)
                            rel_path = img_path.relative_to(output_dir)
                            print(f"🖼️ New image found: {rel_path} (mtime: {img_path.stat().st_mtime}, cutoff: {cutoff_time})")

                if not image_paths:
                    print(f"⚠️ No images found created after {cutoff_time} (workflow start time)")

                    # List recent files for debugging
                    recent_files = []
                    for ext in supported_extensions['image']:
                        recent_files.extend(output_dir.rglob(ext))
                    recent_files = sorted(recent_files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
                    if recent_files:
                        print(f"📋 Most recent images in output directory:")
                        for f in recent_files:
                            rel_path = f.relative_to(output_dir)
                            print(f"   - {rel_path} (mtime: {f.stat().st_mtime})")

        return image_paths

    def cleanup_temp_files(self, file_paths: List[Path]) -> int:
        """Clean up temporary ComfyUI output files"""
        if not config.get('cleanup_temp_files', True):
            print("📋 Cleanup disabled via CLEANUP_TEMP_FILES=false")
            return 0

        deleted_count = 0
        for file_path in file_paths:
            try:
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete temp file {file_path.name}: {e}")

        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} temporary file(s)")

        return deleted_count

    def _prewarm_cuda(self):
        """Pre-warm CUDA for faster first inference (serverless optimization)"""
        try:
            import torch
            if torch.cuda.is_available():
                print("🔥 Pre-warming CUDA...")
                # Quick CUDA operation to initialize context
                _ = torch.zeros(1, device='cuda')
                torch.cuda.synchronize()
                print("✅ CUDA pre-warmed")
        except Exception as e:
            print(f"⚠️ CUDA pre-warm failed: {e}")
    
    def _apply_performance_optimizations(self):
        """Apply runtime performance optimizations"""
        try:
            import torch
            
            print("⚡ Applying performance optimizations...")
            
            # Enable TF32 for Ampere+ GPUs
            if hasattr(torch.backends.cuda, 'matmul'):
                torch.backends.cuda.matmul.allow_tf32 = True
                print("  ✓ TF32 matmul enabled")
            
            if hasattr(torch.backends.cudnn, 'allow_tf32'):
                torch.backends.cudnn.allow_tf32 = True
                print("  ✓ TF32 cuDNN enabled")
            
            # Enable cuDNN benchmarking
            torch.backends.cudnn.benchmark = True
            print("  ✓ cuDNN benchmark enabled")
            
            # Disable deterministic for performance
            torch.backends.cudnn.deterministic = False
            print("  ✓ Non-deterministic mode for speed")
            
            print("✅ Performance optimizations applied")
        except Exception as e:
            print(f"⚠️ Performance optimization failed: {e}")
    
    def start_server_if_needed(self) -> bool:
        """Start ComfyUI server if needed and setup models"""
        # Apply performance optimizations at startup
        if config.get('enable_optimizations', True):
            self._apply_performance_optimizations()
        
        # Volume Models Setup
        comfy_models_dir = config.get_workspace_config()['comfyui_models_path']
        just_setup_models = False

        if not comfy_models_dir.is_symlink() or not comfy_models_dir.exists():
            print("📦 Setting up Volume Models...")
            volume_setup_success = self._setup_volume_models()
            if not volume_setup_success:
                print("⚠️ Volume Models Setup failed - ComfyUI will start without Volume Models")
            else:
                print("✅ Volume Models Setup successful - ComfyUI will find models at startup!")
                time.sleep(2)
                print("🔗 Symlinks stabilized - ComfyUI can now start")
                just_setup_models = True

        # Start ComfyUI if not already running
        if not self._start_comfyui_if_needed():
            return False

        # Model refresh only needed after initial setup
        if just_setup_models and config.get('comfy_refresh_models', True):
            print("⏳ Waiting for ComfyUI model scanning to initialize...")
            time.sleep(3)  # Reduced from 5s for faster serverless startup
            self._force_model_refresh()

        return True


# Global ComfyUI manager instance
# Note: Singleton pattern is intentional for serverless functions.
# RunPod reuses containers between invocations, making this optimal for:
# - Performance: Avoids repeated initialization overhead
# - State management: Maintains ComfyUI server process across requests
# - Resource efficiency: Single process manager per container
# Thread safety is not required as serverless invocations are single-threaded.
comfyui_manager = ComfyUIManager()
