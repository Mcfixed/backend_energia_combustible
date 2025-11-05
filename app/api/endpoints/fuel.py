from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
import datetime
import pymongo
import datetime
from enum import Enum

from app.db.database import get_db
from app.db.mongodb import get_mongo_fuel_collection
from app.api.dependencies import get_current_active_user
from app.models import user as user_model
from app.models import center as center_model # Importamos Center
from app.models.association import UserCompany
from app.models.device import Device, DeviceType # Importamos Device
from app.schemas.fuel import (
    FuelCenter,
    FuelTank,
    FuelSensorData,
    MongoFuelDoc
)

router = APIRouter()

class TimeRange(str, Enum):
    """ Coincide con tu estado de React """
    h24 = "24h"
    d7 = "7d"
    d30 = "30d"

def _get_center_status(tanks: List[FuelTank]) -> str:
    """ Calcula el estado del centro (lógica copiada de tu React) """
    if not tanks:
        return 'neutral'

    has_error = any(not tank.sensor.sensor_ok for tank in tanks)
    if has_error:
        return 'danger'

    low_inventory = any(tank.sensor.percentage < 20 for tank in tanks)
    if low_inventory:
        return 'warning'

    return 'secure'

def _create_tanks_from_mongo(
    device_pg: Device,
    mongo_doc: dict,
    center_id_str: str
) -> List[FuelTank]:
    """
    Función clave: Transforma 1 documento de Mongo (con S0, S1, S2)
    en 3 objetos FuelTank para la API.
    """
    try:
        mongo_data = MongoFuelDoc.model_validate(mongo_doc)
        mongo_obj = mongo_data.object
        last_update_dt = mongo_data.time 
        last_update_iso = last_update_dt.isoformat()

        lat = mongo_data.rxInfo[0].location.latitude if mongo_data.rxInfo and mongo_data.rxInfo[0].location else 0.0
        lon = mongo_data.rxInfo[0].location.longitude if mongo_data.rxInfo and mongo_data.rxInfo[0].location else 0.0

        # Tanque 0
        sensor_0 = FuelSensorData(
            volume_L=mongo_obj.volume_L_S0 or 0.0,
            percentage=mongo_obj.percentage_S0 or 0.0,
            pressure_Bar=mongo_obj.pressure_Bar_S0 or 0.0,
            sensor_ok=mongo_obj.sensor_0_ok,
            lastUpdate=last_update_iso, 
            latitude=lat,
            longitude=lon
        )
        tank_0 = FuelTank(
            id=f"{device_pg.dev_eui}-S0",
            name="Tanque S0 (Diesel)", capacity=10000,
            fuelType="Diesel", sensor=sensor_0, centerId=center_id_str
        )

        # Tanque 1
        sensor_1 = FuelSensorData(
            volume_L=mongo_obj.volume_L_S1 or 0.0,
            percentage=mongo_obj.percentage_S1 or 0.0,
            pressure_Bar=mongo_obj.pressure_Bar_S1 or 0.0,
            sensor_ok=mongo_obj.sensor_1_ok,
            lastUpdate=last_update_iso,
            latitude=lat,
            longitude=lon
        )
        tank_1 = FuelTank(
            id=f"{device_pg.dev_eui}-S1",
            name="Tanque S1 (Gasolina)", capacity=15000,
            fuelType="Gasolina", sensor=sensor_1, centerId=center_id_str
        )

        # Tanque 2
        sensor_2 = FuelSensorData(
            volume_L=mongo_obj.volume_L_S2 or 0.0,
            percentage=mongo_obj.percentage_S2 or 0.0,
            pressure_Bar=mongo_obj.pressure_Bar_S2 or 0.0,
            sensor_ok=mongo_obj.sensor_2_ok,
            lastUpdate=last_update_iso,
            latitude=lat,
            longitude=lon
        )
        tank_2 = FuelTank(
            id=f"{device_pg.dev_eui}-S2",
            name="Tanque S2 (Biodiesel)", capacity=8000,
            fuelType="Biodiesel", sensor=sensor_2, centerId=center_id_str
        )

        print(f" 	-> ÉXITO (Paso 6): Validación de Pydantic correcta. Tanques creados.")
        return [tank_0, tank_1, tank_2]

    except Exception as e:
        print(f" 	-> ERROR (Causa C): Falló la validación de Pydantic en _create_tanks_from_mongo.")
        print(f" 	-> DETALLE DEL ERROR: {e}") 
        return []


@router.get(
    "/summary",
    response_model=List[FuelCenter],
    summary="Obtiene un resumen de todos los centros de combustible"
)
async def get_fuel_summary(
    db: Session = Depends(get_db),
    mongo_collection: AsyncIOMotorCollection = Depends(get_mongo_fuel_collection),
    current_user: user_model.User = Depends(get_current_active_user),
    time_range: TimeRange = TimeRange.h24
):

    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()

    if not user_company_links:
        return []

    allowed_company_ids = [link.company_id for link in user_company_links]

    centers_from_db = db.query(center_model.Center).filter(
        center_model.Center.company_id.in_(allowed_company_ids)
    ).all()

    print(f"\nDIAGNÓSTICO (Paso 2): Centros encontrados en PG: {len(centers_from_db)}")
    for c in centers_from_db:
        print(f" 	-> Centro: id={c.id}, name='{c.name}'")

    response_list = []

    for center_pg in centers_from_db:
        print(f"\n--- Procesando Centro ID: {center_pg.id} ---")

        print(f"DIAGNÓSTICO (Paso 4): Buscando devices en PG con center_id={center_pg.id} y type='combustible'...")
        devices_from_db = db.query(Device).filter(
            Device.center_id == center_pg.id,
            Device.type == DeviceType.combustible
        ).all()

        print(f" 	-> Devices encontrados: {len(devices_from_db)}")
        if not devices_from_db:
            print(" 	-> ERROR (Causa A): No hay devices en PG que coincidan. Revisa la tabla 'devices'.")

        center_tanks: List[FuelTank] = []
        center_id_str = str(center_pg.id)

        for device_pg in devices_from_db:
            print(f" 	DIAGNÓSTICO (Paso 5): Buscando en Mongo 'deviceInfo.devEui': '{device_pg.dev_eui}'")

            query = {
                "deviceInfo.devEui": device_pg.dev_eui,
                "object": { "$type": "object" }
            }

            latest_data_doc = await mongo_collection.find_one(
                query,
                sort=[("time", pymongo.DESCENDING)]
            )

            if not latest_data_doc:
                print(f" 	 	-> ERROR (Causa B): No se encontró el EUI '{device_pg.dev_eui}' en Mongo (o no tiene campo 'object').")
                continue

            print(f" 	 	-> ÉXITO (Paso 5): Documento encontrado en Mongo (Time: {latest_data_doc.get('time')}).")
            print(f" 	DIAGNÓSTICO (Paso 6): Enviando documento a _create_tanks_from_mongo...")

            tanks_from_device = _create_tanks_from_mongo(
                device_pg,
                latest_data_doc,
                center_id_str
            )
            center_tanks.extend(tanks_from_device)

        total_capacity = sum(tank.capacity for tank in center_tanks)
        current_inventory = sum(tank.sensor.volume_L for tank in center_tanks)
        center_status = _get_center_status(center_tanks)

        center_response = FuelCenter(
            id=center_id_str,
            name=center_pg.name,
            location=f"Ubicación de {center_pg.name}",
            status=center_status,
            tanks=center_tanks,
            totalCapacity=total_capacity,
            currentInventory=current_inventory
        )

        print(f"--- Fin Centro ID: {center_pg.id}. Total tanques añadidos: {len(center_tanks)} ---")
        response_list.append(center_response)

    return response_list