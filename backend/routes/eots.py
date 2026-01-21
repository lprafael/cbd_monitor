"""Rutas para manejar operaciones relacionadas con EOTs (Empresas Operadoras de Transporte)."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models.schemas import EOT
from database.connection import DatabaseConnection, get_db_connection

router = APIRouter(prefix="/api/eots", tags=["EOTs"])

@router.get("", response_model=List[EOT])
async def get_eots(db: DatabaseConnection = Depends(get_db_connection)):
    """
    Obtener lista de todas las Empresas Operadoras de Transporte (EOTs).
    
    Returns:
        List[EOT]: Lista de EOTs disponibles.
    """
    try:
        cursor = db.get_cursor()
        
        # Query para obtener EOTs desde la tabla public.eots
        query = """
            SELECT 
                e.cod_catalogo,
                e.eot_nombre,
                e.id_eot_vmt_hex,
                g.gre_nombre,
                e.gre_id
            FROM public.eots e
            LEFT JOIN public.gremios g ON e.gre_id = g.gre_id
            WHERE e.permisionario IS TRUE
            AND e.cod_catalogo NOT IN (75)
            ORDER BY e.eot_nombre
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convertir resultados a lista de diccionarios
        eots = [dict(row) for row in results]
        
        cursor.close()
        
        return eots
        
    except Exception as e:
        # Imprimir el error en la consola para depuración
        print(f"Error en get_eots: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener EOTs: {str(e)}"
        )