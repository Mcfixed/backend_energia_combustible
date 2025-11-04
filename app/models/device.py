# app/models/device.py
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class DeviceStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    do_not_display = "do_not_display"

# --- NUEVO ENUM ---
class DeviceType(str, enum.Enum):
    energia = "energia"
    combustible = "combustible"
    # ... puedes añadir más tipos aquí si lo necesitas

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    dev_eui = Column(String, unique=True, index=True, nullable=False)
    status = Column(SAEnum(DeviceStatus), nullable=False, default=DeviceStatus.active)
    
    # --- CAMBIO ---
    # Ya no pertenece directamente a una compañía, sino a un centro.
    center_id = Column(Integer, ForeignKey("centers.id"))
    center = relationship("Center", back_populates="devices")
    
    # --- NUEVO CAMPO ---
    type = Column(SAEnum(DeviceType), nullable=False)