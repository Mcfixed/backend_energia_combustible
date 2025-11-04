from pydantic import BaseModel
from typing import List, Optional 
from .user import UserInCompany
from .center import Center
from app.models.association import UserRole

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass
class CompanyUpdate(BaseModel):
    name: Optional[str] = None

class Company(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True

class CompanyWithUsers(Company):
    users: List[UserInCompany] = []
class CompanyWithCenters(Company):
    centers: List[Center] = []
class CompanyAssignment(BaseModel):
    user_id: int
    company_id: int
    role: UserRole = UserRole.viewer
    
    
class CompanyInList(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

