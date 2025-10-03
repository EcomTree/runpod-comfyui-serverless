#!/usr/bin/env python3

import runpod
import requests
import json
import time
import subprocess
import os
import sys
import uuid
from pathlib import Path


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
    print("📦 Setup Volume Models mit Symlinks...")
    
    try:
        volume_base = _get_volume_base()
        print(f"🔍 Volume Base: {volume_base}")
        
        # Checke die häufigsten Volume Model Strukturen
        possible_volume_model_dirs = [
            volume_base / "ComfyUI" / "models",     # /runpod-volume/ComfyUI/models
            volume_base / "models",                  # /runpod-volume/models  
            volume_base / "comfyui_models",         # /runpod-volume/comfyui_models
        ]
        
        volume_models_dir = None
        for path in possible_volume_model_dirs:
            if path.exists():
                print(f"✅ Volume Models Directory gefunden: {path}")
                volume_models_dir = path
                break
        
        if not volume_models_dir:
            print(f"⚠️ Keine Volume Models gefunden in: {[str(p) for p in possible_volume_model_dirs]}")
            return False
        
        # ComfyUI Models Directory - hier erwartet ComfyUI die Models
        comfy_models_dir = Path("/workspace/ComfyUI/models")
        comfy_models_parent = comfy_models_dir.parent
        comfy_models_parent.mkdir(parents=True, exist_ok=True)

        symlink_needed = True
        
        if comfy_models_dir.is_symlink():
            try:
                current_target = comfy_models_dir.resolve()
                if current_target == volume_models_dir.resolve():
                    print("🔗 Symlink existiert bereits und zeigt auf das Volume.")
                    symlink_needed = False
                else:
                    print(f"🗑️ Entferne bestehenden Symlink: {comfy_models_dir} → {current_target}")
                    comfy_models_dir.unlink()
            except (FileNotFoundError, OSError) as resolve_error:
                # Broken/malformed symlink - kann nicht resolved werden
                print(f"🗑️ Entferne kaputten Symlink (resolve failed: {resolve_error})...")
                comfy_models_dir.unlink()
        elif comfy_models_dir.exists():
            print(f"🗑️ Entferne lokales models Verzeichnis: {comfy_models_dir}")
            import shutil
            shutil.rmtree(comfy_models_dir)
        
        # Erstelle Symlink nur wenn nötig
        if symlink_needed:
            print(f"🔗 Erstelle Symlink: {comfy_models_dir} → {volume_models_dir}")
            try:
                comfy_models_dir.symlink_to(volume_models_dir, target_is_directory=True)
            except FileExistsError:
                # Edge case: Symlink wurde zwischenzeitlich von anderem Prozess erstellt
                print(f"⚠️ Symlink existiert bereits (race condition)")
                # Verifiziere dass er korrekt ist
                if comfy_models_dir.is_symlink():
                    try:
                        current_target = comfy_models_dir.resolve()
                        if current_target == volume_models_dir.resolve():
                            print("🔗 Symlink ist korrekt")
                        else:
                            print(f"❌ Symlink zeigt auf falsches Ziel: {current_target}")
                            return False
                    except (FileNotFoundError, OSError):
                        print("❌ Symlink ist kaputt")
                        return False
                else:
                    print("❌ Pfad wird von Datei/Directory blockiert")
                    return False
        
        # Verifiziere den Symlink
        if comfy_models_dir.is_symlink() and comfy_models_dir.exists():
            print(f"✅ Symlink erfolgreich erstellt und verifiziert!")
            
            # Zeige verfügbare Model-Types
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
                        print(f"   📂 {subdir}: Verzeichnis vorhanden, aber leer")
            
            if found_types:
                print(f"🎯 Models verfügbar in: {', '.join(found_types)}")
                return True
            else:
                print(f"⚠️ Symlink erstellt, aber keine Models gefunden!")
                return False
        else:
            print(f"❌ Symlink-Erstellung fehlgeschlagen!")
            return False
            
    except Exception as e:
        print(f"❌ Volume Model Setup Fehler: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

def _wait_for_comfyui(max_retries=30, delay=2):
    """Wait until ComfyUI is ready."""
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
            if response.status_code == 200:
                print(f"✅ ComfyUI läuft.")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"⏳ Warte auf ComfyUI... ({i+1}/{max_retries})")
            time.sleep(delay)
    
    print("❌ ComfyUI startet nicht!")
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
        print(f"⚠️ Direct refresh fehlgeschlagen: {error}")
        return False


def _force_model_refresh() -> bool:
    """Attempt model refresh via manager endpoint, fallback to direct scan."""

    print("🔄 Force Model Refresh nach Symlink-Erstellung...")
    manager_root = "http://127.0.0.1:8188/manager"

    try:
        discovery_response = requests.get(manager_root, timeout=5)
        print(f"📋 Manager Discovery Status: {discovery_response.status_code}")
    except requests.exceptions.RequestException as discovery_error:
        print(f"⚠️ Manager Endpoint Discovery fehlgeschlagen: {discovery_error}")
        return _direct_model_refresh()

    if discovery_response.status_code == 404:
        print("⚠️ Manager Plugin nicht vorhanden (404)")
        return _direct_model_refresh()

    if discovery_response.status_code >= 500:
        print(f"⚠️ Manager Discovery Fehlercode {discovery_response.status_code}, nutze Fallback")
        return _direct_model_refresh()

    try:
        refresh_response = requests.post(f"{manager_root}/reboot", timeout=10)
        print(f"📋 Manager Refresh Status: {refresh_response.status_code}")
        if refresh_response.status_code == 200:
            # Warte kurz auf Neustart
            time.sleep(3)
            if not _wait_for_comfyui():
                print("⚠️ ComfyUI restart nach Model Refresh fehlgeschlagen")
                return False
            print("✅ Model Refresh erfolgreich!")
            return True
        print("⚠️ Manager Refresh nicht erfolgreich, versuche Direct Scan")
    except requests.exceptions.RequestException as refresh_error:
        print(f"⚠️ Manager Refresh fehlgeschlagen: {refresh_error}")

    return _direct_model_refresh()


def _run_workflow(workflow):
    """Execute ComfyUI workflow."""
    client_id = str(uuid.uuid4())
    
    try:
        print(f"📤 Sende Workflow an ComfyUI API...")
        print(f"🔗 URL: http://127.0.0.1:8188/prompt")
        print(f"🆔 Client ID: {client_id}")
        print(f"📋 Workflow Node Count: {len(workflow)}")
        print(f"🔍 Workflow Nodes: {list(workflow.keys())}")
        
        # Test system stats
        print(f"🔄 Teste ComfyUI System Stats...")
        stats_response = requests.get("http://127.0.0.1:8188/system_stats", timeout=10)
        print(f"✅ System Stats: {stats_response.status_code}")
        
        # Test available models
        print(f"🔄 Teste verfügbare Models...")
        models_response = requests.get("http://127.0.0.1:8188/object_info", timeout=10)
        if models_response.status_code == 200:
            object_info = models_response.json()
            checkpoints = object_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("ckpt_name", [])
            print(f"📋 Verfügbare Checkpoints: {checkpoints}")
            if not checkpoints:
                print("⚠️ Keine Checkpoints gefunden!")
        
        # Check output directory
        output_dir = Path("/workspace/ComfyUI/output")
        print(f"📁 Output Dir: {output_dir}, existiert: {output_dir.exists()}, beschreibbar: {os.access(output_dir, os.W_OK) if output_dir.exists() else False}")
        
        # Count SaveImage nodes
        save_nodes = [k for k, v in workflow.items() if v.get("class_type") == "SaveImage"]
        print(f"💾 SaveImage Nodes gefunden: {len(save_nodes)}")
        
        print(f"🚀 Sende Workflow mit client_id...")
        
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
            print(f"❌ Keine prompt_id erhalten: {result}")
            return None
            
        print(f"✅ Workflow gesendet. Prompt ID: {prompt_id}")
        
        # Warte auf Fertigstellung
        max_wait = 300  # 5 Minuten
        start_time = time.monotonic()

        while True:
            try:
                history_response = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}", timeout=10)
                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        prompt_history = history[prompt_id]
                        status = prompt_history.get("status", {})
                        
                        if status.get("status_str") == "success":
                            print(f"✅ Workflow erfolgreich abgeschlossen!")
                            return prompt_history
                        elif status.get("status_str") == "error":
                            print(f"❌ Workflow Fehler: {status}")
                            return None
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ History API Fehler: {e}")
            
            elapsed = time.monotonic() - start_time
            if elapsed >= max_wait:
                print(f"⏰ Workflow Timeout nach {max_wait}s")
                return None
            
            print(f"⏳ Workflow läuft... ({int(elapsed)}s)")
            time.sleep(5)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ComfyUI API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Workflow Error: {e}")
        return None

def _copy_to_volume_output(file_path: Path) -> str:
    """Copy file to the volume output directory."""
    print(f"📁 Kopiere Datei zu Volume Output: {file_path}")
    
    try:
        # Volume Output Directory (persistentes Volume, falls vorhanden)
        volume_output_dir = _get_volume_base() / "comfyui" / "output"
        volume_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Unique filename with timestamp and UUID for better collision resistance
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")
        unique_id = str(uuid.uuid4())[:8]
        dest_filename = f"comfyui-{timestamp_str}-{unique_id}-{file_path.name}"
        dest_path = volume_output_dir / dest_filename
        
        # Datei kopieren
        import shutil
        shutil.copy2(file_path, dest_path)
        
        print(f"✅ Datei erfolgreich kopiert zu: {dest_path}")
        print(f"📊 Dateigröße: {dest_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Pfad für Response zurückgeben (absolut im Container)
        relative_path = str(dest_path)
        return relative_path
        
    except Exception as e:
        print(f"❌ Volume Copy Fehler: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return f"Error copying {file_path.name}: {e}"

def handler(event):
    """
    Runpod handler for ComfyUI workflows.
    """
    print("🚀 Handler gestartet - ComfyUI Workflow wird verarbeitet...")
    print(f"📋 Event Type: {event.get('type', 'unknown')}")
    
    # Heartbeat für Runpod Serverless (verhindert Idle Timeout während Download)
    if event.get("type") == "heartbeat":
        print("💓 Heartbeat empfangen - Worker bleibt aktiv")
        return {"status": "ok"}
    
    try:
        # Volume Models Setup - MUSS vor ComfyUI Start passieren!
        print("📦 Setup Volume Models...")
        volume_setup_success = _setup_volume_models()
        if not volume_setup_success:
            print("⚠️ Volume Models Setup fehlgeschlagen - ComfyUI startet ohne Volume Models")
        else:
            print("✅ Volume Models Setup erfolgreich - ComfyUI wird Models beim Start finden!")
            # Kurze Pause um sicherzustellen dass Symlinks fertig sind
            time.sleep(2)
            print("🔗 Symlinks stabilisiert - ComfyUI kann jetzt starten")
        
        # ComfyUI starten (NACH Volume Setup!)
        print("🚀 Starte ComfyUI im Hintergrund mit optimalen Einstellungen...")
        comfy_cmd = [
            "python", "/workspace/ComfyUI/main.py",
            "--listen", "127.0.0.1",
            "--port", "8188",
            "--normalvram",
            "--preview-method", "auto",
            "--verbose",
            "--cache-lru", "3"  # Small LRU cache for better model detection after symlinks
        ]
        print(f"🎯 ComfyUI Start-Command: {' '.join(comfy_cmd)}")
        
        # Use DEVNULL to prevent subprocess from blocking on unconsumed stdout
        comfy_process = subprocess.Popen(
            comfy_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd="/workspace/ComfyUI"
        )
        
        # Warte bis ComfyUI bereit ist
        if not _wait_for_comfyui():
            return {"error": "ComfyUI konnte nicht gestartet werden"}
        
        # Add delay before model refresh to ensure ComfyUI model scanning is fully initialized
        if volume_setup_success and _parse_bool_env("COMFYUI_REFRESH_MODELS", "true"):
            print("⏳ Waiting for ComfyUI model scanning to initialize...")
            time.sleep(5)
            _force_model_refresh()
        
        # Workflow aus Input extrahieren
        workflow = event.get("input", {}).get("workflow")
        if not workflow:
            return {"error": "Kein 'workflow' in input gefunden"}
        
        # Workflow ausführen
        result = _run_workflow(workflow)
        if not result:
            return {"error": "Workflow konnte nicht ausgeführt werden"}
        
        # Generierte Bilder finden
        image_paths = []
        outputs = result.get("outputs", {})
        
        # Durchsuche alle Output-Nodes nach Bildern
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    filename = img_info.get("filename")
                    if filename:
                        full_path = Path("/workspace/ComfyUI/output") / filename
                        if full_path.exists():
                            image_paths.append(full_path)
                            print(f"🖼️ Bild gefunden: {full_path}")
        
        # Fallback: Suche in output Verzeichnis nach neuen Bildern
        if not image_paths:
            print("🔍 Fallback: Suche in output Verzeichnis...")
            output_dir = Path("/workspace/ComfyUI/output")
            if output_dir.exists():
                for img_path in output_dir.glob("*.png"):
                    # Nur Bilder der letzten 60 Sekunden
                    if time.time() - img_path.stat().st_mtime < 60:
                        image_paths.append(img_path)
                        print(f"🖼️ Neues Bild gefunden: {img_path}")
        
        if not image_paths:
            return {"error": "Keine generierten Bilder gefunden"}
        
        # Bilder zu Volume Output kopieren
        output_paths = []
        for img_path in image_paths:
            volume_path = _copy_to_volume_output(img_path)
            output_paths.append(volume_path)
        
        print(f"✅ Handler erfolgreich! {len(output_paths)} Bilder verarbeitet")
        
        return {
            "volume_paths": output_paths,
            "links": output_paths,  # rückwärtskompatibel
            "total_images": len(output_paths),
            "comfy_result": result
        }
        
    except Exception as e:
        print(f"❌ Handler Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {"error": f"Handler Fehler: {str(e)}"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})