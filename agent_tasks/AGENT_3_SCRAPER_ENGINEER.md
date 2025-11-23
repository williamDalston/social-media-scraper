# Agent 3: SCRAPER_ENGINEER (Casey)
## Production Enhancement: Real Scraper Implementation

### 🎯 Mission
Build production-ready scrapers for all supported platforms (X, Instagram, Facebook, LinkedIn, YouTube, Truth Social) with proper error handling, rate limiting, and data extraction.

---

## 📋 Detailed Tasks

### 1. Platform-Specific Scrapers

#### 1.1 X (Twitter) Scraper
- **File:** `scraper/platforms/x_scraper.py`
- **Options:**
  - Option A: Use Twitter API v2 (requires API keys)
  - Option B: Web scraping with proper headers and session management
- **Extract:**
  - Follower count
  - Following count
  - Tweet count
  - Likes, retweets, replies from recent tweets
- **Handle:**
  - Rate limits (429 errors)
  - Private accounts
  - Suspended/deleted accounts
  - Authentication requirements

#### 1.2 Instagram Scraper
- **File:** `scraper/platforms/instagram_scraper.py`
- **Approach:** Web scraping (Instagram API requires approval)
- **Extract:**
  - Follower count
  - Following count
  - Post count
  - Engagement metrics from recent posts
- **Handle:**
  - Login requirements (if needed)
  - Rate limiting
  - Private accounts
  - GraphQL endpoints

#### 1.3 Facebook Scraper
- **File:** `scraper/platforms/facebook_scraper.py`
- **Options:**
  - Option A: Facebook Graph API (requires access token)
  - Option B: Web scraping public pages
- **Extract:**
  - Page likes/followers
  - Post engagement (likes, comments, shares)
  - Recent post count
- **Handle:**
  - API rate limits
  - Public vs private pages
  - Access token expiration

#### 1.4 LinkedIn Scraper
- **File:** `scraper/platforms/linkedin_scraper.py`
- **Approach:** Web scraping (LinkedIn API is restricted)
- **Extract:**
  - Follower count
  - Recent post engagement
  - Company/showcase page metrics
- **Handle:**
  - Login requirements
  - Bot detection
  - Rate limiting
  - Different page types (company, showcase, personal)

#### 1.5 YouTube Scraper
- **File:** `scraper/platforms/youtube_scraper.py`
- **Approach:** YouTube Data API v3 (recommended)
- **Extract:**
  - Subscriber count
  - Video count
  - View counts
  - Engagement (likes, comments)
- **Handle:**
  - API quota limits
  - Channel vs user URLs
  - API key management

#### 1.6 Truth Social Scraper
- **File:** `scraper/platforms/truth_scraper.py`
- **Approach:** Web scraping
- **Extract:**
  - Follower count
  - Following count
  - Post count
  - Engagement metrics
- **Handle:**
  - Platform-specific structure
  - Rate limiting
  - Authentication if required

---

### 2. Scraper Infrastructure

#### 2.1 Base Scraper Enhancement
- **File:** `scraper/scrapers.py`
- Enhance `BaseScraper` with:
  - Retry logic with exponential backoff
  - Timeout handling
  - Error logging
  - Result validation

#### 2.2 Retry Logic
- **File:** `scraper/utils/retry.py`
- Implement:
  - Exponential backoff (1s, 2s, 4s, 8s)
  - Max retries (3-5 attempts)
  - Retry on specific errors (network, 429, 500)
  - Skip retry on permanent errors (404, 403)

#### 2.3 Rate Limiting
- **File:** `scraper/utils/rate_limiter.py`
- Per-platform rate limits:
  - X: 15 requests per 15 minutes (if using API)
  - Instagram: Conservative (avoid blocks)
  - Facebook: Per API tier
  - YouTube: 10,000 units per day (manage quota)
  - LinkedIn: Very conservative
- Use time-based delays between requests

#### 2.4 Proxy Support
- **File:** `scraper/utils/proxy_manager.py`
- Optional proxy rotation:
  - Load proxies from config
  - Rotate on failure
  - Test proxy health
  - Fallback to direct connection

#### 2.5 Error Handling
- **File:** `scraper/utils/errors.py`
- Custom exceptions:
  - `ScraperError` (base)
  - `RateLimitError`
  - `AuthenticationError`
  - `AccountNotFoundError`
  - `PrivateAccountError`

---

### 3. Data Extraction

#### 3.1 Follower Count Extraction
- Parse follower counts from various formats:
  - "1.2M" → 1,200,000
  - "500K" → 500,000
  - "1,234" → 1,234
- Handle different locales and formats

#### 3.2 Engagement Metrics
- Extract from recent posts:
  - Likes
  - Comments
  - Shares/Retweets
  - Views (where available)
- Aggregate daily totals

#### 3.3 Post Count
- Get total post count
- Calculate new posts since last scrape
- Handle pagination for large accounts

#### 3.4 Data Validation
- Validate extracted data:
  - Numbers are positive integers
  - Counts are reasonable (not negative, not impossibly large)
  - Dates are valid
  - Required fields present

---

### 4. Configuration Management

#### 4.1 Scraper Configuration
- **File:** `scraper/config.py`
- Configuration for:
  - API keys (from environment)
  - Rate limits per platform
  - Timeouts
  - Retry settings
  - Proxy settings
  - User agents

#### 4.2 Environment Variables
- Required:
  - `TWITTER_API_KEY` (optional)
  - `TWITTER_API_SECRET` (optional)
  - `FACEBOOK_ACCESS_TOKEN` (optional)
  - `YOUTUBE_API_KEY` (required for YouTube)
  - `INSTAGRAM_USERNAME` (optional, if login needed)
  - `INSTAGRAM_PASSWORD` (optional, if login needed)

#### 4.3 Platform Settings
- **File:** `scraper/platforms/config.py`
- Per-platform settings:
  - Default user agents
  - Request headers
  - Timeout values
  - Retry counts

---

## 📁 File Structure to Create

```
scraper/
├── platforms/
│   ├── __init__.py
│   ├── base_platform.py        # Base class for platform scrapers
│   ├── x_scraper.py
│   ├── instagram_scraper.py
│   ├── facebook_scraper.py
│   ├── linkedin_scraper.py
│   ├── youtube_scraper.py
│   ├── truth_scraper.py
│   └── config.py
├── utils/
│   ├── __init__.py
│   ├── retry.py
│   ├── rate_limiter.py
│   ├── proxy_manager.py
│   ├── errors.py
│   └── parsers.py              # Helper functions for parsing
└── config.py                   # Main scraper configuration
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
beautifulsoup4>=4.12.0
selenium>=4.15.0              # Optional, for JS-heavy sites
requests>=2.31.0
google-api-python-client>=2.100.0  # For YouTube API
tweepy>=4.14.0                # Optional, for Twitter API
lxml>=4.9.0
html5lib>=1.1
```

---

## ✅ Acceptance Criteria

- [ ] All platform scrapers implemented
- [ ] Scrapers handle errors gracefully
- [ ] Rate limiting is implemented
- [ ] Retry logic works correctly
- [ ] Data extraction is accurate
- [ ] Configuration is externalized
- [ ] API keys are managed securely
- [ ] Scrapers fall back to simulation on failure (optional)
- [ ] All scrapers are tested

---

## 🧪 Testing Requirements

- Test each platform scraper independently
- Test error handling (network errors, rate limits)
- Test data parsing (various formats)
- Test retry logic
- Test rate limiting
- Mock external API calls
- Test with real accounts (integration tests)

---

## 📝 Implementation Notes

### X (Twitter) Scraper:
- If using API: Use Tweepy library
- If web scraping: Parse HTML or use Selenium for dynamic content
- Handle both x.com and twitter.com URLs

### Instagram Scraper:
- Web scraping is complex due to bot detection
- May need to use Selenium with proper delays
- Consider using Instagram's GraphQL endpoints (if accessible)
- Handle login sessions carefully

### Facebook Scraper:
- Graph API is preferred if available
- Requires access token
- Handle different page types (pages, groups, profiles)

### YouTube Scraper:
- Use YouTube Data API v3
- Manage API quota carefully
- Handle different URL formats (@handle, /c/, /user/)

### LinkedIn Scraper:
- Most challenging due to bot detection
- May require Selenium with human-like behavior
- Handle login carefully
- Respect rate limits strictly

### Truth Social Scraper:
- Similar to Twitter scraping
- Parse HTML structure
- Handle platform-specific quirks

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-3-scraper`
2. Install dependencies: `pip install -r requirements.txt`
3. Create platform scraper structure
4. Start with one platform (recommend YouTube - easiest with API)
5. Implement base scraper enhancements
6. Add retry and rate limiting
7. Implement remaining platforms
8. Add configuration management
9. Test thoroughly
10. Document API key requirements

---

## 🔑 API Key Setup

Create `.env.example` with:
```
# Twitter API (Optional)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_BEARER_TOKEN=

# Facebook Graph API (Optional)
FACEBOOK_ACCESS_TOKEN=

# YouTube Data API (Required for YouTube)
YOUTUBE_API_KEY=

# Instagram (Optional, if login needed)
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
```

---

## ⚠️ Important Considerations

- **Legal/Ethical:** Ensure scraping complies with platform ToS
- **Rate Limits:** Be respectful of platform rate limits
- **Bot Detection:** Some platforms actively block scrapers
- **API vs Scraping:** Prefer APIs when available
- **Fallback:** Consider falling back to simulation if scraping fails
- **Monitoring:** Log all scraping attempts and failures

---

**Agent Casey - Ready to scrape the web! 🕷️**

