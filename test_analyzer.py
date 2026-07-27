#!/usr/bin/env python3
"""
Test suite for the impact-check skill components.
Run with: pytest test_analyzer.py
"""

import tempfile
import shutil
from pathlib import Path
import pytest

from analyzer import PythonDependencyAnalyzer, ImportInfo, APICallInfo, RouteInfo


class TestPythonDependencyAnalyzer:
    """Test the dependency analyzer"""

    @pytest.fixture
    def temp_work_dir(self):
        """Create a temporary work directory with mock repos"""
        temp_dir = tempfile.mkdtemp()
        work_path = Path(temp_dir) / "work"
        work_path.mkdir()

        # Create mock repos
        repos = ["kube-wizr-logger", "kube-wizr-manager", "webapp-connect"]
        for repo_name in repos:
            repo_path = work_path / repo_name
            repo_path.mkdir()
            (repo_path / ".git").mkdir()
            (repo_path / "app").mkdir()

        yield work_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_discover_repos(self, temp_work_dir):
        """Test repository discovery"""
        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))

        assert len(analyzer.repos) == 3
        repo_names = {repo.name for repo in analyzer.repos}
        assert "kube-wizr-logger" in repo_names
        assert "kube-wizr-manager" in repo_names
        assert "webapp-connect" in repo_names

    def test_extract_imports(self, temp_work_dir):
        """Test import extraction"""
        # Create a test file with imports
        test_file = temp_work_dir / "kube-wizr-logger" / "app" / "test.py"
        test_file.write_text("""
import os
import sys
from app.routers import history
from app.utilities_logger.helpers import history_helper

def main():
    pass
""")

        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))
        imports = analyzer.extract_imports(test_file)

        assert len(imports) >= 4

        module_names = [imp.module for imp in imports]
        assert "os" in module_names
        assert "app.routers" in module_names
        assert "app.utilities_logger.helpers" in module_names

    def test_extract_routes_fastapi(self, temp_work_dir):
        """Test FastAPI route extraction"""
        test_file = temp_work_dir / "kube-wizr-logger" / "app" / "router.py"
        test_file.write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/history/execution")
async def get_execution_history():
    pass

@router.post("/api/history/log")
async def create_log():
    pass
""")

        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))
        routes = analyzer.extract_routes(test_file)

        assert len(routes) == 2

        endpoints = {route.endpoint for route in routes}
        assert "/api/history/execution" in endpoints
        assert "/api/history/log" in endpoints

        methods = {route.method for route in routes}
        assert "GET" in methods
        assert "POST" in methods

    def test_extract_api_calls(self, temp_work_dir):
        """Test API call extraction"""
        test_file = temp_work_dir / "kube-wizr-manager" / "app" / "service.py"
        test_file.write_text("""
import requests
import httpx

def fetch_history():
    response = requests.get("/api/history/execution")
    return response.json()

async def fetch_async():
    async with httpx.AsyncClient() as client:
        response = await client.get("/api/history/execution")
        return response.json()
""")

        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))
        calls = analyzer.extract_api_calls(test_file)

        assert len(calls) >= 2

        endpoints = [call.endpoint for call in calls]
        assert "/api/history/execution" in endpoints

        methods = [call.method for call in calls]
        assert all(method == "GET" for method in methods)

    def test_analyze_changed_module(self, temp_work_dir):
        """Test full module analysis"""
        # Create a router file
        router_file = temp_work_dir / "kube-wizr-logger" / "app" / "routers" / "history.py"
        router_file.parent.mkdir(parents=True)
        router_file.write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/history/execution")
async def get_execution():
    return {"status": "ok"}
""")

        # Create a caller file in another repo
        caller_file = temp_work_dir / "kube-wizr-manager" / "app" / "service.py"
        caller_file.write_text("""
import requests
from app.routers import history

def fetch_data():
    # Import usage
    result = history.router

    # API call
    response = requests.get("/api/history/execution")
    return response.json()
""")

        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))
        result = analyzer.analyze_changed_module(
            str(router_file),
            "kube-wizr-logger"
        )

        assert "direct_callers" in result
        assert len(result["direct_callers"]) >= 1

        # Check that callers from different repo are found
        caller_repos = {caller["repo"] for caller in result["direct_callers"]}
        assert "kube-wizr-manager" in caller_repos

    def test_impact_level_classification(self, temp_work_dir):
        """Test impact level determination"""
        analyzer = PythonDependencyAnalyzer(str(temp_work_dir))

        # High impact: router/manager
        import_info = ImportInfo(
            module="app.routers.history",
            source_file="test.py",
            source_repo="test-repo",
            line_number=1,
            is_from_import=True
        )
        level = analyzer._determine_impact_level(import_info, "app/routers/history.py")
        assert level == "HIGH"

        # Medium impact: helper
        level = analyzer._determine_impact_level(import_info, "app/helpers/util.py")
        assert level == "MEDIUM"

        # Low impact: logging
        level = analyzer._determine_impact_level(import_info, "app/logging/logger.py")
        assert level == "LOW"


def test_module_name_extraction():
    """Test module name extraction from file path"""
    analyzer = PythonDependencyAnalyzer("/tmp/work")

    # Mock file path
    file_path = Path("/tmp/work/kube-wizr-logger/app/routers/history.py")
    module_name = analyzer._get_module_name(file_path, "kube-wizr-logger")

    # Should extract package path
    assert "history" in module_name


def test_endpoint_matching():
    """Test endpoint pattern matching"""
    analyzer = PythonDependencyAnalyzer("/tmp/work")

    # Exact match
    assert analyzer._matches_endpoint(
        "/api/history/execution",
        "/api/history/execution"
    )

    # Path parameter match
    assert analyzer._matches_endpoint(
        "/api/user/123",
        "/api/user/{id}"
    )

    # No match
    assert not analyzer._matches_endpoint(
        "/api/history/log",
        "/api/history/execution"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
