# GitHub Pages Quick Setup Guide

## Repository Information
- **Repository**: `williamDalston/social-media-scraper`
- **Repository URL**: https://github.com/williamDalston/social-media-scraper
- **Public folder**: `/public` (contains `index.html` and data files)

## Step-by-Step Setup

### 1. Go to GitHub Pages Settings
**Direct Link**: https://github.com/williamDalston/social-media-scraper/settings/pages

Or navigate manually:
1. Go to your repository: https://github.com/williamDalston/social-media-scraper
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)

### 2. Configure GitHub Pages

**Source Settings:**
- **Source**: Select "Deploy from a branch"
- **Branch**: Select `main`
- **Folder**: Select `/public` (or `/ (root)` if you want the whole repo)
- Click **Save**

### 3. Wait for Deployment
- GitHub will build and deploy your site
- This usually takes 1-2 minutes
- You'll see a green checkmark when it's ready

### 4. Your Site URL
Once deployed, your site will be available at:
**https://williamDalston.github.io/social-media-scraper/**

## What Gets Deployed

Your `public/` folder contains:
- `index.html` - Your dashboard/website
- `hhs_accounts.json` - Account data
- Any other files in the `public/` folder

## Automatic Updates

Your workflow (`.github/workflows/scrape-and-export.yml`) already:
1. Runs the scraper
2. Exports data to `public/data/`
3. Commits and pushes changes
4. GitHub Pages automatically updates when you push to `main`

## Troubleshooting

If the site doesn't load:
1. Check the Actions tab for deployment status
2. Make sure the `public/` folder exists and has files
3. Wait a few minutes for the first deployment
4. Check the Pages settings show "Your site is live at..."

## Custom Domain (Optional)

If you want a custom domain:
1. Add a `CNAME` file in the `public/` folder with your domain
2. Configure DNS settings for your domain
3. Update GitHub Pages settings with your custom domain
