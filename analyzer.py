#!/usr/bin/env python3
"""
Static analyzer for cross-repo Python dependencies and HTTP call patterns.
Traces imports and API calls across multiple microservice repositories.
"""

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import json


@dataclass
class ImportInfo:
    """Information about an import statement"""
    module: str
    source_file: str
    source_repo: str
    line_number: int
    is_from_import: bool


@dataclass
class APICallInfo:
    """Information about an HTTP API call"""
    endpoint: str
    method: str
    source_file: str
    source_repo: str
    line_number: int


@dataclass
class RouteInfo:
    """Information about a defined API route"""
    endpoint: str
    method: str
    source_file: str
    handler_function: str


class PythonDependencyAnalyzer:
    """Analyzes Python code for imports and API calls"""

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir).expanduser()
        self.repos = self._discover_repos()

    def _discover_repos(self) -> List[Path]:
        """Discover all git repositories under work_dir"""
        repos = []
        if not self.work_dir.exists():
            return repos

        for item in self.work_dir.iterdir():
            if item.is_dir() and (item / '.git').exists():
                repos.append(item)
        return repos

    def _get_repo_name(self, file_path: Path) -> str:
        """Extract repository name from file path"""
        try:
            rel_path = file_path.relative_to(self.work_dir)
            return rel_path.parts[0] if rel_path.parts else "unknown"
        except ValueError:
            return "unknown"

    def extract_imports(self, file_path: Path) -> List[ImportInfo]:
        """Extract all imports from a Python file"""
        imports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            return imports

        repo_name = self._get_repo_name(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=alias.name,
                        source_file=str(file_path),
                        source_repo=repo_name,
                        line_number=node.lineno,
                        is_from_import=False
                    ))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(ImportInfo(
                        module=node.module,
                        source_file=str(file_path),
                        source_repo=repo_name,
                        line_number=node.lineno,
                        is_from_import=True
                    ))

        return imports

    def extract_api_calls(self, file_path: Path) -> List[APICallInfo]:
        """Extract HTTP API calls from a Python file"""
        api_calls = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return api_calls

        repo_name = self._get_repo_name(file_path)

        # Pattern 1: requests.get/post/put/delete/patch
        # Example: requests.get("/api/history/execution")
        pattern1 = r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern1, content):
            method, endpoint = match.groups()
            line_num = content[:match.start()].count('\n') + 1
            api_calls.append(APICallInfo(
                endpoint=endpoint,
                method=method.upper(),
                source_file=str(file_path),
                source_repo=repo_name,
                line_number=line_num
            ))

        # Pattern 2: httpx.AsyncClient or httpx.Client
        # Example: await client.get("/api/history/execution")
        pattern2 = r'(?:await\s+)?client\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern2, content):
            method, endpoint = match.groups()
            line_num = content[:match.start()].count('\n') + 1
            api_calls.append(APICallInfo(
                endpoint=endpoint,
                method=method.upper(),
                source_file=str(file_path),
                source_repo=repo_name,
                line_number=line_num
            ))

        return api_calls

    def extract_routes(self, file_path: Path) -> List[RouteInfo]:
        """Extract API route definitions from a Python file"""
        routes = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            return routes

        # Pattern 1: FastAPI decorator style
        # @router.get("/api/history/execution")
        fastapi_pattern = r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(fastapi_pattern, content):
            method, endpoint = match.groups()
            line_num = content[:match.start()].count('\n') + 1

            # Try to find the function name after the decorator
            func_match = re.search(r'def\s+(\w+)', content[match.end():match.end()+200])
            func_name = func_match.group(1) if func_match else "unknown"

            routes.append(RouteInfo(
                endpoint=endpoint,
                method=method.upper(),
                source_file=str(file_path),
                handler_function=func_name
            ))

        # Pattern 2: Flask style
        # @app.route("/api/history/execution", methods=["GET"])
        flask_pattern = r'@(?:app|bp)\.route\s*\(\s*["\']([^"\']+)["\'].*?methods\s*=\s*\[([^\]]+)\]'
        for match in re.finditer(flask_pattern, content):
            endpoint, methods_str = match.groups()
            line_num = content[:match.start()].count('\n') + 1

            methods = re.findall(r'["\'](\w+)["\']', methods_str)
            func_match = re.search(r'def\s+(\w+)', content[match.end():match.end()+200])
            func_name = func_match.group(1) if func_match else "unknown"

            for method in methods:
                routes.append(RouteInfo(
                    endpoint=endpoint,
                    method=method.upper(),
                    source_file=str(file_path),
                    handler_function=func_name
                ))

        return routes

    def find_python_files(self, repo_path: Path) -> List[Path]:
        """Find all Python files in a repository"""
        python_files = []

        # Common directories to skip
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env',
                    'node_modules', '.pytest_cache', '.mypy_cache', 'dist', 'build'}

        for root, dirs, files in os.walk(repo_path):
            # Remove skip_dirs from dirs to avoid walking into them
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return python_files

    def analyze_changed_module(self, changed_file: str, changed_repo: str) -> Dict:
        """
        Analyze impact of changes to a specific module.
        Returns callers across all repos.
        """
        changed_path = Path(changed_file)
        module_name = self._get_module_name(changed_path, changed_repo)

        # Extract routes defined in the changed file if it's a router
        defined_routes = []
        if changed_path.exists():
            defined_routes = self.extract_routes(changed_path)

        direct_callers = []
        indirect_callers = []

        # Scan all repos for dependencies
        for repo_path in self.repos:
            repo_name = repo_path.name

            # Skip the repo containing the changed file
            if repo_name == changed_repo:
                continue

            python_files = self.find_python_files(repo_path)

            for py_file in python_files:
                # Check for imports
                imports = self.extract_imports(py_file)
                for imp in imports:
                    if self._matches_module(imp.module, module_name):
                        impact_level = self._determine_impact_level(imp, changed_file)
                        direct_callers.append({
                            'repo': repo_name,
                            'file': str(py_file.relative_to(repo_path)),
                            'line': imp.line_number,
                            'type': 'import',
                            'detail': f'imports {imp.module}',
                            'impact_level': impact_level
                        })

                # Check for API calls matching defined routes
                if defined_routes:
                    api_calls = self.extract_api_calls(py_file)
                    for call in api_calls:
                        for route in defined_routes:
                            if self._matches_endpoint(call.endpoint, route.endpoint) and \
                               call.method == route.method:
                                impact_level = self._determine_api_impact_level(call, route)
                                direct_callers.append({
                                    'repo': repo_name,
                                    'file': str(py_file.relative_to(repo_path)),
                                    'line': call.line_number,
                                    'type': 'api_call',
                                    'detail': f'{call.method} {call.endpoint}',
                                    'impact_level': impact_level
                                })

        return {
            'module': module_name,
            'changed_file': changed_file,
            'direct_callers': direct_callers,
            'indirect_callers': indirect_callers,
            'routes_affected': len(defined_routes)
        }

    def _get_module_name(self, file_path: Path, repo_name: str) -> str:
        """Convert file path to Python module name"""
        # Try to find the package root (directory with __init__.py)
        parts = []
        current = file_path

        # Remove .py extension
        if current.suffix == '.py':
            if current.stem == '__init__':
                current = current.parent
            else:
                parts.insert(0, current.stem)
                current = current.parent

        # Walk up to find package root
        while current.name and current.name != repo_name:
            if (current / '__init__.py').exists():
                parts.insert(0, current.name)
                current = current.parent
            else:
                break

        return '.'.join(parts) if parts else file_path.stem

    def _matches_module(self, import_name: str, module_name: str) -> bool:
        """Check if import matches the module (handles partial matches)"""
        return (import_name == module_name or
                import_name.startswith(module_name + '.') or
                module_name.startswith(import_name + '.'))

    def _matches_endpoint(self, call_endpoint: str, route_endpoint: str) -> bool:
        """Check if API call endpoint matches route definition"""
        # Exact match
        if call_endpoint == route_endpoint:
            return True

        # Handle path parameters: /api/user/{id} matches /api/user/123
        route_pattern = re.sub(r'\{[^}]+\}', r'[^/]+', route_endpoint)
        return bool(re.fullmatch(route_pattern, call_endpoint))

    def _determine_impact_level(self, imp: ImportInfo, changed_file: str) -> str:
        """Determine impact level based on import context"""
        # High impact: direct imports of routers, managers, core modules
        if any(keyword in changed_file.lower() for keyword in ['router', 'manager', 'service', 'core']):
            return 'HIGH'

        # Medium impact: utility imports
        if any(keyword in changed_file.lower() for keyword in ['util', 'helper', 'common']):
            return 'MEDIUM'

        # Low impact: logging, analytics, monitoring
        if any(keyword in changed_file.lower() for keyword in ['log', 'analytics', 'monitor', 'insight']):
            return 'LOW'

        return 'MEDIUM'

    def _determine_api_impact_level(self, call: APICallInfo, route: RouteInfo) -> str:
        """Determine impact level of API call"""
        # High impact: critical endpoints or manager services
        if any(keyword in call.source_repo.lower() for keyword in ['manager', 'orchestrator', 'gateway']):
            return 'HIGH'

        # Medium impact: regular service calls
        if 'webapp' in call.source_repo.lower() or 'api' in call.source_repo.lower():
            return 'MEDIUM'

        # Low impact: analytics, insights
        if any(keyword in call.source_repo.lower() for keyword in ['analytics', 'insight', 'log']):
            return 'LOW'

        return 'MEDIUM'


def main():
    """Example usage"""
    import sys

    work_dir = sys.argv[1] if len(sys.argv) > 1 else "~/work"
    analyzer = PythonDependencyAnalyzer(work_dir)

    print(f"Found {len(analyzer.repos)} repositories:")
    for repo in analyzer.repos:
        print(f"  - {repo.name}")

    # Example: analyze a changed file
    if len(sys.argv) > 2:
        changed_file = sys.argv[2]
        changed_repo = sys.argv[3] if len(sys.argv) > 3 else "unknown"

        result = analyzer.analyze_changed_module(changed_file, changed_repo)
        print(f"\nAnalysis for {changed_file}:")
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
