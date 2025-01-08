from pydantic import BaseModel
from typing import Dict, Union

class HealthStatus:
    UP = "UP"
    DOWN = "DOWN"

class HealthComponent(BaseModel):
    status: str
    details: Union[str, None] = None

class HealthResponse(BaseModel):
    status: str
    components: Dict[str, HealthComponent]