from pydantic import BaseModel, EmailStr
from app.models.association import UserRole

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class UserInCompany(User):
    role: UserRole
    
class UserRoleInCompany(BaseModel):
    company_id: int
    company_name: str
    role: UserRole

    class Config:
        from_attributes = True    