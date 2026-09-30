from typing import Annotated

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    name: Annotated[str, Field(default="", max_length=120)]


class LoginIn(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class RefreshIn(BaseModel):
    refresh_token: Annotated[str, Field(min_length=16, max_length=256)]


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: Annotated[str, Field(min_length=16, max_length=256)]
    password: Annotated[str, Field(min_length=8, max_length=128)]


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    model_config = {"from_attributes": True}
