"""
Custom exception classes for API error handling.
"""


class APIError(Exception):
    """Base exception for all API errors."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An internal error occurred"

    def __init__(self, message=None, details=None, code=None):
        """
        Initialize API error.

        Args:
            message: Error message
            details: Additional error details
            code: Error code
        """
        self.message = message or self.message
        self.details = details
        if code:
            self.code = code
        super().__init__(self.message)

    def to_dict(self):
        """Convert error to dictionary for JSON response."""
        error_dict = {"code": self.code, "message": self.message}
        if self.details:
            error_dict["details"] = self.details
        return {"error": error_dict}


class ValidationError(APIError):
    """Raised when request validation fails."""

    status_code = 422
    code = "VALIDATION_ERROR"
    message = "Validation error"

    def __init__(self, message=None, details=None):
        """Initialize validation error with messages."""
        if details and isinstance(details, dict):
            # If details is a dict (like from Marshmallow), format it nicely
            formatted_details = {}
            for key, value in details.items():
                if isinstance(value, list):
                    formatted_details[key] = value[0] if len(value) == 1 else value
                else:
                    formatted_details[key] = value
            details = formatted_details
        super().__init__(message=message, details=details)


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found"

    def __init__(self, resource_type="Resource", resource_id=None):
        """Initialize not found error."""
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message=message)


class UnauthorizedError(APIError):
    """Raised when authentication is required or failed."""

    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication required"

    def __init__(self, message=None):
        """Initialize unauthorized error."""
        super().__init__(message=message or self.message)


class ForbiddenError(APIError):
    """Raised when user lacks required permissions."""

    status_code = 403
    code = "FORBIDDEN"
    message = "Insufficient permissions"

    def __init__(self, message=None, required_permission=None):
        """Initialize forbidden error."""
        if required_permission:
            message = f"Insufficient permissions. Required: {required_permission}"
        super().__init__(message=message or self.message)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded"

    def __init__(self, message=None, retry_after=None):
        """Initialize rate limit error."""
        super().__init__(message=message or self.message)
        self.retry_after = retry_after


class BadRequestError(APIError):
    """Raised when request is malformed."""

    status_code = 400
    code = "BAD_REQUEST"
    message = "Bad request"

    def __init__(self, message=None, details=None):
        """Initialize bad request error."""
        super().__init__(message=message, details=details)


class InternalServerError(APIError):
    """Raised when an internal server error occurs."""

    status_code = 500
    code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred"

    def __init__(self, message=None, details=None):
        """Initialize internal server error."""
        super().__init__(message=message, details=details)
