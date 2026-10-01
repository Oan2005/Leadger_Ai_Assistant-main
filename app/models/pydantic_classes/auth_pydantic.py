from typing import Literal
from pydantic import BaseModel, EmailStr, Field  # type: ignore[reportMissingImports]

Role = Literal["admin", "hr", "employee"]
class SignInRequest(BaseModel):
    email:EmailStr
    password :str

class SignInResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    access_token: str
    refresh_token: str

class SignUpRequest(BaseModel):
    company_name:str
    full_name:str
    email:EmailStr
    password:str
    namespace:str
    phone:str


class SignUpData(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    company_id: str
    role: str
    namespace: str


class SignUpResponse(BaseModel):
    success: bool
    data: SignUpData

class InvitationToken(BaseModel):
    token: str

class SignUpInvitationRequest(BaseModel):
    email:EmailStr
    role:Role
    phone:str

class SignUpInvitationData(BaseModel):
    email:EmailStr
    role:str

class SignUpInvitationResponse(BaseModel):
    success: bool
    data: SignUpInvitationData


class InvitedSignupRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class InvitedSignupResponse(BaseModel):
    full_name: str
    email: EmailStr
    message: str