from sqlalchemy import Column, ForeignKey, String, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"

class UserCompany(Base):
    __tablename__ = "user_company"
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    company_id = Column(ForeignKey("companies.id"), primary_key=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.viewer)
    
    user = relationship("User", back_populates="companies_association")
    company = relationship("Company", back_populates="users_association")