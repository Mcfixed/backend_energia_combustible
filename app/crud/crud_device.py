from sqlalchemy.orm import Session
from app.models import device, center, company
from app.schemas import device as device_schema
from typing import List, Any # <-- Importar Any

def get_device(db: Session, device_id: int) -> device.Device | None:
    return db.query(device.Device).filter(device.Device.id == device_id).first()

def get_device_by_eui(db: Session, dev_eui: str) -> device.Device | None:
    return db.query(device.Device).filter(device.Device.dev_eui == dev_eui).first()

# --- NUEVA FUNCIÓN ---
def get_devices(db: Session, skip: int = 0, limit: int = 100) -> List[device.Device]:
    """
    Obtiene todos los dispositivos de la base de datos.
    """
    return db.query(device.Device).offset(skip).limit(limit).all()

def get_devices_by_company(db: Session, company_id: int, skip: int = 0, limit: int = 100) -> list[device.Device]:
    """
    Obtiene todos los dispositivos de una compañía, 
    uniendo a través de la tabla de centros.
    """
    return db.query(device.Device)\
             .join(center.Center)\
             .filter(center.Center.company_id == company_id)\
             .offset(skip).limit(limit).all()

def get_devices_by_center(db: Session, center_id: int, skip: int = 0, limit: int = 100) -> list[device.Device]:
    """
    Obtiene todos los dispositivos de un centro específico.
    """
    return db.query(device.Device)\
             .filter(device.Device.center_id == center_id)\
             .offset(skip).limit(limit).all() 

def create_device(db: Session, device_data: device_schema.DeviceCreate) -> device.Device:
    db_device = device.Device(**device_data.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

# --- NUEVA FUNCIÓN ---
def update_device(
    db: Session,
    db_device: device.Device,
    device_in: device_schema.DeviceUpdate
) -> device.Device:
    """Actualiza un dispositivo (solo campos enviados)."""
    update_data = device_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_device, field, value)
    
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, device_id: int) -> device.Device | None:
    """Elimina un dispositivo por su ID."""
    db_device = db.query(device.Device).filter(device.Device.id == device_id).first()
    if db_device:
        db.delete(db_device)
        db.commit()
    return db_device


#estadisticas1
def get_devices_with_details(db: Session, skip: int = 0, limit: int = 100) -> List[dict[str, Any]]:
    """
    Obtiene todos los dispositivos con los nombres de su centro y compañía.
   
    """
    results = (
        db.query(
            device.Device.id,
            device.Device.name,
            device.Device.dev_eui,
            device.Device.type,
            device.Device.status,
            center.Center.id.label("center_id"),
            center.Center.name.label("center_name"),
            company.Company.id.label("company_id"),
            company.Company.name.label("company_name")
        )
        .join(center.Center, device.Device.center_id == center.Center.id)
        .join(company.Company, center.Center.company_id == company.Company.id)
        .order_by(company.Company.name, center.Center.name, device.Device.name)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Convertir la lista de objetos Row (que son como tuplas) en una lista de diccionarios
    # Pydantic puede manejar esto sin problemas.
    return [result._asdict() for result in results]