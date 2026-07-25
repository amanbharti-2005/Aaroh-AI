from typing import Optional

from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str


class ProfileUpdateRequest(BaseModel):
    """
    Body for PUT /auth/me — what the frontend's Profile page sends.
    Every field is optional so a partial update only touches what it names.
    `skills` and `goals` are JSON strings, matching how the User model
    stores them and how ProfilePage.tsx serializes them.
    """
    name: Optional[str] = None
    role: Optional[str] = None
    background: Optional[str] = None
    skills: Optional[str] = None
    goals: Optional[str] = None