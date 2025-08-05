# Issue #24: Remove most CI and pre-commit hooks other than tests
**Summary:** Streamlining CI pipeline and pre-commit hooks to only run tests, removing linting/formatting/security checks to save tokens.
**Outcome:** Expected significant reduction in CI token consumption while maintaining test coverage.

## Issue Link
https://github.com/devpouya/swissnews/issues/24

## Problem Analysis
The current CI pipeline and pre-commit hooks are consuming excessive tokens due to numerous quality checks:

### Current CI Jobs (Token Heavy):
1. **backend-test** - Tests + linting (black, flake8, isort) + type checking (mypy) + coverage
2. **frontend-test** - Tests + linting (eslint) + type checking + build + coverage  
3. **e2e-test** - End-to-end tests
4. **security-scan** - pip-audit + npm audit + CodeQL analysis
5. **migration-test** - Database migration tests
6. **performance-test** - Performance tests (main branch only)
7. **deploy** - Deployment (main branch only)

### Current Pre-commit Hooks (Token Heavy):
- File checks (trailing-whitespace, yaml, json, etc.)
- Python: black, isort, flake8, mypy
- Frontend: prettier, eslint
- Additional quality checks

## Solution Plan

### Phase 1: Streamline CI Pipeline
**Keep only essential test jobs:**
- `backend-test` - Unit and integration tests only (remove linting, formatting, type checking)
- `frontend-test` - Unit tests only (remove linting, type checking, build)
- `e2e-test` - Keep for critical functionality validation

**Remove token-heavy jobs:**
- `security-scan` - Remove pip-audit, npm audit, CodeQL
- `migration-test` - Remove database migration tests
- `performance-test` - Remove performance tests
- `deploy` - Keep but simplify dependencies

### Phase 2: Minimize Pre-commit Hooks
**Keep only essential checks:**
- `check-merge-conflict` - Critical for repo integrity
- `check-added-large-files` - Prevent repo bloat
- `debug-statements` - Prevent accidental debug code

**Remove formatting/linting hooks:**
- black, isort, flake8, mypy (Python)
- prettier, eslint (Frontend)
- Most file format checks

### Expected Benefits
- **Significant token reduction** - Removing ~70% of current CI checks
- **Faster CI runs** - Only essential tests remain
- **Maintained quality** - Core functionality still tested
- **Developer flexibility** - Local tooling handles formatting/linting

### Implementation Steps
1. ✅ Create branch: `feature/issue-24-streamline-ci-precommit`
2. 🔄 Document current setup and plan (this file)
3. ⏳ Modify `.github/workflows/ci.yml` - remove non-test jobs and steps
4. ⏳ Modify `.pre-commit-config.yaml` - keep only essential hooks  
5. ⏳ Test simplified CI pipeline
6. ⏳ Create PR for review

### Risk Mitigation
- Tests remain comprehensive ensuring functionality
- Local development tools can still handle formatting
- Future optimization can re-add selective checks if needed
- Code review process catches major issues