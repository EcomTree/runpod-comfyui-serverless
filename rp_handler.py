#!/usr/bin/env python3

import runpod
import requests
import json
import time
import subprocess
import os
import sys
import uuid
import shutil
import datetime
import traceback
from pathlib import Path

# Global variable to track the ComfyUI process
_comfyui_process = None


def _parse_bool_env(key: str, default: str = "false") -> bool:
    """Safely parse environment variable as boolean."""

    value = os.getenv(key, default).lower()
    return value in {"1", "true", "yes", "on"}


def _wait_for_path(path: Path, timeout: int = 20, poll_interval: float = 1.0) -> bool:
    """Wait until a path exists or timeout is reached."""

    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(poll_interval)

    return path.exists()


def _get_volume_base() -> Path:
    """Determine the base mount path for the Network Volume in Serverless/Pods."""
    runpod_volume = Path("/runpod-volume")
    timeout = int(os.getenv("NETWORK_VOLUME_TIMEOUT", "15"))

    if _wait_for_path(runpod_volume, timeout=timeout):
        print("📦 Detected Serverless Network Volume at /runpod-volume")
        return runpod_volume
    print("📦 Using /workspace as volume base (no /runpod-volume detected)")
    return Path("/workspace")

def _setup_volume_models():
    """Setup Volume Models with symlinks - the only solution that works in Serverless!"""
    print("📦 Setting up Volume Models with symlinks...")
    
    try:
        volume_base = _get_volume_base()
        print(f"🔍 Volume Base: {volume_base}")
        
        # Check the most common Volume Model structures
        possible_volume_model_dirs = [
            volume_base / "ComfyUI" / "models",     # /runpod-volume/ComfyUI/models
            volume_base / "models",                  # /runpod-volume/models  
            volume_base / "comfyui_models",         # /runpod-volume/comfyui_models
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
        
        # ComfyUI Models Directory - where ComfyUI expects the models
        comfy_models_dir = Path("/workspace/ComfyUI/models")
        comfy_models_parent = comfy_models_dir.parent
        comfy_models_parent.mkdir(parents=True, exist_ok=True)

        # Check for self-referential symlink: if volume base is /workspace and volume_models_dir
        # would be the same as or contain comfy_models_dir, skip symlink creation
        try:
            volume_resolved = volume_models_dir.resolve()
            comfy_resolved = comfy_models_dir.resolve() if comfy_models_dir.exists() else comfy_models_dir
            
            if volume_resolved == comfy_resolved:
                print(f"✅ Volume models directory is already at the expected location: {comfy_models_dir}")
                print(f"⚠️ Skipping symlink creation (would be self-referential)")
                return True
            
            # Also check if both are under /workspace (no real volume mounted)
            if volume_base == Path("/workspace"):
                print(f"⚠️ No network volume detected (using /workspace as fallback)")
                print(f"✅ Using local models directory: {comfy_models_dir}")
                # Ensure the directory exists
                comfy_models_dir.mkdir(parents=True, exist_ok=True)
                return True
        except (FileNotFoundError, OSError) as e:
            print(f"⚠️ Path resolution warning: {e}")

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
            except (FileNotFoundError, OSError) as resolve_error:
                # Broken/malformed symlink - cannot be resolved
                print(f"🗑️ Removing broken symlink (resolve failed: {resolve_error})...")
                comfy_models_dir.unlink()
        elif comfy_models_dir.exists():
            print(f"🗑️ Removing local models directory: {comfy_models_dir}")
            shutil.rmtree(comfy_models_dir)
        
        # Create symlink only if needed
        if symlink_needed:
            print(f"🔗 Creating symlink: {comfy_models_dir} → {volume_models_dir}")
            try:
                comfy_models_dir.symlink_to(volume_models_dir, target_is_directory=True)
            except FileExistsError:
                # Edge case: Symlink was created by another process in the meantime
                print(f"⚠️ Symlink already exists (race condition)")
                # Verify that it is correct
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

def _is_comfyui_running():
    """Check if ComfyUI is already running."""
    try:
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False


def _wait_for_comfyui(max_retries=30, delay=2):
    """Wait until ComfyUI is ready."""
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
            if response.status_code == 200:
                print(f"✅ ComfyUI is running.")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"⏳ Waiting for ComfyUI... ({i+1}/{max_retries})")
            time.sleep(delay)
    
    print("❌ ComfyUI failed to start!")
    return False


def _direct_model_refresh() -> bool:
    """Trigger a direct model refresh via the object_info endpoint."""

    try:
        print("🔄 Alternative: Direct Model Scan...")
        refresh_response = requests.get(
            "http://127.0.0.1:8188/object_info/CheckpointLoaderSimple",
            params={"refresh": "true"},
            timeout=10,
        )
        print(f"📋 Direct Refresh Response: {refresh_response.status_code}")
        return refresh_response.status_code == 200
    except requests.exceptions.RequestException as error:
        print(f"⚠️ Direct refresh failed: {error}")
        return False


def _force_model_refresh() -> bool:
    """Attempt model refresh via manager endpoint, fallback to direct scan."""

    print("🔄 Force Model Refresh after symlink creation...")
    manager_root = "http://127.0.0.1:8188/manager"

    try:
        discovery_response = requests.get(manager_root, timeout=5)
        print(f"📋 Manager Discovery Status: {discovery_response.status_code}")
    except requests.exceptions.RequestException as discovery_error:
        print(f"⚠️ Manager Endpoint Discovery failed: {discovery_error}")
        return _direct_model_refresh()

    if discovery_response.status_code == 404:
        print("⚠️ Manager Plugin not available (404)")
        return _direct_model_refresh()

    if discovery_response.status_code >= 500:
        print(f"⚠️ Manager Discovery error code {discovery_response.status_code}, using fallback")
        return _direct_model_refresh()

    try:
        refresh_response = requests.post(f"{manager_root}/reboot", timeout=10)
        print(f"📋 Manager Refresh Status: {refresh_response.status_code}")
        if refresh_response.status_code == 200:
            # Wait briefly for restart
            time.sleep(3)
            if not _wait_for_comfyui():
                print("⚠️ ComfyUI restart after Model Refresh failed")
                return False
            print("✅ Model Refresh successful!")
            return True
        print("⚠️ Manager Refresh not successful, trying Direct Scan")
    except requests.exceptions.RequestException as refresh_error:
        print(f"⚠️ Manager Refresh failed: {refresh_error}")

    return _direct_model_refresh()


def _run_workflow(workflow):
    """Execute ComfyUI workflow."""
    client_id = str(uuid.uuid4())
    workflow_start_time = time.time()  # Track when workflow execution starts
    
    try:
        print(f"📤 Sending workflow to ComfyUI API...")
        print(f"🔗 URL: http://127.0.0.1:8188/prompt")
        print(f"🆔 Client ID: {client_id}")
        print(f"📋 Workflow Node Count: {len(workflow)}")
        print(f"🔍 Workflow Nodes: {list(workflow.keys())}")
        
        # Test system stats
        print(f"🔄 Testing ComfyUI System Stats...")
        stats_response = requests.get("http://127.0.0.1:8188/system_stats", timeout=10)
        print(f"✅ System Stats: {stats_response.status_code}")
        
        # Test available models
        print(f"🔄 Testing available models...")
        models_response = requests.get("http://127.0.0.1:8188/object_info", timeout=10)
        if models_response.status_code == 200:
            object_info = models_response.json()
            checkpoints = object_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [])
            # Handle case where ckpt_name returns a nested list format [[model_names], {}]
            if isinstance(checkpoints, list) and len(checkpoints) > 0 and isinstance(checkpoints[0], list):
                checkpoints = checkpoints[0]
            print(f"📋 Available Checkpoints: {checkpoints}")
            if not checkpoints or (isinstance(checkpoints, list) and len(checkpoints) == 0):
                print("⚠️ No checkpoints found!")
        
        # Check output directory
        output_dir = Path("/workspace/ComfyUI/output")
        print(f"📁 Output Dir: {output_dir}, exists: {output_dir.exists()}, writable: {os.access(output_dir, os.W_OK) if output_dir.exists() else False}")
        
        # Count SaveImage nodes
        save_nodes = [k for k, v in workflow.items() if v.get("class_type") == "SaveImage"]
        print(f"💾 SaveImage Nodes found: {len(save_nodes)}")
        
        print(f"🚀 Sending workflow with client_id...")
        
        response = requests.post(
            "http://127.0.0.1:8188/prompt",
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
        max_wait = 300  # 5 minutes
        start_time = time.monotonic()
        poll_interval = 5  # seconds

        while True:
            elapsed = time.monotonic() - start_time
            
            try:
                history_response = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}", timeout=10)
                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        prompt_history = history[prompt_id]
                        status = prompt_history.get("status", {})
                        
                        if status.get("status_str") == "success":
                            print(f"✅ Workflow completed successfully!")
                            # Add workflow_start_time to the result for image filtering
                            prompt_history["_workflow_start_time"] = workflow_start_time
                            return prompt_history
                        elif status.get("status_str") == "error":
                            print(f"❌ Workflow Error: {status}")
                            return None
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ History API Error: {e}")
            
            # Check timeout after the attempt to allow full duration
            if elapsed >= max_wait:
                print(f"⏰ Workflow Timeout after {int(elapsed)}s (max: {max_wait}s)")
                return None
            
            # Sleep only if we haven't timed out
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

def _copy_to_volume_output(file_path: Path) -> str:
    """Copy file to the volume output directory."""
    print(f"📁 Copying file to Volume Output: {file_path}")
    
    try:
        # Volume Output Directory (persistent volume, if available)
        volume_output_dir = _get_volume_base() / "comfyui" / "output"
        volume_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Unique filename with timestamp and UUID for better collision resistance
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")
        unique_id = str(uuid.uuid4())[:8]
        dest_filename = f"comfyui-{timestamp_str}-{unique_id}-{file_path.name}"
        dest_path = volume_output_dir / dest_filename
        
        # Copy file
        shutil.copy2(file_path, dest_path)
        
        print(f"✅ File successfully copied to: {dest_path}")
        print(f"📊 File size: {dest_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Return path for response (absolute in container)
        relative_path = str(dest_path)
        return relative_path
        
    except Exception as e:
        print(f"❌ Volume Copy Error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"Error copying {file_path.name}: {e}"

def _start_comfyui_if_needed():
    """Start ComfyUI if it's not already running."""
    global _comfyui_process
    
    # Check if ComfyUI is already running
    if _is_comfyui_running():
        print("✅ ComfyUI is already running, skipping startup")
        # Check if we have a process reference and it's still alive
        if _comfyui_process and _comfyui_process.poll() is None:
            print(f"📋 Using existing ComfyUI process (PID: {_comfyui_process.pid})")
        return True
    
    # If we have a stale process reference, clear it
    if _comfyui_process and _comfyui_process.poll() is not None:
        print("🔄 Clearing stale ComfyUI process reference")
        _comfyui_process = None
    
    print("🚀 Starting ComfyUI in background with optimal settings...")
    comfy_cmd = [
        "python", "/workspace/ComfyUI/main.py",
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--normalvram",
        "--preview-method", "auto",
        "--verbose",
        "--cache-lru", "3"  # Small LRU cache for better model detection after symlinks
    ]
    print(f"🎯 ComfyUI Start Command: {' '.join(comfy_cmd)}")
    
    # Create log files for debugging
    log_dir = Path("/workspace/logs")
    log_dir.mkdir(exist_ok=True)
    stdout_log = log_dir / "comfyui_stdout.log"
    stderr_log = log_dir / "comfyui_stderr.log"
    
    # Open log files and start process
    try:
        stdout_file = open(stdout_log, "a")
        stderr_file = open(stderr_log, "a")
        
        _comfyui_process = subprocess.Popen(
            comfy_cmd,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd="/workspace/ComfyUI"
        )
        
        print(f"📋 ComfyUI process started (PID: {_comfyui_process.pid})")
        print(f"📝 Logs: stdout={stdout_log}, stderr={stderr_log}")
        
        # Wait until ComfyUI is ready
        if not _wait_for_comfyui():
            print("❌ ComfyUI failed to start, check logs for details")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start ComfyUI: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False


def handler(event):
    """
    Runpod handler for ComfyUI workflows.
    """
    print("🚀 Handler started - processing ComfyUI workflow...")
    print(f"📋 Event Type: {event.get('type', 'unknown')}")
    
    # Heartbeat for Runpod Serverless (prevents idle timeout during download)
    if event.get("type") == "heartbeat":
        print("💓 Heartbeat received - worker stays active")
        return {"status": "ok"}
    
    try:
        # Volume Models Setup - only on first run or if symlinks are missing
        comfy_models_dir = Path("/workspace/ComfyUI/models")
        if not comfy_models_dir.is_symlink() or not comfy_models_dir.exists():
            print("📦 Setting up Volume Models...")
            volume_setup_success = _setup_volume_models()
            if not volume_setup_success:
                print("⚠️ Volume Models Setup failed - ComfyUI will start without Volume Models")
            else:
                print("✅ Volume Models Setup successful - ComfyUI will find models at startup!")
                # Short pause to ensure symlinks are ready
                time.sleep(2)
                print("🔗 Symlinks stabilized - ComfyUI can now start")
        else:
            print("✅ Volume Models symlink already exists, skipping setup")
            volume_setup_success = True
        
        # Start ComfyUI if not already running
        if not _start_comfyui_if_needed():
            return {"error": "ComfyUI could not be started"}
        
        # Model refresh only needed after initial setup
        if volume_setup_success and _parse_bool_env("COMFYUI_REFRESH_MODELS", "true"):
            # Only refresh if we just set up the volume models
            if not comfy_models_dir.is_symlink():
                print("⏳ Waiting for ComfyUI model scanning to initialize...")
                time.sleep(5)
                _force_model_refresh()
        
        # Extract workflow from input
        workflow = event.get("input", {}).get("workflow")
        if not workflow:
            return {"error": "No 'workflow' found in input"}
        
        # Execute workflow
        result = _run_workflow(workflow)
        if not result:
            return {"error": "Workflow could not be executed"}
        
        # Find generated images
        image_paths = []
        outputs = result.get("outputs", {})
        workflow_start_time = result.get("_workflow_start_time", time.time() - 60)
        
        # Search all output nodes for images
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    filename = img_info.get("filename")
                    if filename:
                        full_path = Path("/workspace/ComfyUI/output") / filename
                        if full_path.exists():
                            image_paths.append(full_path)
                            print(f"🖼️ Image found: {full_path}")
        
        # Fallback: Search output directory for new images created after workflow start
        if not image_paths:
            print("🔍 Fallback: Searching output directory for images created after workflow start...")
            output_dir = Path("/workspace/ComfyUI/output")
            if output_dir.exists():
                # Use workflow_start_time for more accurate filtering
                cutoff_time = workflow_start_time
                for img_path in output_dir.glob("*.png"):
                    # Only images modified after workflow started
                    if img_path.stat().st_mtime >= cutoff_time:
                        image_paths.append(img_path)
                        print(f"🖼️ New image found: {img_path} (mtime: {img_path.stat().st_mtime}, cutoff: {cutoff_time})")
                
                if not image_paths:
                    print(f"⚠️ No images found created after {cutoff_time} (workflow start time)")
                    # List recent files for debugging
                    recent_files = sorted(
                        [f for f in output_dir.glob("*.png")],
                        key=lambda p: p.stat().st_mtime,
                        reverse=True
                    )[:5]
                    if recent_files:
                        print(f"📋 Most recent images in output directory:")
                        for f in recent_files:
                            print(f"   - {f.name} (mtime: {f.stat().st_mtime})")
        
        if not image_paths:
            return {"error": "No generated images found"}
        
        # Copy images to Volume Output
        output_paths = []
        for img_path in image_paths:
            volume_path = _copy_to_volume_output(img_path)
            output_paths.append(volume_path)
        
        print(f"✅ Handler successful! {len(output_paths)} images processed")
        
        return {
            "volume_paths": output_paths,
            "links": output_paths,  # backward compatible
            "total_images": len(output_paths),
            "comfy_result": result
        }
        
    except Exception as e:
        print(f"❌ Handler Error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {"error": f"Handler Error: {str(e)}"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})