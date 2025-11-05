from pydantic import BaseModel
from typing import List, Optional
from .device import Device

class CenterBase(BaseModel):
    name: str
    company_id: int

class CenterCreate(CenterBase):
    pass
class CenterUpdate(BaseModel):
    name: Optional[str] = None

class Center(CenterBase):
    id: int
    
    class Config:
        from_attributes = True

class CenterWithDevices(Center):
    devices: List[Device] = []