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
    ifo_mensual_eot: float  # The calculated IFO for the EOT in the selected month
    ifo_sistema_anterior: float  # Average IFO of all EOTs in month n-1
    umbral_teorico: float  # ifo_sistema_anterior * 0.95
    factor_ajuste: float  # -0.49
    umbral_aplicable: float  # umbral_teorico - factor_ajuste
    
    # Final Result
    infraccion: bool  # True if ifo_mensual_eot < umbral_aplicable
    sancion: str  # "Infracción Gravísima (173 jornales)" if infraction else "Sin Infracción"
    
    # Details (optional, maybe for a chart?)
    ifo_diarios: List[dict]  # list of {fecha: str, ifo: float}
