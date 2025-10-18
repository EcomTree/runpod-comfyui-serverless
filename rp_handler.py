#!/usr/bin/env python3
"""
RunPod Handler for Codex Coding Background Agent

This handler is designed for a coding background agent that performs
code analysis, maintenance, and development tasks rather than ComfyUI workflows.
"""

import asyncio
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict, Any

# Import our modular components
from src.config import config
from src.code_analyzer import CodeAnalyzer
from src.git_manager import GitManager
from src.project_manager import ProjectManager
from src.quality_checker import QualityChecker


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for Codex Coding Background Agent.

    Args:
        event: RunPod event containing task and metadata

    Returns:
        Dict containing results or error information
    """
    print("🚀 Codex Agent Handler started - processing coding task...")
    print(f"📋 Event Type: {event.get('type', 'unknown')}")

    # Handle heartbeat events
    if event.get("type") == "heartbeat":
        print("💓 Heartbeat received - agent stays active")
        return {"status": "ok"}

    try:
        # Initialize components
        code_analyzer = CodeAnalyzer(config)
        git_manager = GitManager(config)
        project_manager = ProjectManager(config)
        quality_checker = QualityChecker(config)

        # Extract task information
        task_type = event.get("input", {}).get("task_type", "analyze")
        task_data = event.get("input", {}).get("task_data", {})
        
        # Generate job_id for organizing results
        job_id = event.get("id", str(uuid.uuid4()))

        # Process different task types
        if task_type == "analyze":
            result = asyncio.run(_handle_analysis_task(code_analyzer, task_data, job_id))
        elif task_type == "quality_check":
            result = asyncio.run(_handle_quality_check_task(quality_checker, task_data, job_id))
        elif task_type == "git_operation":
            result = asyncio.run(_handle_git_task(git_manager, task_data, job_id))
        elif task_type == "maintenance":
            result = asyncio.run(_handle_maintenance_task(project_manager, task_data, job_id))
        else:
            result = {"error": f"Unknown task type: {task_type}"}

        # Add common metadata
        result["job_id"] = job_id
        result["task_type"] = task_type
        result["timestamp"] = time.time()

        print(f"✅ Handler successful! Task '{task_type}' completed")
        return result

    except Exception as e:
        print(f"❌ Handler Error: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {"error": f"Handler Error: {str(e)}"}


async def _handle_analysis_task(code_analyzer: CodeAnalyzer, task_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Handle code analysis tasks."""
    try:
        path = task_data.get("path", ".")
        recursive = task_data.get("recursive", True)
        
        if recursive:
            results = await code_analyzer.analyze_directory(path)
        else:
            results = [await code_analyzer.analyze_file(path)]
        
        # Aggregate results
        total_issues = sum(len(result.issues) for result in results)
        total_files = len(results)
        total_lines = sum(result.lines_of_code for result in results)
        total_functions = sum(result.functions for result in results)
        total_classes = sum(result.classes for result in results)
        
        return {
            "success": True,
            "analysis_results": {
                "total_files": total_files,
                "total_issues": total_issues,
                "total_lines_of_code": total_lines,
                "total_functions": total_functions,
                "total_classes": total_classes,
                "files_analyzed": [
                    {
                        "file_path": result.file_path,
                        "issues": len(result.issues),
                        "lines_of_code": result.lines_of_code,
                        "complexity": result.complexity,
                        "functions": result.functions,
                        "classes": result.classes
                    }
                    for result in results
                ]
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Analysis failed: {e}"}


async def _handle_quality_check_task(quality_checker: QualityChecker, task_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Handle code quality check tasks."""
    try:
        report = await quality_checker.run_full_check()
        
        return {
            "success": True,
            "quality_report": {
                "total_issues": len(report.issues),
                "test_passed": report.test_result.passed if report.test_result else False,
                "test_count": report.test_result.total_count if report.test_result else 0,
                "coverage_percentage": report.coverage_percentage,
                "complexity_score": report.complexity_score,
                "security_issues": len(report.security_issues),
                "issues_by_severity": {
                    "error": len([i for i in report.issues if i.severity == "error"]),
                    "warning": len([i for i in report.issues if i.severity == "warning"]),
                    "info": len([i for i in report.issues if i.severity == "info"])
                }
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Quality check failed: {e}"}


async def _handle_git_task(git_manager: GitManager, task_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Handle git operation tasks."""
    try:
        operation = task_data.get("operation", "status")
        
        if operation == "status":
            status = await git_manager.get_status()
            return {
                "success": True,
                "git_status": {
                    "is_git_repo": status.is_git_repo,
                    "current_branch": status.current_branch,
                    "has_changes": status.has_changes,
                    "staged_files": status.staged_files,
                    "unstaged_files": status.unstaged_files,
                    "untracked_files": status.untracked_files,
                    "ahead_count": status.ahead_count,
                    "behind_count": status.behind_count
                }
            }
        elif operation == "commit":
            message = task_data.get("message", "Codex agent commit")
            files = task_data.get("files", [])
            success = await git_manager.commit(message, files)
            return {"success": success, "message": f"Commit {'successful' if success else 'failed'}"}
        elif operation == "push":
            branch = task_data.get("branch")
            success = await git_manager.push(branch)
            return {"success": success, "message": f"Push {'successful' if success else 'failed'}"}
        else:
            return {"success": False, "error": f"Unknown git operation: {operation}"}
    
    except Exception as e:
        return {"success": False, "error": f"Git operation failed: {e}"}


async def _handle_maintenance_task(project_manager: ProjectManager, task_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Handle project maintenance tasks."""
    try:
        report = await project_manager.run_maintenance()
        
        return {
            "success": True,
            "maintenance_report": {
                "tasks_completed": len(report.tasks_completed),
                "tasks_failed": len(report.tasks_failed),
                "total_duration": report.total_duration,
                "completed_tasks": [
                    {
                        "name": task.name,
                        "description": task.description,
                        "duration": (task.end_time - task.start_time).total_seconds() if task.end_time and task.start_time else 0
                    }
                    for task in report.tasks_completed
                ],
                "failed_tasks": [
                    {
                        "name": task.name,
                        "description": task.description,
                        "error": task.error
                    }
                    for task in report.tasks_failed
                ]
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Maintenance failed: {e}"}


if __name__ == "__main__":
    # For local testing
    test_event = {
        "type": "test",
        "input": {
            "task_type": "analyze",
            "task_data": {
                "path": ".",
                "recursive": True
            }
        }
    }
    
    result = handler(test_event)
    print(f"Test result: {result}")