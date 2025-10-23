from pydantic import BaseModel
from app.models.device import DeviceStatus

# --- Esquemas para PostgreSQL ---

class DeviceBase(BaseModel):
    name: str
    dev_eui: str
    status: DeviceStatus
    company_id: int

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Esquemas para MongoDB ---
# Este modelo representa el campo "object" de tu JSON de MongoDB
class MongoMeasurementData(BaseModel):
    agg_activePower: float | int
    phaseA_reactiveEnergy: float | int
    phaseB_reactiveEnergy: float | int
    phaseC_voltage: float | int
    agg_voltage: float | int
    agg_activeEnergy: float | int
    phaseB_activePower: float | int
    phaseA_powerFactor: float | int
    # ... añade todos los demás campos que necesites del "object"
    agg_frequency: float | int
    
    class Config:
        extra = 'ignore' # Ignora campos del JSON que no definamos aquí

# --- Esquema combinado ---
# Este es el modelo que devolverá tu API
class DeviceWithLatestData(Device):
    latest_measurement: MongoMeasurementData | None = None