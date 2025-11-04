# app/models/tank.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Tank(Base):
    __tablename__ = "tanks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)           # Ej: "Tanque A"
    capacity = Column(Float, nullable=False)    # Ej: 10000 (litros)
    fuel_type = Column(String, nullable=False)     # Ej: "Diesel"
    
    # A qué centro pertenece
    center_id = Column(Integer, ForeignKey("centers.id"))
    center = relationship("Center", back_populates="tanks")
    
    # Qué dispositivo físico le da los datos
    device_id = Column(Integer, ForeignKey("devices.id"))
    device = relationship("Device", back_populates="tanks")
    
    # Qué clave de datos usar del 'object' de Mongo (Ej: "S0", "S1", "S2")
    data_key = Column(String, nullable=False)