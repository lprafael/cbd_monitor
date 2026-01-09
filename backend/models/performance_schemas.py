"""Modelos Pydantic para el módulo de desempeño diario."""

from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class PerformanceResult(BaseModel):
    """Resultados detallados por franja para un EOT."""
    id_franja: int
    denominacion_franja: str
    
    # Métricas CBD
    cbd_obs_promedio: float
    cbd_minimo_franja_exigido: float
    cbd_cumplimiento_franja_indice: float
    cbd_estado_cumplimiento: str
    origen_cbd_final: str
    
    # Métricas IFO
    b_dist_ajustado: float
    ifo_franja_calculado: float
    ifo_minimo_exigido: float
    ifo_estado_cumplimiento: str
    
    ajuste_aplicado: str

    class Config:
        from_attributes = True

class EOTPerformance(BaseModel):
    """Desempeño diario agrupado por EOT."""
    eot_id: int
    eot_nombre: str
    gre_nombre: Optional[str] = None
    resultados_franjas: List[PerformanceResult]

class PerformanceResponse(BaseModel):
    """Respuesta general del endpoint de desempeño."""
    fecha_analisis: date
    tipo_dia: str
    resultados_eots: List[EOTPerformance]

class PerformanceRequest(BaseModel):
    """Payload para solicitud de desempeño."""
    fecha: date
    eot_ids: List[int]

class IFOHistoricoItem(BaseModel):
    """Item individual para guardar en ifo_historico."""
    id_eot_vmt_hex: str
    fecha: date
    id_franja: int
    ifo: float
    ifo_minimo: float
    cbd_indice: Optional[float] = None
    cbd_cantidad: Optional[int] = None

class SaveIFORequest(BaseModel):
    """Payload para guardar resultados de IFO en historico."""
    resultados: List[IFOHistoricoItem]

class SaveIFOResponse(BaseModel):
    """Respuesta al guardar resultados de IFO."""
    guardados: int
    actualizados: int
    total: int