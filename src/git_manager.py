"""
Git Manager Module

Provides git repository management functionality for the Codex agent.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple
import json
import os

class GitStatus(NamedTuple):
    """Git repository status."""
    is_git_repo: bool
    current_branch: str
    has_changes: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    ahead_count: int
    behind_count: int

class GitCommit(NamedTuple):
    """Git commit information."""
    hash: str
    author: str
    date: str
    message: str
    files_changed: List[str]

class GitManager:
    """Git repository manager."""
    
    def __init__(self, config):
        self.config = config
        self.repo_path = Path(config.get('PROJECT_ROOT', '/workspace'))
    
    async def check_changes(self) -> List[str]:
        """Check for changes in the repository."""
        try:
            # Get status
            status = await self.get_status()
            
            if not status.is_git_repo:
                return []
            
            # Return all changed files
            changed_files = status.staged_files + status.unstaged_files + status.untracked_files
            return changed_files
            
        except Exception as e:
            print(f"Error checking git changes: {e}")
            return []
    
    async def get_status(self) -> GitStatus:
        """Get git repository status."""
        try:
            # Check if it's a git repo
            result = await self._run_git_command(['rev-parse', '--git-dir'])
            if result.returncode != 0:
                return GitStatus(
                    is_git_repo=False,
                    current_branch='',
                    has_changes=False,
                    staged_files=[],
                    unstaged_files=[],
                    untracked_files=[],
                    ahead_count=0,
                    behind_count=0
                )
            
            # Get current branch
            branch_result = await self._run_git_command(['branch', '--show-current'])
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ''
            
            # Get status
            status_result = await self._run_git_command(['status', '--porcelain'])
            if status_result.returncode != 0:
                return GitStatus(
                    is_git_repo=True,
                    current_branch=current_branch,
                    has_changes=False,
                    staged_files=[],
                    unstaged_files=[],
                    untracked_files=[],
                    ahead_count=0,
                    behind_count=0
                )
            
            # Parse status output
            staged_files = []
            unstaged_files = []
            untracked_files = []
            
            for line in status_result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                status_code = line[:2]
                filename = line[3:]
                
                if status_code[0] in 'MADRC':
                    staged_files.append(filename)
                if status_code[1] in 'MADRC':
                    unstaged_files.append(filename)
                if status_code == '??':
                    untracked_files.append(filename)
            
            has_changes = bool(staged_files or unstaged_files or untracked_files)
            
            # Get ahead/behind count
            ahead_count = 0
            behind_count = 0
            
            try:
                # Get upstream branch
                upstream_result = await self._run_git_command(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'])
                if upstream_result.returncode == 0:
                    upstream = upstream_result.stdout.strip()
                    
                    # Get ahead count
                    ahead_result = await self._run_git_command(['rev-list', '--count', f'{upstream}..HEAD'])
                    if ahead_result.returncode == 0:
                        ahead_count = int(ahead_result.stdout.strip())
                    
                    # Get behind count
                    behind_result = await self._run_git_command(['rev-list', '--count', f'HEAD..{upstream}'])
                    if behind_result.returncode == 0:
                        behind_count = int(behind_result.stdout.strip())
            
            except Exception:
                pass  # Ignore errors for ahead/behind count
            
            return GitStatus(
                is_git_repo=True,
                current_branch=current_branch,
                has_changes=has_changes,
                staged_files=staged_files,
                unstaged_files=unstaged_files,
                untracked_files=untracked_files,
                ahead_count=ahead_count,
                behind_count=behind_count
            )
            
        except Exception as e:
            print(f"Error getting git status: {e}")
            return GitStatus(
                is_git_repo=False,
                current_branch='',
                has_changes=False,
                staged_files=[],
                unstaged_files=[],
                untracked_files=[],
                ahead_count=0,
                behind_count=0
            )
    
    async def add_files(self, files: List[str]) -> bool:
        """Add files to git staging."""
        try:
            result = await self._run_git_command(['add'] + files)
            return result.returncode == 0
        except Exception as e:
            print(f"Error adding files: {e}")
            return False
    
    async def commit(self, message: str, files: Optional[List[str]] = None) -> bool:
        """Commit changes."""
        try:
            if files:
                # Add specific files
                await self.add_files(files)
            
            result = await self._run_git_command(['commit', '-m', message])
            return result.returncode == 0
        except Exception as e:
            print(f"Error committing: {e}")
            return False
    
    async def push(self, branch: Optional[str] = None) -> bool:
        """Push changes to remote."""
        try:
            if branch:
                result = await self._run_git_command(['push', 'origin', branch])
            else:
                result = await self._run_git_command(['push'])
            return result.returncode == 0
        except Exception as e:
            print(f"Error pushing: {e}")
            return False
    
    async def pull(self, branch: Optional[str] = None) -> bool:
        """Pull changes from remote."""
        try:
            if branch:
                result = await self._run_git_command(['pull', 'origin', branch])
            else:
                result = await self._run_git_command(['pull'])
            return result.returncode == 0
        except Exception as e:
            print(f"Error pulling: {e}")
            return False
    
    async def fetch(self) -> bool:
        """Fetch changes from remote."""
        try:
            result = await self._run_git_command(['fetch'])
            return result.returncode == 0
        except Exception as e:
            print(f"Error fetching: {e}")
            return False
    
    async def get_commits(self, count: int = 10) -> List[GitCommit]:
        """Get recent commits."""
        try:
            result = await self._run_git_command([
                'log', 
                f'-{count}',
                '--pretty=format:%H|%an|%ad|%s',
                '--date=iso'
            ])
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|', 3)
                if len(parts) >= 4:
                    commits.append(GitCommit(
                        hash=parts[0],
                        author=parts[1],
                        date=parts[2],
                        message=parts[3],
                        files_changed=[]  # Would need separate command to get files
                    ))
            
            return commits
            
        except Exception as e:
            print(f"Error getting commits: {e}")
            return []
    
    async def create_branch(self, branch_name: str) -> bool:
        """Create a new branch."""
        try:
            result = await self._run_git_command(['checkout', '-b', branch_name])
            return result.returncode == 0
        except Exception as e:
            print(f"Error creating branch: {e}")
            return False
    
    async def switch_branch(self, branch_name: str) -> bool:
        """Switch to a branch."""
        try:
            result = await self._run_git_command(['checkout', branch_name])
            return result.returncode == 0
        except Exception as e:
            print(f"Error switching branch: {e}")
            return False
    
    async def merge_branch(self, branch_name: str) -> bool:
        """Merge a branch into current branch."""
        try:
            result = await self._run_git_command(['merge', branch_name])
            return result.returncode == 0
        except Exception as e:
            print(f"Error merging branch: {e}")
            return False
    
    async def get_branches(self) -> List[str]:
        """Get list of branches."""
        try:
            result = await self._run_git_command(['branch', '-a'])
            if result.returncode != 0:
                return []
            
            branches = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Remove leading * and whitespace
                branch = line.lstrip('* ').strip()
                if branch:
                    branches.append(branch)
            
            return branches
            
        except Exception as e:
            print(f"Error getting branches: {e}")
            return []
    
    async def get_remotes(self) -> Dict[str, str]:
        """Get remote repositories."""
        try:
            result = await self._run_git_command(['remote', '-v'])
            if result.returncode != 0:
                return {}
            
            remotes = {}
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    url = parts[1]
                    remotes[name] = url
            
            return remotes
            
        except Exception as e:
            print(f"Error getting remotes: {e}")
            return {}
    
    async def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run a git command."""
        cmd = ['git'] + args
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.repo_path
        )