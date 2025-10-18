"""
Configuration management for RunPod ComfyUI Serverless Handler
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration management class"""

    def __init__(self):
        self._config = {}
        self._load_config()

    @property
    def logger(self):
        """Get logger for this module"""
        from .logger import get_logger
        return get_logger('config')

    def _load_config(self):
        """Load configuration from environment variables"""
        # ComfyUI Configuration
        self._config.update({
            'comfy_port': self._parse_int_env('COMFY_PORT', '8188'),
            'comfy_host': os.getenv('COMFY_HOST', '127.0.0.1'),
            'randomize_seeds': self._parse_bool_env('RANDOMIZE_SEEDS', 'true'),
            'comfy_refresh_models': self._parse_bool_env('COMFYUI_REFRESH_MODELS', 'true'),
            'cleanup_temp_files': self._parse_bool_env('CLEANUP_TEMP_FILES', 'true'),
            'debug_s3_urls': self._parse_bool_env('DEBUG_S3_URLS', 'false'),
        })

        # S3 Configuration
        self._config['s3'] = {
            'bucket': os.getenv('S3_BUCKET'),
            'access_key': os.getenv('S3_ACCESS_KEY'),
            'secret_key': os.getenv('S3_SECRET_KEY'),
            'endpoint_url': os.getenv('S3_ENDPOINT_URL'),
            'region': os.getenv('S3_REGION', 'auto'),
            'public_url': os.getenv('S3_PUBLIC_URL'),
            'signed_url_expiry': int(os.getenv('S3_SIGNED_URL_EXPIRY', '3600')),
            'cache_control': os.getenv('S3_CACHE_CONTROL', 'public, max-age=31536000'),
            'signature_version': os.getenv('S3_SIGNATURE_VERSION', 's3v4'),
            'addressing_style': os.getenv('S3_ADDRESSING_STYLE', 'path'),
        }

        # Volume Configuration
        self._config['volume'] = {
            'runpod_volume_path': Path(os.getenv('RUNPOD_VOLUME_PATH', '/runpod-volume')),
            'runpod_output_dir': os.getenv('RUNPOD_OUTPUT_DIR'),
            'network_volume_timeout': self._parse_int_env('NETWORK_VOLUME_TIMEOUT', '15'),
        }

        # Workspace Configuration
        self._config['workspace'] = {
            'workspace_path': Path('/workspace'),
            'comfyui_path': Path('/workspace/ComfyUI'),
            'comfyui_models_path': Path('/workspace/ComfyUI/models'),
            'comfyui_output_path': Path('/workspace/ComfyUI/output'),
            'comfyui_logs_path': Path('/workspace/logs'),
        }

        # Workflow Configuration
        self._config['workflow'] = {
            'max_wait_time': 3600,  # 60 minutes for video rendering
            'poll_interval': 5,     # seconds
            'default_workflow_duration': 60,  # seconds
        }

    def _parse_bool_env(self, key: str, default: str = 'false') -> bool:
        """Safely parse environment variable as boolean"""
        value = os.getenv(key, default).lower()
        return value in {'1', 'true', 'yes', 'on'}

    def _parse_int_env(self, key: str, default: str) -> int:
        """Safely parse environment variable as integer"""
        value = os.getenv(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            print(f"[config] WARNING: Invalid integer value for {key}: '{value}', attempting to use default: {default}")
            try:
                return int(default)
            except (ValueError, TypeError):
                print(f"[config] ERROR: Invalid default integer value for {key}: '{default}', using fallback value 0")
                return 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def get_s3_config(self) -> Dict[str, Any]:
        """Get S3 configuration"""
        return self._config['s3']

    def get_volume_config(self) -> Dict[str, Any]:
        """Get volume configuration"""
        return self._config['volume']

    def get_workspace_config(self) -> Dict[str, Any]:
        """Get workspace configuration"""
        return self._config['workspace']

    def get_workflow_config(self) -> Dict[str, Any]:
        """Get workflow configuration"""
        return self._config['workflow']

    def is_s3_configured(self) -> bool:
        """Check if S3 is properly configured"""
        s3_config = self.get_s3_config()
        return all([
            s3_config['bucket'],
            s3_config['access_key'],
            s3_config['secret_key']
        ])

    def get_comfyui_base_url(self) -> str:
        """Get ComfyUI base URL"""
        return f"http://{self._config['comfy_host']}:{self._config['comfy_port']}"

    def get_supported_extensions(self) -> Dict[str, list]:
        """Get supported file extensions"""
        return {
            'image': ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.gif'],
            'video': ['*.mp4', '*.webm', '*.mov', '*.avi']
        }


# Global configuration instance
config = Config()