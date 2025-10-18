"""
Configuration management for Codex Coding Background Agent
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration management class for Codex Agent"""

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
        # Git Configuration
        self._config.update({
            'git_user_email': os.getenv('GIT_USER_EMAIL', 'codex@runpod.io'),
            'git_user_name': os.getenv('GIT_USER_NAME', 'Codex Agent'),
            'git_default_branch': os.getenv('GIT_DEFAULT_BRANCH', 'main'),
        })

        # Development Environment
        self._config['development'] = {
            'python_path': os.getenv('PYTHON_PATH', '/usr/bin/python3'),
            'virtual_env_path': os.getenv('VIRTUAL_ENV_PATH', '.venv'),
            'enable_linting': self._parse_bool_env('ENABLE_LINTING', 'true'),
            'enable_formatting': self._parse_bool_env('ENABLE_FORMATTING', 'true'),
            'enable_type_checking': self._parse_bool_env('ENABLE_TYPE_CHECKING', 'true'),
        }

        # Project Configuration
        self._config['project'] = {
            'project_root': Path(os.getenv('PROJECT_ROOT', '/workspace')),
            'temp_dir': Path(os.getenv('TEMP_DIR', '/tmp/codex-agent')),
            'log_file': os.getenv('LOG_FILE', '/workspace/logs/codex-agent.log'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        }

        # Code Quality Tools
        self._config['quality'] = {
            'linter_tools': os.getenv('LINTER_TOOLS', 'flake8,black,isort,mypy').split(','),
            'test_framework': os.getenv('TEST_FRAMEWORK', 'pytest'),
            'test_coverage_threshold': int(os.getenv('TEST_COVERAGE_THRESHOLD', '80')),
            'doc_format': os.getenv('DOC_FORMAT', 'markdown'),
            'doc_generator': os.getenv('DOC_GENERATOR', 'sphinx'),
            'enable_complexity_analysis': self._parse_bool_env('ENABLE_COMPLEXITY_ANALYSIS', 'true'),
            'max_complexity': int(os.getenv('MAX_COMPLEXITY', '10')),
            'enable_security_scan': self._parse_bool_env('ENABLE_SECURITY_SCAN', 'true'),
            'security_tools': os.getenv('SECURITY_TOOLS', 'bandit,safety').split(','),
        }

        # Repository Management
        self._config['repository'] = {
            'default_remote': os.getenv('DEFAULT_REMOTE', 'origin'),
            'default_branch': os.getenv('DEFAULT_BRANCH', 'main'),
            'auto_commit': self._parse_bool_env('AUTO_COMMIT', 'false'),
            'commit_message_prefix': os.getenv('COMMIT_MESSAGE_PREFIX', 'codex:'),
        }

        # Performance Monitoring
        self._config['monitoring'] = {
            'monitor_memory': self._parse_bool_env('MONITOR_MEMORY', 'true'),
            'max_memory_mb': int(os.getenv('MAX_MEMORY_MB', '2048')),
            'monitor_cpu': self._parse_bool_env('MONITOR_CPU', 'true'),
            'max_cpu_percent': int(os.getenv('MAX_CPU_PERCENT', '80')),
        }

        # File Management
        self._config['files'] = {
            'cleanup_temp_files': self._parse_bool_env('CLEANUP_TEMP_FILES', 'true'),
            'temp_file_age_hours': int(os.getenv('TEMP_FILE_AGE_HOURS', '24')),
            'enable_backup': self._parse_bool_env('ENABLE_BACKUP', 'true'),
            'backup_retention_days': int(os.getenv('BACKUP_RETENTION_DAYS', '7')),
        }

        # Network Configuration
        self._config['network'] = {
            'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'connection_timeout': int(os.getenv('CONNECTION_TIMEOUT', '10')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('RETRY_DELAY', '2')),
        }

        # Debugging
        self._config['debug'] = {
            'debug_mode': self._parse_bool_env('DEBUG_MODE', 'false'),
            'verbose_logging': self._parse_bool_env('VERBOSE_LOGGING', 'false'),
            'trace_execution': self._parse_bool_env('TRACE_EXECUTION', 'false'),
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
            self.logger.warning(f"Invalid integer value for {key}: '{value}', using default: {default}")
            try:
                return int(default)
            except (ValueError, TypeError):
                raise ValueError(f"[config] ERROR: Invalid default integer value for {key}: '{default}' (env value: '{value}')")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)

    def get_development_config(self) -> Dict[str, Any]:
        """Get development configuration"""
        return self._config['development']

    def get_project_config(self) -> Dict[str, Any]:
        """Get project configuration"""
        return self._config['project']

    def get_quality_config(self) -> Dict[str, Any]:
        """Get code quality configuration"""
        return self._config['quality']

    def get_repository_config(self) -> Dict[str, Any]:
        """Get repository configuration"""
        return self._config['repository']

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self._config['monitoring']

    def get_files_config(self) -> Dict[str, Any]:
        """Get file management configuration"""
        return self._config['files']

    def get_network_config(self) -> Dict[str, Any]:
        """Get network configuration"""
        return self._config['network']

    def get_debug_config(self) -> Dict[str, Any]:
        """Get debug configuration"""
        return self._config['debug']

    def is_development_mode(self) -> bool:
        """Check if development mode is enabled"""
        return self.get_debug_config()['debug_mode']

    def get_supported_languages(self) -> Dict[str, list]:
        """Get supported programming languages and their extensions"""
        return {
            'python': ['.py', '.pyi', '.pyc'],
            'javascript': ['.js', '.jsx', '.mjs'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'cpp': ['.cpp', '.cc', '.cxx', '.c++'],
            'c': ['.c'],
            'go': ['.go'],
            'rust': ['.rs'],
            'html': ['.html', '.htm'],
            'css': ['.css', '.scss', '.sass'],
            'json': ['.json'],
            'yaml': ['.yaml', '.yml'],
            'markdown': ['.md', '.markdown'],
            'xml': ['.xml'],
            'sql': ['.sql'],
        }

    def get_project_root(self) -> Path:
        """Get project root directory"""
        return self._config['project']['project_root']

    def get_temp_dir(self) -> Path:
        """Get temporary directory"""
        return self._config['project']['temp_dir']


# Global configuration instance
# Note: Singleton pattern is intentional for background agents.
# Configuration is loaded once at startup and reused across operations.
config = Config()