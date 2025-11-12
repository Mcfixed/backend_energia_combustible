import datetime
import pytz
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List
import pymongo
import random
import calendar
from app.db.database import get_db
from app.db import mongodb
from app.core.config import settings
from app.api.dependencies import get_current_active_user
from app.models import user as user_model
from app.models import center as center_model
from app.models.association import UserCompany
from app.models.device import Device, DeviceType
from app.schemas.energy import DeviceSummary, HistoricalDataPoint, DeviceHistoricalData, DeviceAlert, DailyConsumptionPoint, DeviceDetailsResponse, DeviceInfo, MonthlyConsumptionPoint
from app.schemas.center import CenterPriceUpdate
from enum import Enum

CHILE_TZ = pytz.timezone("America/Santiago")

router = APIRouter()
ALL_HISTORICAL_FIELDS = {
    "consumption": "object.agg_activeEnergy",
    "power": "object.agg_activePower",
    "voltage": "object.phaseA_voltage",
    "current": "object.agg_current",
    "powerFactor": "object.agg_powerFactor",
    "frequency": "object.agg_frequency",
    "reactivePower": "object.agg_reactivePower",
    "apparentPower": "object.agg_apparentPower",
    "thd": "object.agg_thdI", 
    "apparentEnergy": "object.agg_apparentEnergy",
    "reactiveEnergy": "object.agg_reactiveEnergy",

    "power_a": "object.phaseA_activePower",
    "voltage_a": "object.phaseA_voltage",
    "current_a": "object.phaseA_current",
    "powerFactor_a": "object.phaseA_powerFactor",
    "reactivePower_a": "object.phaseA_reactivePower",
    "apparentPower_a": "object.phaseA_apparentPower",
    "thd_i_a": "object.phaseA_thdI",
    "thd_u_a": "object.phaseA_thdU",
    "apparentEnergy_a": "object.phaseA_apparentEnergy",
    "reactiveEnergy_a": "object.phaseA_reactiveEnergy",
    "activeEnergy_a": "object.phaseA_activeEnergy",
    "activePower_a": "object.phaseA_activePower",
    "reactiveEnergy_a": "object.phaseA_reactiveEnergy",
    
}


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
    time_range: str = Query(
        "1d", 
        description="Rango de tiempo: 5m, 30m, 1h, 6h, 12h, 1d, 7d, 14d, 30d"
    )
):
    """
    Este endpoint entrega una lista de todos los dispositivos.
    - Usa datos crudos para rangos <= 1 día.
    - Usa agregación ($bucketAuto) para rangos > 1 día (7d, 14d, 30d).
    """
    
    mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]

    # 1. Obtener permisos de usuario
    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    if not user_company_links:
        return [] 
    allowed_company_ids = [link.company_id for link in user_company_links]

    # 2. Obtener dispositivos de Postgres
    devices_from_db = db.query(Device)\
        .join(center_model.Center)\
        .filter(
            center_model.Center.company_id.in_(allowed_company_ids),
            Device.type == DeviceType.energia
        )\
        .all()
    
    summary_list = []

    # 3. Iterar por cada dispositivo
    for i, device_pg in enumerate(devices_from_db):
        latest_data_doc = await mongo_collection.find_one(
            {"deviceInfo.devEui": device_pg.dev_eui, "object": { "$type": "object" }},
            sort=[("time", pymongo.DESCENDING)]
        )

        if not latest_data_doc:
            continue

        # --- Lógica de Rango de Tiempo y Flag de Agregación ---
        end_time = datetime.datetime.now(datetime.timezone.utc)
        USE_AGGREGATION = False # Por defecto, traemos datos crudos
        
        # --- ¡CAMBIO SOLICITADO! ---
        # Define el número de buckets deseado para la agregación
        num_buckets = 1500
        
        if time_range == "5m":
            start_time = end_time - datetime.timedelta(minutes=5)
            days_to_query = 0
        elif time_range == "30m":
            start_time = end_time - datetime.timedelta(minutes=30)
            days_to_query = 0
        elif time_range == "1h":
            start_time = end_time - datetime.timedelta(hours=1)
            days_to_query = 0
        elif time_range == "6h":
            start_time = end_time - datetime.timedelta(hours=6)
            days_to_query = 0
        elif time_range == "12h":
            start_time = end_time - datetime.timedelta(hours=12)
            days_to_query = 0
        
        # --- RANGOS LARGOS (Aquí activamos la agregación) ---
        elif time_range == "7d":
            start_time = end_time - datetime.timedelta(days=7)
            days_to_query = 7
            USE_AGGREGATION = True
        elif time_range == "14d":
            start_time = end_time - datetime.timedelta(days=14)
            days_to_query = 14
            USE_AGGREGATION = True
        elif time_range == "30d":
            start_time = end_time - datetime.timedelta(days=30)
            days_to_query = 30
            USE_AGGREGATION = True
        # --- Fin Rangos Largos ---
            
        else: # default 1d
            start_time = end_time - datetime.timedelta(days=1)
            days_to_query = 1
            # Mantenemos USE_AGGREGATION = False para 1d

        
        # --- CÁLCULO DE CONSUMO EFICIENTE (Se mantiene igual para todos) ---
        base_query = {
            "deviceInfo.devEui": device_pg.dev_eui,
            "time": { "$gte": start_time, "$lte": end_time },
            "object": { "$type": "object" }
        }
        projection_energy = {
            "_id": 0,
            "object.agg_activeEnergy": 1, "object.phaseA_activeEnergy": 1,
            "object.phaseB_activeEnergy": 1, "object.phaseC_activeEnergy": 1,
        }
        
        first_doc = await mongo_collection.find_one(
            base_query, projection=projection_energy, sort=[("time", pymongo.ASCENDING)]
        )
        last_doc = await mongo_collection.find_one(
            base_query, projection=projection_energy, sort=[("time", pymongo.DESCENDING)]
        )

        total_agg_wh, total_a_wh, total_b_wh, total_c_wh = 0, 0, 0, 0
        if first_doc and last_doc:
            first_obj = first_doc.get("object", {})
            last_obj = last_doc.get("object", {})
            total_agg_wh = max(last_obj.get("agg_activeEnergy", 0) - first_obj.get("agg_activeEnergy", 0), 0)
            total_a_wh = max(last_obj.get("phaseA_activeEnergy", 0) - first_obj.get("phaseA_activeEnergy", 0), 0)
            total_b_wh = max(last_obj.get("phaseB_activeEnergy", 0) - first_obj.get("phaseB_activeEnergy", 0), 0)
            total_c_wh = max(last_obj.get("phaseC_activeEnergy", 0) - first_obj.get("phaseC_activeEnergy", 0), 0)
        
        
        # --- OBTENCIÓN DE DATOS HISTÓRICOS (HÍBRIDO) ---
        daily_data_raw = {field_key: [] for field_key in ALL_HISTORICAL_FIELDS.keys()}

        if USE_AGGREGATION:
            # --- RUTA 1: AGREGACIÓN (7d, 14d, 30d) ---
            
            bucket_outputs = {"time": {"$first": "$time"}}
            for field_key, field_path in ALL_HISTORICAL_FIELDS.items():
                if "Energy" in field_path or "consumption" in field_key:
                    bucket_outputs[field_key] = {"$last": f"${field_path}"}
                else:
                    bucket_outputs[field_key] = {"$avg": f"${field_path}"}

            pipeline = [
                {"$match": base_query},
                {"$bucketAuto": {
                    "groupBy": "$time",
                    "buckets": num_buckets, # <-- Aquí se usa el valor 2000
                    "output": bucket_outputs
                }},
                {"$sort": {"time": 1}}
            ]
            historical_cursor = mongo_collection.aggregate(pipeline)
            aggregated_docs = await historical_cursor.to_list(length=None) 

            # Procesar docs agregados (loop rápido)
            for doc in aggregated_docs:
                try:
                    time_utc = doc["time"]
                    if time_utc and time_utc.tzinfo is None:
                        time_utc = time_utc.replace(tzinfo=datetime.timezone.utc)
                    time_santiago = time_utc.astimezone(CHILE_TZ)
                    
                    time_str = time_santiago.strftime("%d-%m") if days_to_query > 1 else time_santiago.strftime("%H:%M")
                    
                    for field_key in ALL_HISTORICAL_FIELDS.keys():
                        value = doc.get(field_key, 0) 
                        daily_data_raw[field_key].append({"time": time_str, "value": value})
                except Exception:
                    continue

        else:
            # --- RUTA 2: DATOS CRUDOS (5m, 30m, 1h, 6h, 12h, 1d) ---
            
            projection_historical = {"time": 1}
            for field_path in ALL_HISTORICAL_FIELDS.values():
                projection_historical[field_path] = 1
            
            historical_cursor = mongo_collection.find(
                base_query,
                projection=projection_historical
            ).sort("time", pymongo.ASCENDING)

            historical_docs = await historical_cursor.to_list(length=None) 

            # Procesar docs crudos (tu loop original)
            for doc in historical_docs:
                try:
                    time_utc = doc["time"]
                    if time_utc and time_utc.tzinfo is None:
                        time_utc = time_utc.replace(tzinfo=datetime.timezone.utc)
                    time_santiago = time_utc.astimezone(CHILE_TZ)
                    
                    time_str = time_santiago.strftime("%d-%m") if days_to_query > 1 else time_santiago.strftime("%H:%M")
                    
                    obj = doc.get("object", {})
                    
                    for field_key, field_path in ALL_HISTORICAL_FIELDS.items():
                        key_in_obj = field_path.split('.', 1)[1]
                        value = obj.get(key_in_obj, 0)
                        daily_data_raw[field_key].append({"time": time_str, "value": value})
                except Exception:
                    continue
        
        # --- FIN DE LA BIFURCACIÓN ---

        
        # --- ENSAMBLAR LA RESPUESTA (Sin cambios) ---
        latest_obj = latest_data_doc.get("object", {}).copy()
        
        final_energy_counter = latest_obj.get("agg_activeEnergy", 0)
        
        latest_obj["agg_activeEnergy"] = total_agg_wh
        latest_obj["phaseA_activeEnergy"] = total_a_wh
        latest_obj["phaseB_activeEnergy"] = total_b_wh
        latest_obj["phaseC_activeEnergy"] = total_c_wh
        
        historical_data = {
            "daily": DeviceHistoricalData(**daily_data_raw),
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
            "dailyConsumption": total_agg_wh,
            "alerts": alerts,
            "final_energy_counter": final_energy_counter
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
    summary="Obtiene los detalles de consumo diario y mensual de un dispositivo"
)
async def get_device_details(
    dev_eui: str,
    days: int = Query(30, description="Número de días para el gráfico diario"),
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Calcula el consumo diario (últimos N días) y mensual (últimos 12 meses)
    usando la resta directa entre el valor final e inicial del contador
    (agg_activeEnergy), en lugar de sumar deltas.
    """

    mongo_collection = mongodb.db_energy[settings.MONGO_COLLECTION_NAME]
    user_company_links = db.query(UserCompany).filter(
        UserCompany.user_id == current_user.id
    ).all()
    if not user_company_links:
        raise HTTPException(status_code=403, detail="Usuario no asociado a ninguna empresa")

    allowed_company_ids = [link.company_id for link in user_company_links]
    device_pg = db.query(Device).join(center_model.Center).filter(
        Device.dev_eui == dev_eui,
        center_model.Center.company_id.in_(allowed_company_ids)
    ).first()

    if not device_pg:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado o sin permisos")

    price_from_db = device_pg.center.price_kwh if device_pg.center else 250.0

    end_time_utc = datetime.datetime.now(pytz.utc)
    start_time_daily_utc = end_time_utc - datetime.timedelta(days=days)

    # === DAILY CONSUMPTION ===
    pipeline_daily = [
        {"$match": {
            "deviceInfo.devEui": dev_eui,
            "time": {"$gte": start_time_daily_utc, "$lte": end_time_utc},
            "object.agg_activeEnergy": {"$exists": True}
        }},
        {"$project": {
            "time": "$time",
            "energy": "$object.agg_activeEnergy",
            "date_chile": {"$dateToString": {
                "format": "%Y-%m-%d", "date": "$time", "timezone": "America/Santiago"
            }}
        }},
        {"$sort": {"time": 1}},
        {"$group": {"_id": "$date_chile", "readings": {"$push": "$energy"}}},
        {"$sort": {"_id": 1}}
    ]

    cursor_daily = mongo_collection.aggregate(pipeline_daily)
    daily_results = await cursor_daily.to_list(length=None)

    daily_consumption_list = []
    total_consumption_kwh_30days = 0

    for doc in daily_results:
        readings_list = doc.get("readings", [])
        if len(readings_list) < 2:
            continue

        # ✅ Simple resta entre el último y el primero
        start_reading = readings_list[0]
        end_reading = readings_list[-1]
        delta_wh = end_reading - start_reading
        delta_wh = max(delta_wh, 0)  # evitar negativos por reinicio

        consumption_kwh = delta_wh / 1000.0
        date_obj = datetime.datetime.strptime(doc["_id"], "%Y-%m-%d")
        date_str = date_obj.strftime("%d-%m")

        daily_consumption_list.append(DailyConsumptionPoint(
            date=date_str,
            consumption=round(consumption_kwh, 2)
        ))
        total_consumption_kwh_30days += consumption_kwh

    avg_kwh_30days = total_consumption_kwh_30days / len(daily_consumption_list) if daily_consumption_list else 0

    # === MONTHLY CONSUMPTION ===
    start_time_monthly_utc = end_time_utc - datetime.timedelta(days=365)
    pipeline_monthly = [
        {"$match": {
            "deviceInfo.devEui": dev_eui,
            "time": {"$gte": start_time_monthly_utc, "$lte": end_time_utc},
            "object.agg_activeEnergy": {"$exists": True}
        }},
        {"$project": {
            "time": "$time",
            "energy": "$object.agg_activeEnergy",
            "month_chile": {"$dateToString": {
                "format": "%Y-%m", "date": "$time", "timezone": "America/Santiago"
            }}
        }},
        {"$sort": {"time": 1}},
        {"$group": {"_id": "$month_chile", "readings": {"$push": "$energy"}}},
        {"$sort": {"_id": 1}}
    ]

    cursor_monthly = mongo_collection.aggregate(pipeline_monthly)
    monthly_results = await cursor_monthly.to_list(length=None)

    monthly_consumption_list = []
    month_abbr_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    for doc in monthly_results:
        readings_list = doc.get("readings", [])
        if len(readings_list) < 2:
            continue

        # ✅ Simple resta entre el último y el primero
        start_reading = readings_list[0]
        end_reading = readings_list[-1]
        delta_wh = end_reading - start_reading
        delta_wh = max(delta_wh, 0)

        consumption_kwh = delta_wh / 1000.0
        date_obj = datetime.datetime.strptime(doc["_id"], "%Y-%m")
        month_name_str = month_abbr_es.get(date_obj.month, "??")

        monthly_consumption_list.append(MonthlyConsumptionPoint(
            date=doc["_id"],
            month_name=f"{month_name_str} {date_obj.year}",
            consumption=round(consumption_kwh, 2)
        ))

    # === FINAL RESPONSE ===
    device_info_data = {
        "deviceName": device_pg.name,
        "devEui": device_pg.dev_eui,
        "location": f"Centro: {device_pg.center_id}",
        "applicationName": "N/A",
        "deviceProfileName": "N/A"
    }

    return DeviceDetailsResponse(
        deviceInfo=DeviceInfo(**device_info_data),
        price_kwh=price_from_db,
        dailyConsumption=daily_consumption_list,
        totalConsumptionLast30Days=round(total_consumption_kwh_30days, 2),
        avgDailyConsumption=round(avg_kwh_30days, 2),
        monthlyConsumption=monthly_consumption_list
    )


@router.put(
    "/price/{dev_eui}",
    summary="Actualiza el precio de kWh del centro asociado a un dispositivo"
)
async def update_center_price_by_device(
    dev_eui: str,
    price_data: CenterPriceUpdate,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_active_user)
):
    """
    Este endpoint busca un dispositivo por su EUI, encuentra el
    centro al que pertenece, y actualiza el 'price_kwh' de ESE centro.
    """
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
    
    if not device_pg.center:
         raise HTTPException(status_code=404, detail="Dispositivo no está asociado a ningún centro")

    try:
        center_to_update = device_pg.center
        center_to_update.price_kwh = price_data.price_kwh
        
        db.add(center_to_update)
        db.commit()
        db.refresh(center_to_update)
        
        return {"message": "Precio actualizado correctamente", "new_price": center_to_update.price_kwh}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar la base de datos: {e}")