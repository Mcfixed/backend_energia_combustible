from pydantic import BaseModel, Field
from app.models.device import DeviceStatus, DeviceType
from typing import Optional, List, Any
import datetime # <-- Importante

# --- Esquemas para PostgreSQL ---

class DeviceBase(BaseModel):
    name: str
    dev_eui: str = Field(..., min_length=16, max_length=16)
    status: DeviceStatus
    center_id: int 
    type: DeviceType

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[DeviceStatus] = None
    type: Optional[DeviceType] = None
    center_id: Optional[int] = None

    class Config:
        from_attributes = True

class Device(DeviceBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Schema (Para Vista 1: Tabla) ---
class DeviceDetails(BaseModel):
    """Schema para la tabla principal de sensores."""
    id: int
    name: str
    dev_eui: str
    type: DeviceType
    status: DeviceStatus
    center_id: int
    center_name: str
    company_id: int
    company_name: str
    
    class Config:
        from_attributes = True

# --- Esquemas para MongoDB ---

class MongoCombustibleData(BaseModel):
    pressure_Bar_S0: Optional[float] = None
    sensor_2_ok: Optional[bool] = None
    volume_L_S1: Optional[float] = None
    percentage_S0: Optional[float] = None
    percentage_S1: Optional[float] = None
    sensor_1_ok: Optional[bool] = None
    percentage_S2: Optional[float] = None
    pressure_Bar_S1: Optional[float] = None
    volume_L_S2: Optional[float] = None
    pressure_Bar_S2: Optional[float] = None
    volume_L_S0: Optional[float] = None
    sensor_0_ok: Optional[bool] = None
    
    class Config:
        extra = 'ignore'

class MongoEnergiaData(BaseModel):
    agg_frequency: Optional[float] = None
    phaseB_apparentPower: Optional[float] = None
    phaseA_thdI: Optional[float] = None
    agg_activePower: Optional[float] = None
    agg_voltage: Optional[float] = None
    agg_current: Optional[float] = None
    
    class Config:
        extra = 'ignore'

class MongoMeasurementData(MongoEnergiaData):
    # (Mantenido por compatibilidad)
    pass
    
# --- ESTA ES LA CLASE QUE FALTABA ---
class MongoHistoryRecord(BaseModel):
    """Un solo registro histórico de MongoDB."""
    time: datetime.datetime
    object: Any # El 'object' de Mongo

    # --- CORRECCIÓN (Problema Futuro) ---
    # Añadimos 'extra = 'ignore'' para que Pydantic no rechace
    # el campo '_id' que viene de MongoDB.
    class Config:
        extra = 'ignore'

# --- Esquema combinado (de tu endpoint get_device_with_latest_data) ---
class DeviceWithLatestData(Device):
    latest_measurement: MongoMeasurementData | MongoCombustibleData | dict | None = None