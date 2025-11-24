# Potential Issues Analysis

## The Error You're Seeing

The error shows:
```
Run python -c "from scraper.schema import init_db; init_db('social_media.db')"
```

But this command is **NOT** in the current workflow file.

## Possible Issues (in order of likelihood)

### 1. ⚠️ **OLD WORKFLOW RUN** (Most Likely)
- The error is from a workflow run that happened BEFORE our fixes
- GitHub Actions shows old runs in the UI
- **Solution**: Check the workflow run timestamp and commit hash
- **Verify**: Look at the "Run" details in GitHub Actions - what commit does it show?

### 2. 🔍 **PYTHON MODULE CACHING**
- Python might be importing a cached version of `schema.py`
- `__pycache__` files might contain old bytecode
- **Solution**: Clear Python cache in workflow
- **Check**: Add step to remove `__pycache__` before running

### 3. 📦 **DIFFERENT BRANCH OR COMMIT**
- Workflow might be running from a different branch
- `ref: ${{ github.head_ref || github.ref }}` might resolve to wrong commit
- **Solution**: Explicitly set the ref to `main` branch
- **Check**: Add step to print exact commit hash being used

### 4. 🔄 **GITHUB ACTIONS CACHE**
- GitHub might be caching the repository state
- Even with `clean: true`, some caches might persist
- **Solution**: Disable all caching or use cache-busting
- **Check**: Look for any `actions/cache` usage (we don't have any)

### 5. 🐍 **PYTHON PATH ISSUES**
- Python might be importing from wrong location
- Multiple `schema.py` files might exist
- **Solution**: Verify Python path and import location
- **Check**: Add step to show `sys.path` and module location

### 6. 📝 **WORKFLOW FILE NOT UPDATED ON GITHUB**
- The workflow file on GitHub might be different from local
- **Solution**: Force push or verify remote
- **Check**: Compare local vs remote workflow file

### 7. 🔗 **FORK OR DIFFERENT REPOSITORY**
- Workflow might be running from a fork
- **Solution**: Verify repository URL in workflow run
- **Check**: Look at workflow run details for repository

### 8. ⚙️ **WORKFLOW_DISPATCH PARAMETERS**
- Manual trigger might have different parameters
- **Solution**: Check if workflow_dispatch has inputs
- **Check**: Look at workflow definition for inputs

### 9. 🧩 **IMPORT FROM DIFFERENT MODULE**
- Code might be importing from a different `schema.py`
- **Solution**: Verify import path
- **Check**: Add step to show where module is imported from

### 10. 🕐 **SCHEDULED RUN VS MANUAL RUN**
- Scheduled runs might use different code
- **Solution**: Check if scheduled run uses different commit
- **Check**: Compare manual vs scheduled run commits

## Diagnostic Steps to Add

Add these to the workflow to diagnose:

```yaml
- name: DIAGNOSTIC - Show exact environment
  run: |
    echo "=== Python Path ==="
    python -c "import sys; print('\n'.join(sys.path))"
    echo ""
    echo "=== Module Location ==="
    python -c "from scraper.schema import init_db; import inspect; print(inspect.getfile(init_db))"
    echo ""
    echo "=== Schema.py Content Check ==="
    head -20 scraper/schema.py
    echo ""
    echo "=== Check for __pycache__ ==="
    find . -name "__pycache__" -type d
    echo ""
    echo "=== Git Info ==="
    git rev-parse HEAD
    git branch --show-current
    git remote -v
```

## Most Likely Solution

The error is from an **OLD workflow run**. To verify:
1. Go to GitHub Actions
2. Check the run timestamp
3. Check the commit hash shown in the run
4. Compare with our latest commit: `0cf8014`

If the commit is different, that's the issue - it's an old run.
