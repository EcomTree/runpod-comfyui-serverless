#!/usr/bin/env python3

import runpod
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict, Any

# Import our modular components
from src.config import config
from src.comfyui_manager import comfyui_manager
from src.s3_handler import s3_handler
from src.workflow_processor import workflow_processor


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for ComfyUI workflows.

    Args:
        event: RunPod event containing workflow and metadata

    Returns:
        Dict containing results or error information
    """
    print("🚀 Handler started - processing ComfyUI workflow...")
    print(f"📋 Event Type: {event.get('type', 'unknown')}")

    # Handle heartbeat events
    if event.get("type") == "heartbeat":
        print("💓 Heartbeat received - worker stays active")
        return {"status": "ok"}

    try:
        # Start ComfyUI server if needed
        if not comfyui_manager.start_server_if_needed():
            return {"error": "ComfyUI could not be started"}

        # Extract and validate workflow
        workflow = event.get("input", {}).get("workflow")
        if not workflow:
            return {"error": "No 'workflow' found in input"}

        # Randomize seeds if enabled
        workflow = workflow_processor.randomize_seeds(workflow)

        # Execute workflow
        result = comfyui_manager.run_workflow(workflow)
        if not result:
            return {"error": "Workflow could not be executed"}

        # Find generated images
        workflow_start_time = result.get("_workflow_start_time", time.time() - config.get_workflow_config()['default_workflow_duration'])
        image_paths = comfyui_manager.find_generated_images(result, workflow_start_time)

        if not image_paths:
            return {"error": "No generated images found"}

        # Generate job_id for organizing uploads
        job_id = event.get("id", str(uuid.uuid4()))

        # Process images with S3 and/or volume storage
        output_urls = []
        volume_paths = []
        failed_uploads = []
        s3_success_count = 0

        for img_path in image_paths:
            # Always save to volume as backup
            volume_result = s3_handler.copy_to_volume(img_path)
            if volume_result["success"]:
                volume_paths.append(volume_result["path"])

            # Upload to S3 if configured
            if config.is_s3_configured():
                s3_result = s3_handler.upload_file(img_path, job_id)
                if s3_result["success"]:
                    output_urls.append(s3_result["url"])
                    s3_success_count += 1
                else:
                    failed_uploads.append({
                        "source": str(img_path),
                        "error": s3_result["error"]
                    })
                    if volume_result["success"]:
                        output_urls.append(volume_result["path"])
                        print(f"⚠️ S3 upload failed for {img_path.name}, using volume path as fallback")
            else:
                # No S3, use volume paths as URLs
                if volume_result["success"]:
                    output_urls.append(volume_result["path"])

        # Check if we have any output
        if not output_urls:
            # Build clear error message based on storage configuration
            if config.is_s3_configured():
                error_details = "; ".join([f["error"] for f in failed_uploads])
                error_message = f"Failed to upload all images to S3 and no volume paths available: {error_details}"
            else:
                error_message = "Failed to save all images to volume"
            return {"error": error_message}

        # Determine storage type
        actual_storage_type = "s3" if (config.is_s3_configured() and s3_success_count > 0) else "volume"

        # Build response
        response = {
            "links": output_urls,
            "total_images": len(output_urls),
            "job_id": job_id,
            "storage_type": actual_storage_type,
        }

        # Add S3-specific info if S3 was used
        if config.is_s3_configured() and s3_success_count > 0:
            s3_config = config.get_s3_config()
            response["s3_bucket"] = s3_config["bucket"]
            response["local_paths"] = [str(p) for p in image_paths]

        # Add volume paths if available
        if volume_paths:
            response["volume_paths"] = volume_paths

        # Add warnings for failed uploads
        if failed_uploads:
            response["warnings"] = {
                "failed_uploads": len(failed_uploads),
                "details": failed_uploads
            }
            print(f"⚠️ {len(failed_uploads)} image(s) failed to upload")

        # Cleanup temp files if enabled
        comfyui_manager.cleanup_temp_files(image_paths)

        print(f"✅ Handler successful! {len(output_urls)} images processed")
        if actual_storage_type == "s3":
            s3_config = config.get_s3_config()
            print(f"☁️ Images uploaded to S3: {s3_config['bucket']}")

        if volume_paths:
            print(f"📦 Images saved to volume: {volume_paths}")

        # Log all output URLs (sanitized for security)
        for idx, url in enumerate(output_urls, 1):
            sanitized_url = s3_handler._sanitize_url_for_logging(url)
            print(f"🔗 URL {idx}/{len(output_urls)}: {sanitized_url}")

        return response

    except Exception as e:
        print(f"❌ Handler Error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {"error": f"Handler Error: {str(e)}"}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})