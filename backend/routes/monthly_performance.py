"""Rutas para obtener resultados de desempeño mensual (IFO mensual)."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/monthly-performance", tags=["Monthly Performance"])


class MonthlyPerformanceRequest(BaseModel):
    eot_id: int
    month: int
    year: int


class IFODiarioItem(BaseModel):
    fecha: str
    ifo: float


class MonthlyPerformanceResponse(BaseModel):
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
    ifo_diarios: List[IFODiarioItem]


@router.post("/", response_model=MonthlyPerformanceResponse)
async def get_monthly_performance(
    request: MonthlyPerformanceRequest,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtiene el desempeño mensual de IFO para un EOT.
    
    Calcula:
    - IFO mensual del EOT (promedio de IFO diarios del mes)
    - IFO del sistema del mes anterior
    - Umbral teórico (95% del IFO sistema anterior)
    - Factor de ajuste según el mes
    - Umbral aplicable
    - Si hay infracción y la sanción correspondiente
    """
    try:
        cursor = db.get_cursor()
        
        # Validar mes y año
        if not (1 <= request.month <= 12):
            raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")
        
        if request.year < 2020 or request.year > 2100:
            raise HTTPException(status_code=400, detail="Año inválido")
        
        # Obtener información del EOT
        cursor.execute("""
            SELECT cod_catalogo, nombre, id_eot_vmt_hex
            FROM public.eots
            WHERE cod_catalogo = %s
        """, (request.eot_id,))
        
        eot_info = cursor.fetchone()
        if not eot_info:
            raise HTTPException(status_code=404, detail=f"EOT con ID {request.eot_id} no encontrada")
        
        eot_nombre = eot_info['nombre']
        id_eot_vmt_hex = eot_info.get('id_eot_vmt_hex')
        
        # Calcular rango de fechas del mes
        primer_dia = date(request.year, request.month, 1)
        if request.month == 12:
            ultimo_dia = date(request.year + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(request.year, request.month + 1, 1) - timedelta(days=1)
        
        # Obtener IFO diarios del mes desde ifo_historico
        ifo_diarios = []
        if id_eot_vmt_hex:
            cursor.execute("""
                SELECT fecha, AVG(ifo) as ifo_promedio
                FROM control_metricas.ifo_historico
                WHERE id_eot_vmt_hex = %s
                  AND fecha >= %s
                  AND fecha <= %s
                GROUP BY fecha
                ORDER BY fecha
            """, (id_eot_vmt_hex, primer_dia, ultimo_dia))
            
            resultados = cursor.fetchall()
            for row in resultados:
                ifo_diarios.append(IFODiarioItem(
                    fecha=row['fecha'].strftime('%Y-%m-%d'),
                    ifo=float(row['ifo_promedio']) * 100 if row['ifo_promedio'] else 0.0
                ))
        
        # Calcular IFO mensual del EOT (promedio de IFO diarios)
        ifo_mensual_eot = 0.0
        if ifo_diarios:
            ifo_mensual_eot = sum(d.ifo for d in ifo_diarios) / len(ifo_diarios)
        
        # Obtener IFO del sistema del mes anterior
        mes_anterior = request.month - 1
        año_anterior = request.year
        if mes_anterior == 0:
            mes_anterior = 12
            año_anterior -= 1
        
        primer_dia_anterior = date(año_anterior, mes_anterior, 1)
        if mes_anterior == 12:
            ultimo_dia_anterior = date(año_anterior + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia_anterior = date(año_anterior, mes_anterior + 1, 1) - timedelta(days=1)
        
        # Calcular IFO sistema del mes anterior (promedio de todos los EOTs)
        cursor.execute("""
            SELECT AVG(ifo) as ifo_sistema
            FROM control_metricas.ifo_historico
            WHERE fecha >= %s
              AND fecha <= %s
        """, (primer_dia_anterior, ultimo_dia_anterior))
        
        resultado_sistema = cursor.fetchone()
        ifo_sistema_anterior = float(resultado_sistema['ifo_sistema']) * 100 if resultado_sistema and resultado_sistema['ifo_sistema'] else 100.0
        
        # Umbral teórico = 95% del IFO sistema anterior
        umbral_teorico = ifo_sistema_anterior * 0.95
        
        # Factor de ajuste según el mes (según Resolución 120/2025)
        factor_ajuste = 0.0
        if request.month == 1:  # Enero
            factor_ajuste = 0.80
        elif request.month == 12:  # Diciembre
            factor_ajuste = 0.80
        else:
            factor_ajuste = 0.0  # Sin ajuste para otros meses
        
        # Umbral aplicable = umbral teórico * factor de ajuste (si hay factor)
        # El factor de ajuste es una reducción (0.80 = 80% del umbral teórico)
        umbral_aplicable = umbral_teorico * (1.0 - factor_ajuste) if factor_ajuste > 0 else umbral_teorico
        
        # Determinar si hay infracción
        infraccion = ifo_mensual_eot < umbral_aplicable
        
        # Determinar sanción
        if infraccion:
            diferencia = umbral_aplicable - ifo_mensual_eot
            if diferencia >= 10:
                sancion = "Infracción Grave - Sanción según normativa vigente"
            elif diferencia >= 5:
                sancion = "Infracción Intermedia - Sanción según normativa vigente"
            else:
                sancion = "Infracción Leve - Sanción según normativa vigente"
        else:
            sancion = "Cumple con el desempeño requerido"
        
        return MonthlyPerformanceResponse(
            month=request.month,
            year=request.year,
            eot_nombre=eot_nombre,
            ifo_mensual_eot=ifo_mensual_eot,
            ifo_sistema_anterior=ifo_sistema_anterior,
            umbral_teorico=umbral_teorico,
            factor_ajuste=factor_ajuste * 100,  # Convertir a porcentaje
            umbral_aplicable=umbral_aplicable,
            infraccion=infraccion,
            sancion=sancion,
            ifo_diarios=ifo_diarios
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular desempeño mensual: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
