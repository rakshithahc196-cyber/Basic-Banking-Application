from pydantic import EmailStr, Field, field_validator

from app.schemas.base import APIModel


class RegisterRequest(APIModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value

    @field_validator("password")
    @classmethod
    def password_must_fit_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserResponse(APIModel):
    id: int
    name: str
    email: EmailStr


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"


class RegistrationResponse(APIModel):
    user: UserResponse
    account_number: str