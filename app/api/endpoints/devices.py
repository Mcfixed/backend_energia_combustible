from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo # Para ordenar

from app.db.database import get_db
from app.db.mongodb import get_mongo_collection
from app.crud import crud_device
from app.schemas import device as device_schema
from app.models import user as user_model, device as device_model
from app.api.dependencies import get_current_active_user

router = APIRouter()

@router.post("/devices", response_model=device_schema.Device, status_code=status.HTTP_201_CREATED)
def create_device(
    device: device_schema.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user)
):
    # Aquí deberías validar que el usuario (o su empresa) tiene permiso para crear
    db_device = crud_device.get_device_by_eui(db, dev_eui=device.dev_eui)
    if db_device:
        raise HTTPException(status_code=400, detail="Device EUI already registered")
    return crud_device.create_device(db=db, device_data=device)


@router.get("/devices/{device_id}", response_model=device_schema.DeviceWithLatestData)
async def get_device_with_latest_data(
    device_id: int,
    db: Session = Depends(get_db),
    mongo_collection: AsyncIOMotorCollection = Depends(get_mongo_collection),
    current_user: user_model.User = Depends(get_current_active_user)
):
    # 1. Obtener dispositivo de PostgreSQL
    device = crud_device.get_device(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # 2. TODO: Lógica de autorización
    # Validar que 'current_user' tiene permiso para ver 'device'
    # (ej. si pertenece a device.company_id)
    # ...

    # 3. Si el estado es "no visualizar", no continuar
    if device.status == device_model.DeviceStatus.do_not_display:
         raise HTTPException(status_code=403, detail="Device access forbidden")

    # 4. Obtener últimos datos de MongoDB
    # Buscamos por el 'devEui' y ordenamos por 'time' descendente
    latest_data_doc = await mongo_collection.find_one(
        {"deviceInfo.devEui": device.dev_eui},
        sort=[("time", pymongo.DESCENDING)]
    )

    # 5. Combinar los datos
    response_data = device_schema.Device.model_validate(device)
    combined_response = device_schema.DeviceWithLatestData(**response_data.model_dump())

    if latest_data_doc and "object" in latest_data_doc:
        try:
            # Validamos los datos de mongo con nuestro esquema Pydantic
            measurement = device_schema.MongoMeasurementData.model_validate(latest_data_doc["object"])
            combined_response.latest_measurement = measurement
        except Exception as e:
            # Si los datos de Mongo no coinciden con el esquema, lo dejamos en None
            print(f"Error al validar datos de Mongo: {e}")
            combined_response.latest_measurement = None
            
    return combined_response