# GitHub Pages Configuration

This repository uses GitHub Pages to serve the static dashboard.

## Current Configuration

- **Source**: Deploy from branch `main`
- **Branch**: `main`
- **Folder**: `/ (root)` 
- **File**: `index.html` in root directory
- **Jekyll**: Disabled (`.nojekyll` file present)

## Accessing the Dashboard

The dashboard is available at:
https://williamdalston.github.io/social-media-scraper/

## Troubleshooting

If the old landing page appears:
1. Check Repository Settings → Pages → Source is set to `main` branch, `/ (root)`
2. Wait 5-10 minutes for GitHub Pages to rebuild
3. Clear browser cache (Ctrl+F5 or Cmd+Shift+R)
4. Check the Actions tab for any build errors

## Files

- `index.html` - Main dashboard (root)
- `.nojekyll` - Prevents Jekyll processing
- `public/index.html` - Same dashboard (backup location)
