"""
Authentication API namespace.

Endpoints for user authentication and authorization.
"""

from flask_restx import Namespace, Resource, fields
from flask import request, jsonify
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User, UserRole
from auth.jwt_utils import (
    generate_token,
    verify_token,
    get_current_user,
    get_db_session,
)
from auth.decorators import require_auth
from auth.validators import validate_email, validate_password, validate_username
from datetime import datetime
import os
from api.errors import BadRequestError, ValidationError, UnauthorizedError

ns = Namespace("auth", description="Authentication and authorization operations")

# Flask-RESTX models for documentation
login_request_model = ns.model(
    "LoginRequest",
    {
        "username": fields.String(required=True, description="Username or email"),
        "password": fields.String(required=True, description="Password"),
    },
)

register_request_model = ns.model(
    "RegisterRequest",
    {
        "username": fields.String(required=True, description="Username"),
        "email": fields.String(required=True, description="Email address"),
        "password": fields.String(required=True, description="Password"),
        "role": fields.String(
            description="User role (Admin, Editor, Viewer)", default="Viewer"
        ),
    },
)

refresh_request_model = ns.model(
    "RefreshRequest",
    {"refresh_token": fields.String(required=True, description="Refresh token")},
)

user_model = ns.model(
    "User",
    {
        "id": fields.Integer(description="User ID"),
        "username": fields.String(description="Username"),
        "email": fields.String(description="Email address"),
        "role": fields.String(description="User role"),
        "created_at": fields.DateTime(description="Account creation date"),
        "last_login": fields.DateTime(description="Last login date"),
    },
)

login_response_model = ns.model(
    "LoginResponse",
    {
        "message": fields.String(description="Response message"),
        "user": fields.Nested(user_model, description="User information"),
        "access_token": fields.String(description="JWT access token"),
        "refresh_token": fields.String(description="JWT refresh token"),
        "expires_in": fields.Integer(description="Token expiration time in seconds"),
    },
)

token_response_model = ns.model(
    "TokenResponse",
    {
        "access_token": fields.String(description="JWT access token"),
        "expires_in": fields.Integer(description="Token expiration time in seconds"),
    },
)

error_model = ns.model(
    "Error",
    {
        "error": fields.Nested(
            ns.model(
                "ErrorDetail",
                {
                    "code": fields.String(description="Error code"),
                    "message": fields.String(description="Error message"),
                    "details": fields.Raw(description="Additional error details"),
                },
            )
        )
    },
)


@ns.route("/register")
class Register(Resource):
    """Register a new user."""

    @ns.doc("register")
    @ns.expect(register_request_model)
    @ns.marshal_with(login_response_model, code=201)
    @ns.response(201, "User registered successfully")
    @ns.response(400, "Bad Request", error_model)
    @ns.response(409, "Conflict - User already exists", error_model)
    def post(self):
        """
        Register a new user.

        The first user will automatically be assigned the Admin role.
        Subsequent users default to Viewer role unless specified.
        """
        data = request.get_json()

        if not data:
            raise BadRequestError("No data provided")

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        role = data.get("role", UserRole.VIEWER.value)

        # Validate input
        username_valid, username_error = validate_username(username)
        if not username_valid:
            raise ValidationError(message=username_error)

        email_valid, email_error = validate_email(email)
        if not email_valid:
            raise ValidationError(message=email_error)

        password_valid, password_error = validate_password(password)
        if not password_valid:
            raise ValidationError(message=password_error)

        # Check if role is valid
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValidationError(
                message=f'Invalid role. Must be one of: {", ".join(valid_roles)}'
            )

        session = get_db_session()

        try:
            # Check if user already exists
            existing_user = (
                session.query(User)
                .filter((User.username == username) | (User.email == email))
                .first()
            )

            if existing_user:
                raise ValidationError(
                    message="Username or email already exists", code="USER_EXISTS"
                )

            # Check if this is the first user (make them admin)
            user_count = session.query(User).count()
            if user_count == 0:
                role = UserRole.ADMIN.value

            # Create new user
            user = User(username=username, email=email, role=role, is_active=True)
            user.set_password(password)

            session.add(user)
            session.commit()

            user_id = user.id

            # Generate tokens
            tokens = generate_token(user_id, role)

            return {
                "message": "User registered successfully",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                },
                "access_token": tokens["token"],
                "refresh_token": generate_token(user_id, role, "refresh")["token"],
                "expires_in": tokens["expires_in"],
            }, 201
        finally:
            session.close()


@ns.route("/login")
class Login(Resource):
    """Login and get JWT token."""

    @ns.doc("login")
    @ns.expect(login_request_model)
    @ns.marshal_with(login_response_model)
    @ns.response(200, "Login successful")
    @ns.response(400, "Bad Request", error_model)
    @ns.response(401, "Unauthorized - Invalid credentials", error_model)
    @ns.response(403, "Forbidden - Account disabled", error_model)
    def post(self):
        """
        Login with username/email and password.

        Returns JWT access token and refresh token.
        """
        data = request.get_json()

        if not data:
            raise BadRequestError("No data provided")

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            raise BadRequestError("Username and password are required")

        session = get_db_session()

        try:
            # Find user by username or email
            user = (
                session.query(User)
                .filter((User.username == username) | (User.email == username))
                .first()
            )

            if not user or not user.check_password(password):
                raise UnauthorizedError("Invalid username or password")

            if not user.is_active:
                raise UnauthorizedError("Account is disabled")

            # Update last login
            user.last_login = datetime.utcnow()
            session.commit()

            user_id = user.id
            role = user.role

            # Generate tokens
            access_token = generate_token(user_id, role, "access")
            refresh_token = generate_token(user_id, role, "refresh")

            return {
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                },
                "access_token": access_token["token"],
                "refresh_token": refresh_token["token"],
                "expires_in": access_token["expires_in"],
            }, 200
        finally:
            session.close()


@ns.route("/logout")
class Logout(Resource):
    """Logout endpoint."""

    @ns.doc("logout")
    @ns.response(200, "Logout successful")
    def post(self):
        """
        Logout endpoint.

        Note: With JWT, logout is typically handled client-side by removing the token.
        This endpoint can be used for server-side token blacklisting if needed.
        """
        return {"message": "Logout successful"}, 200


@ns.route("/me")
@ns.doc(security="Bearer Auth")
class CurrentUser(Resource):
    """Get current authenticated user information."""

    @ns.doc("get_current_user")
    @ns.marshal_with(user_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized", error_model)
    @ns.response(404, "User not found", error_model)
    @require_auth
    def get(self):
        """
        Get current authenticated user information.

        Requires valid JWT token in Authorization header.
        """
        user = get_current_user()
        if not user:
            raise UnauthorizedError("User not found")
        return user.to_dict(), 200


@ns.route("/refresh")
class RefreshToken(Resource):
    """Refresh access token."""

    @ns.doc("refresh_token")
    @ns.expect(refresh_request_model)
    @ns.marshal_with(token_response_model)
    @ns.response(200, "Token refreshed successfully")
    @ns.response(400, "Bad Request", error_model)
    @ns.response(401, "Unauthorized - Invalid token", error_model)
    def post(self):
        """
        Refresh access token using refresh token.

        Use this endpoint to get a new access token when the current one expires.
        """
        data = request.get_json()

        if not data:
            raise BadRequestError("No data provided")

        refresh_token_str = data.get("refresh_token", "")

        if not refresh_token_str:
            raise BadRequestError("Refresh token is required")

        try:
            payload = verify_token(refresh_token_str)

            if payload.get("type") != "refresh":
                raise UnauthorizedError("Invalid token type")

            user_id = payload.get("user_id")
            role = payload.get("role")

            session = get_db_session()
            try:
                user = session.query(User).filter_by(id=user_id, is_active=True).first()

                if not user:
                    raise UnauthorizedError("User not found or inactive")

                # Generate new access token
                access_token = generate_token(user_id, role, "access")

                return {
                    "access_token": access_token["token"],
                    "expires_in": access_token["expires_in"],
                }, 200
            finally:
                session.close()

        except ValueError as e:
            raise UnauthorizedError(str(e))
