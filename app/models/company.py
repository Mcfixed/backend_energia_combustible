# app/models/company.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)

    # Relación M2M con User (esto no cambia)
    users_association = relationship("UserCompany", back_populates="company")
    
    # --- CAMBIO ---
    # Relación 1-M con Center (Una compañía tiene MUCHOS centros)
    centers = relationship("Center", back_populates="company")