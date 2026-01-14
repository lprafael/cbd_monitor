"""Aplicación principal de FastAPI para el monitoreo de CBD."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import eots, tipo_dia, franjas, cbd_data, performance, performance_detail
from config.settings import settings

# Crear instancia de FastAPI
app = FastAPI(
    title="CBD Monitor API",
    description="API para monitorear Control de Buses Distintos (CBD)",
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers de cada módulo
app.include_router(eots.router)
app.include_router(tipo_dia.router)
app.include_router(franjas.router)
app.include_router(cbd_data.router)
app.include_router(performance.router)
app.include_router(performance_detail.router)

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
            "cbd_data": "/api/cbd-data"
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
