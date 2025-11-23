# API Tutorial - Getting Started

## Introduction

This tutorial will guide you through using the HHS Social Media Scraper API. We'll cover authentication, making requests, and common use cases.

## Prerequisites

- API access credentials
- `curl` or a REST client (Postman, Insomnia, etc.)
- Basic understanding of REST APIs

## Step 1: Authentication

### Register a New User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "password": "SecurePassword123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 86400
}
```

### Using the Token

Include the token in the Authorization header:

```bash
curl -X GET http://localhost:5000/api/summary \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Step 2: Get Account Summary

Get the latest metrics for all accounts:

```bash
curl -X GET http://localhost:5000/api/summary \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
[
  {
    "platform": "X",
    "handle": "HHSGov",
    "followers": 500000,
    "engagement": 15000,
    "posts": 5
  }
]
```

## Step 3: Get Historical Data

Get historical data for a specific account:

```bash
curl -X GET "http://localhost:5000/api/history/X/HHSGov" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "dates": ["2024-01-01", "2024-01-02", ...],
  "followers": [500000, 501000, ...],
  "engagement": [15000, 16000, ...]
}
```

## Step 4: Upload Accounts

Upload a CSV file with accounts to track:

```bash
curl -X POST http://localhost:5000/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@accounts.csv"
```

CSV format:
```csv
Platform,Handle,Organization
X,HHSGov,HHS
Instagram,hhsgov,HHS
```

## Step 5: Run Scraper

Trigger a scraper run:

```bash
curl -X POST http://localhost:5000/api/run-scraper \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'
```

## Step 6: Download Data

Download all data as CSV:

```bash
curl -X GET http://localhost:5000/api/download \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -o data.csv
```

## Advanced: OAuth2 Login

### Google OAuth

1. Get OAuth providers:
```bash
curl http://localhost:5000/api/auth/oauth/providers
```

2. Redirect user to:
```
http://localhost:5000/api/auth/oauth/google/authorize
```

3. Handle callback and receive tokens

## Advanced: MFA Setup

1. Setup MFA:
```bash
curl -X POST http://localhost:5000/api/auth/mfa/setup \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

2. Scan QR code with authenticator app

3. Enable MFA:
```bash
curl -X POST http://localhost:5000/api/auth/mfa/enable \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token": "123456"}'
```

## Error Handling

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## Rate Limiting

API requests are rate-limited. Check response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Best Practices

1. **Store tokens securely** - Never commit tokens to version control
2. **Handle token expiration** - Use refresh tokens to get new access tokens
3. **Implement retry logic** - Retry on 429 (rate limit) and 500 errors
4. **Cache responses** - Cache summary and history data
5. **Use pagination** - For large datasets, use pagination
6. **Monitor rate limits** - Track your API usage

## Code Examples

### Python

```python
import requests

BASE_URL = "http://localhost:5000"

# Login
response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "myuser",
    "password": "password"
})
tokens = response.json()
access_token = tokens['access_token']

# Get summary
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/api/summary", headers=headers)
data = response.json()
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:5000';

// Login
const loginResponse = await fetch(`${BASE_URL}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'myuser',
    password: 'password'
  })
});
const tokens = await loginResponse.json();

// Get summary
const summaryResponse = await fetch(`${BASE_URL}/api/summary`, {
  headers: { 'Authorization': `Bearer ${tokens.access_token}` }
});
const data = await summaryResponse.json();
```

## Next Steps

- Read the [API Documentation](./API_USAGE.md) for detailed endpoint documentation
- Check out [Swagger UI](http://localhost:5000/api/docs) for interactive API exploration
- Review [Best Practices](./REFINEMENTS.md) for production usage

