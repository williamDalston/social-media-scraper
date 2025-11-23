# Agent 7: API_DOCS_SPECIALIST (Gray)
## Production Enhancement: API Documentation & Validation

### 🎯 Mission
Create comprehensive API documentation with Swagger/OpenAPI, implement request/response validation, standardize error handling, and add API versioning.

---

## 📋 Detailed Tasks

### 1. API Documentation

#### 1.1 Flask-RESTX Integration
- **Package:** `flask-restx` or `flask-restful` with `flasgger`
- **File:** `app.py` (modify)
- Set up:
  - Swagger UI at `/api/docs`
  - OpenAPI specification at `/api/swagger.json`
  - API namespace organization

#### 1.2 Endpoint Documentation
- Document all endpoints:
  - Description
  - Parameters (query, path, body)
  - Request examples
  - Response examples
  - Error responses
  - Authentication requirements

#### 1.3 API Organization
- Organize into namespaces:
  - `auth` - Authentication endpoints
  - `accounts` - Account management
  - `metrics` - Metrics and data
  - `jobs` - Background jobs
  - `admin` - Admin operations

---

### 2. Request/Response Validation

#### 2.1 Marshmallow Schemas
- **Package:** `marshmallow`
- **File:** `api/schemas.py`
- Create schemas for:
  - Account creation/update
  - CSV upload
  - Scraper execution request
  - Job status response
  - Metrics response
  - Error response

#### 2.2 Validation Middleware
- **File:** `api/validators.py`
- Validate:
  - Request body format
  - Query parameters
  - Path parameters
  - File uploads
  - Return clear error messages

#### 2.3 Response Serialization
- Serialize responses using schemas
- Format dates consistently
- Handle null values
- Include metadata (pagination, etc.)

---

### 3. API Versioning

#### 3.1 Version Structure
- **File:** `api/v1/__init__.py`
- Organize:
  - `api/v1/` - Version 1 endpoints
  - `api/v2/` - Future version (optional)
- URL prefix: `/api/v1/...`

#### 3.2 Version Management
- Support multiple versions simultaneously
- Deprecation warnings for old versions
- Version in response headers
- Migration guide for version changes

---

### 4. Error Handling

#### 4.1 Custom Exceptions
- **File:** `api/errors.py`
- Exceptions:
  - `APIError` (base)
  - `ValidationError`
  - `NotFoundError`
  - `UnauthorizedError`
  - `ForbiddenError`
  - `RateLimitError`

#### 4.2 Error Response Format
- Standardized format:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input",
      "details": {...}
    }
  }
  ```

#### 4.3 Error Handlers
- Global error handlers:
  - 400 Bad Request
  - 401 Unauthorized
  - 403 Forbidden
  - 404 Not Found
  - 422 Validation Error
  - 429 Too Many Requests
  - 500 Internal Server Error

---

### 5. API Testing Documentation

#### 5.1 API Usage Examples
- **File:** `docs/API_USAGE.md`
- Include:
  - Authentication flow
  - Common use cases
  - Code examples (Python, curl, JavaScript)
  - Error handling examples

#### 5.2 Postman Collection (Optional)
- **File:** `docs/postman_collection.json`
- Create Postman collection with:
  - All endpoints
  - Example requests
  - Environment variables
  - Tests

---

## 📁 File Structure to Create

```
api/
├── __init__.py
├── schemas.py              # Marshmallow schemas
├── validators.py           # Validation utilities
├── errors.py               # Custom exceptions
└── v1/
    ├── __init__.py
    ├── auth.py             # Auth endpoints
    ├── accounts.py          # Account endpoints
    ├── metrics.py           # Metrics endpoints
    ├── jobs.py              # Job endpoints
    └── admin.py             # Admin endpoints

docs/
├── API_USAGE.md
└── postman_collection.json  # Optional
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
flask-restx>=1.1.0
marshmallow>=3.20.0
apispec>=6.3.0              # Optional: Additional OpenAPI support
```

---

## ✅ Acceptance Criteria

- [ ] Swagger UI is accessible and functional
- [ ] All endpoints are documented
- [ ] Request validation works
- [ ] Response validation works
- [ ] Error handling is standardized
- [ ] API versioning is implemented
- [ ] Error messages are clear and helpful
- [ ] API documentation is complete

---

## 🧪 Testing Requirements

- Test API documentation accessibility
- Test request validation
- Test error responses
- Test API versioning
- Test Swagger UI functionality

---

## 📝 Implementation Details

### Flask-RESTX Setup:
```python
from flask_restx import Api, Resource, fields

api = Api(
    app,
    version='1.0',
    title='HHS Social Media API',
    description='API for HHS Social Media Scraper',
    doc='/api/docs'
)

ns = api.namespace('accounts', description='Account operations')
```

### Marshmallow Schema Example:
```python
from marshmallow import Schema, fields, validate

class AccountSchema(Schema):
    platform = fields.Str(required=True, validate=validate.OneOf(['X', 'Instagram', 'Facebook']))
    handle = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    org_name = fields.Str(required=True)
```

### Error Handler Example:
```python
@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return {
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid input',
            'details': error.messages
        }
    }, 422
```

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-7-api-docs`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up Flask-RESTX
4. Create API namespaces
5. Create Marshmallow schemas
6. Add validation to endpoints
7. Implement error handling
8. Add API versioning
9. Document all endpoints
10. Create usage documentation

---

## 📚 API Documentation Structure

### Swagger UI Sections:
1. **Authentication** - Login, token management
2. **Accounts** - Account CRUD operations
3. **Metrics** - Data retrieval endpoints
4. **Jobs** - Background job management
5. **Admin** - Administrative operations

### Each Endpoint Should Include:
- Summary
- Description
- Parameters (with types, required, examples)
- Request body (if applicable)
- Response examples (success and error)
- Authentication requirements
- Rate limits

---

## 🔍 Example API Documentation

### Endpoint: GET /api/v1/accounts
```yaml
get:
  summary: Get all accounts
  description: Retrieve a list of all social media accounts
  parameters:
    - name: platform
      in: query
      schema:
        type: string
        enum: [X, Instagram, Facebook]
    - name: page
      in: query
      schema:
        type: integer
        default: 1
  responses:
    200:
      description: List of accounts
      content:
        application/json:
          schema: AccountListSchema
    401:
      description: Unauthorized
```

---

## ⚠️ Important Considerations

- **Backward Compatibility:** Maintain compatibility when adding features
- **Documentation Updates:** Keep docs in sync with code
- **Error Messages:** Make error messages user-friendly
- **Validation:** Validate early, fail fast
- **Examples:** Provide clear examples for all endpoints
- **Versioning:** Plan for future API versions

---

## 📝 Best Practices

- Use consistent naming conventions
- Follow RESTful principles
- Include pagination for list endpoints
- Use appropriate HTTP status codes
- Provide detailed error messages
- Document rate limits
- Include authentication in all protected endpoints

---

**Agent Gray - Ready to document! 📚**

