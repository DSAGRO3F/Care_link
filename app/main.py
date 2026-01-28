"""
CareLink - Application principale FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.session.tenant_context import TenantContextMiddleware

# Créer l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="Application de gestion des soins pour les personnes âgées en perte d'autonomie",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantContextMiddleware)

# Inclure les routes API v1
app.include_router(api_router)  # ← Ajouter cette ligne


@app.get("/")
async def root():
    """Page d'accueil - Health check"""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé"""
    return {"status": "healthy"}