# app/models/tank.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Tank(Base):
    __tablename__ = "tanks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)      
    capacity = Column(Float, nullable=False) 
    fuel_type = Column(String, nullable=False)
    
    center_id = Column(Integer, ForeignKey("centers.id"))
    center = relationship("Center", back_populates="tanks")
    
    device_id = Column(Integer, ForeignKey("devices.id"))
    device = relationship("Device", back_populates="tanks")

    data_key = Column(String, nullable=False)