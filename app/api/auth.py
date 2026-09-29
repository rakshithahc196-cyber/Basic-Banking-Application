from fastapi import APIRouter, status

from app.api.deps import CurrentSession, DatabaseSession
from app.schemas.auth import LoginRequest, RegisterRequest, RegistrationResponse, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user and create their bank account",
    responses={409: {"description": "An account with this email already exists"}},
)
def register(payload: RegisterRequest, db: DatabaseSession):
    user, account_number = auth_service.register(db, **payload.model_dump())
    return RegistrationResponse(
        user={"id": user.id, "name": user.name, "email": user.email},
        account_number=account_number,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT",
    responses={401: {"description": "Invalid email or password"}},
)
def login(payload: LoginRequest, db: DatabaseSession):
    token = auth_service.login(db, email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)


@router.post(
    "/logout",
    summary="Revoke the current access token",
    responses={401: {"description": "Missing, invalid, expired, or revoked bearer token"}},
)
def logout(session: CurrentSession, db: DatabaseSession):
    auth_service.logout(db, token_id=session.token_id, expires_at=session.expires_at)
    return {"message": "You have been logged out"}