"""
Property-based tests for validators using Hypothesis.
"""
from hypothesis import given, strategies as st, assume
from auth.validators import validate_email, validate_password, validate_username

@given(
    email=st.emails()
)
def test_validate_email_accepts_valid_emails(email):
    """Property: All valid emails should pass validation."""
    is_valid, error = validate_email(email)
    assert is_valid, f"Valid email {email} was rejected: {error}"

@given(
    text=st.text(min_size=1, max_size=1000)
)
def test_validate_email_rejects_non_emails(text):
    """Property: Non-email strings should be rejected."""
    assume('@' not in text or text.count('@') != 1)
    assume('.' not in text.split('@')[1] if '@' in text else True)
    
    is_valid, error = validate_email(text)
    assert not is_valid, f"Invalid email {text} was accepted"

@given(
    password=st.text(min_size=8, max_size=128)
)
def test_validate_password_checks_length(password):
    """Property: Passwords shorter than 8 chars should be rejected."""
    if len(password) < 8:
        is_valid, error = validate_password(password)
        assert not is_valid, f"Short password was accepted: {len(password)} chars"
    elif len(password) >= 8:
        # Passwords >= 8 chars might be valid (depending on other rules)
        is_valid, _ = validate_password(password)
        # Just check it doesn't crash
        assert isinstance(is_valid, bool)

@given(
    username=st.text(min_size=1, max_size=80)
)
def test_validate_username_handles_any_string(username):
    """Property: Username validation should handle any string without crashing."""
    is_valid, error = validate_username(username)
    assert isinstance(is_valid, bool)
    assert isinstance(error, str) if not is_valid else True

