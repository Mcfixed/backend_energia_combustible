from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection

import datetime
import pymongo 
from typing import List

from app.db.database import get_db
from app.db import mongodb

from app.db.mongodb import db_energy, db_fuel
from app.crud import crud_device, crud_user
from app.schemas import device as device_schema
from app.models import user as user_model, device as device_model
from app.api.dependencies import get_current_active_user
from app.core.config import settings

router = APIRouter()

@router.post("/devices", response_model=device_schema.Device, status_code=status.HTTP_201_CREATED)
def create_device(
    device: device_schema.DeviceCreate,
    db: Session = Depends(get_db),
):
    db_center = crud_user.get_center_by_id(db, center_id=device.center_id)
    if not db_center:
        raise HTTPException(status_code=404, detail="Center not found")
        
    db_device = crud_device.get_device_by_eui(db, dev_eui=device.dev_eui)
    if db_device:
        raise HTTPException(status_code=400, detail="Device EUI already registered")
    return crud_device.create_device(db=db, device_data=device)


@router.get("/devices/details", response_model=List[device_schema.DeviceDetails])
def read_devices_with_details(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Obtiene todos los dispositivos con detalles de centro y compañía
    para la tabla principal de estadísticas.
    """
    devices = crud_device.get_devices_with_details(db, skip=skip, limit=limit)
    return devices


@router.get("/devices/{device_id}", response_model=device_schema.DeviceWithLatestData)
async def get_device_with_latest_data(
    device_id: int,
    db: Session = Depends(get_db),
):
    device = crud_device.get_device(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.status == device_model.DeviceStatus.do_not_display:
         raise HTTPException(status_code=403, detail="Device access forbidden")
    mongo_collection: AsyncIOMotorCollection
    
    if device.type == "combustible":
        mongo_collection = mongodb.db_fuel[settings.MONGO_COLLECTION_NAME2]
    elif device.type == "energia":
        mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown device type: {device.type}")

    latest_data_doc = await mongo_collection.find_one(
        {"deviceInfo.devEui": device.dev_eui},
        sort=[("time", pymongo.DESCENDING)]
    )

    response_data = device_schema.Device.model_validate(device)
    combined_response = device_schema.DeviceWithLatestData(**response_data.model_dump())

    if latest_data_doc and "object" in latest_data_doc:
        try:
            measurement = device_schema.MongoMeasurementData.model_validate(latest_data_doc["object"])
            combined_response.latest_measurement = measurement
        except Exception as e:
            print(f"Error al validar datos de Mongo: {e}")
            combined_response.latest_measurement = None
            
    return combined_response

@router.get("/devices", response_model=List[device_schema.Device])
def read_devices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Obtiene una lista de todos los dispositivos.
    """
    devices = crud_device.get_devices(db, skip=skip, limit=limit)
    return devices

@router.get("/devices/by_center/{center_id}", response_model=List[device_schema.Device])
def read_devices_by_center(
    center_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Obtiene todos los dispositivos de un centro específico.
    """
    devices = crud_device.get_devices_by_center(db, center_id=center_id, skip=skip, limit=limit)
    return devices

@router.patch("/devices/{device_id}", response_model=device_schema.Device)
def update_device(
    device_id: int,
    device_in: device_schema.DeviceUpdate, 
    db: Session = Depends(get_db),
):
    """
    Actualiza un dispositivo (nombre, status, tipo, centro).
    """
    db_device = crud_device.get_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if device_in.center_id:
        db_center = crud_user.get_center_by_id(db, center_id=device_in.center_id)
        if not db_center:
            raise HTTPException(status_code=404, detail="New center not found")

    device = crud_device.update_device(db=db, db_device=db_device, device_in=device_in)
    return device

@router.delete("/devices/{device_id}", response_model=device_schema.Device)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
):
    """
    Elimina un dispositivo de la base de datos.
    """
    db_device = crud_device.delete_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device


@router.get("/devices/{dev_eui}/history", response_model=List[device_schema.MongoHistoryRecord])
async def get_device_history(
    dev_eui: str,
    start_date: datetime.datetime = Query(..., description="Fecha de inicio (ISO format)"),
    end_date: datetime.datetime = Query(..., description="Fecha de fin (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de un sensor, AGREGADO en ~500 puntos (Min/Max)
    para optimizar la visualización de picos.
    """
    
    print("\n--- INICIO DE DEBUG: get_device_history (CON AGREGACIÓN MIN/MAX) ---")
    
    db_device = crud_device.get_device_by_eui(db, dev_eui=dev_eui)
    
    if not db_device:
        raise HTTPException(status_code=440, detail=f"Device with EUI {dev_eui} not found in SQL database")

    print(f"Dispositivo encontrado en SQL. Campo 'type': '{db_device.type}'")

    mongo_collection: AsyncIOMotorCollection
    db_name: str
    
    agg_fields = {}            
    project_object_fields = {}  

    device_type_str = db_device.type 

    if device_type_str == "combustible":
        print("Lógica: 'combustible'. Configurando agregación Min/Max.")
        mongo_collection = mongodb.db_fuel[settings.MONGO_COLLECTION_NAME2]
        db_name = settings.MONGO_FUEL_DB_NAME
        
        fields_to_agg = ["volume_L_S0", "volume_L_S1", "pressure_Bar_S0"]
        
    elif device_type_str == "energia":
        print("Lógica: 'energia'. Configurando agregación Min/Max.")
        mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]
        db_name = settings.MONGO_DB_NAME
        
        fields_to_agg = ["agg_activePower", "agg_voltage", "agg_current"] 
    else:
        raise HTTPException(status_code=400, detail=f"Unknown or unsupported device type: {db_device.type}")
        
    for field in fields_to_agg:
        field_min = f"{field}_min"
        field_max = f"{field}_max"
        
        agg_fields[field_min] = { "$min": f"$object.{field}" }
        agg_fields[field_max] = { "$max": f"$object.{field}" }
        
        project_object_fields[field_min] = f"${field_min}"
        project_object_fields[field_max] = f"${field_max}"
    
    print(f"Acceso a Mongo: DB='{db_name}', Colección='{mongo_collection.name}'")
    

    match_stage = {
        "$match": {
            "deviceInfo.devEui": dev_eui,
            "time": { "$gte": start_date, "$lte": end_date },
            "object": { "$exists": True, "$ne": None }
        }
    }
    
    bucket_stage = {
        "$bucketAuto": {
            "groupBy": "$time",
            "buckets": 500,
            "output": {
                "time": { "$min": "$time" },
                **agg_fields
            }
        }
    }
    
    project_stage = {
        "$project": {
            "_id": 0, 
            "time": "$time",
            "object": project_object_fields 
        }
    }
    
    sort_stage = { "$sort": { "time": 1 } }
    
    pipeline = [ match_stage, bucket_stage, project_stage, sort_stage ]
    
    print(f"Mongo Pipeline: {pipeline}")
    
    cursor = mongo_collection.aggregate(pipeline)
    historical_docs = await cursor.to_list(length=None)
    
    print(f"Documentos (agregados) encontrados: {len(historical_docs)}")
    print("--- FIN DE DEBUG ---\n")
    
    return historical_docs