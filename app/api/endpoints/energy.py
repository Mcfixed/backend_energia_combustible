# app/api/endpoints/energia.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
import pymongo
import random
import datetime

from app.db.database import get_db
from app.db.mongodb import get_mongo_collection
from app.api.dependencies import get_current_active_user
from app.models import user as user_model
from app.models.association import UserCompany
from app.models.device import Device
from app.schemas.energy import DeviceSummary, HistoricalDataPoint, DeviceHistoricalData, DeviceAlert
from enum import Enum

router = APIRouter()


class TimeRange(str, Enum):
    day = "1d"
    week = "7d"
    two_weeks = "14d"
    month = "30d"
def _generate_mock_monthly_data(device_number: int) -> DeviceHistoricalData:
    """
    Genera datos simulados solo para la vista mensual,
    ya que la diaria ahora vendrá de datos reales.
    """
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
# --- Fin de Funciones de Simulación ---


@router.get(
    "/summary",
    response_model=List[DeviceSummary],
    summary="Obtiene un resumen de todos los dispositivos de energía del usuario"
)
async def get_energy_summary(
    db: Session = Depends(get_db),
    mongo_collection: AsyncIOMotorCollection = Depends(get_mongo_collection),
    current_user: user_model.User = Depends(get_current_active_user),
    time_range: TimeRange = TimeRange.day
):
    """
    Este endpoint entrega una lista de todos los dispositivos
    a los que el usuario tiene acceso, combinando:
    - Datos estáticos de PostgreSQL (Nombre, EUI)
    - El último documento de MongoDB (Datos en tiempo real)
    - Datos históricos y alertas (Simulados por ahora)
    """
    
    # 1. Obtener las empresas del usuario
    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    
    if not user_company_links:
        return [] # El usuario no está en ninguna empresa

    allowed_company_ids = [link.company_id for link in user_company_links]

    # 2. Obtener todos los dispositivos de Postgres para esas empresas
    devices_from_db = db.query(Device).filter(
        Device.company_id.in_(allowed_company_ids)
    ).all()
    
    summary_list = []

    # 3. Para cada dispositivo, obtener su última data de Mongo
    for device_pg in devices_from_db:
        latest_data_doc = await mongo_collection.find_one(
            {"deviceInfo.devEui": device_pg.dev_eui},
            sort=[("time", pymongo.DESCENDING)]
        )

        if not latest_data_doc:
            # Si no hay datos en Mongo, saltamos este dispositivo
            continue

        # 3.2. --- NUEVO: Obtener historial real de las últimas 24 horas ---
        end_time = datetime.datetime.now(datetime.timezone.utc)
        
        if time_range == TimeRange.week:
            days_to_query = 7
        elif time_range == TimeRange.two_weeks:
            days_to_query = 14
        elif time_range == TimeRange.month:
            days_to_query = 30
        else: # TimeRange.day
            days_to_query = 1
            
        start_time = end_time - datetime.timedelta(days=days_to_query)

        historical_cursor = mongo_collection.find(
            {
                "deviceInfo.devEui": device_pg.dev_eui,
                "time": {
                    "$gte": start_time.isoformat(),
                    "$lte": end_time.isoformat()
                }
            },
            projection={
                "time": 1,
                "object.agg_activePower": 1,
                "object.agg_voltage": 1,
                "object.agg_current": 1,
                "object.agg_powerFactor": 1,
                "object.agg_frequency": 1,
                "object.phaseA_thdI": 1,
                "object.agg_reactivePower": 1,
                "object.agg_apparentPower": 1
            }
        ).sort("time", pymongo.ASCENDING)

        historical_docs = await historical_cursor.to_list(length=None) # Obtener todos (máx 2880)

        # 3.3. --- NUEVO: Formatear los datos reales para el frontend ---
        daily_data_raw = {
            "consumption": [], "voltage": [], "current": [], "power": [],
            "powerFactor": [], "frequency": [], "thd": [], "reactivePower": [], "apparentPower": []
        }

        for doc in historical_docs:
            try:
                # Formatear la hora como "HH:MM"
                time_str = datetime.datetime.fromisoformat(doc["time"]).strftime("%H:%M")
                obj = doc.get("object", {})
                
                daily_data_raw["consumption"].append({"time": time_str, "value": obj.get("agg_activePower", 0)})
                daily_data_raw["power"].append({"time": time_str, "value": obj.get("agg_activePower", 0)})
                daily_data_raw["voltage"].append({"time": time_str, "value": obj.get("agg_voltage", 0)})
                daily_data_raw["current"].append({"time": time_str, "value": obj.get("agg_current", 0)})
                daily_data_raw["powerFactor"].append({"time": time_str, "value": obj.get("agg_powerFactor", 0)})
                daily_data_raw["frequency"].append({"time": time_str, "value": obj.get("agg_frequency", 0)})
                daily_data_raw["thd"].append({"time": time_str, "value": obj.get("phaseA_thdI", 0)}) # Usamos Fase A como en tu mock
                daily_data_raw["reactivePower"].append({"time": time_str, "value": obj.get("agg_reactivePower", 0)})
                daily_data_raw["apparentPower"].append({"time": time_str, "value": obj.get("agg_apparentPower", 0)})
            except Exception:
                # Omitir dato si falla el parseo
                continue
        
        # 4. Combinar historial real (diario) con simulado (mensual)
        historical_data = {
            "daily": DeviceHistoricalData(**daily_data_raw),
            "monthly": _generate_mock_monthly_data(device_pg.id) # Mantenemos el mock mensual
        }
        alerts = _generate_mock_alerts(latest_data_doc.get("object", {}))
        
         
        # Usamos el nombre de Postgres como fuente de verdad
        device_info_data = latest_data_doc.get("deviceInfo", {})
        device_info_data["deviceName"] = device_pg.name
        device_info_data["location"] = f"Área {device_pg.id}" # Simulado como en tu JS
        mongo_id = latest_data_doc.get("_id")
        device_data = {
            "_id": {"$oid": str(mongo_id)},
            "time": latest_data_doc.get("time"),
            "deviceInfo": device_info_data,
            "object": latest_data_doc.get("object"),
            "historicalData": historical_data,
            "dailyConsumption": latest_data_doc.get("object", {}).get("agg_activePower", 0),
            "alerts": alerts
        }
        
        try:
            # Validamos que los datos coincidan con el schema Pydantic
            summary_list.append(DeviceSummary.model_validate(device_data))
        except Exception as e:
            # Si un dispositivo falla la validación, lo omitimos y logueamos
            print(f"Error al validar dispositivo {device_pg.dev_eui}: {e}")
            continue

    return summary_list