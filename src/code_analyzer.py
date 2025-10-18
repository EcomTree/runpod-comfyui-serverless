"""
Code Analyzer Module

Provides code analysis functionality for the Codex agent.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple
import asyncio
import subprocess
import json

class CodeIssue(NamedTuple):
    """Represents a code quality issue."""
    file_path: str
    line_number: int
    column: int
    issue_type: str
    message: str
    severity: str  # 'error', 'warning', 'info'

class AnalysisResult(NamedTuple):
    """Result of code analysis."""
    file_path: str
    issues: List[CodeIssue]
    complexity: int
    lines_of_code: int
    functions: int
    classes: int

class CodeAnalyzer:
    """Code analyzer for various programming languages."""
    
    def __init__(self, config):
        self.config = config
        self.supported_extensions = {
            '.py': self._analyze_python,
            '.js': self._analyze_javascript,
            '.ts': self._analyze_typescript,
            '.java': self._analyze_java,
            '.cpp': self._analyze_cpp,
            '.c': self._analyze_c,
            '.go': self._analyze_go,
            '.rs': self._analyze_rust,
        }
    
    async def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze a single file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        ext = path.suffix.lower()
        
        if ext not in self.supported_extensions:
            return AnalysisResult(
                file_path=file_path,
                issues=[],
                complexity=0,
                lines_of_code=0,
                functions=0,
                classes=0
            )
        
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Analyze based on file type
        analyzer_func = self.supported_extensions[ext]
        return await analyzer_func(file_path, content)
    
    async def analyze_directory(self, directory_path: str) -> List[AnalysisResult]:
        """Analyze all files in a directory."""
        results = []
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all supported files
        for ext in self.supported_extensions:
            for file_path in path.rglob(f"*{ext}"):
                try:
                    result = await self.analyze_file(str(file_path))
                    results.append(result)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
        
        return results
    
    async def _analyze_python(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze Python code."""
        issues = []
        lines = content.split('\n')
        
        try:
            # Parse AST
            tree = ast.parse(content)
            
            # Basic metrics
            functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            
            # Calculate complexity (simplified)
            complexity = self._calculate_python_complexity(tree)
            
            # Check for common issues
            issues.extend(self._check_python_style(content, file_path))
            issues.extend(self._check_python_best_practices(tree, file_path))
            
        except SyntaxError as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line_number=e.lineno or 0,
                column=e.offset or 0,
                issue_type='syntax_error',
                message=f"Syntax error: {e.msg}",
                severity='error'
            ))
            functions = classes = complexity = 0
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=complexity,
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )
    
    def _calculate_python_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity for Python code."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _check_python_style(self, content: str, file_path: str) -> List[CodeIssue]:
        """Check Python style issues."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=0,
                    issue_type='line_too_long',
                    message=f"Line too long ({len(line)} > 120 characters)",
                    severity='warning'
                ))
            
            # Check for trailing whitespace
            if line.rstrip() != line:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=len(line.rstrip()),
                    issue_type='trailing_whitespace',
                    message="Trailing whitespace",
                    severity='warning'
                ))
            
            # Check for mixed tabs and spaces
            if '\t' in line and '    ' in line:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=0,
                    issue_type='mixed_tabs_spaces',
                    message="Mixed tabs and spaces",
                    severity='error'
                ))
        
        return issues
    
    def _check_python_best_practices(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """Check Python best practices."""
        issues = []
        
        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    issue_type='bare_except',
                    message="Bare except clause",
                    severity='warning'
                ))
            
            # Check for unused imports (simplified)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname is None and not self._is_import_used(tree, alias.name):
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            issue_type='unused_import',
                            message=f"Unused import: {alias.name}",
                            severity='warning'
                        ))
        
        return issues
    
    def _is_import_used(self, tree: ast.AST, import_name: str) -> bool:
        """Check if an import is used in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == import_name:
                return True
            elif isinstance(node, ast.Attribute) and self._is_import_used_in_attribute(node, import_name):
                return True
        return False
    
    def _is_import_used_in_attribute(self, node: ast.Attribute, import_name: str) -> bool:
        """Check if import is used in attribute access."""
        if isinstance(node.value, ast.Name) and node.value.id == import_name:
            return True
        elif isinstance(node.value, ast.Attribute):
            return self._is_import_used_in_attribute(node.value, import_name)
        return False
    
    async def _analyze_javascript(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze JavaScript code."""
        issues = []
        lines = content.split('\n')
        
        # Basic metrics (simplified)
        functions = len(re.findall(r'function\s+\w+', content))
        classes = len(re.findall(r'class\s+\w+', content))
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Check for console.log (should be removed in production)
            if 'console.log' in line:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=line.find('console.log'),
                    issue_type='console_log',
                    message="console.log should be removed in production",
                    severity='warning'
                ))
            
            # Check for var usage (should use let/const)
            if re.search(r'\bvar\s+', line):
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=0,
                    issue_type='var_usage',
                    message="Use 'let' or 'const' instead of 'var'",
                    severity='warning'
                ))
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=0,  # Would need more sophisticated analysis
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )
    
    async def _analyze_typescript(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze TypeScript code."""
        # For now, treat TypeScript similar to JavaScript
        return await self._analyze_javascript(file_path, content)
    
    async def _analyze_java(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze Java code."""
        issues = []
        lines = content.split('\n')
        
        # Basic metrics
        functions = len(re.findall(r'public\s+\w+.*\(', content))
        classes = len(re.findall(r'class\s+\w+', content))
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Check for TODO comments
            if 'TODO' in line.upper():
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i,
                    column=0,
                    issue_type='todo_comment',
                    message="TODO comment found",
                    severity='info'
                ))
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=0,
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )
    
    async def _analyze_cpp(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze C++ code."""
        return await self._analyze_c(file_path, content)
    
    async def _analyze_c(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze C code."""
        issues = []
        lines = content.split('\n')
        
        # Basic metrics
        functions = len(re.findall(r'\w+\s+\w+\s*\(', content))
        classes = 0  # C doesn't have classes
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=0,
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )
    
    async def _analyze_go(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze Go code."""
        issues = []
        lines = content.split('\n')
        
        # Basic metrics
        functions = len(re.findall(r'func\s+\w+', content))
        classes = 0  # Go doesn't have classes in the traditional sense
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=0,
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )
    
    async def _analyze_rust(self, file_path: str, content: str) -> AnalysisResult:
        """Analyze Rust code."""
        issues = []
        lines = content.split('\n')
        
        # Basic metrics
        functions = len(re.findall(r'fn\s+\w+', content))
        classes = 0  # Rust uses structs and impl blocks
        
        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            complexity=0,
            lines_of_code=len(lines),
            functions=functions,
            classes=classes
        )