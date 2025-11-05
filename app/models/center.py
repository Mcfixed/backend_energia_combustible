# app/models/center.py
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="centers")
    
    devices = relationship("Device", back_populates="center")
    price_kwh = Column(Float, nullable=True, server_default="250.0")