#!/usr/bin/env python3
"""
Test coverage analyzer for changed files.
Parses pytest-cov output and maps coverage to specific files.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET


@dataclass
class CoverageInfo:
    """Coverage information for a file"""
    file_path: str
    coverage_percent: float
    lines_covered: int
    lines_total: int
    missing_lines: List[int]
    below_threshold: bool


class CoverageAnalyzer:
    """Analyzes test coverage for Python files"""

    def __init__(self, repo_path: str, threshold: float = 80.0):
        self.repo_path = Path(repo_path).expanduser()
        self.threshold = threshold
        self.coverage_data = {}

    def run_coverage(self, files: List[str]) -> bool:
        """
        Run pytest with coverage on specified files.
        Returns True if successful.
        """
        try:
            # Run pytest with coverage
            cmd = [
                'pytest',
                '--cov=' + str(self.repo_path),
                '--cov-report=json:coverage.json',
                '--cov-report=xml:coverage.xml',
                '--cov-report=term',
                '-q'
            ]

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def load_coverage_json(self, coverage_file: str = 'coverage.json') -> bool:
        """Load coverage data from JSON file"""
        coverage_path = self.repo_path / coverage_file

        if not coverage_path.exists():
            return False

        try:
            with open(coverage_path, 'r') as f:
                data = json.load(f)
                self.coverage_data = data.get('files', {})
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def load_coverage_xml(self, coverage_file: str = 'coverage.xml') -> bool:
        """Load coverage data from XML file (Cobertura format)"""
        coverage_path = self.repo_path / coverage_file

        if not coverage_path.exists():
            return False

        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()

            self.coverage_data = {}

            for package in root.findall('.//package'):
                for cls in package.findall('classes/class'):
                    filename = cls.get('filename')

                    lines = cls.findall('lines/line')
                    lines_covered = sum(1 for line in lines if line.get('hits', '0') != '0')
                    lines_total = len(lines)

                    coverage_percent = (lines_covered / lines_total * 100) if lines_total > 0 else 0

                    missing_lines = [
                        int(line.get('number'))
                        for line in lines
                        if line.get('hits', '0') == '0'
                    ]

                    self.coverage_data[filename] = {
                        'coverage': coverage_percent,
                        'covered_lines': lines_covered,
                        'num_statements': lines_total,
                        'missing_lines': missing_lines
                    }

            return True

        except (ET.ParseError, AttributeError):
            return False

    def parse_coverage_report(self, report_text: str) -> Dict[str, CoverageInfo]:
        """
        Parse coverage report from pytest --cov terminal output.
        Format: Name    Stmts   Miss  Cover   Missing
        """
        coverage_map = {}

        # Find the coverage table in the output
        lines = report_text.strip().split('\n')

        in_table = False
        for line in lines:
            line = line.strip()

            # Detect table start
            if 'Name' in line and 'Stmts' in line and 'Cover' in line:
                in_table = True
                continue

            # Detect table end
            if in_table and line.startswith('---'):
                continue

            if in_table and line:
                # Parse table row
                # Example: app/routers/history.py    150     45    70%   23-45, 67-89
                match = re.match(
                    r'(\S+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%(?:\s+(.+))?',
                    line
                )

                if match:
                    file_path, stmts, miss, cover, missing = match.groups()

                    stmts = int(stmts)
                    miss = int(miss)
                    cover_pct = int(cover)
                    covered = stmts - miss

                    # Parse missing lines
                    missing_lines = []
                    if missing:
                        for part in missing.split(','):
                            part = part.strip()
                            if '-' in part:
                                start, end = map(int, part.split('-'))
                                missing_lines.extend(range(start, end + 1))
                            elif part.isdigit():
                                missing_lines.append(int(part))

                    coverage_map[file_path] = CoverageInfo(
                        file_path=file_path,
                        coverage_percent=cover_pct,
                        lines_covered=covered,
                        lines_total=stmts,
                        missing_lines=missing_lines,
                        below_threshold=cover_pct < self.threshold
                    )

        return coverage_map

    def get_file_coverage(self, file_path: str) -> Optional[CoverageInfo]:
        """Get coverage info for a specific file"""

        # Normalize file path
        file_path = str(Path(file_path))

        # Try direct lookup
        if file_path in self.coverage_data:
            data = self.coverage_data[file_path]
            return CoverageInfo(
                file_path=file_path,
                coverage_percent=data.get('coverage', 0),
                lines_covered=data.get('covered_lines', 0),
                lines_total=data.get('num_statements', 0),
                missing_lines=data.get('missing_lines', []),
                below_threshold=data.get('coverage', 0) < self.threshold
            )

        # Try basename lookup
        basename = Path(file_path).name
        for path, data in self.coverage_data.items():
            if Path(path).name == basename:
                return CoverageInfo(
                    file_path=file_path,
                    coverage_percent=data.get('coverage', 0),
                    lines_covered=data.get('covered_lines', 0),
                    lines_total=data.get('num_statements', 0),
                    missing_lines=data.get('missing_lines', []),
                    below_threshold=data.get('coverage', 0) < self.threshold
                )

        return None

    def analyze_changed_files(self, changed_files: List[str]) -> Dict[str, CoverageInfo]:
        """Analyze coverage for a list of changed files"""
        result = {}

        for file_path in changed_files:
            # Only analyze Python files
            if not file_path.endswith('.py'):
                continue

            coverage = self.get_file_coverage(file_path)
            if coverage:
                result[file_path] = coverage
            else:
                # File has no coverage data (possibly untested)
                result[file_path] = CoverageInfo(
                    file_path=file_path,
                    coverage_percent=0.0,
                    lines_covered=0,
                    lines_total=0,
                    missing_lines=[],
                    below_threshold=True
                )

        return result


def main():
    """Example usage"""
    import sys

    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    analyzer = CoverageAnalyzer(repo_path)

    # Try to load existing coverage data
    if analyzer.load_coverage_json():
        print("Loaded coverage data from coverage.json")
    elif analyzer.load_coverage_xml():
        print("Loaded coverage data from coverage.xml")
    else:
        print("No coverage data found. Run pytest with --cov first.")
        return

    # Example: analyze specific files
    if len(sys.argv) > 2:
        files = sys.argv[2:]
        result = analyzer.analyze_changed_files(files)

        print(f"\nCoverage analysis for {len(files)} files:")
        for file_path, info in result.items():
            status = "⚠️ BELOW THRESHOLD" if info.below_threshold else "✓"
            print(f"  {status} {file_path}: {info.coverage_percent:.0f}%")


if __name__ == '__main__':
    main()
