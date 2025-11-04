# app/models/center.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Center(Base):
    __tablename__ = "centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    # Relación 1-M con Company (Un centro pertenece a UNA compañía)
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="centers")
    
    # Relación 1-M con Device (Un centro tiene MUCHOS dispositivos)
    devices = relationship("Device", back_populates="center")