#!/usr/bin/env python3
"""
Generates formatted IMPACT CHECK REPORT for PR descriptions.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class BlastRadiusItem:
    """A single item in the blast radius"""
    repo: str
    detail: str
    impact_level: str  # HIGH, MEDIUM, LOW


@dataclass
class CoverageSummary:
    """Coverage summary for a file"""
    file_path: str
    coverage_percent: float
    below_threshold: bool


@dataclass
class ImpactCheckReport:
    """Complete impact check report data"""
    pr_number: Optional[str]
    pr_title: Optional[str]
    changed_files: List[str]
    direct_callers: List[BlastRadiusItem]
    indirect_callers: List[BlastRadiusItem]
    coverage_items: List[CoverageSummary]
    coverage_threshold: float
    risk_level: str  # OK, CAUTION, WARNING
    suggested_action: Optional[str]
    appended_to_pr: bool


class ReportGenerator:
    """Generates formatted impact check reports"""

    def __init__(self, coverage_threshold: float = 80.0):
        self.coverage_threshold = coverage_threshold

    def generate_text_report(self, report: ImpactCheckReport) -> str:
        """Generate text-based report matching the screenshot format"""
        lines = []

        # Header
        lines.append("IMPACT CHECK REPORT")
        lines.append("=" * 50)

        # PR Info
        if report.pr_number:
            pr_title = report.pr_title or "N/A"
            lines.append(f"PR       : #{report.pr_number} {pr_title}")

        # Changed files
        lines.append(f"Changed  : {report.changed_files[0]}")
        for file_path in report.changed_files[1:]:
            lines.append(f"           {file_path}")

        lines.append("")

        # Blast Radius
        lines.append("BLAST RADIUS")
        lines.append("-" * 50)

        if report.direct_callers:
            lines.append("Direct callers (cross-repo):")

            # Group by impact level
            high_callers = [c for c in report.direct_callers if c.impact_level == 'HIGH']
            medium_callers = [c for c in report.direct_callers if c.impact_level == 'MEDIUM']
            low_callers = [c for c in report.direct_callers if c.impact_level == 'LOW']

            for caller in high_callers:
                lines.append(f"  {caller.repo:30} → {caller.detail:40} [HIGH]")

            for caller in medium_callers:
                lines.append(f"  {caller.repo:30} → {caller.detail:40} [MEDIUM]")

            for caller in low_callers:
                lines.append(f"  {caller.repo:30} → {caller.detail:40} [LOW]")
        else:
            lines.append("  No direct callers detected.")

        lines.append("")

        if report.indirect_callers:
            lines.append("Indirect:")
            for caller in report.indirect_callers:
                lines.append(f"  {caller.repo:30} → {caller.detail:40} [{caller.impact_level}]")
            lines.append("")

        # Coverage
        lines.append("COVERAGE ON CHANGED PATHS")
        lines.append("-" * 50)

        if report.coverage_items:
            for item in report.coverage_items:
                status = "✓" if not item.below_threshold else "⚠ below 80% threshold"
                lines.append(f"  {item.file_path:40} → {item.coverage_percent:.0f}% {status}")
        else:
            lines.append("  No coverage data available")

        lines.append("")

        # Risk Verdict
        lines.append("RISK VERDICT")
        lines.append("-" * 50)

        if report.risk_level == "CAUTION":
            high_impact_count = sum(1 for c in report.direct_callers if c.impact_level == 'HIGH')
            lines.append(f"  ⚠ CAUTION — {high_impact_count} high-impact caller(s) detected.")

            if report.suggested_action:
                lines.append(f"  Suggested action: {report.suggested_action}")
        elif report.risk_level == "WARNING":
            lines.append(f"  ⚠ WARNING — Multiple issues detected.")
            if report.suggested_action:
                lines.append(f"  Suggested action: {report.suggested_action}")
        else:
            lines.append("  ✓ OK — No high-risk issues detected.")

        lines.append("")

        # Append status
        append_status = "YES" if report.appended_to_pr else "NO (no PR found or --no-append-pr flag)"
        lines.append(f"APPENDED TO PR DESCRIPTION: {append_status}")

        return "\n".join(lines)

    def generate_markdown_report(self, report: ImpactCheckReport) -> str:
        """Generate markdown-formatted report for PR descriptions"""
        lines = []

        lines.append("## 🔍 IMPACT CHECK REPORT")
        lines.append("")

        # Changed files
        lines.append("**Changed files:**")
        for file_path in report.changed_files:
            lines.append(f"- `{file_path}`")
        lines.append("")

        # Blast Radius
        lines.append("### 💥 Blast Radius")
        lines.append("")

        if report.direct_callers:
            lines.append("**Direct callers (cross-repo):**")
            lines.append("")
            lines.append("| Repository | Detail | Impact |")
            lines.append("|------------|--------|--------|")

            for caller in report.direct_callers:
                impact_emoji = {
                    'HIGH': '🔴',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }.get(caller.impact_level, '⚪')

                lines.append(f"| `{caller.repo}` | {caller.detail} | {impact_emoji} {caller.impact_level} |")

            lines.append("")
        else:
            lines.append("✅ No direct cross-repo callers detected.")
            lines.append("")

        if report.indirect_callers:
            lines.append("**Indirect callers:**")
            lines.append("")
            for caller in report.indirect_callers:
                lines.append(f"- `{caller.repo}` → {caller.detail} *({caller.impact_level})*")
            lines.append("")

        # Coverage
        lines.append("### 📊 Coverage on Changed Paths")
        lines.append("")

        if report.coverage_items:
            below_threshold = [item for item in report.coverage_items if item.below_threshold]

            if below_threshold:
                lines.append(f"⚠️ **{len(below_threshold)} file(s) below {self.coverage_threshold}% threshold:**")
                lines.append("")
                lines.append("| File | Coverage |")
                lines.append("|------|----------|")

                for item in below_threshold:
                    emoji = "🔴" if item.coverage_percent < 60 else "🟡"
                    lines.append(f"| `{item.file_path}` | {emoji} {item.coverage_percent:.0f}% |")

                lines.append("")

            above_threshold = [item for item in report.coverage_items if not item.below_threshold]
            if above_threshold:
                lines.append("✅ **Files meeting coverage threshold:**")
                lines.append("")
                for item in above_threshold:
                    lines.append(f"- `{item.file_path}`: {item.coverage_percent:.0f}%")
                lines.append("")
        else:
            lines.append("ℹ️ No coverage data available for changed files.")
            lines.append("")

        # Risk Verdict
        lines.append("### 🎯 Risk Verdict")
        lines.append("")

        if report.risk_level == "CAUTION":
            high_impact_count = sum(1 for c in report.direct_callers if c.impact_level == 'HIGH')
            lines.append(f"⚠️ **CAUTION** — {high_impact_count} high-impact caller(s) detected.")
            lines.append("")

            if report.suggested_action:
                lines.append(f"**Suggested action:** {report.suggested_action}")
                lines.append("")
        elif report.risk_level == "WARNING":
            lines.append("⚠️ **WARNING** — Multiple issues detected.")
            lines.append("")
            if report.suggested_action:
                lines.append(f"**Suggested action:** {report.suggested_action}")
                lines.append("")
        else:
            lines.append("✅ **OK** — No high-risk issues detected.")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by impact-check skill at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def determine_risk_level(self,
                            direct_callers: List[BlastRadiusItem],
                            coverage_items: List[CoverageSummary]) -> tuple[str, Optional[str]]:
        """
        Determine risk level and suggested action.
        Returns (risk_level, suggested_action)
        """
        high_impact_count = sum(1 for c in direct_callers if c.impact_level == 'HIGH')
        below_threshold_count = sum(1 for c in coverage_items if c.below_threshold)

        # Determine risk level
        if high_impact_count >= 2 or (high_impact_count >= 1 and below_threshold_count >= 2):
            risk_level = "WARNING"
        elif high_impact_count >= 1 or below_threshold_count >= 1:
            risk_level = "CAUTION"
        else:
            risk_level = "OK"

        # Suggest action
        suggested_action = None

        if high_impact_count >= 2:
            suggested_action = "Review with tech lead; coordinate deployment with dependent services"
        elif high_impact_count == 1 and below_threshold_count >= 1:
            suggested_action = "Add tests for coverage gaps; notify dependent service team"
        elif high_impact_count == 1:
            suggested_action = "Notify dependent service team before merge"
        elif below_threshold_count >= 2:
            suggested_action = f"Run /coverage-gap to improve test coverage below {self.coverage_threshold}%"
        elif below_threshold_count == 1:
            suggested_action = f"Consider adding tests to reach {self.coverage_threshold}% threshold"

        return risk_level, suggested_action


def main():
    """Example usage"""
    # Create example report
    generator = ReportGenerator(coverage_threshold=80.0)

    report = ImpactCheckReport(
        pr_number="7310",
        pr_title="DEV:FEATURE(BE)(add) — Add token usage to details tab",
        changed_files=[
            "kube-wizr-logger-history / app/routers/history.py",
            "kube-wizr-logger-history / app/utilities_logger/helpers/history_helper.py"
        ],
        direct_callers=[
            BlastRadiusItem("kube-wizr-agentmanager", "GET /api/history/execution", "HIGH"),
            BlastRadiusItem("kube-wizr-app-orchestrator", "GET /api/history/execution", "HIGH"),
            BlastRadiusItem("webapp-wizrai-connect", "GET /api/history via WizrAPIInstance", "MEDIUM"),
        ],
        indirect_callers=[
            BlastRadiusItem("kube-wizr-insights-manager", "reads execution history for analytics", "LOW"),
        ],
        coverage_items=[
            CoverageSummary("history_helper.py", 61, True),
            CoverageSummary("history.py (router)", 86, False),
        ],
        coverage_threshold=80.0,
        risk_level="CAUTION",
        suggested_action="run /coverage-gap on history_helper.py before merge",
        appended_to_pr=True
    )

    print(generator.generate_text_report(report))
    print("\n" + "="*50 + "\n")
    print(generator.generate_markdown_report(report))


if __name__ == '__main__':
    main()
