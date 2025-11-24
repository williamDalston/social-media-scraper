import re
import csv
import io
from email_validator import validate_email as validate_email_format, EmailNotValidError

# Platform whitelist
ALLOWED_PLATFORMS = [
    "x",
    "twitter",
    "instagram",
    "facebook",
    "linkedin",
    "youtube",
    "truth_social",
    "tiktok",
]


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format.

    Returns:
        (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email is required and must be a string"

    email = email.strip().lower()

    try:
        validate_email_format(email, check_deliverability=False)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required and must be a string"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"

    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format.
    Requirements:
    - 3-30 characters
    - Alphanumeric and underscores only
    - Must start with a letter

    Returns:
        (is_valid, error_message)
    """
    if not username or not isinstance(username, str):
        return False, "Username is required and must be a string"

    username = username.strip()

    if len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters"

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", username):
        return (
            False,
            "Username must start with a letter and contain only letters, numbers, and underscores",
        )

    return True, ""


def validate_csv_file(
    file_content: bytes, max_size_mb: int = 10
) -> tuple[bool, str, list]:
    """
    Validate CSV file content.

    Args:
        file_content: File content as bytes
        max_size_mb: Maximum file size in MB

    Returns:
        (is_valid, error_message, parsed_rows)
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    if len(file_content) > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB", []

    if len(file_content) == 0:
        return False, "File is empty", []

    try:
        # Decode and parse CSV
        stream = io.StringIO(file_content.decode("utf-8"), newline=None)
        csv_reader = csv.DictReader(stream)

        rows = []
        required_columns = ["Platform", "Handle"]

        for i, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            # Check for required columns
            if not all(col in row for col in required_columns):
                return (
                    False,
                    f"Row {i}: Missing required columns. Required: {', '.join(required_columns)}",
                    [],
                )

            platform = row.get("Platform", "").strip().lower()
            handle = row.get("Handle", "").strip()

            # Validate platform
            if platform not in ALLOWED_PLATFORMS:
                return (
                    False,
                    f"Row {i}: Invalid platform '{platform}'. Allowed: {', '.join(ALLOWED_PLATFORMS)}",
                    [],
                )

            # Validate handle (basic check - not empty)
            if not handle:
                return False, f"Row {i}: Handle cannot be empty", []

            # Sanitize handle (remove dangerous characters)
            handle = re.sub(r'[<>"\']', "", handle)

            rows.append(
                {
                    "Platform": platform,
                    "Handle": handle,
                    "Organization": row.get("Organization", "").strip(),
                }
            )

        if len(rows) == 0:
            return False, "CSV file contains no data rows", []

        return True, "", rows

    except UnicodeDecodeError:
        return False, "File must be valid UTF-8 encoded text", []
    except csv.Error as e:
        return False, f"Invalid CSV format: {str(e)}", []
    except Exception as e:
        return False, f"Error processing file: {str(e)}", []


def sanitize_string(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize string input by removing dangerous characters and limiting length.

    Args:
        input_str: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return ""

    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', "", input_str)
    # Limit length
    sanitized = sanitized[:max_length].strip()

    return sanitized
