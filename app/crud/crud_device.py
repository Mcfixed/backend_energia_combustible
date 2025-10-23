from sqlalchemy.orm import Session
from app.models import device
from app.schemas import device as device_schema

def get_device(db: Session, device_id: int) -> device.Device | None:
    return db.query(device.Device).filter(device.Device.id == device_id).first()

def get_device_by_eui(db: Session, dev_eui: str) -> device.Device | None:
    return db.query(device.Device).filter(device.Device.dev_eui == dev_eui).first()

def get_devices_by_company(db: Session, company_id: int, skip: int = 0, limit: int = 100) -> list[device.Device]:
    return db.query(device.Device).filter(device.Device.company_id == company_id).offset(skip).limit(limit).all()

def create_device(db: Session, device_data: device_schema.DeviceCreate) -> device.Device:
    db_device = device.Device(**device_data.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device