# app/models/company.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)

    users_association = relationship("UserCompany", back_populates="company")

    centers = relationship("Center", back_populates="company")