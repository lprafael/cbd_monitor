"""Modelos Pydantic para el módulo de desempeño mensual."""

from pydantic import BaseModel
from typing import List

class IFODiario(BaseModel):
    """Modelo para IFO diario en el desempeño mensual."""
    fecha: str
    ifo: float

class MonthlyPerformanceRequest(BaseModel):
    """Payload para solicitud de desempeño mensual."""
    eot_id: int
    year: int
    month: int

class MonthlyPerformanceResult(BaseModel):
    """Resultado del cálculo de desempeño mensual."""
    month: int
    year: int
    eot_nombre: str
    ifo_mensual_eot: float
    ifo_sistema_anterior: float
    umbral_teorico: float
    factor_ajuste: float
    umbral_aplicable: float
    infraccion: bool
    sancion: str
    ifo_diarios: List[IFODiario]

    class Config:
        from_attributes = True
