"""Aplicación principal de FastAPI para el monitoreo de CBD."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import eots, tipo_dia, franjas, cbd_data, performance, performance_detail, monthly_performance, verify_290, reports, auth, notify
from config.settings import settings

# Crear instancia de FastAPI
app = FastAPI(
    title="CBD Monitor API",
    description="API para monitorear Control de Buses Distintos (CBD)",
    version="1.0.0"
)

# CORS: con allow_credentials=True no se puede usar "*"; hay que listar orígenes
_cors_origins = [
    "https://sistemas.mopc.gov.py",
    "http://sistemas.mopc.gov.py",
    "https://sistemas.mopc.gov.py/cbd_monitor",
    "http://sistemas.mopc.gov.py/cbd_monitor",
    "https://sistemas.mopc.gov.py/cbd_monitor/",
    "http://sistemas.mopc.gov.py/cbd_monitor/",
    "http://cbd-monitor-frontend:80",
    "http://cbd-monitor-frontend:8080",
    "http://172.16.222.222:8080",
    "http://172.16.222.222:5001",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5001",
    "http://127.0.0.1:8080",
]

if os.getenv("CORS_ORIGINS"):
    _cors_origins.extend(o.strip() for o in os.getenv("CORS_ORIGINS").split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_details = traceback.format_exc()
    print(f"ERROR GLOBAL: {error_details}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "exception": str(exc)},
    )

# Incluir routers de cada módulo
app.include_router(auth.router)
app.include_router(notify.router)
app.include_router(eots.router)
app.include_router(tipo_dia.router)
app.include_router(franjas.router)
app.include_router(cbd_data.router)
app.include_router(performance.router)
app.include_router(performance_detail.router)
app.include_router(monthly_performance.router)
app.include_router(verify_290.router)
app.include_router(reports.router)

@app.get("/")
async def root():
    """Endpoint raíz de bienvenida."""
    return {
        "message": "Bienvenido a la API de CBD Monitor",
        "version": "1.0.0",
        "endpoints": {
            "eots": "/api/eots",
            "tipo_dia": "/api/tipo-dia/{fecha}",
            "franjas": "/api/franjas/{id_tipo_dia}",
            "cbd_data": "/api/cbd-data",
            "monthly_performance": "/api/monthly-performance",
            "verify_290": "/api/verify-290"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud de la API."""
    return {"status": "healthy", "service": "cbd-monitor-api"}

if __name__ == "__main__":
    import uvicorn
    
    # Ejecutar servidor
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True  # Activar recarga automática en desarrollo
    )
