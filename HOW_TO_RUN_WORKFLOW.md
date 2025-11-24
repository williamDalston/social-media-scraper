# How to Run the GitHub Actions Workflow

## Quick Links

### Main Actions Page
🔗 **https://github.com/williamDalston/social-media-scraper/actions**

### Direct Workflow Link
🔗 **https://github.com/williamDalston/social-media-scraper/actions/workflows/scrape-and-export.yml**

## Step-by-Step Instructions

### Option 1: From the Actions Page

1. **Go to GitHub Actions**
   - Navigate to: https://github.com/williamDalston/social-media-scraper/actions
   - Or click "Actions" tab in your repository

2. **Find the Workflow**
   - Look for "Scrape and Export Data" in the workflow list
   - Click on it to see the workflow details

3. **Run the Workflow**
   - Click the **"Run workflow"** button (top right, dropdown)
   - Select branch: **main**
   - Click **"Run workflow"** button

4. **Monitor the Run**
   - You'll see a new workflow run appear
   - Click on it to see the progress
   - Watch the steps execute in real-time

### Option 2: From the Workflow File

1. **Go to the Workflow File**
   - Navigate to: `.github/workflows/scrape-and-export.yml`
   - Or: https://github.com/williamDalston/social-media-scraper/blob/main/.github/workflows/scrape-and-export.yml

2. **Click "Actions" Tab**
   - You'll see a banner at the top
   - Click "Actions" or "View workflow runs"

3. **Run the Workflow**
   - Click **"Run workflow"** dropdown
   - Select branch: **main**
   - Click **"Run workflow"**

## What to Look For

### ✅ Successful Run
- All steps show green checkmarks ✓
- "Initialize database" step completes successfully
- Final step "Commit and push changes" completes

### ⚠️ Failed Run
- Red X marks on failed steps
- Click on the failed step to see error details
- Check the diagnostic output in "CRITICAL DIAGNOSTIC" step

## Understanding the Output

### Diagnostic Step
The workflow now includes a "CRITICAL DIAGNOSTIC" step that shows:
- Git commit hash (should be `a85a160` or newer)
- Branch name (should be `main`)
- Python path and version
- Schema.py file verification
- Module import location

### Initialize Database Step
This step will:
1. Run `scripts/init_db_ci.py` (uses explicit SQLite URLs)
2. If that fails, use fallback with explicit URLs
3. Show detailed error messages if anything fails

## Troubleshooting

### If Workflow Fails

1. **Check the commit hash**
   - In the diagnostic step, verify it shows `a85a160` or newer
   - If it shows an older commit, the workflow is using old code

2. **Check the error message**
   - Look at the "Initialize database" step output
   - The diagnostic step will show exactly what's wrong

3. **Verify secrets are set**
   - Go to: Settings → Secrets and variables → Actions
   - Make sure `SECRET_KEY` and `JWT_SECRET_KEY` are set

### If You Don't See "Run workflow" Button

- Make sure you're logged into GitHub
- Make sure you have write access to the repository
- Try refreshing the page

## Automatic Runs

The workflow also runs automatically:
- **Scheduled**: Daily at 2 AM UTC (configured in workflow)
- **On push**: When code is pushed to `main` branch (if configured)

## Quick Access

Bookmark this link for quick access:
**https://github.com/williamDalston/social-media-scraper/actions/workflows/scrape-and-export.yml**
