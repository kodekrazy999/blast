# Impact Check - Quick Start Guide

## Installation (30 seconds)

The skill is already installed at `~/.claude/skills/impact-check/` and ready to use!

## Basic Usage

### Option 1: Through Claude Code (Recommended)

```bash
# In any repo with changes
/impact-check
```

That's it! Claude will:
1. Detect your changed files
2. Scan all repos under ~/work for dependencies
3. Check test coverage
4. Generate and append report to your PR

### Option 2: Direct Python Script

```bash
python ~/.claude/skills/impact-check/impact_check.py
```

## Your First Run (5 minutes)

### Step 1: Set up your work directory

```bash
# Your repos should be organized like this:
~/work/
├── kube-wizr-logger-history/
├── kube-wizr-agentmanager/
├── kube-wizr-app-orchestrator/
├── webapp-wizrai-connect/
└── ... (other services)
```

If your repos are elsewhere:

```bash
/impact-check --work-dir ~/projects
```

### Step 2: Make sure you have changes on a branch

```bash
git checkout -b feature/my-changes
# ... make some changes ...
git add .
git commit -m "My changes"
```

### Step 3: (Optional) Generate coverage data

```bash
pytest --cov=. --cov-report=json:coverage.json
```

Without this, the skill will still work but won't show coverage info.

### Step 4: Run impact check

```bash
/impact-check
```

## Understanding the Output

### Blast Radius Section

Shows who's calling your changed code:

- **[HIGH]** 🔴 - Critical services (managers, orchestrators, gateways)
- **[MEDIUM]** 🟡 - Regular services (webapps, APIs)
- **[LOW]** 🟢 - Non-critical (analytics, logging, monitoring)

### Coverage Section

Shows test coverage on your changed files:

- **✓** - Meets 80% threshold
- **⚠** - Below 80% threshold

### Risk Verdict

- **✓ OK** - No issues detected
- **⚠ CAUTION** - 1+ high-impact callers OR coverage gaps
- **⚠ WARNING** - Multiple high-impact callers AND coverage gaps

## Common Scenarios

### Scenario 1: Changing a utility function

```
BLAST RADIUS: 3 services importing your helper
COVERAGE: 85% ✓
VERDICT: OK
```

**What to do**: Proceed with PR, low risk.

### Scenario 2: Changing an API endpoint

```
BLAST RADIUS: 2 HIGH-impact callers (manager, orchestrator)
COVERAGE: 90% ✓
VERDICT: CAUTION
```

**What to do**: Notify the teams owning the calling services before merge.

### Scenario 3: New feature with low coverage

```
BLAST RADIUS: No callers (new code)
COVERAGE: 45% ⚠
VERDICT: CAUTION
```

**What to do**: Run `/coverage-gap` to add tests before merge.

### Scenario 4: High-risk change

```
BLAST RADIUS: 3 HIGH-impact callers
COVERAGE: 55% ⚠
VERDICT: WARNING
```

**What to do**: 
1. Add tests to reach 80%
2. Review with tech lead
3. Coordinate deployment with dependent services

## Customization

### Change coverage threshold

```bash
/impact-check --coverage-threshold 85
```

### Skip PR append

```bash
/impact-check --no-append-pr
```

### Different work directory

```bash
/impact-check --work-dir ~/my-projects
```

## Integration with Story-to-PR

Add to your workflow:

```bash
# 1. Implement feature
# 2. Run tests
pytest --cov=. --cov-report=json:coverage.json

# 3. Check impact before PR
/impact-check

# 4. If OK, create PR
/story-to-pr
```

The impact report will be automatically added to your PR description!

## Troubleshooting

### "No repos found"

Check your work directory structure:

```bash
ls ~/work/
```

Should show multiple repos. If not, use `--work-dir`:

```bash
/impact-check --work-dir /path/to/your/repos
```

### "No changed files detected"

Make sure you're on a feature branch with commits:

```bash
git branch  # Check current branch
git status  # Check for changes
```

### "No coverage data found"

Run pytest with coverage first:

```bash
pytest --cov=. --cov-report=json:coverage.json
```

Or continue without coverage - the skill will still show blast radius.

### "Failed to append to PR"

Make sure:
1. You have GitHub CLI installed: `gh --version`
2. You're authenticated: `gh auth login`
3. You have an open PR: `gh pr view`

## Next Steps

- Set up automatic coverage generation in CI
- Add impact-check to your pre-PR checklist
- Configure in `.claude/settings.json` for your preferences
- Share the skill with your team!

## Need Help?

Check the full documentation: `~/.claude/skills/impact-check/README.md`
