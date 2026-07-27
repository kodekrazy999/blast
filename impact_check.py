#!/usr/bin/env python3
"""
Main orchestration script for impact-check skill.
Coordinates git diff, dependency analysis, coverage analysis, and report generation.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add skill directory to path for imports
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from analyzer import PythonDependencyAnalyzer
from coverage_analyzer import CoverageAnalyzer
from report_generator import (
    ReportGenerator,
    ImpactCheckReport,
    BlastRadiusItem,
    CoverageSummary
)


class ImpactChecker:
    """Main orchestrator for impact check analysis"""

    def __init__(self,
                 work_dir: str = "~/work",
                 coverage_threshold: float = 80.0,
                 repo_path: Optional[str] = None):
        self.work_dir = Path(work_dir).expanduser()
        self.coverage_threshold = coverage_threshold
        self.repo_path = Path(repo_path).expanduser() if repo_path else Path.cwd()

        self.dependency_analyzer = PythonDependencyAnalyzer(str(self.work_dir))
        self.coverage_analyzer = CoverageAnalyzer(str(self.repo_path), coverage_threshold)
        self.report_generator = ReportGenerator(coverage_threshold)

    def get_changed_files(self, base_branch: str = "main") -> List[str]:
        """Get list of changed files in current branch vs base branch"""
        try:
            # Try main first, then master
            for branch in [base_branch, "master"]:
                result = subprocess.run(
                    ["git", "diff", "--name-only", f"{branch}...HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and result.stdout.strip():
                    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                    return files

            # Fallback: get unstaged and staged changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                return files

            return []

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def get_current_repo_name(self) -> str:
        """Get the name of the current repository"""
        return self.repo_path.name

    def get_pr_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get PR number and title using gh CLI"""
        try:
            # Check if gh is available
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "number,title"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                return str(data.get('number')), data.get('title')

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None, None

    def append_to_pr_description(self, report_text: str) -> bool:
        """Append report to PR description using gh CLI"""
        try:
            # Get current description
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "body"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return False

            import json
            current_body = json.loads(result.stdout).get('body', '')

            # Check if report already exists
            if "IMPACT CHECK REPORT" in current_body:
                # Remove old report
                parts = current_body.split("## 🔍 IMPACT CHECK REPORT")
                current_body = parts[0].rstrip()

            # Append new report
            new_body = f"{current_body}\n\n{report_text}"

            # Update PR description
            result = subprocess.run(
                ["gh", "pr", "edit", "--body", new_body],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            return False

    def run_analysis(self, append_pr: bool = True) -> ImpactCheckReport:
        """Run complete impact analysis"""

        # Get changed files
        changed_files = self.get_changed_files()

        if not changed_files:
            print("⚠ No changed files detected. Make sure you're on a feature branch.")
            changed_files = []

        current_repo = self.get_current_repo_name()

        # Analyze dependencies
        all_direct_callers = []
        all_indirect_callers = []

        for changed_file in changed_files:
            if not changed_file.endswith('.py'):
                continue

            full_path = self.repo_path / changed_file

            if not full_path.exists():
                continue

            result = self.dependency_analyzer.analyze_changed_module(
                str(full_path),
                current_repo
            )

            for caller in result['direct_callers']:
                all_direct_callers.append(BlastRadiusItem(
                    repo=caller['repo'],
                    detail=caller['detail'],
                    impact_level=caller['impact_level']
                ))

            for caller in result['indirect_callers']:
                all_indirect_callers.append(BlastRadiusItem(
                    repo=caller['repo'],
                    detail=caller['detail'],
                    impact_level=caller.get('impact_level', 'LOW')
                ))

        # Analyze coverage
        coverage_items = []

        # Try to load existing coverage data
        if self.coverage_analyzer.load_coverage_json():
            print("✓ Loaded coverage data from coverage.json")
        elif self.coverage_analyzer.load_coverage_xml():
            print("✓ Loaded coverage data from coverage.xml")
        else:
            print("ℹ No coverage data found. Run pytest with --cov to generate coverage.")

        coverage_results = self.coverage_analyzer.analyze_changed_files(changed_files)

        for file_path, coverage in coverage_results.items():
            coverage_items.append(CoverageSummary(
                file_path=file_path,
                coverage_percent=coverage.coverage_percent,
                below_threshold=coverage.below_threshold
            ))

        # Determine risk level
        risk_level, suggested_action = self.report_generator.determine_risk_level(
            all_direct_callers,
            coverage_items
        )

        # Get PR info
        pr_number, pr_title = self.get_pr_info()

        # Format changed files with repo prefix
        formatted_files = [f"{current_repo} / {f}" for f in changed_files]

        # Create report
        report = ImpactCheckReport(
            pr_number=pr_number,
            pr_title=pr_title,
            changed_files=formatted_files,
            direct_callers=all_direct_callers,
            indirect_callers=all_indirect_callers,
            coverage_items=coverage_items,
            coverage_threshold=self.coverage_threshold,
            risk_level=risk_level,
            suggested_action=suggested_action,
            appended_to_pr=False
        )

        # Try to append to PR
        if append_pr and pr_number:
            markdown_report = self.report_generator.generate_markdown_report(report)
            if self.append_to_pr_description(markdown_report):
                report.appended_to_pr = True
                print("✓ Report appended to PR description")
            else:
                print("⚠ Failed to append report to PR description")

        return report


def main():
    parser = argparse.ArgumentParser(
        description="Analyze impact of code changes across microservices"
    )
    parser.add_argument(
        '--work-dir',
        default='~/work',
        help='Path to directory containing all microservice repos (default: ~/work)'
    )
    parser.add_argument(
        '--coverage-threshold',
        type=float,
        default=80.0,
        help='Minimum coverage percentage threshold (default: 80)'
    )
    parser.add_argument(
        '--repo-path',
        help='Path to repository to analyze (default: current directory)'
    )
    parser.add_argument(
        '--no-append-pr',
        action='store_true',
        help='Do not append report to PR description'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )

    args = parser.parse_args()

    # Run analysis
    checker = ImpactChecker(
        work_dir=args.work_dir,
        coverage_threshold=args.coverage_threshold,
        repo_path=args.repo_path
    )

    print("🔍 Running impact check analysis...")
    print(f"   Work directory: {checker.work_dir}")
    print(f"   Repository: {checker.repo_path}")
    print(f"   Coverage threshold: {args.coverage_threshold}%")
    print()

    report = checker.run_analysis(append_pr=not args.no_append_pr)

    # Print report
    print()
    if args.format == 'markdown':
        print(checker.report_generator.generate_markdown_report(report))
    else:
        print(checker.report_generator.generate_text_report(report))


if __name__ == '__main__':
    main()
