"""
Project Manager Module

Provides project maintenance and management functionality for the Codex agent.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple
import json
import time
from datetime import datetime, timedelta

class MaintenanceTask(NamedTuple):
    """Represents a maintenance task."""
    name: str
    description: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]

class MaintenanceReport(NamedTuple):
    """Report of maintenance tasks."""
    tasks_completed: List[MaintenanceTask]
    tasks_failed: List[MaintenanceTask]
    total_duration: float
    timestamp: datetime

class ProjectManager:
    """Project maintenance manager."""
    
    def __init__(self, config):
        self.config = config
        self.project_root = Path(config.get('PROJECT_ROOT', '/workspace'))
        self.temp_dir = Path(config.get('TEMP_DIR', '/tmp/codex-agent'))
        
        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_maintenance(self) -> MaintenanceReport:
        """Run all maintenance tasks."""
        start_time = datetime.now()
        tasks = []
        
        # Define maintenance tasks
        maintenance_tasks = [
            self._cleanup_temp_files,
            self._cleanup_old_logs,
            self._check_disk_space,
            self._update_dependencies,
            self._backup_important_files,
            self._check_file_permissions,
            self._optimize_git_repo,
        ]
        
        # Run tasks
        for task_func in maintenance_tasks:
            task = await self._run_maintenance_task(task_func)
            tasks.append(task)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Separate completed and failed tasks
        completed_tasks = [t for t in tasks if t.status == 'completed']
        failed_tasks = [t for t in tasks if t.status == 'failed']
        
        return MaintenanceReport(
            tasks_completed=completed_tasks,
            tasks_failed=failed_tasks,
            total_duration=total_duration,
            timestamp=end_time
        )
    
    async def _run_maintenance_task(self, task_func) -> MaintenanceTask:
        """Run a single maintenance task."""
        task_name = task_func.__name__
        task_description = task_func.__doc__ or f"Run {task_name}"
        
        task = MaintenanceTask(
            name=task_name,
            description=task_description,
            status='running',
            start_time=datetime.now(),
            end_time=None,
            error=None
        )
        
        try:
            await task_func()
            task = task._replace(
                status='completed',
                end_time=datetime.now()
            )
        except Exception as e:
            task = task._replace(
                status='failed',
                end_time=datetime.now(),
                error=str(e)
            )
        
        return task
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files."""
        if not self.config.get('CLEANUP_TEMP_FILES', True):
            return
        
        temp_age_hours = int(self.config.get('TEMP_FILE_AGE_HOURS', 24))
        cutoff_time = datetime.now() - timedelta(hours=temp_age_hours)
        
        cleaned_count = 0
        for file_path in self.temp_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                except Exception:
                    pass  # Ignore errors for individual files
        
        print(f"Cleaned up {cleaned_count} temporary files")
    
    async def _cleanup_old_logs(self):
        """Clean up old log files."""
        log_dir = self.project_root / 'logs'
        if not log_dir.exists():
            return
        
        log_retention_days = int(self.config.get('LOG_RETENTION_DAYS', 7))
        cutoff_time = datetime.now() - timedelta(days=log_retention_days)
        
        cleaned_count = 0
        for log_file in log_dir.glob('*.log'):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            except Exception:
                pass
        
        print(f"Cleaned up {cleaned_count} old log files")
    
    async def _check_disk_space(self):
        """Check available disk space."""
        try:
            stat = os.statvfs(self.project_root)
            free_space_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
            
            min_free_space = float(self.config.get('MIN_FREE_SPACE_GB', 1.0))
            if free_space_gb < min_free_space:
                raise Exception(f"Low disk space: {free_space_gb:.2f}GB free (minimum: {min_free_space}GB)")
            
            print(f"Disk space OK: {free_space_gb:.2f}GB free")
        except Exception as e:
            raise Exception(f"Disk space check failed: {e}")
    
    async def _update_dependencies(self):
        """Update project dependencies."""
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            print("No requirements.txt found, skipping dependency update")
            return
        
        try:
            # Check if virtual environment exists
            venv_path = self.project_root / '.venv'
            if not venv_path.exists():
                print("No virtual environment found, skipping dependency update")
                return
            
            # Update pip
            await self._run_command(['python', '-m', 'pip', 'install', '--upgrade', 'pip'])
            
            # Update requirements
            await self._run_command(['python', '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'])
            
            print("Dependencies updated successfully")
        except Exception as e:
            raise Exception(f"Dependency update failed: {e}")
    
    async def _backup_important_files(self):
        """Backup important project files."""
        if not self.config.get('ENABLE_BACKUP', True):
            return
        
        backup_dir = self.project_root / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Define important files to backup
        important_files = [
            'requirements.txt',
            '.env',
            'README.md',
            'Dockerfile',
            'codex_agent.py',
        ]
        
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = backup_dir / f"backup_{backup_timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        backed_up_count = 0
        for file_name in important_files:
            source_file = self.project_root / file_name
            if source_file.exists():
                try:
                    shutil.copy2(source_file, backup_subdir / file_name)
                    backed_up_count += 1
                except Exception:
                    pass
        
        # Clean up old backups
        retention_days = int(self.config.get('BACKUP_RETENTION_DAYS', 7))
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        for backup_path in backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith('backup_'):
                try:
                    backup_time = datetime.strptime(backup_path.name[7:], '%Y%m%d_%H%M%S')
                    if backup_time < cutoff_time:
                        shutil.rmtree(backup_path)
                except Exception:
                    pass
        
        print(f"Backed up {backed_up_count} important files")
    
    async def _check_file_permissions(self):
        """Check file permissions."""
        # Check if important files are readable
        important_files = [
            'requirements.txt',
            'codex_agent.py',
            'src/config.py',
        ]
        
        for file_name in important_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                if not os.access(file_path, os.R_OK):
                    raise Exception(f"File not readable: {file_name}")
        
        # Check if we can write to project directory
        if not os.access(self.project_root, os.W_OK):
            raise Exception(f"Project directory not writable: {self.project_root}")
        
        print("File permissions OK")
    
    async def _optimize_git_repo(self):
        """Optimize git repository."""
        try:
            # Run git gc to optimize repository
            await self._run_command(['git', 'gc', '--prune=now'])
            
            # Run git repack to optimize pack files
            await self._run_command(['git', 'repack', '-ad'])
            
            print("Git repository optimized")
        except Exception as e:
            # Git optimization is not critical, just log the error
            print(f"Git optimization failed (non-critical): {e}")
    
    async def _run_command(self, cmd: List[str]) -> None:
        """Run a command and raise exception on failure."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.project_root
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else stdout.decode()
            raise Exception(f"Command failed: {' '.join(cmd)} - {error_msg}")
    
    async def get_project_info(self) -> Dict[str, Any]:
        """Get project information."""
        info = {
            'project_root': str(self.project_root),
            'temp_dir': str(self.temp_dir),
            'config': dict(self.config),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add file counts
        try:
            py_files = list(self.project_root.rglob('*.py'))
            info['python_files'] = len(py_files)
            
            total_files = list(self.project_root.rglob('*'))
            info['total_files'] = len([f for f in total_files if f.is_file()])
        except Exception:
            info['python_files'] = 0
            info['total_files'] = 0
        
        return info