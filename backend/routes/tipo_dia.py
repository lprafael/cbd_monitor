"""Rutas para manejar operaciones relacionadas con tipos de día."""

from fastapi import APIRouter, HTTPException, Depends
from datetime import date, datetime
from models.schemas import TipoDiaResponse
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/tipo-dia", tags=["Tipo de Día"])

@router.get("/{fecha}", response_model=TipoDiaResponse)
async def get_tipo_dia(fecha: str, db: DatabaseConnection = Depends(get_db_connection)):
    """
    Determinar el tipo de día basado en una fecha.
    
    Lógica:
    - Lunes a Viernes: id_tipo_dia = 5 (LABORAL)
    - Sábado: id_tipo_dia = 6 (SABADO)
    - Domingo: id_tipo_dia = 7 (NO LABORAL)
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD
    
    Returns:
        TipoDiaResponse: Información del tipo de día
    """
    try:
        # Convertir string a objeto date
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        
        # Obtener el día de la semana (0=Lunes, 6=Domingo)
        dia_semana = fecha_obj.weekday()
        
        # Determinar el id_tipo_dia según el día de la semana
        if dia_semana >= 0 and dia_semana <= 4:  # Lunes a Viernes
            id_tipo_dia = 5
            nombre_tipo_dia = "LABORAL"
            descripcion = "Día laboral (Lunes a Viernes)"
        elif dia_semana == 5:  # Sábado
            id_tipo_dia = 6
            nombre_tipo_dia = "SABADO"
            descripcion = "Sábado"
        else:  # Domingo
            id_tipo_dia = 7
            nombre_tipo_dia = "NO LABORAL"
            descripcion = "Domingos y Feriados"
        
        # Opcionalmente, verificar contra la base de datos
        cursor = db.get_cursor()
        query = """
            SELECT 
                id_tipo_dia,
                codigo,
                descripcion
            FROM control_metricas.tipo_dia
            WHERE id_tipo_dia = %s
        """
        cursor.execute(query, (id_tipo_dia,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            nombre_tipo_dia = result['codigo']
            descripcion = result['descripcion']
        
        return TipoDiaResponse(
            fecha=fecha_obj,
            id_tipo_dia=id_tipo_dia,
            nombre_tipo_dia=nombre_tipo_dia,
            descripcion=descripcion
        )
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al determinar tipo de día: {str(e)}"
        )
