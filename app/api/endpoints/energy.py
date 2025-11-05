import datetime
import pytz
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
import pymongo
import random

from app.db.database import get_db
from app.db import mongodb
from app.core.config import settings
from app.api.dependencies import get_current_active_user
from app.models import user as user_model
from app.models import center as center_model
from app.models.association import UserCompany
from app.models.device import Device, DeviceType
from app.schemas.energy import DeviceSummary, HistoricalDataPoint, DeviceHistoricalData, DeviceAlert, DailyConsumptionPoint, DeviceDetailsResponse, DeviceInfo
from enum import Enum

CHILE_TZ = pytz.timezone("America/Santiago")

router = APIRouter()

def _generate_mock_monthly_data(device_number: int) -> DeviceHistoricalData:
    base_data = {
        "consumption": [], "voltage": [], "current": [], "power": [],
        "powerFactor": [], "frequency": [], "thd": [], "reactivePower": [], "apparentPower": []
    }
    labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    base_data["consumption"] = [{"time": m, "value": random.randint(500, 1500) + (device_number * 300)} for m in labels]
    base_data["voltage"] = [{"time": m, "value": 230 + random.uniform(-2, 2)} for m in labels]
    base_data["current"] = [{"time": m, "value": 50 + random.uniform(-10, 10)} for m in labels]
    base_data["power"] = [{"time": m, "value": random.randint(500, 1500) + (device_number * 300)} for m in labels]
    base_data["powerFactor"] = [{"time": m, "value": 90 + random.uniform(-5, 5)} for m in labels]
    base_data["frequency"] = [{"time": m, "value": 50} for m in labels]
    base_data["thd"] = [{"time": m, "value": 5 + random.uniform(0, 10)} for m in labels]
    base_data["reactivePower"] = [{"time": m, "value": random.randint(100, 300) + (device_number * 50)} for m in labels]
    base_data["apparentPower"] = [{"time": m, "value": random.randint(600, 1600) + (device_number * 300)} for m in labels]
    return DeviceHistoricalData(**base_data)

def _generate_mock_alerts(obj: dict) -> List[DeviceAlert]:
    alerts = []
    thd_a = obj.get("phaseA_thdI", 0)
    if thd_a > 60:
        alerts.append(DeviceAlert(
            id=1,
            type="warning",
            message=f"THD Fase A elevado: {thd_a:.1f}%",
            timestamp=(datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat()
        ))
    else:
        alerts.append(DeviceAlert(
            id=2,
            type="info",
            message="Consumo estable",
            timestamp=(datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
        ))
    return alerts

@router.get(
    "/summary",
    response_model=List[DeviceSummary],
    summary="Obtiene un resumen de todos los dispositivos de energía del usuario"
)
async def get_energy_summary(
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user),
    time_range: str = Query("1d", description="Rango de tiempo: 1d, 7d, 14d, 30d")
):
    """
    Este endpoint entrega una lista de todos los dispositivos
    a los que el usuario tiene acceso, combinando:
    - Datos estáticos de PostgreSQL (Nombre, EUI)
    - El último documento de MongoDB (Datos en tiempo real)
    - El historial de consumo DIARIO (E_now - E_start)
    """
    
    mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]

    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    
    if not user_company_links:
        return [] 

    allowed_company_ids = [link.company_id for link in user_company_links]

    devices_from_db = db.query(Device)\
        .join(center_model.Center)\
        .filter(
            center_model.Center.company_id.in_(allowed_company_ids),
            Device.type == DeviceType.energia
        )\
        .all()
    
    summary_list = []

    for i, device_pg in enumerate(devices_from_db):
        latest_data_doc = await mongo_collection.find_one(
            {
                "deviceInfo.devEui": device_pg.dev_eui,
                "object": { "$type": "object" } 
            },
            sort=[("time", pymongo.DESCENDING)]
        )

        if not latest_data_doc:
            continue

        end_time = datetime.datetime.now(datetime.timezone.utc)
        
        if time_range == "7d":
            days_to_query = 7
        elif time_range == "14d":
            days_to_query = 14
        elif time_range == "30d":
            days_to_query = 30
        else:
            days_to_query = 1  

            
        start_time = end_time - datetime.timedelta(days=days_to_query)

        projection = {
            "time": 1,
            "object.agg_activePower": 1,
            "object.agg_voltage": 1,
            "object.agg_current": 1,
            "object.agg_powerFactor": 1,
            "object.agg_frequency": 1,
            "object.phaseA_thdI": 1,
            "object.agg_reactivePower": 1,
            "object.agg_apparentPower": 1,
            "object.agg_activeEnergy": 1,
            "object.phaseA_activeEnergy": 1,
            "object.phaseB_activeEnergy": 1,
            "object.phaseC_activeEnergy": 1
        }
        
        historical_cursor = mongo_collection.find(
            {
                "deviceInfo.devEui": device_pg.dev_eui,
                "time": { "$gte": start_time, "$lte": end_time },
                "object": { "$type": "object" }
            },
            projection=projection
        ).sort("time", pymongo.ASCENDING)

        historical_docs = await historical_cursor.to_list(length=None) 

        daily_data_raw = {
            "consumption": [], "voltage": [], "current": [], "power": [],
            "powerFactor": [], "frequency": [], "thd": [], "reactivePower": [], "apparentPower": []
        }

        for doc in historical_docs:
            try:
                time_utc = doc["time"]
                
                if time_utc and time_utc.tzinfo is None:
                    time_utc = time_utc.replace(tzinfo=datetime.timezone.utc)
                
                time_santiago = time_utc.astimezone(CHILE_TZ)
                
                if days_to_query > 1:
                    time_str = time_santiago.strftime("%d-%m") 
                else:
                    time_str = time_santiago.strftime("%H:%M")
                
                obj = doc.get("object", {})
                
                daily_data_raw["consumption"].append({"time": time_str, "value": obj.get("agg_activeEnergy", 0)})
                daily_data_raw["power"].append({"time": time_str, "value": obj.get("agg_activePower", 0)})
                daily_data_raw["voltage"].append({"time": time_str, "value": obj.get("agg_voltage", 0)})
                daily_data_raw["current"].append({"time": time_str, "value": obj.get("agg_current", 0)})
                daily_data_raw["powerFactor"].append({"time": time_str, "value": obj.get("agg_powerFactor", 0)})
                daily_data_raw["frequency"].append({"time": time_str, "value": obj.get("agg_frequency", 0)})
                daily_data_raw["thd"].append({"time": time_str, "value": obj.get("phaseA_thdI", 0)})
                daily_data_raw["reactivePower"].append({"time": time_str, "value": obj.get("agg_reactivePower", 0)})
                daily_data_raw["apparentPower"].append({"time": time_str, "value": obj.get("agg_apparentPower", 0)})
            except Exception:
                continue
        
        
        total_agg_wh = 0
        total_a_wh = 0
        total_b_wh = 0
        total_c_wh = 0

        if len(historical_docs) < 2:
            pass 
        else:
            last_obj = historical_docs[0].get("object", {})
            last_agg = last_obj.get("agg_activeEnergy", 0)
            last_a = last_obj.get("phaseA_activeEnergy", 0)
            last_b = last_obj.get("phaseB_activeEnergy", 0)
            last_c = last_obj.get("phaseC_activeEnergy", 0)
            
            for doc in historical_docs[1:]:
                current_obj = doc.get("object", {})
                
                current_agg = current_obj.get("agg_activeEnergy", 0)
                delta_agg = current_agg - last_agg
                if delta_agg < 0:
                    total_agg_wh += current_agg
                else:
                    total_agg_wh += delta_agg
                last_agg = current_agg

                current_a = current_obj.get("phaseA_activeEnergy", 0)
                delta_a = current_a - last_a
                if delta_a < 0: 
                    total_a_wh += current_a
                else:
                    total_a_wh += delta_a
                last_a = current_a

                current_b = current_obj.get("phaseB_activeEnergy", 0)
                delta_b = current_b - last_b
                if delta_b < 0: 
                    total_b_wh += current_b
                else:
                    total_b_wh += delta_b
                last_b = current_b
                
                current_c = current_obj.get("phaseC_activeEnergy", 0)
                delta_c = current_c - last_c
                if delta_c < 0: 
                    total_c_wh += current_c
                else:
                    total_c_wh += delta_c
                last_c = current_c

        latest_obj = latest_data_doc.get("object", {}).copy()
        
        latest_obj["agg_activeEnergy"] = total_agg_wh
        latest_obj["phaseA_activeEnergy"] = total_a_wh
        latest_obj["phaseB_activeEnergy"] = total_b_wh
        latest_obj["phaseC_activeEnergy"] = total_c_wh
        
        historical_data = {
            "daily": DeviceHistoricalData(**daily_data_raw),
            "monthly": _generate_mock_monthly_data(i) 
        }
        alerts = _generate_mock_alerts(latest_obj) 
        
        device_info_data = latest_data_doc.get("deviceInfo", {})
        device_info_data["deviceName"] = device_pg.name
        device_info_data["location"] = f"Centro: {device_pg.center_id}"
        mongo_id = latest_data_doc.get("_id")
        
        time_obj = latest_data_doc.get("time")
        if time_obj and time_obj.tzinfo is None:
            time_obj = time_obj.replace(tzinfo=datetime.timezone.utc)

        local_time = time_obj.astimezone(CHILE_TZ) if time_obj else None
        
        device_data = {
            "_id": {"$oid": str(mongo_id)},
            "time": local_time.isoformat() if local_time else None, 
            "deviceInfo": device_info_data,
            "object": latest_obj,
            "historicalData": historical_data,
            "dailyConsumption": latest_obj["agg_activeEnergy"], 
            "alerts": alerts
        }
        
        try:
            summary_list.append(DeviceSummary.model_validate(device_data))
        except Exception as e:
            print(f"Error al validar dispositivo {device_pg.dev_eui}: {e}")
            continue

    return summary_list

@router.get(
    "/details/{dev_eui}",
    response_model=DeviceDetailsResponse,
    summary="Obtiene los detalles de consumo diario de un dispositivo"
)
async def get_device_details(
    dev_eui: str,
    days: int = Query(30, description="Número de días de historial a consultar"),
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Este endpoint calcula el consumo de energía DIARIO para un dispositivo,
    manejando el valor incremental 'agg_activeEnergy' Y LOS REINICIOS DEL CONTADOR.
    
    Utiliza una agregación de MongoDB para:
    1. Agrupar lecturas por día (en zona horaria de Chile).
    2. Obtener un array con TODAS las lecturas de 'agg_activeEnergy' de ese día.
    
    Luego, en Python, procesa cada array diario para:
    1. Calcular los "deltas" entre lecturas consecutivas.
    2. Manejar deltas negativos (reinicios) sumando solo la lectura actual.
    3. Sumar todos los deltas positivos para obtener el consumo diario.
    """
    
    mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]

    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    if not user_company_links:
        raise HTTPException(status_code=403, detail="Usuario no asociado a ninguna empresa")

    allowed_company_ids = [link.company_id for link in user_company_links]

    device_pg = db.query(Device)\
        .join(center_model.Center)\
        .filter(
            Device.dev_eui == dev_eui,
            center_model.Center.company_id.in_(allowed_company_ids)
        )\
        .first()

    if not device_pg:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado o sin permisos")
    
    
    end_time_utc = datetime.datetime.now(pytz.utc)
    start_time_utc = end_time_utc - datetime.timedelta(days=days)

    pipeline = [
        {
            "$match": {
                "deviceInfo.devEui": dev_eui,
                "time": {"$gte": start_time_utc, "$lte": end_time_utc},
                "object.agg_activeEnergy": {"$exists": True}
            }
        },
        {
            "$project": {
                "time": "$time",
                "energy": "$object.agg_activeEnergy",
                "date_chile": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$time",
                        "timezone": "America/Santiago"
                    }
                }
            }
        },
        {
            "$sort": {"time": 1}
        },
        {
            "$group": {
                "_id": "$date_chile",
                "readings": {"$push": "$energy"} 
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]

    cursor = mongo_collection.aggregate(pipeline)
    daily_results = await cursor.to_list(length=None)

    daily_consumption_list = []
    total_consumption_kwh = 0
    
    for doc in daily_results:
        readings_list = doc.get("readings", [])
        
        if len(readings_list) < 2:
            continue
        daily_total_wh = 0
        last_reading = readings_list[0] 
        
        for i in range(1, len(readings_list)):
            current_reading = readings_list[i]
            
            delta = current_reading - last_reading
            
            if delta < 0:
                daily_total_wh += current_reading
            else:
                daily_total_wh += delta
                
            last_reading = current_reading 
        
        consumption_kwh = daily_total_wh / 1000.0
        
        date_obj = datetime.datetime.strptime(doc["_id"], "%Y-%m-%d")
        date_str = date_obj.strftime("%d-%m")

        daily_consumption_list.append(DailyConsumptionPoint(
            date=date_str,
            consumption=round(consumption_kwh, 2)
        ))
        total_consumption_kwh += consumption_kwh

    avg_kwh = total_consumption_kwh / len(daily_consumption_list) if daily_consumption_list else 0

    device_info_data = {
        "deviceName": device_pg.name,
        "devEui": device_pg.dev_eui,
        "location": f"Centro: {device_pg.center_id}",
        "applicationName": "N/A",
        "deviceProfileName": "N/A"
    }
    
    return DeviceDetailsResponse(
        deviceInfo=DeviceInfo(**device_info_data),
        dailyConsumption=daily_consumption_list,
        totalConsumption=round(total_consumption_kwh, 2),
        avgDailyConsumption=round(avg_kwh, 2)
    )