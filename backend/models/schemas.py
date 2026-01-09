"""Modelos Pydantic para las respuestas de la API."""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, time

class EOT(BaseModel):
    """Modelo para Empresa Operadora de Transporte."""
    cod_catalogo: int
    eot_nombre: str
    id_eot_vmt_hex: Optional[str] = None
    gre_nombre: Optional[str] = None
    gre_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class TipoDiaResponse(BaseModel):
    """Modelo para la respuesta del tipo de día."""
    fecha: date
    id_tipo_dia: int
    nombre_tipo_dia: str
    descripcion: str

class FranjaOperativa(BaseModel):
    """Modelo para franja operativa."""
    id_franja: int
    denominacion: str
    hora_inicio: time
    hora_fin: time
    id_tipo_dia: int
    activo: bool
    
    class Config:
        from_attributes = True

class ParametroMinimo(BaseModel):
    """Modelo para parámetros mínimos de CBD."""
    id: int
    id_tipo_dia: int
    id_franja: int
    cbd_minimo_franja: Optional[int] = None
    cbd_minimo_hora: Optional[int] = None
    vigencia_desde: Optional[date] = None
    vigencia_hasta: Optional[date] = None

class DatoCelda(BaseModel):
    """Modelo para datos de una celda en la tabla."""
    cantidad_buses: int
    cumple_parametro: bool
    parametro_minimo: Optional[int] = None

class FilaEOT(BaseModel):
    """Modelo para una fila de datos de un EOT."""
    tipo_fila: str  # "servicios_diarios" o "cbd_detalle_buses"
    datos_por_franja: Dict[str, DatoCelda]  # Key: id_franja o hora
    total: int

class DatosEOT(BaseModel):
    """Modelo para los datos completos de un EOT."""
    eot_id: int
    eot_nombre: str
    gre_nombre: Optional[str] = None
    fila_servicios: FilaEOT
    fila_cbd: FilaEOT

class CBDDataRequest(BaseModel):
    """Modelo para la solicitud de datos CBD."""
    eot_ids: List[int]
    fecha: date
    modo_visualizacion: str  # "hora" o "franja"

class CBDDataResponse(BaseModel):
    """Modelo para la respuesta completa de datos CBD."""
    fecha: date
    id_tipo_dia: int
    nombre_tipo_dia: str
    modo_visualizacion: str
    franjas_operativas: List[FranjaOperativa]
    datos_eots: List[DatosEOT]
    parametros_minimos: Optional[Dict[int, Dict[str, Any]]] = None  # Indexado por id_franja
