from pydantic import BaseModel
from typing import List, Optional, Dict

class Verify290Request(BaseModel):
    eot_id: int
    month: int
    year: int

class FranjaResult(BaseModel):
    id_franja: int
    nombre_franja: str
    servicios_realizados: float
    sum_servicios: float # Total Raw Count
    total_horas: float    # Denominator (Days * HoursPerFranja)
    exigencia: float
    umbral: float        # e.g. 80.0
    rendimiento: float
    rendimiento_normalizado: float # Capped at 100%
    dias_contabilizados: int
    dias_lluvia: int
    proyeccion_requerida: Optional[float] = None
    dias_restantes: Optional[int] = None
    desglose_diario: Optional[List[Dict]] = None  # [{fecha, hora, servicios}, ...]
    cumple: bool
    estado: str  # "CUMPLE" / "NO CUMPLE"

class TroncalResult(BaseModel):
    nombre_troncal: str
    resultados_franjas: List[FranjaResult]

class Verify290ResultV2(BaseModel):
    month: int
    year: int
    eot_nombre: str
    detalles_troncal: List[TroncalResult]
    resumen_global: str  # Optional text summary
