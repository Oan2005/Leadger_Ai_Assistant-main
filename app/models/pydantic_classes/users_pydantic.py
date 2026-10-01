from typing import Literal
from .model_service import BaseModel,EmailStr,field_validator

Role = Literal["admin", "hr", "employee"]

class UpdateEmployeeByAdminRequest(BaseModel):
    full_name: str | None = None
    phone:str | None = None
    role: Role | None = None

class UpdateEmployeeByAdminResponse(BaseModel):
    full_name: str | None = None
    phone:str | None = None
    role:str | None = None

class SendInvitationToEmployee(BaseModel):
    email: EmailStr
    role: Role
    phone: str

class UpdateEmployeeByEmployeeRequest(BaseModel):
    full_name: str | None = None
    phone:str | None = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

    @field_validator('refresh_token')
    def validate_refresh_token(cls, v):
        if len(v) <12:
            raise ValueError('Refresh token is too short')
        return v




