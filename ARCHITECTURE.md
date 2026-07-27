# Impact Check Skill - Architecture

## Overview

The impact-check skill is designed to analyze the blast radius of code changes across a microservices platform. It consists of modular components that work together to provide comprehensive impact analysis.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Impact Check Skill                     │
└─────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │   impact_check.py     │
                │   (Main Orchestrator)  │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  analyzer.py │   │coverage_     │   │report_       │
│              │   │analyzer.py   │   │generator.py  │
│ Dependency   │   │              │   │              │
│ Analysis     │   │ Coverage     │   │ Report       │
│              │   │ Analysis     │   │ Generation   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Git repos    │   │ pytest-cov   │   │ GitHub PR    │
│ under ~/work │   │ output       │   │ description  │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Components

### 1. Main Orchestrator (`impact_check.py`)

**Purpose**: Coordinates the entire analysis workflow.

**Responsibilities**:
- Parse command-line arguments
- Detect changed files via git
- Coordinate dependency and coverage analysis
- Generate and output reports
- Append reports to PR descriptions

**Key Methods**:
- `get_changed_files()`: Detects files changed in current branch
- `get_pr_info()`: Retrieves PR metadata via GitHub CLI
- `run_analysis()`: Orchestrates complete analysis
- `append_to_pr_description()`: Updates PR with report

**External Dependencies**:
- Git CLI for change detection
- GitHub CLI (`gh`) for PR operations

### 2. Dependency Analyzer (`analyzer.py`)

**Purpose**: Static analysis of Python code for imports and API calls.

**Key Classes**:

#### `PythonDependencyAnalyzer`

Analyzes Python code across multiple repositories.

**Key Methods**:
- `extract_imports()`: Parse Python AST for import statements
- `extract_api_calls()`: Regex-based HTTP call detection
- `extract_routes()`: Parse FastAPI/Flask route definitions
- `analyze_changed_module()`: Full dependency analysis for a file
- `_determine_impact_level()`: Classify caller impact as HIGH/MEDIUM/LOW

**Analysis Strategies**:

##### Import Analysis
Uses Python's `ast` module to parse syntax trees:

```python
import ast

tree = ast.parse(source_code)
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        # Handle: import module
    elif isinstance(node, ast.ImportFrom):
        # Handle: from module import name
```

##### API Call Detection
Pattern matching for common HTTP client libraries:

```python
# Pattern 1: requests library
r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'

# Pattern 2: httpx async client
r'(?:await\s+)?client\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
```

##### Route Extraction
Detects route definitions in web frameworks:

```python
# FastAPI pattern
r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'

# Flask pattern
r'@(?:app|bp)\.route\s*\(\s*["\']([^"\']+)["\'].*?methods\s*=\s*\[([^\]]+)\]'
```

**Impact Level Classification**:

- **HIGH**: Changes to routers, managers, services, core modules
- **MEDIUM**: Changes to utilities, helpers, common modules
- **LOW**: Changes to logging, analytics, monitoring, insights

### 3. Coverage Analyzer (`coverage_analyzer.py`)

**Purpose**: Parse and analyze test coverage data.

**Key Classes**:

#### `CoverageAnalyzer`

Maps test coverage to changed files.

**Key Methods**:
- `load_coverage_json()`: Parse pytest-cov JSON output
- `load_coverage_xml()`: Parse Cobertura XML output
- `get_file_coverage()`: Retrieve coverage for specific file
- `analyze_changed_files()`: Batch coverage analysis

**Supported Formats**:

##### JSON Format (pytest-cov)
```json
{
  "files": {
    "app/routers/history.py": {
      "coverage": 86.5,
      "covered_lines": 173,
      "num_statements": 200,
      "missing_lines": [45, 67, 89]
    }
  }
}
```

##### XML Format (Cobertura)
```xml
<coverage>
  <packages>
    <package name="app.routers">
      <classes>
        <class filename="history.py">
          <lines>
            <line number="45" hits="0"/>
            <line number="46" hits="5"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
```

**Coverage Threshold**:
- Default: 80%
- Configurable via `--coverage-threshold` flag
- Files below threshold flagged in report

### 4. Report Generator (`report_generator.py`)

**Purpose**: Format analysis results into human-readable reports.

**Key Classes**:

#### `ReportGenerator`

Generates both text and markdown reports.

**Report Formats**:

##### Text Format
Console-friendly output matching the specification:
- ASCII art borders
- Aligned columns
- Color indicators (✓, ⚠)
- Concise summaries

##### Markdown Format
GitHub PR-friendly formatting:
- Headers and sections
- Emoji indicators (🔴🟡🟢)
- Tables for structured data
- Collapsible sections for large reports

**Risk Level Determination**:

```python
if high_impact_count >= 2 or (high_impact >= 1 and coverage_gaps >= 2):
    risk = "WARNING"
elif high_impact_count >= 1 or coverage_gaps >= 1:
    risk = "CAUTION"
else:
    risk = "OK"
```

**Suggested Actions**:

Based on risk profile:
- No issues: "OK — proceed with PR"
- Coverage gaps only: "Run /coverage-gap"
- High-impact callers only: "Notify dependent teams"
- Both: "Review with tech lead; coordinate deployment"

## Data Flow

```
1. User runs /impact-check
        ↓
2. Main orchestrator detects changed files (git diff)
        ↓
3. For each changed Python file:
   a. Dependency analyzer scans all repos
   b. Extract imports matching the changed module
   c. Extract API calls matching defined routes
   d. Classify impact level (HIGH/MEDIUM/LOW)
        ↓
4. Coverage analyzer loads pytest-cov data
   a. Map coverage to changed files
   b. Flag files below threshold
        ↓
5. Report generator creates report
   a. Determine risk level
   b. Generate suggested actions
   c. Format as text or markdown
        ↓
6. Optional: Append report to PR via gh CLI
        ↓
7. Display report to user
```

## File System Structure

```
~/.claude/skills/impact-check/
├── SKILL.md                 # Skill metadata and documentation
├── README.md                # User documentation
├── QUICK_START.md          # Quick start guide
├── ARCHITECTURE.md         # This file
├── CHANGELOG.md            # Version history
├── requirements.txt        # Dependencies (none for v1.0)
├── .gitignore              # Git ignore rules
│
├── impact_check.py         # Main orchestrator script
├── analyzer.py             # Dependency analysis
├── coverage_analyzer.py    # Coverage analysis
├── report_generator.py     # Report formatting
│
├── test_analyzer.py        # Test suite
└── example_output.txt      # Sample output
```

## Performance Characteristics

### Time Complexity

- **Repository discovery**: O(n) where n = number of directories under work_dir
- **File scanning**: O(r × f) where r = repos, f = avg files per repo
- **Import extraction**: O(l) where l = lines of code per file
- **API call detection**: O(l) for regex matching
- **Coverage mapping**: O(c) where c = changed files

### Expected Performance

For a typical Wizr setup:
- 12 microservices
- ~500 Python files per service
- ~200 lines per file
- **Total analysis time**: 10-30 seconds

**Optimization Opportunities**:
1. Cache AST parsing results
2. Parallelize repo scanning
3. Index imports/routes for fast lookup
4. Skip test files and vendor directories

### Memory Usage

- Minimal: Only one file's AST in memory at a time
- Coverage data: ~1-5 MB for typical project
- Report: <100 KB

## Extension Points

### Adding New Language Support

To support JavaScript/TypeScript:

1. Create `js_analyzer.py` similar to `analyzer.py`
2. Implement JS/TS AST parsing (using `esprima` or similar)
3. Add import detection for ES6 modules
4. Detect HTTP calls in axios/fetch patterns
5. Integrate into `impact_check.py` orchestrator

### Adding New Coverage Formats

To support other coverage tools:

1. Add parsing method to `coverage_analyzer.py`
2. Implement format detection (XML, JSON, LCOV, etc.)
3. Normalize to common `CoverageInfo` structure
4. Test with sample coverage files

### Adding New Report Formats

To support Slack, email, or other formats:

1. Add format method to `report_generator.py`
2. Implement format-specific structure
3. Add output option to CLI
4. Document in README

## Security Considerations

### Input Validation

- File paths: Use `Path().resolve()` to prevent directory traversal
- Regex patterns: Pre-compiled, no user input
- Git commands: Parameterized, no shell injection
- Coverage files: Parse with safe XML/JSON libraries

### Data Privacy

- No data sent to external services
- PR append requires explicit user consent (gh CLI auth)
- Coverage data stays local
- No logging of sensitive file contents

### Access Control

- Respects file system permissions
- Only reads .git repositories
- No write operations except PR append
- No modification of source files

## Testing Strategy

### Unit Tests

Located in `test_analyzer.py`:

- Import extraction accuracy
- API call pattern matching
- Route detection
- Impact level classification
- Coverage mapping

### Integration Tests

Manual testing workflow:

1. Set up test repos under ~/work
2. Create feature branch with changes
3. Generate coverage data
4. Run impact-check
5. Verify report accuracy
6. Test PR append

### Edge Cases

- Empty repositories
- No changed files
- Files with syntax errors
- Missing coverage data
- No PR exists
- Multiple PRs

## Dependencies

### Required

- Python 3.7+
- Git CLI
- Standard library only (ast, pathlib, subprocess, json, xml, re)

### Optional

- GitHub CLI (`gh`) - for PR operations
- pytest-cov - for coverage generation
- pytest - for running test suite

### No External Packages

By design, the skill uses only Python standard library to:
- Minimize installation complexity
- Reduce version conflicts
- Ensure portability
- Simplify maintenance

## Deployment

### Installation

```bash
# Skill is auto-detected by Claude Code in ~/.claude/skills/
cp -r impact-check ~/.claude/skills/
```

### Configuration

Set environment variables:

```bash
export WIZR_WORK_DIR=~/work
export WIZR_COVERAGE_THRESHOLD=80
```

Or configure in `.claude/settings.json`:

```json
{
  "skills": {
    "impact-check": {
      "workDir": "~/work",
      "coverageThreshold": 80
    }
  }
}
```

### Updates

Future updates will:
1. Maintain backward compatibility
2. Follow semantic versioning
3. Provide migration guides
4. Preserve user configurations

## Monitoring and Debugging

### Verbose Mode

Add `--verbose` flag (future):

```bash
/impact-check --verbose
```

Outputs:
- Repos scanned
- Files analyzed
- Imports found
- API calls detected
- Coverage lookup attempts

### Error Handling

Graceful degradation:
- Missing work directory → warning, continue with current repo only
- No coverage data → warning, skip coverage section
- Git errors → fallback to alternate detection methods
- gh CLI errors → skip PR append, show report only

### Logging

Future: Optional logging to `~/.claude/skills/impact-check/logs/`:
- Analysis runs
- Performance metrics
- Error occurrences
- Usage statistics

## Future Enhancements

See [CHANGELOG.md](CHANGELOG.md) for roadmap.
