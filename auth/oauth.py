"""
OAuth2/OpenID Connect authentication support.
Supports Google, Microsoft, and GitHub OAuth providers.
"""
from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User, UserRole
from authlib.integrations.flask_client import OAuth
from authlib.jose import jwt
from datetime import datetime
import os
import secrets

oauth_bp = Blueprint("oauth", __name__, url_prefix="/api/auth/oauth")

# Initialize OAuth
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth providers."""
    oauth.init_app(app)

    # Google OAuth
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # Microsoft OAuth
    oauth.register(
        name="microsoft",
        client_id=os.getenv("MICROSOFT_CLIENT_ID"),
        client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # GitHub OAuth
    oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        authorize_url="https://github.com/login/oauth/authorize",
        authorize_params=None,
        access_token_url="https://github.com/login/oauth/access_token",
        access_token_params=None,
        refresh_token_url=None,
        client_kwargs={"scope": "user:email"},
    )


def get_or_create_oauth_user(provider, user_info, email, name):
    """Get existing user or create new user from OAuth info."""
    from auth.jwt_utils import get_db_session

    db_session = get_db_session()

    # Try to find user by email
    user = db_session.query(User).filter_by(email=email).first()

    if user:
        # Update OAuth provider info if not set
        if not user.oauth_provider:
            user.oauth_provider = provider
            user.oauth_id = user_info.get("sub") or user_info.get("id")
            db_session.commit()
    else:
        # Create new user from OAuth
        username = email.split("@")[0]  # Use email prefix as username
        # Ensure username is unique
        base_username = username
        counter = 1
        while db_session.query(User).filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Check if this is the first user (make them admin)
        user_count = db_session.query(User).count()
        role = UserRole.ADMIN.value if user_count == 0 else UserRole.VIEWER.value

        user = User(
            username=username,
            email=email,
            role=role,
            is_active=True,
            oauth_provider=provider,
            oauth_id=user_info.get("sub") or user_info.get("id"),
            display_name=name,
        )
        # OAuth users don't need password
        user.password_hash = None

        db_session.add(user)
        db_session.commit()

    user_id = user.id
    db_session.close()

    return user_id, user.role


@oauth_bp.route("/<provider>/authorize")
def authorize(provider):
    """Initiate OAuth flow with the specified provider."""
    if provider not in ["google", "microsoft", "github"]:
        return jsonify({"error": "Invalid OAuth provider"}), 400

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_provider"] = provider

    redirect_uri = url_for("oauth.callback", provider=provider, _external=True)

    try:
        if provider == "github":
            # GitHub uses different flow
            return oauth.github.authorize_redirect(redirect_uri, state=state)
        elif provider == "google":
            return oauth.google.authorize_redirect(redirect_uri, state=state)
        elif provider == "microsoft":
            return oauth.microsoft.authorize_redirect(redirect_uri, state=state)
        else:
            return jsonify({"error": "Unsupported OAuth provider"}), 400
    except Exception as e:
        current_app.logger.error(f"OAuth authorization error: {str(e)}")
        return jsonify({"error": "OAuth authorization failed"}), 500


@oauth_bp.route("/<provider>/callback")
def callback(provider):
    """Handle OAuth callback from provider."""
    if provider not in ["google", "microsoft", "github"]:
        return jsonify({"error": "Invalid OAuth provider"}), 400

    # Verify state token
    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return jsonify({"error": "Invalid state parameter"}), 400

    try:
        # Get token from provider
        if provider == "github":
            token = oauth.github.authorize_access_token()
            # GitHub doesn't use OpenID Connect, so we need to fetch user info separately
            resp = oauth.github.get("https://api.github.com/user", token=token)
            user_info = resp.json()

            # Get email from GitHub (may need separate API call)
            email_resp = oauth.github.get(
                "https://api.github.com/user/emails", token=token
            )
            emails = email_resp.json()
            email = next(
                (e["email"] for e in emails if e.get("primary")),
                emails[0]["email"] if emails else None,
            )

            if not email:
                return jsonify({"error": "Could not retrieve email from GitHub"}), 400

            user_data = {
                "id": user_info.get("id"),
                "email": email,
                "name": user_info.get("name") or user_info.get("login"),
                "avatar_url": user_info.get("avatar_url"),
            }
        else:
            # Google and Microsoft use OpenID Connect
            if provider == "google":
                token = oauth.google.authorize_access_token()
            elif provider == "microsoft":
                token = oauth.microsoft.authorize_access_token()
            else:
                return jsonify({"error": "Unsupported OAuth provider"}), 400

            user_info = token.get("userinfo")

            if not user_info:
                # Parse JWT token if userinfo not provided
                id_token = token.get("id_token")
                if id_token:
                    user_info = jwt.decode(id_token, None, verify=False)

            user_data = {
                "sub": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name")
                or user_info.get("given_name", "")
                + " "
                + user_info.get("family_name", ""),
                "picture": user_info.get("picture"),
            }

        # Get or create user
        user_id, role = get_or_create_oauth_user(
            provider, user_data, user_data["email"], user_data.get("name", "")
        )

        # Generate JWT tokens
        from auth.jwt_utils import generate_token

        access_token = generate_token(user_id, role, "access")
        refresh_token = generate_token(user_id, role, "refresh")

        # Clear session
        session.pop("oauth_state", None)
        session.pop("oauth_provider", None)

        # In production, redirect to frontend with tokens
        # For now, return JSON (frontend should handle redirect)
        return (
            jsonify(
                {
                    "message": "OAuth authentication successful",
                    "user": {
                        "id": user_id,
                        "email": user_data["email"],
                        "name": user_data.get("name", ""),
                        "role": role,
                    },
                    "access_token": access_token["token"],
                    "refresh_token": refresh_token["token"],
                    "expires_in": access_token["expires_in"],
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"OAuth callback error: {str(e)}")
        return jsonify({"error": f"OAuth authentication failed: {str(e)}"}), 500


@oauth_bp.route("/providers", methods=["GET"])
def list_providers():
    """List available OAuth providers."""
    providers = []

    if os.getenv("GOOGLE_CLIENT_ID"):
        providers.append(
            {
                "name": "google",
                "display_name": "Google",
                "authorize_url": url_for(
                    "oauth.authorize", provider="google", _external=True
                ),
            }
        )

    if os.getenv("MICROSOFT_CLIENT_ID"):
        providers.append(
            {
                "name": "microsoft",
                "display_name": "Microsoft",
                "authorize_url": url_for(
                    "oauth.authorize", provider="microsoft", _external=True
                ),
            }
        )

    if os.getenv("GITHUB_CLIENT_ID"):
        providers.append(
            {
                "name": "github",
                "display_name": "GitHub",
                "authorize_url": url_for(
                    "oauth.authorize", provider="github", _external=True
                ),
            }
        )

    return jsonify({"providers": providers}), 200
