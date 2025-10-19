"""
S3 storage handler for RunPod ComfyUI Serverless
"""
import datetime
import mimetypes
import shutil
import traceback
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from .config import config


class S3Handler:
    """Handle S3 storage operations"""

    def __init__(self):
        self._s3_client = None
        self._logger = None
    
    @property
    def logger(self):
        """Lazy initialization of logger to avoid circular imports"""
        if self._logger is None:
            from .logger import get_logger
            self._logger = get_logger('s3_handler')
        return self._logger

    def _get_s3_client(self):
        """Create and return S3 client"""
        if self._s3_client is None:
            s3_config = config.get_s3_config()

            client_kwargs = {
                'aws_access_key_id': s3_config['access_key'],
                'aws_secret_access_key': s3_config['secret_key'],
                'config': Config(
                    signature_version=s3_config['signature_version'],
                    s3={'addressing_style': s3_config['addressing_style']}
                ),
            }

            if s3_config['endpoint_url']:
                client_kwargs['endpoint_url'] = s3_config['endpoint_url']

            if s3_config['region']:
                client_kwargs['region_name'] = s3_config['region']

            self._s3_client = boto3.client('s3', **client_kwargs)

        return self._s3_client

    def _get_content_type(self, file_path: Path) -> str:
        """Determine MIME type based on file extension"""
        if not mimetypes.inited:
            mimetypes.init()

        mime_type, _ = mimetypes.guess_type(str(file_path))

        if mime_type is None:
            fallback_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.gif': 'image/gif',
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.webm': 'video/webm',
            }
            mime_type = fallback_types.get(file_path.suffix.lower(), 'application/octet-stream')

        return mime_type

    def _sanitize_url_for_logging(self, url: str) -> str:
        """Sanitize URL for safe logging by removing sensitive query parameters"""
        try:
            parsed = urlparse(url)

            if parsed.query and 'X-Amz-Signature' in parsed.query:
                sanitized = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    '', '', ''
                ))
                return f"{sanitized} [presigned - query params redacted for security]"
            else:
                return url
        except (ValueError, TypeError):
            return url

    def upload_file(self, file_path: Path, job_id: str) -> Dict[str, Any]:
        """Upload file to S3"""
        self.logger.info(f"Uploading to S3: {file_path.name}")

        try:
            s3_config = config.get_s3_config()
            s3_client = self._get_s3_client()

            # Generate S3 key with job_id prefix and timestamp
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            s3_key = f"{job_id}/{timestamp}_{file_path.name}"

            # Determine content type
            content_type = self._get_content_type(file_path)
            self.logger.debug(f"Detected content type: {content_type}")

            # Upload file
            self.logger.debug(f"Uploading to bucket: {s3_config['bucket']}, key: {s3_key}")
            with open(file_path, "rb") as f:
                s3_client.upload_fileobj(
                    f,
                    s3_config["bucket"],
                    s3_key,
                    ExtraArgs={
                        "ContentType": content_type,
                        "CacheControl": s3_config["cache_control"],
                    }
                )

            # Generate URL
            if s3_config["public_url"]:
                url = f"{s3_config['public_url'].rstrip('/')}/{s3_key}"
            else:
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": s3_config["bucket"], "Key": s3_key},
                    ExpiresIn=s3_config["signed_url_expiry"],
                )

            self.logger.info(f"S3 Upload successful: {s3_key}")

            safe_url = self._sanitize_url_for_logging(url)
            self.logger.info(f"Generated URL: {safe_url}")

            if config.get('debug_s3_urls', False):
                self.logger.warning("DEBUG: Logging full presigned S3 URL for debugging purposes. WARNING: Presigned S3 URLs contain sensitive authentication tokens and should not be shared or logged in production environments.")
                self.logger.warning(f"Full Presigned S3 URL for key {s3_key}: {url}")

            return {
                "success": True,
                "url": url,
                "s3_key": s3_key,
                "error": None
            }

        except NoCredentialsError:
            error_msg = "S3 credentials not found or invalid"
            self.logger.error(f"S3 Upload Error: {error_msg}")
            return {"success": False, "url": None, "error": error_msg}

        except ClientError as e:
            error_msg = f"S3 Client Error: {e}"
            self.logger.error(f"S3 Upload Error: {error_msg}")
            return {"success": False, "url": None, "error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected S3 Error: {e}"
            self.logger.error(f"S3 Upload Error: {error_msg}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "url": None, "error": error_msg}

    def copy_to_volume(self, file_path: Path) -> Dict[str, Any]:
        """Copy file to volume output directory"""
        self.logger.info(f"Copying file to Volume Output: {file_path}")

        try:
            volume_config = config.get_volume_config()
            volume_output_dir = volume_config['runpod_volume_path'] / "comfyui" / "output"
            volume_output_dir.mkdir(parents=True, exist_ok=True)

            # Unique filename with timestamp and UUID for better collision resistance
            now = datetime.datetime.now(datetime.timezone.utc)
            timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")
            unique_id = str(uuid.uuid4())[:8]
            dest_filename = f"comfyui-{timestamp_str}-{unique_id}-{file_path.name}"
            dest_path = volume_output_dir / dest_filename

            # Copy file
            shutil.copy2(file_path, dest_path)

            self.logger.info(f"File successfully copied to: {dest_path}")
            self.logger.debug(f"File size: {dest_path.stat().st_size / (1024*1024):.2f} MB")

            return {
                "success": True,
                "path": str(dest_path),
                "error": None
            }

        except Exception as e:
            error_msg = f"Error copying {file_path.name}: {e}"
            self.logger.error(f"Volume Copy Error: {error_msg}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "path": None,
                "error": error_msg
            }


# Global S3 handler instance
# Note: Singleton pattern is intentional for serverless functions.
# RunPod reuses containers between invocations, optimizing S3 client reuse.
s3_handler = S3Handler()