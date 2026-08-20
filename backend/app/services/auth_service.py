import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt

from dotenv import load_dotenv

from google.auth.transport import (
    requests as google_requests,
)

from google.oauth2 import id_token


load_dotenv()


GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID"
)

AUTH_JWT_SECRET = os.getenv(
    "AUTH_JWT_SECRET"
)

AUTH_SESSION_HOURS = int(
    os.getenv(
        "AUTH_SESSION_HOURS",
        "24",
    )
)


if not GOOGLE_CLIENT_ID:
    raise RuntimeError(
        "GOOGLE_CLIENT_ID is missing from .env"
    )


if not AUTH_JWT_SECRET:
    raise RuntimeError(
        "AUTH_JWT_SECRET is missing from .env"
    )


class GoogleAuthenticationError(
    Exception
):
    pass


class SessionAuthenticationError(
    Exception
):
    pass


# ======================================================================================
# GOOGLE TOKEN
# ======================================================================================

def verify_google_credential(
    credential: str,
) -> dict:
    """
    Verify the Google Identity Services ID token.

    The expected audience must match OceanEye's
    configured Google Client ID.
    """

    try:
        payload = (
            id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                GOOGLE_CLIENT_ID,
            )
        )

    except Exception as error:
        raise GoogleAuthenticationError(
            "Google credential verification failed."
        ) from error


    google_user_id = payload.get(
        "sub"
    )

    email = payload.get(
        "email"
    )

    email_verified = payload.get(
        "email_verified",
        False,
    )


    if not google_user_id:
        raise GoogleAuthenticationError(
            "Google account identifier is missing."
        )


    if not email:
        raise GoogleAuthenticationError(
            "Google account email is missing."
        )


    if not email_verified:
        raise GoogleAuthenticationError(
            "Google account email is not verified."
        )


    return {
        "id":
            google_user_id,

        "email":
            email,

        "name":
            payload.get(
                "name"
            ),

        "picture":
            payload.get(
                "picture"
            ),
    }


# ======================================================================================
# OCEANEYE SESSION TOKEN
# ======================================================================================

def create_session_token(
    user: dict,
) -> str:

    now = datetime.now(
        timezone.utc
    )

    expires_at = (
        now
        + timedelta(
            hours=AUTH_SESSION_HOURS
        )
    )


    payload = {
        "sub":
            user["id"],

        "email":
            user["email"],

        "name":
            user.get(
                "name"
            ),

        "picture":
            user.get(
                "picture"
            ),

        "iat":
            now,

        "exp":
            expires_at,

        "type":
            "oceaneye_session",
    }


    return jwt.encode(
        payload,
        AUTH_JWT_SECRET,
        algorithm="HS256",
    )


# ======================================================================================
# VERIFY OCEANEYE SESSION
# ======================================================================================

def verify_session_token(
    token: str,
) -> dict:

    try:
        payload = jwt.decode(
            token,
            AUTH_JWT_SECRET,
            algorithms=[
                "HS256",
            ],
        )

    except jwt.ExpiredSignatureError as error:
        raise SessionAuthenticationError(
            "OceanEye session has expired."
        ) from error

    except jwt.InvalidTokenError as error:
        raise SessionAuthenticationError(
            "Invalid OceanEye session."
        ) from error


    if (
        payload.get(
            "type"
        )
        !=
        "oceaneye_session"
    ):
        raise SessionAuthenticationError(
            "Invalid OceanEye session type."
        )


    return {
        "id":
            payload["sub"],

        "email":
            payload["email"],

        "name":
            payload.get(
                "name"
            ),

        "picture":
            payload.get(
                "picture"
            ),
    }