from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date

class MonthlyReportRequest(BaseModel):
    id_eot_vmt_hex: str
    fecha_referencia: date

class FranjaInfo(BaseModel):
    denominacion: str
    hora_inicio: Optional[str]
    hora_fin: Optional[str]
    cbd_minimo: Optional[float]

class DiaData(BaseModel):
    franjas: Dict[str, Dict[str, Any]]
    ifo_diario: Optional[float]

class TipoDiaReport(BaseModel):
    nombre: str
    franjas: Dict[str, FranjaInfo]
    dias: Dict[str, DiaData]

class MonthlyReportResponse(BaseModel):
    tipos_dia: Dict[int, TipoDiaReport]
    ifo_mes: float
    total_franjas: int
    total_dias: int

class SystemIFOResponse(BaseModel):
    ifo_sistema_mes_anterior: float
    anio: int
    mes: int

class ParametersIFOResponse(BaseModel):
    resumen: str
    parametros: List[Dict[str, Any]]

class EOTMonthlyIFO(BaseModel):
    """IFO Mensual de una EOT individual"""
    id_eot_vmt_hex: str
    eot_nombre: str
    ifo_mensual: float  # Porcentaje (0-100+)
    ifo_mensual_topeado: float  # Porcentaje topeado a 110% (Res 120/2025)
    dias_validos: int  # Cantidad de días con datos válidos

class SystemIFOBreakdownResponse(BaseModel):
    """Desglose completo del IFO Sistema para un mes"""
    year: int
    month: int
    ifo_sistema: float  # Promedio de todas las EOTs
    ifo_sistema_topeado: float  # Promedio topeado
    total_eots: int  # Cantidad de EOTs con datos
    eots: List[EOTMonthlyIFO]  # Detalle por EOT
    umbral_obligatorio_mes_siguiente: float  # Calculado para el mes n+1
    dias_excluidos: Dict[str, List[str]]  # Días excluidos por tipo
