import os

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    status,
)

from dotenv import load_dotenv

from app.models.auth import (
    AuthResponse,
    AuthenticatedUser,
    GoogleAuthRequest,
)

from app.services.auth_service import (
    GoogleAuthenticationError,
    SessionAuthenticationError,
    create_session_token,
    verify_google_credential,
    verify_session_token,
)


load_dotenv()


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


SESSION_COOKIE_NAME = (
    "oceaneye_session"
)


AUTH_COOKIE_SECURE = (
    os.getenv(
        "AUTH_COOKIE_SECURE",
        "false",
    )
    .strip()
    .lower()
    ==
    "true"
)


AUTH_SESSION_HOURS = int(
    os.getenv(
        "AUTH_SESSION_HOURS",
        "24",
    )
)


# ======================================================================================
# GOOGLE LOGIN
# ======================================================================================

@router.post(
    "/google",
    response_model=AuthResponse,
)
async def google_login(
    payload: GoogleAuthRequest,
    response: Response,
):
    """
    Verify a Google Identity Services credential and
    create an OceanEye application session.
    """

    try:
        user = verify_google_credential(
            payload.credential
        )

    except GoogleAuthenticationError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=str(
                error
            ),
        ) from error


    session_token = (
        create_session_token(
            user
        )
    )


    response.set_cookie(
        key=SESSION_COOKIE_NAME,

        value=session_token,

        httponly=True,

        secure=AUTH_COOKIE_SECURE,

        samesite="lax",

        max_age=(
            AUTH_SESSION_HOURS
            * 60
            * 60
        ),

        path="/",
    )


    return {
        "authenticated":
            True,

        "user":
            user,
    }


# ======================================================================================
# CURRENT USER
# ======================================================================================

@router.get(
    "/me",
    response_model=AuthenticatedUser,
)
async def get_current_user(
    request: Request,
):
    """
    Return the currently authenticated OceanEye user.
    """

    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )


    if not token:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Authentication required."
            ),
        )


    try:
        return verify_session_token(
            token
        )

    except SessionAuthenticationError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=str(
                error
            ),
        ) from error


# ======================================================================================
# LOGOUT
# ======================================================================================

@router.post(
    "/logout",
)
async def logout(
    response: Response,
):

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,

        path="/",

        httponly=True,

        secure=AUTH_COOKIE_SECURE,

        samesite="lax",
    )


    return {
        "authenticated":
            False
    }