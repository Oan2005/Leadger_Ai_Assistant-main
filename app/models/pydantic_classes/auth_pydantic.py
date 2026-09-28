from pydantic import BaseModel,EmailStr
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
    role:str
    phone:str

class SignUpInvitationData(BaseModel):
    email:EmailStr
    role:str

class SignUpInvitationResponse(BaseModel):
    success: bool
    data: SignUpInvitationData


class InvitedSignupRequest(BaseModel):
    token: str
    password: str
    full_name: str


class InvitedSignupResponse(BaseModel):
    full_name: str
    email: EmailStr
    message: str