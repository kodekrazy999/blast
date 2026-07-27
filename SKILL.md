---
name: impact-check
description: Analyze blast radius and test coverage of code changes across microservices
tags: [analysis, testing, code-review]
version: 1.0.0
---

# Impact Check Skill

Scans all repos under ~/work/ to trace cross-repo callers of changed modules, maps test coverage on changed paths, and generates a structured IMPACT CHECK REPORT. Designed for the Wizr platform with 12+ microservices.

## When to use

- Before creating a PR to understand the blast radius of your changes
- During code review to assess impact on dependent services
- When making changes to shared libraries or commonly imported modules
- To verify test coverage meets the 80% threshold on changed paths

## What it does

1. **Detects changed files** in the current git branch vs main/master
2. **Traces cross-repo dependencies** by scanning all repos under ~/work/ for:
   - Direct Python imports of changed modules
   - HTTP API calls to endpoints defined in changed routers
3. **Maps test coverage** using pytest-cov output
4. **Generates IMPACT CHECK REPORT** with:
   - PR context (number, changed files)
   - Blast radius (direct and indirect callers with impact levels)
   - Coverage metrics on changed paths
   - Risk verdict with suggested actions
5. **Appends report to PR description** if PR exists

## Usage

```bash
# Run on current branch
/impact-check

# Run with custom work directory
/impact-check --work-dir ~/projects

# Run with custom coverage threshold
/impact-check --coverage-threshold 85

# Skip PR description append
/impact-check --no-append-pr
```

## Configuration

Set these in your environment or .claude/settings.json:

- `WIZR_WORK_DIR`: Path to parent directory containing all microservice repos (default: ~/work)
- `WIZR_COVERAGE_THRESHOLD`: Minimum coverage percentage (default: 80)
- `WIZR_SERVICE_REGISTRY`: Path to service registry file (optional)

## Output

The skill produces a formatted IMPACT CHECK REPORT showing:

- **BLAST RADIUS**: Cross-repo callers categorized by impact level
  - `[HIGH]` - Direct API consumers or critical import paths
  - `[MEDIUM]` - Indirect dependencies via shared utilities
  - `[LOW]` - Analytics or logging dependencies
  
- **COVERAGE ON CHANGED PATHS**: Per-file coverage with warnings for <80%

- **RISK VERDICT**: Non-blocking warning with suggested actions

## Integration with other skills

- **story-to-pr**: Automatically runs impact-check before PR creation
- **pr-review**: Can be invoked as part of review checklist
- **coverage-gap**: Suggested when coverage is below threshold

## Implementation details

The skill uses:
- `ast` module for Python static analysis
- `git diff` for detecting changed files
- `pytest --cov` output for coverage mapping
- `gh pr view` for PR context and description updates

## Limitations

- Python-only analysis (no JavaScript/TypeScript support yet)
- HTTP call detection limited to common patterns (FastAPI, Flask routes)
- Requires repos to be on disk under the work directory
- Coverage data requires recent pytest-cov run
