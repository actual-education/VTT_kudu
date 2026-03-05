import hmac

from fastapi import APIRouter, HTTPException, Response, Request

from app.auth import create_auth_token, verify_auth_token
from app.config import settings
from app.schemas.auth import LoginRequest, AuthStatusResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthStatusResponse)
def login(req: LoginRequest, response: Response):
    if not settings.AUTH_PASSWORD:
        raise HTTPException(status_code=400, detail="AUTH_PASSWORD is not configured")
    if not hmac.compare_digest(req.password, settings.AUTH_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_auth_token()
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        max_age=settings.AUTH_SESSION_TTL_HOURS * 3600,
        path="/",
    )
    return AuthStatusResponse(authenticated=True)


@router.post("/logout", response_model=AuthStatusResponse)
def logout(response: Response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/")
    return AuthStatusResponse(authenticated=False)


@router.get("/me", response_model=AuthStatusResponse)
def me(request: Request):
    if not settings.AUTH_PASSWORD:
        return AuthStatusResponse(authenticated=True)
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    return AuthStatusResponse(authenticated=bool(token and verify_auth_token(token)))
