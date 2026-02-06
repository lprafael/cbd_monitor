"""
Prefect flow para ejecutar calcular_ifo.py --notificacion (Res 120/2025).
Programado para correr todos los días a las 8:00 AM (Prefect 3: flow.serve con schedule).

Uso en el servidor:
  export PREFECT_API_URL=http://172.16.222.222:4201/api
  cd /home/user/cbd_monitor/res_120
  python flow_calcular_ifo.py   # registra el deployment con cron 8:00 y queda sirviendo (worker)
"""

import os
import subprocess
import sys
from pathlib import Path

from prefect import flow
from prefect.tasks import task

# Directorio donde está este script (res_120); el servidor usa /home/user/cbd_monitor/res_120
SCRIPT_DIR = Path(__file__).resolve().parent
CALCULAR_IFO = SCRIPT_DIR / "calcular_ifo.py"
# URL del backend en el servidor (no usar placeholder "TU_IP")
DEFAULT_CBD_API_URL = "http://172.16.222.222:5001"


def _get_cbd_api_url():
    """URL del backend: env CBD_API_URL o default. Si env tiene placeholder (TU_IP, etc.), usa default."""
    url = os.environ.get("CBD_API_URL") or DEFAULT_CBD_API_URL
    if "TU_IP" in url or "TU_HOST" in url or url.startswith("http://TU_"):
        return DEFAULT_CBD_API_URL
    return url


def _load_env_file(path: Path) -> dict:
    """Lee un .env y devuelve dict KEY=VALUE (sin export, sin comentarios)."""
    out = {}
    if not path.exists():
        return out
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def _build_subprocess_env():
    """Env para el subprocess: CBD_API_URL + DB_* y EMAIL_* desde backend/.env o res_120/.env."""
    env = os.environ.copy()
    env["CBD_API_URL"] = _get_cbd_api_url()
    for env_file in (SCRIPT_DIR.parent / "backend" / ".env", SCRIPT_DIR / ".env"):
        if not env_file.exists():
            continue
        for k, v in _load_env_file(env_file).items():
            if k and v and k.startswith(("DB_", "EMAIL_", "CBD_")):
                env[k] = v
    return env


@task(name="ejecutar-calcular-ifo")
def ejecutar_calcular_ifo_notificacion():
    """Ejecuta python calcular_ifo.py --notificacion desde res_120 (D-1 por defecto)."""
    env = _build_subprocess_env()

    cmd = [sys.executable, str(CALCULAR_IFO), "--notificacion"]
    result = subprocess.run(
        cmd,
        cwd=str(SCRIPT_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"calcular_ifo.py falló (exit {result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


@flow(name="Calcular IFO con notificación", log_prints=True)
def flow_calcular_ifo_notificacion():
    """Flow Prefect: cálculo IFO Res 120 + notificaciones a empresas (día anterior)."""
    return ejecutar_calcular_ifo_notificacion()


if __name__ == "__main__":
    # Prefect 3: serve() registra el deployment con schedule y queda escuchando runs
    try:
        from prefect.schedules import Cron
        schedule = Cron("0 8 * * *", timezone="America/Asuncion")
    except ImportError:
        from prefect.server.schemas.schedules import CronSchedule
        schedule = CronSchedule(cron="0 8 * * *", timezone="America/Asuncion")

    flow_calcular_ifo_notificacion.serve(
        name="calcular-ifo-diario",
        schedule=schedule,
        tags=["res120", "ifo", "notificacion"],
    )
