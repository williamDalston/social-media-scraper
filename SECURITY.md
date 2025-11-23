# Security Documentation

This document outlines the security features implemented in the HHS Social Media Scraper application.

## Authentication & Authorization

### JWT-Based Authentication
- **Access Tokens**: Valid for 24 hours
- **Refresh Tokens**: Valid for 7 days
- **Algorithm**: HS256
- **Storage**: Tokens stored client-side (localStorage/sessionStorage recommended)

### User Roles
- **Admin**: Full access to all endpoints, can manage users
- **Editor**: Can upload files and run scrapers, view all data
- **Viewer**: Read-only access to data endpoints

### Authentication Endpoints
- `POST /api/auth/register` - Register new user (first user becomes admin)
- `POST /api/auth/login` - Login and receive JWT tokens
- `POST /api/auth/logout` - Logout (client-side token removal)
- `GET /api/auth/me` - Get current user information
- `POST /api/auth/refresh` - Refresh access token

### Account Security
- **Password Requirements**:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character
- **Account Lockout**: Accounts are locked for 30 minutes after 5 failed login attempts
- **Failed Login Tracking**: Tracks failed login attempts to prevent brute force attacks

## Rate Limiting

Rate limiting is implemented using Flask-Limiter to prevent abuse:

- **Login**: 5 requests per minute per IP
- **Register**: 3 requests per hour per IP
- **API Endpoints**: 100 requests per minute per user
- **File Upload**: 10 requests per hour per user
- **Run Scraper**: 5 requests per hour per user
- **Download**: 10 requests per hour per user

Rate limit errors return HTTP 429 with appropriate error messages.

## CSRF Protection

CSRF protection is enabled using Flask-WTF:
- All state-changing requests require CSRF tokens
- API endpoints using JWT authentication are exempt from CSRF (using `@csrf.exempt`)
- Forms should include CSRF tokens

## Security Headers

The following security headers are automatically added to all responses:

- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - Enables XSS protection
- `Content-Security-Policy` - Restricts resource loading
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

## CORS Configuration

CORS is configured to allow requests only from specified origins:
- Default: `http://localhost:5000, http://127.0.0.1:5000`
- Configurable via `CORS_ORIGINS` environment variable
- Supports credentials for authenticated requests

## Input Validation & Sanitization

### Email Validation
- Validates email format using `email-validator`
- Converts to lowercase for consistency

### Username Validation
- 3-30 characters
- Must start with a letter
- Only alphanumeric characters and underscores allowed

### Password Validation
- Minimum 8 characters
- Requires uppercase, lowercase, digit, and special character
- Validated on registration and password changes

### File Upload Security
- **File Type**: Only CSV files allowed
- **File Size**: Maximum 10MB
- **Content Validation**: 
  - Validates CSV structure
  - Validates platform names against whitelist
  - Sanitizes all input data
  - Removes dangerous characters

### Input Sanitization
- All user inputs are sanitized before processing
- Special characters (`<`, `>`, `"`, `'`) are removed
- String length limits enforced

## Protected Endpoints

All API endpoints require authentication unless otherwise specified:

### Public Endpoints
- `GET /` - Dashboard (public)
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Authenticated Endpoints (All Users)
- `GET /api/summary` - Get summary data
- `GET /api/history/<platform>/<handle>` - Get account history
- `GET /api/download` - Download CSV data
- `GET /api/grid` - Get grid data
- `GET /api/accounts` - List accounts
- `GET /api/performance` - Get performance metrics
- `GET /api/auth/me` - Get current user info

### Admin/Editor Only Endpoints
- `POST /upload` - Upload CSV file
- `POST /api/run-scraper` - Run scraper

## Error Handling

Security-related errors return appropriate HTTP status codes:

- **401 Unauthorized**: Authentication required or invalid token
- **403 Forbidden**: Insufficient permissions or account locked
- **429 Too Many Requests**: Rate limit exceeded

## Environment Variables

Required security-related environment variables:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production

# Flask Secret Key
SECRET_KEY=your-secret-key-change-in-production

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000

# Database Path
DATABASE_PATH=social_media.db
```

## Default Admin User

On first startup, if no users exist, a default admin user is created:

- **Username**: `admin`
- **Email**: `admin@example.com`
- **Password**: `Admin123!@#`

**⚠️ IMPORTANT**: Change the default password immediately after first login!

## Security Best Practices

1. **Never commit secrets**: Use environment variables for all secrets
2. **Use HTTPS in production**: All security features assume HTTPS
3. **Regular password updates**: Encourage users to change passwords regularly
4. **Monitor failed logins**: Track and alert on suspicious activity
5. **Keep dependencies updated**: Regularly update security packages
6. **Log security events**: All authentication events should be logged
7. **Token expiration**: Use short-lived access tokens with refresh tokens
8. **Input validation**: Always validate and sanitize user input

## Security Audit Checklist

- [x] JWT authentication implemented
- [x] Role-based access control
- [x] Rate limiting on all endpoints
- [x] CSRF protection
- [x] Security headers
- [x] CORS configuration
- [x] Input validation
- [x] File upload validation
- [x] Password strength requirements
- [x] Account lockout after failed attempts
- [x] SQL injection prevention (using ORM)
- [x] XSS protection
- [x] Error handling without information leakage

## Reporting Security Issues

If you discover a security vulnerability, please report it responsibly:
1. Do not create a public issue
2. Contact the security team directly
3. Provide detailed information about the vulnerability
4. Allow time for the issue to be addressed before disclosure

