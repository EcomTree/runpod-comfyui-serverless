#!/usr/bin/env python3
"""
Codex Coding Background Agent

A background agent for automated code analysis, maintenance, and development tasks.
This agent runs continuously and performs various coding-related operations.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import time
from datetime import datetime

# Third-party imports
import click
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

# Local imports
from src.config import config
from src.logger import setup_logging
from src.code_analyzer import CodeAnalyzer
from src.git_manager import GitManager
from src.project_manager import ProjectManager
from src.quality_checker import QualityChecker

# Initialize Rich console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="codex-agent",
    help="Codex Coding Background Agent",
    add_completion=False
)

class CodexAgent:
    """
    Main Codex Coding Background Agent class.
    
    This agent performs various coding-related tasks including:
    - Code analysis and quality checks
    - Git repository management
    - Project maintenance
    - Automated testing
    - Documentation generation
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Codex agent."""
        self.config = config
        self.logger = setup_logging()
        self.console = Console()
        
        # Initialize components
        self.code_analyzer = CodeAnalyzer(self.config)
        self.git_manager = GitManager(self.config)
        self.project_manager = ProjectManager(self.config)
        self.quality_checker = QualityChecker(self.config)
        
        # Agent state
        self.running = False
        self.tasks = []
        
        self.logger.info("Codex Agent initialized")
    
    async def start(self) -> None:
        """Start the background agent."""
        self.logger.info("Starting Codex Agent...")
        self.running = True
        
        try:
            # Start background tasks
            tasks = [
                asyncio.create_task(self._monitor_repository()),
                asyncio.create_task(self._analyze_code_quality()),
                asyncio.create_task(self._maintain_project()),
                asyncio.create_task(self._health_check())
            ]
            
            self.tasks = tasks
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Agent error: {e}")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the background agent."""
        self.logger.info("Stopping Codex Agent...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.logger.info("Codex Agent stopped")
    
    async def _monitor_repository(self) -> None:
        """Monitor git repository for changes."""
        self.logger.info("Starting repository monitoring...")
        
        while self.running:
            try:
                # Check for changes
                changes = await self.git_manager.check_changes()
                
                if changes:
                    self.logger.info(f"Repository changes detected: {len(changes)} files")
                    
                    # Analyze changed files
                    for file_path in changes:
                        await self.code_analyzer.analyze_file(file_path)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Repository monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _analyze_code_quality(self) -> None:
        """Perform code quality analysis."""
        self.logger.info("Starting code quality analysis...")
        
        while self.running:
            try:
                # Run quality checks
                quality_report = await self.quality_checker.run_full_check()
                
                if quality_report.issues:
                    self.logger.warning(f"Code quality issues found: {len(quality_report.issues)}")
                    
                    # Log issues
                    for issue in quality_report.issues:
                        self.logger.warning(f"Quality issue: {issue}")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Code quality analysis error: {e}")
                await asyncio.sleep(600)  # Wait longer on error
    
    async def _maintain_project(self) -> None:
        """Perform project maintenance tasks."""
        self.logger.info("Starting project maintenance...")
        
        while self.running:
            try:
                # Run maintenance tasks
                maintenance_report = await self.project_manager.run_maintenance()
                
                if maintenance_report.tasks_completed:
                    self.logger.info(f"Maintenance completed: {len(maintenance_report.tasks_completed)} tasks")
                
                # Wait before next maintenance cycle
                await asyncio.sleep(1800)  # Run every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Project maintenance error: {e}")
                await asyncio.sleep(3600)  # Wait longer on error
    
    async def _health_check(self) -> None:
        """Perform health checks."""
        self.logger.info("Starting health monitoring...")
        
        while self.running:
            try:
                # Check system health
                health_status = await self._check_system_health()
                
                if not health_status.healthy:
                    self.logger.warning(f"Health check failed: {health_status.issues}")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health status."""
        health_status = {
            "healthy": True,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Check disk space
            disk_usage = os.statvfs("/workspace")
            free_space_gb = (disk_usage.f_frsize * disk_usage.f_bavail) / (1024**3)
            
            if free_space_gb < 1.0:  # Less than 1GB free
                health_status["healthy"] = False
                health_status["issues"].append(f"Low disk space: {free_space_gb:.2f}GB free")
            
            # Check memory usage
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()
            
            # Parse memory info (simplified)
            for line in meminfo.split("\n"):
                if "MemAvailable" in line:
                    available_kb = int(line.split()[1])
                    available_gb = available_kb / (1024**2)
                    
                    if available_gb < 0.5:  # Less than 500MB available
                        health_status["healthy"] = False
                        health_status["issues"].append(f"Low memory: {available_gb:.2f}GB available")
                    break
            
        except Exception as e:
            health_status["healthy"] = False
            health_status["issues"].append(f"Health check error: {e}")
        
        return health_status
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "running": self.running,
            "tasks": len(self.tasks),
            "active_tasks": [task.get_name() for task in self.tasks if not task.done()],
            "timestamp": datetime.now().isoformat()
        }

# CLI Commands
@app.command()
def start(
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Start the Codex agent."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    agent = CodexAgent(config_file)
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down Codex Agent...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting agent: {e}[/red]")
        sys.exit(1)

@app.command()
def status():
    """Show agent status."""
    agent = CodexAgent()
    status_info = agent.get_status()
    
    table = Table(title="Codex Agent Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in status_info.items():
        table.add_row(key, str(value))
    
    console.print(table)

@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to analyze"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Analyze recursively")
):
    """Analyze code at specified path."""
    agent = CodexAgent()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing code...", total=None)
        
        try:
            if recursive:
                results = asyncio.run(agent.code_analyzer.analyze_directory(path))
                # Handle list of results for directory analysis
                total_issues = sum(len(result.issues) for result in results)
                total_files = len(results)
                total_lines = sum(result.lines_of_code for result in results)
                
                progress.update(task, description="Analysis complete")
                
                console.print(f"[green]Analyzed {total_files} files with {total_lines} total lines of code[/green]")
                
                if total_issues > 0:
                    console.print(f"[yellow]Found {total_issues} total issues across all files:[/yellow]")
                    for result in results:
                        if result.issues:
                            console.print(f"[blue]  {result.file_path}:[/blue]")
                            for issue in result.issues:
                                console.print(f"    • {issue}")
                else:
                    console.print("[green]No issues found in any files![/green]")
            else:
                results = asyncio.run(agent.code_analyzer.analyze_file(path))
                # Handle single result for file analysis
                progress.update(task, description="Analysis complete")
                
                console.print(f"[green]Analyzed {results.file_path} ({results.lines_of_code} lines)[/green]")
                
                if results.issues:
                    console.print(f"[yellow]Found {len(results.issues)} issues:[/yellow]")
                    for issue in results.issues:
                        console.print(f"  • {issue}")
                else:
                    console.print("[green]No issues found![/green]")
                
        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            sys.exit(1)

@app.command()
def test():
    """Run tests."""
    agent = CodexAgent()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running tests...", total=None)
        
        try:
            results = asyncio.run(agent.quality_checker.run_tests())
            progress.update(task, description="Tests complete")
            
            # Display results
            if results.passed:
                console.print(f"[green]Tests passed: {results.passed_count}/{results.total_count}[/green]")
            else:
                console.print(f"[red]Tests failed: {results.failed_count}/{results.total_count}[/red]")
                
        except Exception as e:
            console.print(f"[red]Test execution failed: {e}[/red]")
            sys.exit(1)

def main():
    """Main entry point."""
    app()

if __name__ == "__main__":
    main()