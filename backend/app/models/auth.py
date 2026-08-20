from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthResponse(BaseModel):
    authenticated: bool
    user: AuthenticatedUser