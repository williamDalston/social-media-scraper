# Metrics Analysis & Recommendations

## Current Metrics Assessment

### ✅ Currently Tracking (High Likelihood to Get)

#### Account-Level Metrics (FactFollowersSnapshot)
- **followers_count** ✅ **HIGH** - Available on all platforms
- **following_count** ✅ **HIGH** - Available on X, Instagram, LinkedIn
- **posts_count** ✅ **MEDIUM-HIGH** - Available on most platforms (some require API)
- **subscribers_count** ✅ **HIGH** - YouTube specific
- **listed_count** ⚠️ **LOW** - X specific, rarely visible without login

#### Engagement Metrics (Daily Aggregates)
- **likes_count** ⚠️ **MEDIUM** - Requires post-level scraping (not currently implemented)
- **comments_count** ⚠️ **MEDIUM** - Requires post-level scraping
- **shares_count** ⚠️ **MEDIUM** - Requires post-level scraping
- **engagements_total** ⚠️ **MEDIUM** - Calculated from above
- **video_views** ✅ **HIGH** - YouTube via API

#### Activity Metrics
- **stories_count** ⚠️ **LOW** - Instagram/Facebook stories, ephemeral, hard to track
- **videos_count** ⚠️ **MEDIUM** - Can be scraped but may not be accurate total
- **live_streams_count** ⚠️ **LOW** - Requires tracking during live events

### ⚠️ Low Likelihood to Get Without APIs

1. **Individual Post Metrics** - Would require scraping each post individually
   - Post-level likes/comments/shares
   - Post impressions
   - Post reach
   - Click-through rates

2. **Real-time Engagement** - Would require continuous monitoring
   - Stories views
   - Live stream viewers
   - Moment-to-moment engagement

3. **Demographics/Audience** - Typically requires API or business tools
   - Audience age/gender breakdown
   - Geographic distribution
   - Device types
   - Interests

---

## Recommended Additional Metrics (Feasible)

### 1. **Engagement Rate** ✅ **HIGH PRIORITY**
**Feasibility: HIGH** - Can be calculated from existing data

```python
engagement_rate = (total_engagements / followers_count) * 100
```

**Why it's useful:**
- Normalizes engagement across accounts with different follower counts
- Shows account health and content effectiveness
- Industry standard metric

**Implementation:** Calculate when storing snapshots

---

### 2. **Follower Growth Rate** ✅ **HIGH PRIORITY**
**Feasibility: HIGH** - Can be calculated from historical snapshots

```python
growth_rate = ((current_followers - previous_followers) / previous_followers) * 100
growth_absolute = current_followers - previous_followers
```

**Why it's useful:**
- Identifies trending accounts
- Shows impact of campaigns/events
- Detects account issues (negative growth)

**Implementation:** Calculate daily/weekly/monthly growth rates

---

### 3. **Account Age / Days Active** ✅ **HIGH PRIORITY**
**Feasibility: MEDIUM** - Can extract from profile pages or API

**Additional Fields Needed:**
```python
account_created_date = Column(Date)  # When account was created
days_active = Column(Integer)  # Calculated: today - created_date
```

**Why it's useful:**
- Context for follower counts (new vs. established)
- Growth velocity calculation
- Account maturity assessment

---

### 4. **Posting Frequency** ✅ **MEDIUM PRIORITY**
**Feasibility: MEDIUM** - Calculate from post count changes

```python
# Daily posting rate
posts_per_day = posts_count / days_active
posts_per_week = posts_count / (days_active / 7)
```

**Why it's useful:**
- Identifies inactive accounts
- Shows content strategy consistency
- Helps predict future activity

---

### 5. **Verified Status** ✅ **ALREADY IN SCHEMA**
**Feasibility: HIGH** - Visible on profile pages

**Status:**
- ✅ Already tracked in `DimAccount.verified_status`
- ⚠️ Need to ensure scrapers extract this

**Why it's useful:**
- Trust indicator
- Official vs. unofficial accounts
- Platform-specific verification types

---

### 6. **Video Metrics (YouTube)** ✅ **HIGH PRIORITY**
**Feasibility: HIGH** - Available via YouTube API

**Additional Metrics:**
```python
total_video_count = Column(Integer)  # Total videos on channel
total_video_views = Column(Integer)  # Lifetime video views
average_view_count = Column(Integer)  # Calculated: total_views / video_count
subscriber_growth_rate = Column(Float)  # Daily subscriber growth
```

**Why it's useful:**
- YouTube is a major platform (20+ accounts)
- Video engagement different from social posts
- Content performance tracking

---

### 7. **Account Reach / Impressions** ⚠️ **LOW PRIORITY**
**Feasibility: LOW** - Usually requires API access

**Why it's useful:**
- Shows actual audience size (beyond followers)
- Algorithmic distribution metrics
- Better engagement rate calculation

**Recommendation:** Add as optional field, populate if API available

---

### 8. **Hashtag Usage** ✅ **MEDIUM PRIORITY** 
**Feasibility: MEDIUM** - Can extract from recent posts

**Additional Fields Needed:**
```python
# In FactSocialPost (already exists)
hashtags = Column(Text)  # ✅ Already in schema

# New: aggregate at account level
top_hashtags = Column(Text)  # JSON array of most used hashtags
hashtag_count = Column(Integer)  # Number of unique hashtags used
```

**Why it's useful:**
- Content strategy insights
- Campaign tracking
- Topic identification

---

### 9. **Mentions / Tags** ✅ **MEDIUM PRIORITY**
**Feasibility: MEDIUM** - Can extract from recent posts

**Additional Fields:**
```python
# In FactSocialPost (already exists)
mentions = Column(Text)  # ✅ Already in schema

# New: aggregate at account level
mention_count = Column(Integer)  # Times account was mentioned
active_mentions = Column(Integer)  # Mentions in last 30 days
```

**Why it's useful:**
- Brand awareness tracking
- Influencer collaboration tracking
- Community engagement

---

### 10. **Response Time** ⚠️ **LOW PRIORITY**
**Feasibility: LOW** - Requires tracking comments/replies

**Why it's useful:**
- Customer service quality
- Engagement responsiveness
- Community management effectiveness

**Recommendation:** Future enhancement if post-level scraping implemented

---

## Platform-Specific Recommendations

### X (Twitter) - 43 accounts
**Currently Getting:**
- ✅ Followers ✅ Following ✅ Posts
- ⚠️ Engagement (requires individual post scraping)

**Recommended Additions:**
1. **Verified badge type** (Blue/Org/Gov) - ✅ Already tracked
2. **Listed count** - Available but may require login
3. **Account age** - Extract from profile
4. **Bio text** - For context and keyword tracking

**Likelihood: HIGH** ✅

---

### Facebook - 26 accounts
**Currently Getting:**
- ✅ Page likes/followers (via API or scraping)
- ⚠️ Engagement (limited without API)

**Recommended Additions:**
1. **Page verification status**
2. **Page category** (Government/Organization)
3. **Check-ins** (if public)
4. **Page rating** (if available)

**Likelihood: MEDIUM-HIGH** ⚠️ (Better with API token)

---

### Instagram - 7 accounts
**Currently Getting:**
- ✅ Followers ✅ Following ✅ Posts
- ⚠️ Engagement (requires individual post scraping)

**Recommended Additions:**
1. **Account type** (Business/Personal/Creator)
2. **Bio link** (often contains important URLs)
3. **Account category** (Government/Organization)
4. **Highlights count** (featured stories)

**Likelihood: HIGH** ✅ (Browser automation helps)

---

### LinkedIn - 12 accounts
**Currently Getting:**
- ✅ Followers (company pages)
- ⚠️ Engagement (requires API for reliable data)

**Recommended Additions:**
1. **Company size** (employee count)
2. **Industry**
3. **Follower growth trend**
4. **Recent job postings count**

**Likelihood: MEDIUM** ⚠️ (API access recommended)

---

### YouTube - 8 accounts
**Currently Getting:**
- ✅ Subscribers (via API)
- ✅ Video views (via API)
- ✅ Total videos (via API)

**Recommended Additions:**
1. **Total video views** (lifetime)
2. **Average views per video**
3. **Channel age**
4. **Upload frequency**
5. **Top video performance** (most viewed recent video)

**Likelihood: HIGH** ✅ (API makes this easy)

---

### Flickr - 1 account
**Currently Getting:**
- ✅ Photos count (basic scraping)

**Recommended Additions:**
1. **Collections count**
2. **Groups joined**
3. **Account age**

**Likelihood: MEDIUM** (Limited public data)

---

### Truth Social - 1 account
**Currently Getting:**
- ✅ Followers (basic scraping)

**Recommended Additions:**
1. **Account verification status**
2. **Following count**

**Likelihood: MEDIUM** (Platform has limited public API)

---

## Implementation Priority

### Phase 1: Quick Wins (Calculate from existing data)
1. ✅ **Engagement Rate** - Calculate on snapshot creation
2. ✅ **Follower Growth Rate** - Calculate from historical snapshots  
3. ✅ **Account Age** - Extract once, store in DimAccount

### Phase 2: Enhanced Scraping (Update scrapers)
4. ✅ **Verified Status** - Ensure all scrapers extract this
5. ✅ **Bio/Bio Link** - Extract from profile pages
6. ✅ **Account Type/Category** - Extract platform-specific info

### Phase 3: API Enhancements (If API keys available)
7. ✅ **YouTube Video Metrics** - Enhanced via API
8. ✅ **Facebook Page Details** - Via Graph API
9. ⚠️ **LinkedIn Company Info** - Via LinkedIn API (if available)

### Phase 4: Post-Level Scraping (Future)
10. ⚠️ **Individual Post Metrics** - Requires significant changes
11. ⚠️ **Hashtag Aggregation** - From post-level data
12. ⚠️ **Mention Tracking** - From post-level data

---

## Database Schema Updates Needed

### Add to FactFollowersSnapshot:
```python
# Calculated metrics (can be computed, not scraped)
engagement_rate = Column(Float)  # (engagements / followers) * 100
follower_growth_rate = Column(Float)  # Daily/weekly growth %
follower_growth_absolute = Column(Integer)  # Net follower change
posts_per_day = Column(Float)  # Average posting frequency

# Video-specific (YouTube)
total_video_views = Column(Integer)  # Lifetime video views
average_views_per_video = Column(Float)  # Calculated metric
```

### Add to DimAccount:
```python
account_created_date = Column(Date)  # When account was created
account_type = Column(String)  # Business/Personal/Creator/Government
account_category = Column(String)  # Platform-specific category
bio_text = Column(Text)  # Account bio/description
bio_link = Column(String)  # Link in bio (Instagram, X, etc.)
profile_image_url = Column(String)  # Profile picture URL
```

---

## Likelihood Assessment Summary

### High Likelihood (90-100%) ✅
- Engagement Rate (calculated)
- Follower Growth Rate (calculated)
- Account Age (scrape once)
- Verified Status (already in schema)
- YouTube Video Metrics (with API)
- Bio/Bio Link (visible on profiles)

### Medium Likelihood (50-90%) ⚠️
- Posting Frequency (calculated, needs accurate post counts)
- Account Type/Category (platform-dependent)
- Hashtag Usage (requires post scraping)
- LinkedIn Company Info (needs API)

### Low Likelihood (<50%) ❌
- Post-level engagement (requires massive scraping effort)
- Audience Demographics (API only)
- Real-time metrics (continuous monitoring)
- Response Times (requires reply tracking)

---

## Recommended Action Items

### Immediate (Can implement today):
1. ✅ Add engagement_rate calculation to snapshot creation
2. ✅ Add follower_growth_rate calculation  
3. ✅ Ensure verified_status is extracted by all scrapers

### Short-term (This week):
4. ✅ Extract account_created_date and store in DimAccount
5. ✅ Extract bio_text and bio_link from profiles
6. ✅ Add account_type and account_category fields

### Medium-term (This month):
7. ✅ Enhance YouTube scraper to get video metrics via API
8. ✅ Add posting frequency calculations
9. ✅ Create migration for new fields

### Long-term (Future):
10. ⚠️ Implement post-level scraping if needed
11. ⚠️ Add API integrations where beneficial
12. ⚠️ Build analytics dashboard for new metrics

---

## Conclusion

**Most useful metrics we can realistically track:**

1. **Engagement Rate** - Essential for comparing accounts
2. **Follower Growth Rate** - Shows account momentum  
3. **Posting Frequency** - Identifies inactive accounts
4. **Account Age** - Provides context for metrics
5. **Verified Status** - Trust indicator (already tracked)
6. **YouTube Video Metrics** - Critical for 8 accounts

**All of these are HIGH likelihood (80-100%) to successfully implement.**

The current schema is well-designed and already tracks most essential metrics. The recommended additions are primarily:
- Calculated metrics (no additional scraping needed)
- One-time profile data (scrape once and store)
- Enhanced API usage (where API keys are available)

