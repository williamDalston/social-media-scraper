# HHS Social Media API Documentation

## Overview

The HHS Social Media API provides endpoints for managing social media accounts, retrieving metrics, running scrapers, and performing administrative operations.

**Base URL:** `http://localhost:5000/api/v1`  
**API Version:** 1.0  
**Documentation:** `http://localhost:5000/api/docs` (Swagger UI)

---

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### Authentication Endpoints (v1)

All authentication endpoints are available under `/api/v1/auth`:

- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/logout` - Logout (client-side token removal)
- `GET /api/v1/auth/me` - Get current user information
- `POST /api/v1/auth/refresh` - Refresh access token

**Note:** Authentication endpoints are also available at `/api/auth/*` for backward compatibility.

### Getting an Access Token

1. **Register** (Admin only) or **Login** to get an access token:

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "your_username",
    "role": "Admin"
  }
}
```

2. **Use the token** in subsequent requests:

```bash
curl -X GET http://localhost:5000/api/v1/metrics/summary \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Roles

- **Admin**: Full access to all endpoints
- **Editor**: Can manage accounts, run scrapers, view all data
- **Viewer**: Read-only access to metrics and data

---

## Endpoints

### Metrics Endpoints

#### Get Summary Metrics

Get summary metrics for all accounts at the latest snapshot date.

**Endpoint:** `GET /api/v1/metrics/summary`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/metrics/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
[
  {
    "platform": "X",
    "handle": "@hhsgov",
    "followers": 1250000,
    "engagement": 45000,
    "posts": 5
  },
  {
    "platform": "Instagram",
    "handle": "hhsgov",
    "followers": 800000,
    "engagement": 32000,
    "posts": 3
  }
]
```

#### Get Account History

Get historical metrics for a specific account.

**Endpoint:** `GET /api/v1/metrics/history/{platform}/{handle}`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Path Parameters:**
- `platform` (string, required): Social media platform (X, Instagram, Facebook, LinkedIn, YouTube, Truth Social)
- `handle` (string, required): Account handle

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/metrics/history/X/@hhsgov \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
  "followers": [1200000, 1210000, 1250000],
  "engagement": [40000, 42000, 45000]
}
```

#### Get Grid Data

Get all metrics data in grid format.

**Endpoint:** `GET /api/v1/metrics/grid`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/metrics/grid \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
[
  {
    "platform": "X",
    "handle": "@hhsgov",
    "org_name": "HHS",
    "snapshot_date": "2024-01-03",
    "followers_count": 1250000,
    "engagements_total": 45000,
    "posts_count": 5,
    "likes_count": 30000,
    "comments_count": 10000,
    "shares_count": 5000
  }
]
```

#### Download CSV

Download all metrics data as a CSV file.

**Endpoint:** `GET /api/v1/metrics/download`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/metrics/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o data.csv
```

---

### Accounts Endpoints

#### List Accounts

Get a list of all accounts.

**Endpoint:** `GET /api/v1/accounts`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/accounts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
[
  {
    "account_key": 1,
    "platform": "X",
    "handle": "@hhsgov",
    "org_name": "HHS",
    "account_display_name": "HHS on X",
    "account_url": "https://x.com/@hhsgov",
    "is_core_account": true,
    "account_type": "official dept"
  }
]
```

#### Upload Accounts (CSV)

Upload accounts from a CSV file.

**Endpoint:** `POST /api/v1/accounts/upload`  
**Authentication:** Required  
**Authorization:** Admin or Editor only

**Request:** Multipart form data with CSV file

**CSV Format:**
```csv
Platform,Handle,Organization
X,@hhsgov,HHS
Instagram,hhsgov,HHS
Facebook,hhsgov,HHS
```

**Example Request:**
```bash
curl -X POST http://localhost:5000/api/v1/accounts/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@accounts.csv"
```

**Example Response:**
```json
{
  "message": "Successfully added 3 accounts",
  "count": 3
}
```

---

### Jobs Endpoints

#### Run Scraper

Run the scraper to collect metrics for all accounts.

**Endpoint:** `POST /api/v1/jobs/run-scraper`  
**Authentication:** Required  
**Authorization:** Admin or Editor only

**Request Body:**
```json
{
  "mode": "simulated"
}
```

**Parameters:**
- `mode` (string, optional): Scraper mode - "simulated" or "real" (default: "simulated")

**Example Request:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/run-scraper \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'
```

**Example Response:**
```json
{
  "message": "Scraper finished successfully",
  "execution_time": 12.5
}
```

#### Get Job Status

Get status of background jobs.

**Endpoint:** `GET /api/v1/jobs/status`  
**Authentication:** Required  
**Authorization:** Any authenticated user

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/jobs/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Admin Endpoints

#### Get Admin Info

Get administrative information (Admin only).

**Endpoint:** `GET /api/v1/admin/info`  
**Authentication:** Required  
**Authorization:** Admin only

**Example Request:**
```bash
curl -X GET http://localhost:5000/api/v1/admin/info \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**
```json
{
  "message": "Admin information",
  "version": "1.0",
  "note": "Admin endpoints will be expanded in future versions"
}
```

---

## Error Responses

All errors follow a standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error details (optional)
    }
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR` (422): Request validation failed
- `UNAUTHORIZED` (401): Authentication required
- `FORBIDDEN` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `BAD_REQUEST` (400): Malformed request
- `INTERNAL_SERVER_ERROR` (500): Internal server error
- `RATE_LIMIT_EXCEEDED` (429): Rate limit exceeded

### Example Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation error",
    "details": {
      "platform": ["Invalid platform. Must be one of: X, Instagram, Facebook, LinkedIn, YouTube, Truth Social"],
      "handle": ["Handle is required"]
    }
  }
}
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limits:** 200 requests per day, 50 requests per hour
- **Rate limit headers:** Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`
- **Exceeding limits:** Returns `429 Too Many Requests` with retry information

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `page` (integer, default: 1): Page number
- `per_page` (integer, default: 10, max: 100): Items per page

**Example:**
```bash
curl -X GET "http://localhost:5000/api/v1/accounts?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

## Code Examples

### Python

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"
TOKEN = "your_access_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get summary
response = requests.get(f"{BASE_URL}/metrics/summary", headers=headers)
data = response.json()
print(data)

# Run scraper
response = requests.post(
    f"{BASE_URL}/jobs/run-scraper",
    headers=headers,
    json={"mode": "simulated"}
)
print(response.json())
```

### JavaScript (Fetch API)

```javascript
const BASE_URL = 'http://localhost:5000/api/v1';
const TOKEN = 'your_access_token';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// Get summary
fetch(`${BASE_URL}/metrics/summary`, { headers })
  .then(response => response.json())
  .then(data => console.log(data));

// Run scraper
fetch(`${BASE_URL}/jobs/run-scraper`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ mode: 'simulated' })
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### cURL

```bash
# Set token variable
TOKEN="your_access_token"

# Get summary
curl -X GET "http://localhost:5000/api/v1/metrics/summary" \
  -H "Authorization: Bearer $TOKEN"

# Run scraper
curl -X POST "http://localhost:5000/api/v1/jobs/run-scraper" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'
```

---

## Swagger UI

Interactive API documentation is available at:

**URL:** `http://localhost:5000/api/docs`

The Swagger UI provides:
- Interactive endpoint testing
- Request/response examples
- Schema documentation
- Authentication testing

---

## Versioning

The API uses URL-based versioning:

- **Current version:** `/api/v1`
- **Future versions:** `/api/v2`, etc.

When a new version is released, the previous version will remain available for backward compatibility. A deprecation warning will be included in response headers for older versions.

---

## Support

For issues or questions:
- Check the Swagger UI documentation at `/api/docs`
- Review error messages and status codes
- Check logs for detailed error information

---

## Changelog

### Version 1.0 (Current)
- Initial API release
- Metrics endpoints
- Account management
- Job management
- Admin endpoints
- Swagger/OpenAPI documentation
- Request/response validation
- Standardized error handling
- JWT authentication
- Rate limiting

