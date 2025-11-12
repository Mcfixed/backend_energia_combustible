# app/schemas/energia.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Oid(BaseModel):
    oid: str = Field(..., alias="$oid")

class DeviceInfo(BaseModel):
    deviceName: str
    devEui: str
    location: str
    applicationName: str
    deviceProfileName: str

class EnergyObject(BaseModel):
    agg_activePower: float
    phaseA_activePower: float
    phaseB_activePower: float
    phaseC_activePower: float
    agg_reactivePower: float
    phaseA_reactivePower: float
    phaseB_reactivePower: float
    phaseC_reactivePower: float
    agg_apparentPower: float
    phaseA_apparentPower: float
    phaseB_apparentPower: float
    phaseC_apparentPower: float
    agg_voltage: float
    phaseA_voltage: float
    phaseB_voltage: float
    phaseC_voltage: float
    agg_current: float
    phaseA_current: float
    phaseB_current: float
    phaseC_current: float
    agg_activeEnergy: float
    phaseA_activeEnergy: float
    phaseB_activeEnergy: float
    phaseC_activeEnergy: float
    agg_reactiveEnergy: float
    phaseA_reactiveEnergy: float
    phaseB_reactiveEnergy: float
    phaseC_reactiveEnergy: float
    agg_apparentEnergy: float
    phaseA_apparentEnergy: float
    phaseB_apparentEnergy: float
    phaseC_apparentEnergy: float
    agg_powerFactor: float
    phaseA_powerFactor: float
    phaseB_powerFactor: float
    phaseC_powerFactor: float
    agg_frequency: float
    agg_thdI: float
    phaseA_thdI: float
    phaseB_thdI: float
    phaseC_thdI: float
    phaseA_thdU: float
    phaseB_thdU: float
    phaseC_thdU: float
    model: int
    address: int
    
    class Config:
        extra = 'ignore'

class HistoricalDataPoint(BaseModel):
    time: str
    value: float

class DeviceHistoricalData(BaseModel):
    consumption: List[HistoricalDataPoint]= []
    voltage: List[HistoricalDataPoint]= []
    current: List[HistoricalDataPoint]= []
    power: List[HistoricalDataPoint]= []
    powerFactor: List[HistoricalDataPoint]= []
    frequency: List[HistoricalDataPoint]= []
    thd: List[HistoricalDataPoint]= []
    reactivePower: List[HistoricalDataPoint]= []
    apparentPower: List[HistoricalDataPoint]= []
    apparentEnergy: List[HistoricalDataPoint]= []
    reactiveEnergy: List[HistoricalDataPoint]= []
    
    power_a: List[HistoricalDataPoint] = []
    voltage_a: List[HistoricalDataPoint] = []
    current_a: List[HistoricalDataPoint] = []
    powerFactor_a: List[HistoricalDataPoint] = []
    reactivePower_a: List[HistoricalDataPoint] = []
    apparentPower_a: List[HistoricalDataPoint] = []
    thd_i_a: List[HistoricalDataPoint] = []
    thd_u_a: List[HistoricalDataPoint] = []
    apparentEnergy_a: List[HistoricalDataPoint] = []
    reactiveEnergy_a: List[HistoricalDataPoint] = []
    activeEnergy_a: List[HistoricalDataPoint] = []
    activePower_a: List[HistoricalDataPoint] = []
    reactiveEnergy_a: List[HistoricalDataPoint] = []
    
    

class DeviceAlert(BaseModel):
    id: int
    type: str
    message: str
    timestamp: str

class DeviceSummary(BaseModel):
    id: Oid = Field(..., alias="_id")
    time: str
    deviceInfo: DeviceInfo
    object: EnergyObject
    historicalData: Dict[str, DeviceHistoricalData]
    dailyConsumption: float
    alerts: List[DeviceAlert]
    final_energy_counter: float

    class Config:
        populate_by_name = True
        json_encoders = {Oid: lambda v: v.oid if isinstance(v, Oid) else str(v)}

class DailyConsumptionPoint(BaseModel):
    """Representa el consumo total de un solo día."""
    date: str
    consumption: float  
class MonthlyConsumptionPoint(BaseModel):
    """Representa el consumo total de un solo mes."""
    date: str   
    month_name: str 
    consumption: float
    
class DeviceDetailsResponse(BaseModel):
    """La respuesta completa para la vista de detalles."""
    deviceInfo: DeviceInfo
    price_kwh: float
    dailyConsumption: List[DailyConsumptionPoint]
    totalConsumptionLast30Days: float
    avgDailyConsumption: float
    
    monthlyConsumption: List[MonthlyConsumptionPoint]