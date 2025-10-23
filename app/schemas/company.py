from pydantic import BaseModel
from typing import List
from .user import UserInCompany
from app.models.association import UserRole

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True

class CompanyWithUsers(Company):
    users: List[UserInCompany] = []

class CompanyAssignment(BaseModel):
    user_id: int
    company_id: int
    role: UserRole = UserRole.viewer