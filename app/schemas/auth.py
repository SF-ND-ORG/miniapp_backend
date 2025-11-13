from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    code: str

class BindRequest(BaseModel):
    student_id: str
    name: str
    agree_privacy: bool = False

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"