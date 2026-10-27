"""
Prefect flow para ejecutar servicios_diariosv3.py.
Permite ejecutar el procesamiento diario o programarlo como deployment / servicio en Prefect.

Uso:
  python flow_servicios_diarios.py               # Ejecuta o sirve el flow en Prefect
  python flow_servicios_diarios.py 2026-01-14    # Ejecuta para una fecha específica
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

from prefect import flow
from servicios_diariosv3 import run_servicios_diarios

@flow(name="Servicios Diarios Flow Runner", log_prints=True)
def flow_servicios_diarios_runner(fecha: str = None, fecha_hasta: str = None):
    """Flow Prefect para procesar servicios diarios."""
    run_servicios_diarios(fecha, fecha_hasta)

if __name__ == "__main__":
    arg_fecha = sys.argv[1] if len(sys.argv) > 1 else None
    arg_fecha_hasta = sys.argv[2] if len(sys.argv) > 2 else None

    # Si se pasan argumentos de fecha, ejecutar directamente
    if arg_fecha:
        flow_servicios_diarios_runner(arg_fecha, arg_fecha_hasta)
    else:
        # Por defecto, servir con schedule diario a las 05:00 AM si Prefect está activo
        try:
            from prefect.schedules import Cron
            schedule = Cron("0 5 * * *", timezone="America/Asuncion")
        except ImportError:
            try:
                from prefect.server.schemas.schedules import CronSchedule
                schedule = CronSchedule(cron="0 5 * * *", timezone="America/Asuncion")
            except Exception:
                schedule = None

        if schedule is not None:
            flow_servicios_diarios_runner.serve(
                name="servicios-diarios-diario",
                schedule=schedule,
                tags=["servicios_diarios", "vmt", "res120"],
            )
        else:
            flow_servicios_diarios_runner()
