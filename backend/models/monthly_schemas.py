from pydantic import BaseModel
from typing import List, Optional

class MonthlyPerformanceRequest(BaseModel):
    eot_id: int
    month: int
    year: int

class MonthlyPerformanceResult(BaseModel):
    month: int
    year: int
    eot_nombre: str
    
    # Calculation Metrics
    ifo_mensual_eot: float  # The calculated IFO for the EOT (not topped)
    ifo_mensual_eot_topeado: float  # The capped IFO for the EOT (max 110)
    ifo_sistema_anterior: float  # Average IFO of all EOTs in month n-1
    ifo_sistema_anterior_topeado: float  # Average of capped IFOs (max 110)
    umbral_objetivo: float  # The target IFO for this month based on new rules
    
    # Final Result
    infraccion: bool  # True if ifo_mensual_eot_topeado < umbral_objetivo
    sancion: str  # "Infracción Gravísima (173 jornales)" if infraction else "Sin Infracción"
    
    # Details (optional, maybe for a chart?)
    ifo_diarios: List[dict]  # list of {fecha: str, ifo: float}
