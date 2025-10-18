"""
Quality Checker Module

Provides code quality checking functionality for the Codex agent.
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple
import json
import os

class QualityIssue(NamedTuple):
    """Represents a code quality issue."""
    file_path: str
    line_number: int
    column: int
    issue_type: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    tool: str

class TestResult(NamedTuple):
    """Result of test execution."""
    passed: bool
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    duration: float
    output: str
    errors: List[str]

class QualityReport(NamedTuple):
    """Report of quality checks."""
    issues: List[QualityIssue]
    test_result: Optional[TestResult]
    coverage_percentage: float
    complexity_score: float
    security_issues: List[QualityIssue]
    timestamp: str

class QualityChecker:
    """Code quality checker for various programming languages."""
    
    def __init__(self, config):
        self.config = config
        self.project_root = Path(config.get('PROJECT_ROOT', '/workspace'))
        self.temp_dir = Path(config.get('TEMP_DIR', '/tmp/codex-agent'))
        
        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_full_check(self) -> QualityReport:
        """Run all quality checks."""
        issues = []
        test_result = None
        security_issues = []
        
        # Run linting
        linting_issues = await self._run_linting()
        issues.extend(linting_issues)
        
        # Run formatting check
        formatting_issues = await self._run_formatting_check()
        issues.extend(formatting_issues)
        
        # Run type checking
        type_issues = await self._run_type_checking()
        issues.extend(type_issues)
        
        # Run tests
        test_result = await self.run_tests()
        
        # Run security scan
        security_issues = await self._run_security_scan()
        
        # Calculate coverage
        coverage_percentage = await self._calculate_coverage()
        
        # Calculate complexity score
        complexity_score = await self._calculate_complexity()
        
        return QualityReport(
            issues=issues,
            test_result=test_result,
            coverage_percentage=coverage_percentage,
            complexity_score=complexity_score,
            security_issues=security_issues,
            timestamp=str(asyncio.get_event_loop().time())
        )
    
    async def run_tests(self) -> TestResult:
        """Run tests using the configured test framework."""
        test_framework = self.config.get_quality_config()['test_framework']
        
        if test_framework == 'pytest':
            return await self._run_pytest_tests()
        else:
            return TestResult(
                passed=False,
                total_count=0,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                duration=0.0,
                output="Test framework not supported",
                errors=["Test framework not supported"]
            )
    
    async def _run_pytest_tests(self) -> TestResult:
        """Run pytest tests."""
        try:
            # Check if pytest is available
            result = await self._run_command(['python', '-m', 'pytest', '--version'])
            if result.returncode != 0:
                return TestResult(
                    passed=False,
                    total_count=0,
                    passed_count=0,
                    failed_count=0,
                    skipped_count=0,
                    duration=0.0,
                    output="pytest not available",
                    errors=["pytest not available"]
                )
            
            # Run tests with coverage
            cmd = [
                'python', '-m', 'pytest',
                '--tb=short',
                '--cov=.',
                '--cov-report=json',
                '--json-report',
                '--json-report-file=pytest-report.json',
                '-v'
            ]
            
            result = await self._run_command(cmd)
            
            # Parse JSON report if available
            report_file = self.project_root / 'pytest-report.json'
            if report_file.exists():
                with open(report_file, 'r') as f:
                    report_data = json.load(f)
                
                summary = report_data.get('summary', {})
                return TestResult(
                    passed=summary.get('passed', 0) > 0 and summary.get('failed', 0) == 0,
                    total_count=summary.get('total', 0),
                    passed_count=summary.get('passed', 0),
                    failed_count=summary.get('failed', 0),
                    skipped_count=summary.get('skipped', 0),
                    duration=summary.get('duration', 0.0),
                    output=result.stdout.decode() if result.stdout else "",
                    errors=[result.stderr.decode()] if result.stderr else []
                )
            else:
                # Fallback parsing from stdout
                output = result.stdout.decode() if result.stdout else ""
                return TestResult(
                    passed=result.returncode == 0,
                    total_count=0,
                    passed_count=0,
                    failed_count=0,
                    skipped_count=0,
                    duration=0.0,
                    output=output,
                    errors=[result.stderr.decode()] if result.stderr else []
                )
                
        except Exception as e:
            return TestResult(
                passed=False,
                total_count=0,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                duration=0.0,
                output=f"Test execution failed: {e}",
                errors=[str(e)]
            )
    
    async def _run_linting(self) -> List[QualityIssue]:
        """Run linting tools."""
        issues = []
        linter_tools = self.config.get_quality_config()['linter_tools']
        
        for tool in linter_tools:
            if tool == 'flake8':
                issues.extend(await self._run_flake8())
            elif tool == 'pylint':
                issues.extend(await self._run_pylint())
        
        return issues
    
    async def _run_flake8(self) -> List[QualityIssue]:
        """Run flake8 linting."""
        issues = []
        
        try:
            result = await self._run_command(['python', '-m', 'flake8', '--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s', '.'])
            
            if result.returncode == 0:
                return issues
            
            output = result.stdout.decode() if result.stdout else ""
            for line in output.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(':', 4)
                if len(parts) >= 5:
                    file_path, line_num, col_num, code, message = parts
                    issues.append(QualityIssue(
                        file_path=file_path,
                        line_number=int(line_num),
                        column=int(col_num),
                        issue_type=code,
                        message=message.strip(),
                        severity='warning',
                        tool='flake8'
                    ))
        
        except Exception as e:
            print(f"Flake8 error: {e}")
        
        return issues
    
    async def _run_pylint(self) -> List[QualityIssue]:
        """Run pylint linting."""
        issues = []
        
        try:
            result = await self._run_command(['python', '-m', 'pylint', '--output-format=json', '.'])
            
            if result.returncode == 0:
                return issues
            
            output = result.stdout.decode() if result.stdout else ""
            try:
                pylint_data = json.loads(output)
                for item in pylint_data:
                    issues.append(QualityIssue(
                        file_path=item['path'],
                        line_number=item['line'],
                        column=item['column'],
                        issue_type=item['message-id'],
                        message=item['message'],
                        severity=item['type'],
                        tool='pylint'
                    ))
            except json.JSONDecodeError:
                # Fallback parsing
                for line in output.strip().split('\n'):
                    if ':' in line:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            file_path, line_num, col_num, message = parts
                            issues.append(QualityIssue(
                                file_path=file_path,
                                line_number=int(line_num) if line_num.isdigit() else 0,
                                column=int(col_num) if col_num.isdigit() else 0,
                                issue_type='pylint',
                                message=message.strip(),
                                severity='warning',
                                tool='pylint'
                            ))
        
        except Exception as e:
            print(f"Pylint error: {e}")
        
        return issues
    
    async def _run_formatting_check(self) -> List[QualityIssue]:
        """Check code formatting."""
        issues = []
        
        if not self.config.get_quality_config()['enable_formatting']:
            return issues
        
        try:
            # Check with black
            result = await self._run_command(['python', '-m', 'black', '--check', '--diff', '.'])
            
            if result.returncode != 0:
                output = result.stdout.decode() if result.stdout else ""
                issues.append(QualityIssue(
                    file_path='formatting',
                    line_number=0,
                    column=0,
                    issue_type='formatting',
                    message="Code formatting issues detected",
                    severity='warning',
                    tool='black'
                ))
        
        except Exception as e:
            print(f"Formatting check error: {e}")
        
        return issues
    
    async def _run_type_checking(self) -> List[QualityIssue]:
        """Run type checking."""
        issues = []
        
        if not self.config.get_quality_config()['enable_type_checking']:
            return issues
        
        try:
            result = await self._run_command(['python', '-m', 'mypy', '.'])
            
            if result.returncode != 0:
                output = result.stdout.decode() if result.stdout else ""
                for line in output.strip().split('\n'):
                    if ':' in line and 'error:' in line:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            file_path, line_num, col_num, message = parts
                            issues.append(QualityIssue(
                                file_path=file_path,
                                line_number=int(line_num) if line_num.isdigit() else 0,
                                column=int(col_num) if col_num.isdigit() else 0,
                                issue_type='type_error',
                                message=message.strip(),
                                severity='error',
                                tool='mypy'
                            ))
        
        except Exception as e:
            print(f"Type checking error: {e}")
        
        return issues
    
    async def _run_security_scan(self) -> List[QualityIssue]:
        """Run security scanning tools."""
        issues = []
        
        if not self.config.get_quality_config()['enable_security_scan']:
            return issues
        
        security_tools = self.config.get_quality_config()['security_tools']
        
        for tool in security_tools:
            if tool == 'bandit':
                issues.extend(await self._run_bandit())
            elif tool == 'safety':
                issues.extend(await self._run_safety())
        
        return issues
    
    async def _run_bandit(self) -> List[QualityIssue]:
        """Run bandit security scanner."""
        issues = []
        
        try:
            result = await self._run_command(['python', '-m', 'bandit', '-r', '-f', 'json', '.'])
            
            if result.returncode != 0:
                output = result.stdout.decode() if result.stdout else ""
                try:
                    bandit_data = json.loads(output)
                    for item in bandit_data.get('results', []):
                        issues.append(QualityIssue(
                            file_path=item['filename'],
                            line_number=item['line_number'],
                            column=0,
                            issue_type=item['test_name'],
                            message=item['issue_text'],
                            severity=item['issue_severity'],
                            tool='bandit'
                        ))
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            print(f"Bandit error: {e}")
        
        return issues
    
    async def _run_safety(self) -> List[QualityIssue]:
        """Run safety vulnerability scanner."""
        issues = []
        
        try:
            result = await self._run_command(['python', '-m', 'safety', 'check', '--json'])
            
            if result.returncode != 0:
                output = result.stdout.decode() if result.stdout else ""
                try:
                    safety_data = json.loads(output)
                    for item in safety_data:
                        issues.append(QualityIssue(
                            file_path='requirements',
                            line_number=0,
                            column=0,
                            issue_type='vulnerability',
                            message=f"Vulnerability in {item.get('package', 'unknown')}: {item.get('advisory', 'No details')}",
                            severity='error',
                            tool='safety'
                        ))
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            print(f"Safety error: {e}")
        
        return issues
    
    async def _calculate_coverage(self) -> float:
        """Calculate test coverage percentage."""
        try:
            # Check if coverage report exists
            coverage_file = self.project_root / '.coverage'
            if not coverage_file.exists():
                return 0.0
            
            result = await self._run_command(['python', '-m', 'coverage', 'report', '--show-missing'])
            
            if result.returncode == 0:
                output = result.stdout.decode() if result.stdout else ""
                # Parse coverage percentage from output
                for line in output.split('\n'):
                    if 'TOTAL' in line and '%' in line:
                        try:
                            percentage = float(line.split()[-1].replace('%', ''))
                            return percentage
                        except (ValueError, IndexError):
                            pass
        
        except Exception as e:
            print(f"Coverage calculation error: {e}")
        
        return 0.0
    
    async def _calculate_complexity(self) -> float:
        """Calculate code complexity score."""
        try:
            # Use radon for complexity analysis
            result = await self._run_command(['python', '-m', 'radon', 'cc', '-a', '-s', '.'])
            
            if result.returncode == 0:
                output = result.stdout.decode() if result.stdout else ""
                # Parse complexity scores
                total_complexity = 0
                function_count = 0
                
                for line in output.split('\n'):
                    if ':' in line and ' - ' in line:
                        try:
                            parts = line.split(' - ')
                            if len(parts) >= 2:
                                complexity = int(parts[1].split()[0])
                                total_complexity += complexity
                                function_count += 1
                        except (ValueError, IndexError):
                            pass
                
                if function_count > 0:
                    return total_complexity / function_count
        
        except Exception as e:
            print(f"Complexity calculation error: {e}")
        
        return 0.0
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.project_root
        )