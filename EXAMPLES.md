# Impact Check Skill - Usage Examples

This document shows real-world examples of the impact-check skill in action.

## Example 1: Simple Change with No Dependencies

**Scenario**: Adding a new utility function that isn't imported elsewhere.

```bash
cd ~/work/my-service
git checkout -b feature/add-helper
# ... make changes to utils/helper.py ...
/impact-check
```

**Output**:
```
IMPACT CHECK REPORT
==================================================
Changed  : my-service / utils/helper.py

BLAST RADIUS
--------------------------------------------------
  No direct callers detected.

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  utils/helper.py                      -> 92% [OK]

RISK VERDICT
--------------------------------------------------
  [OK] No high-risk issues detected.
```

**Action**: Safe to merge ✅

---

## Example 2: API Change with Multiple Callers

**Scenario**: Modifying an API endpoint that's called by several services.

```bash
cd ~/work/data-service
git checkout -b feature/enhance-api
# ... modify app/routers/data.py ...
pytest --cov=. --cov-report=json:coverage.json
/impact-check
```

**Output**:
```
IMPACT CHECK REPORT
==================================================
Changed  : data-service / app/routers/data.py

BLAST RADIUS
--------------------------------------------------
Direct callers (cross-repo):
  user-manager                   -> GET /api/data/fetch        [HIGH]
  analytics-service              -> GET /api/data/fetch        [MEDIUM]
  reporting-service              -> GET /api/data/fetch        [MEDIUM]

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  app/routers/data.py                  -> 88% [OK]

RISK VERDICT
--------------------------------------------------
  [CAUTION] 1 high-impact caller(s) detected.
  Suggested action: Notify dependent service team before merge
```

**Action**: Contact user-manager team before deploying ⚠️

---

## Example 3: Breaking Change with Coverage Gap

**Scenario**: Refactoring a shared module with insufficient test coverage.

```bash
cd ~/work/shared-lib
git checkout -b refactor/data-processor
# ... refactor app/services/processor.py ...
pytest --cov=. --cov-report=json:coverage.json
/impact-check
```

**Output**:
```
IMPACT CHECK REPORT
==================================================
Changed  : shared-lib / app/services/processor.py

BLAST RADIUS
--------------------------------------------------
Direct callers (cross-repo):
  api-gateway                    -> import processor           [HIGH]
  worker-service                 -> import processor           [HIGH]
  scheduler-service              -> import processor           [MEDIUM]

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  app/services/processor.py            -> 58% [WARNING] below 80% threshold

RISK VERDICT
--------------------------------------------------
  [WARNING] Multiple issues detected.
  Suggested action: Review with tech lead; coordinate deployment with dependent services
```

**Action**: 
1. Add tests to reach 80% coverage
2. Review with tech lead
3. Coordinate deployment with all dependent teams 🚨

---

## Example 4: Low-Impact Logging Change

**Scenario**: Updating analytics logging code.

```bash
cd ~/work/analytics-logger
git checkout -b fix/improve-logging
# ... update app/logging/metrics.py ...
/impact-check
```

**Output**:
```
IMPACT CHECK REPORT
==================================================
Changed  : analytics-logger / app/logging/metrics.py

BLAST RADIUS
--------------------------------------------------
Direct callers (cross-repo):
  insights-dashboard             -> reads metrics for display  [LOW]

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  app/logging/metrics.py               -> 75% [WARNING] below 80% threshold

RISK VERDICT
--------------------------------------------------
  [CAUTION] 0 high-impact caller(s) detected.
  Suggested action: Consider adding tests to reach 80.0% threshold
```

**Action**: Add a few tests, then safe to merge ⚠️

---

## Example 5: Full Test Scenario (from TEST_REPORT.md)

**Scenario**: Enhancing data processing with breaking changes to function signatures.

### Setup
```bash
# Mock microservices environment
~/work/
├── test-service-a/         # Source service
├── test-service-b/         # MEDIUM impact
├── test-service-c/         # LOW impact (analytics)
├── test-agentmanager/      # HIGH impact
└── test-orchestrator/      # HIGH impact
```

### Changes Made
```bash
cd ~/work/test-service-a
git checkout -b feature/improve-data-processing

# Enhanced app/routers/api.py - added include_metadata parameter
# Enhanced app/services/data_processor.py - added percentile calculations

git add -A
git commit -m "feat: Enhance data processing with metadata and percentiles"
pytest --cov=. --cov-report=json:coverage.json
/impact-check
```

### Output
```
IMPACT CHECK REPORT
==================================================
Changed  : test-service-a / app/routers/api.py
           test-service-a / app/services/data_processor.py

BLAST RADIUS
--------------------------------------------------
Direct callers (cross-repo):
  test-agentmanager              -> GET /api/data/process        [HIGH]
  test-orchestrator              -> GET /api/data/process        [HIGH]
  test-service-b                 -> GET /api/data/process        [MEDIUM]
  test-service-b                 -> POST /api/users              [MEDIUM]
  test-service-c                 -> GET /api/data/process        [MEDIUM]

COVERAGE ON CHANGED PATHS
--------------------------------------------------
  app/routers/api.py                  -> 86% [OK]
  app/services/data_processor.py      -> 65% [WARNING] below 80% threshold

RISK VERDICT
--------------------------------------------------
  [WARNING] Multiple issues detected.
  Suggested action: Review with tech lead; coordinate deployment with dependent services
```

### Analysis
- **2 HIGH-impact callers** detected (agentmanager, orchestrator)
- **3 MEDIUM-impact callers** detected (service-b, service-c)
- **1 coverage gap** below 80% threshold
- **Breaking change** in function signature

### Action Taken
1. ✅ Added tests to improve coverage from 65% → 82%
2. ✅ Reviewed changes with tech lead
3. ✅ Notified agentmanager and orchestrator teams
4. ✅ Coordinated deployment schedule
5. ✅ Created migration guide for dependent services
6. ✅ Merged after all teams confirmed readiness

---

## Command Line Options

### Run with custom work directory
```bash
/impact-check --work-dir ~/projects
```

### Run with custom coverage threshold
```bash
/impact-check --coverage-threshold 85
```

### Skip PR description append
```bash
/impact-check --no-append-pr
```

### Output in markdown format
```bash
/impact-check --format markdown > impact-report.md
```

---

## Integration Examples

### Pre-PR Checklist
```bash
#!/bin/bash
# pre-pr.sh - Run before creating a PR

echo "Running pre-PR checks..."

# Run tests with coverage
pytest --cov=. --cov-report=json:coverage.json

# Check impact
/impact-check

# If high-risk, prompt for confirmation
# ... add logic based on exit code or output parsing ...
```

### CI/CD Integration
```yaml
# .github/workflows/impact-check.yml
name: Impact Analysis

on: [pull_request]

jobs:
  impact-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install impact-check
        run: |
          git clone https://github.com/kodekrazy999/blast.git
          cp -r blast ~/.claude/skills/impact-check
      
      - name: Run tests with coverage
        run: pytest --cov=. --cov-report=json:coverage.json
      
      - name: Run impact check
        run: python ~/.claude/skills/impact-check/impact_check.py --format markdown >> $GITHUB_STEP_SUMMARY
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('impact-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

---

## Interpreting Results

### Impact Levels

| Level | Services | Action Required |
|-------|----------|-----------------|
| **[HIGH]** | Managers, Orchestrators, Gateways | Coordinate deployment, notify teams |
| **[MEDIUM]** | Regular services, APIs, WebApps | Review changes, update consumers |
| **[LOW]** | Analytics, Logging, Monitoring | Safe to proceed, minimal risk |

### Risk Verdicts

| Verdict | Meaning | Next Steps |
|---------|---------|------------|
| **[OK]** | No issues detected | Safe to merge |
| **[CAUTION]** | 1 high-impact caller OR coverage gap | Address issue before merge |
| **[WARNING]** | Multiple high-impact callers AND coverage gaps | Tech lead review + coordination required |

### Coverage Flags

| Status | Coverage | Action |
|--------|----------|--------|
| **[OK]** | ≥80% | Meets threshold |
| **[WARNING]** | <80% | Add tests before merge |

---

## Tips & Best Practices

### 1. Run Early and Often
```bash
# Check impact before starting work
/impact-check

# Check again after major changes
git add -A && git commit -m "WIP"
/impact-check
```

### 2. Keep Coverage Data Fresh
```bash
# Always run tests before impact-check
pytest --cov=. --cov-report=json:coverage.json
/impact-check
```

### 3. Use with PR Templates
```markdown
## PR Checklist
- [ ] Tests added/updated
- [ ] Ran `/impact-check`
- [ ] Blast radius reviewed
- [ ] HIGH-impact teams notified
- [ ] Coverage meets 80% threshold
```

### 4. Automate Notifications
```python
# parse_impact.py - Parse impact-check output
import subprocess
import json

result = subprocess.run([
    'python', '~/.claude/skills/impact-check/impact_check.py'
], capture_output=True, text=True)

# Parse HIGH impact callers
if '[HIGH]' in result.stdout:
    # Send Slack notification
    # Send email to teams
    # Create Jira tickets
    pass
```

---

## Troubleshooting

### No repos found
```bash
# Check work directory
ls ~/work
# Should show multiple repo directories

# Verify they're git repos
ls ~/work/*/.git
```

### No changed files detected
```bash
# Make sure you're on a feature branch
git branch
# Should show feature/* or fix/* branch

# Check for commits
git log --oneline -3
```

### No coverage data
```bash
# Run pytest with coverage
pytest --cov=. --cov-report=json:coverage.json

# Verify coverage file exists
ls -la coverage.json
```

---

See [TEST_REPORT.md](TEST_REPORT.md) for detailed test results and validation.
