# Impact Check Skill

A Claude Code skill for analyzing the blast radius of code changes across microservices.

## Features

- 🔍 **Cross-repo dependency tracing**: Finds all services that import your changed modules
- 🌐 **HTTP API call detection**: Identifies services calling your modified endpoints
- 📊 **Test coverage analysis**: Maps coverage to changed files and flags gaps below threshold
- 📝 **Automated PR reports**: Appends structured impact reports to PR descriptions
- ⚠️ **Non-blocking warnings**: Issues CAUTION/WARNING verdicts without blocking PRs

## Installation

The skill is self-contained and requires only Python 3.7+. No external dependencies needed.

```bash
# Copy skill directory to Claude skills folder
cp -r impact-check ~/.claude/skills/

# Make the main script executable
chmod +x ~/.claude/skills/impact-check/impact_check.py
```

## Usage

### From Claude Code

```bash
# Run on current branch
/impact-check

# Run with custom parameters
/impact-check --work-dir ~/projects --coverage-threshold 85

# Skip PR description append
/impact-check --no-append-pr
```

### Standalone

```bash
# Run directly
python ~/.claude/skills/impact-check/impact_check.py

# With custom work directory
python ~/.claude/skills/impact-check/impact_check.py --work-dir ~/work

# Output in markdown format
python ~/.claude/skills/impact-check/impact_check.py --format markdown
```

## Configuration

### Environment Variables

Set in your shell profile or `.claude/settings.json`:

```bash
export WIZR_WORK_DIR=~/work
export WIZR_COVERAGE_THRESHOLD=80
```

### Project Settings

Add to `.claude/settings.json` in your project:

```json
{
  "skills": {
    "impact-check": {
      "workDir": "~/work",
      "coverageThreshold": 80,
      "autoAppendPR": true
    }
  }
}
```

## How It Works

### 1. Detect Changed Files

Uses `git diff` to find files changed in current branch vs main/master:

```bash
git diff --name-only main...HEAD
```

### 2. Trace Dependencies

For each changed Python file:

- **Import analysis**: Uses Python's `ast` module to parse all Python files in sibling repos
- **API call detection**: Regex patterns to find HTTP calls matching your route definitions
- **Impact classification**: Categorizes callers as HIGH/MEDIUM/LOW based on service type

### 3. Map Coverage

Parses pytest-cov output (JSON or XML format):

```bash
pytest --cov=. --cov-report=json:coverage.json
```

Maps coverage percentages to changed files and flags those below threshold.

### 4. Generate Report

Creates both text and markdown formatted reports:

- Text format: Console output matching the screenshot
- Markdown format: Rich formatted report for PR descriptions

### 5. Append to PR (optional)

Uses GitHub CLI to append report to PR description:

```bash
gh pr view --json body
gh pr edit --body "updated body with report"
```

## Report Format

```
IMPACT CHECK REPORT
==================================================
PR       : #7310 DEV:FEATURE(BE)(add) — Add token usage to details tab
Changed  : kube-wizr-logger-history / app/routers/history.py
           kube-wizr-logger-history / app/utilities_logger/helpers/history_helper.py

BLAST RADIUS
--------------------------------------------------
Direct callers (cross-repo):
  kube-wizr-agentmanager      → GET /api/history/execution          [HIGH]
  kube-wizr-app-orchestrator  → GET /api/history/execution          [HIGH]
  webapp-wizrai-connect       → GET /api/history via WizrAPIInstance [MEDIUM]

Indirect:
  kube-wizr-insights-manager  → reads execution history for analytics [LOW]

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  history_helper.py                          → 61% ⚠ below 80% threshold
  history.py (router)                        → 86% ✓

RISK VERDICT
--------------------------------------------------
  ⚠ CAUTION — 2 high-impact caller(s) detected.
  Suggested action: run /coverage-gap on history_helper.py before merge

APPENDED TO PR DESCRIPTION: YES
```

## Integration with Other Skills

### story-to-pr

Add to your `story-to-pr` skill to run impact-check automatically:

```markdown
## Before creating PR

1. Run impact-check to assess blast radius
2. If CAUTION/WARNING, review with tech lead
3. Create PR with impact report appended
```

### pr-review

Include in PR review checklist:

```markdown
## Review Checklist

- [ ] Run /impact-check to verify impact assessment
- [ ] Review high-impact callers
- [ ] Verify coverage on changed paths
```

### coverage-gap

Suggested when coverage is below threshold:

```bash
# From impact-check verdict
Suggested action: run /coverage-gap on history_helper.py before merge

# Then run
/coverage-gap history_helper.py
```

## Limitations

- **Python-only**: Currently only analyzes Python code (no JS/TS support)
- **Local repos required**: All microservice repos must be cloned under work directory
- **Recent coverage data**: Requires recent pytest-cov run for accurate coverage
- **HTTP pattern detection**: Limited to common FastAPI/Flask route patterns
- **Git CLI required**: Needs `git` and optionally `gh` CLI installed

## Troubleshooting

### No repos found

```bash
# Verify work directory structure
ls ~/work
# Should show: kube-wizr-service1, kube-wizr-service2, etc.

# Check each is a git repo
ls ~/work/*/. git
```

### No coverage data

```bash
# Run pytest with coverage first
cd your-repo
pytest --cov=. --cov-report=json:coverage.json
pytest --cov=. --cov-report=xml:coverage.xml

# Then run impact-check
/impact-check
```

### PR append fails

```bash
# Verify gh CLI is installed and authenticated
gh auth status

# Check you're in a repo with a PR
gh pr view
```

### Import analysis misses dependencies

The analyzer uses regex patterns for common import styles. If it misses imports:

1. Check the import style in your code
2. Update regex patterns in `analyzer.py`
3. Submit a PR to improve the patterns

## Contributing

To improve the skill:

1. Add support for more languages (JS/TS/Go)
2. Enhance HTTP call pattern detection
3. Add database dependency tracking
4. Improve impact level classification
5. Add caching for faster re-runs

## License

Part of Claude Code skills collection. Use freely for your projects.
