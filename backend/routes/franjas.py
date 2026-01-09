"""Rutas para manejar operaciones relacionadas con franjas operativas."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models.schemas import FranjaOperativa
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/franjas", tags=["Franjas Operativas"])

@router.get("/{id_tipo_dia}", response_model=List[FranjaOperativa])
async def get_franjas_operativas(
    id_tipo_dia: int,
    fecha: str = None,
    db: DatabaseConnection = Depends(get_db_connection)
):
    """
    Obtener franjas operativas para un tipo de día específico y fecha (opcional).
    Si no se envía fecha, se usa la fecha actual.
    """
    if not fecha:
        from datetime import date
        target_fecha = date.today()
    else:
        from datetime import datetime
        target_fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    try:
        cursor = db.get_cursor()
        
        # Query para obtener franjas operativas activas
        query = """
            SELECT 
                id_franja,
                denominacion,
                hora_inicio,
                hora_fin,
                id_tipo_dia,
                inicio_vigencia,
                fin_vigencia,
                activo
            FROM control_metricas.franjas_operativas
            WHERE id_tipo_dia = %s
                AND (inicio_vigencia IS NULL OR inicio_vigencia <= %s)
                AND (fin_vigencia IS NULL OR fin_vigencia >= %s)
            ORDER BY hora_inicio
        """
        
        cursor.execute(query, (id_tipo_dia, target_fecha, target_fecha))
        results = cursor.fetchall()
        
        # Convertir resultados a lista de diccionarios
        franjas = [dict(row) for row in results]
        
        cursor.close()
        
        if not franjas:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron franjas operativas activas para el tipo de día {id_tipo_dia}"
            )
        
        return franjas
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener franjas operativas: {str(e)}"
        )
