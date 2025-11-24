"""
Validation utilities for API requests.
"""

from marshmallow import ValidationError as MarshmallowValidationError
from flask import request
from .errors import ValidationError, BadRequestError


def validate_request_body(schema_class):
    """
    Decorator to validate request body using a Marshmallow schema.

    Args:
        schema_class: Marshmallow Schema class

    Returns:
        Decorated function with validated data in request.validated_data
    """

    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise BadRequestError("Request must be JSON")

            schema = schema_class()
            try:
                data = schema.load(request.get_json() or {})
            except MarshmallowValidationError as err:
                raise ValidationError(details=err.messages)

            # Attach validated data to request
            request.validated_data = data
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_query_params(schema_class):
    """
    Decorator to validate query parameters using a Marshmallow schema.

    Args:
        schema_class: Marshmallow Schema class

    Returns:
        Decorated function with validated params in request.validated_params
    """

    def decorator(f):
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            try:
                params = schema.load(request.args.to_dict())
            except MarshmallowValidationError as err:
                raise ValidationError(details=err.messages)

            # Attach validated params to request
            request.validated_params = params
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_file_upload(allowed_extensions=None, max_size=None):
    """
    Decorator to validate file uploads.

    Args:
        allowed_extensions: List of allowed file extensions (e.g., ['csv', 'txt'])
        max_size: Maximum file size in bytes

    Returns:
        Decorated function with file in request.validated_file
    """
    if allowed_extensions is None:
        allowed_extensions = ["csv"]

    def decorator(f):
        def decorated_function(*args, **kwargs):
            if "file" not in request.files:
                raise BadRequestError("No file provided")

            file = request.files["file"]

            if file.filename == "":
                raise BadRequestError("No file selected")

            # Check file extension
            if allowed_extensions:
                file_ext = (
                    file.filename.rsplit(".", 1)[1].lower()
                    if "." in file.filename
                    else ""
                )
                if file_ext not in allowed_extensions:
                    raise BadRequestError(
                        f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                    )

            # Check file size
            if max_size:
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning

                if file_size > max_size:
                    raise BadRequestError(
                        f"File too large. Maximum size: {max_size / 1024 / 1024:.1f}MB"
                    )

            # Attach validated file to request
            request.validated_file = file
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def serialize_response(data, schema_class, many=False):
    """
    Serialize response data using a Marshmallow schema.

    Args:
        data: Data to serialize
        schema_class: Marshmallow Schema class
        many: Whether data is a list

    Returns:
        Serialized data
    """
    schema = schema_class()
    return schema.dump(data, many=many)
