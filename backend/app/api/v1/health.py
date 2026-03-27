"""
Health check endpoint.

Teste la connectivité aux services critiques (PostgreSQL, Redis)
et retourne un statut synthétique pour le monitoring et les load balancers.

🆕 Session 19/03/2026 : Remplace le healthcheck inline de router.py
   qui ne testait que la disponibilité du process Python.

Usage:
    GET /api/v1/health → 200 si tout OK, 503 si un composant est en panne

Pas d'authentification requise (endpoint public).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database.session import SessionLocal


router = APIRouter(tags=["System"])


def _check_db() -> str:
    """Teste la connexion PostgreSQL avec un SELECT 1."""
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return "ok"
        finally:
            db.close()
    except Exception as e:
        return f"error: {e.__class__.__name__}"


def _check_redis() -> str:
    """Teste la connexion Redis avec un PING."""
    try:
        from app.core.session.redis_client import get_redis

        r = get_redis()
        if r.ping():
            return "ok"
        return "error: ping failed"
    except Exception as e:
        return f"error: {e.__class__.__name__}"


@router.get(
    "/health",
    summary="Health check",
    description="""
    Vérifie que l'API et ses dépendances sont opérationnelles.

    Teste :
    - **db** : Connexion PostgreSQL (`SELECT 1`)
    - **redis** : Connexion Redis (`PING`)

    Retourne HTTP 200 si tout est OK, HTTP 503 si un composant est en panne.
    Pas d'authentification requise.
    """,
    responses={
        200: {"description": "Tous les services sont opérationnels"},
        503: {"description": "Au moins un service est en panne"},
    },
)
async def health_check():
    """
    Endpoint de santé pour les load balancers et le monitoring.
    """
    db_status = _check_db()
    redis_status = _check_redis()

    all_ok = db_status == "ok" and redis_status == "ok"

    body = {
        "status": "healthy" if all_ok else "degraded",
        "service": "carelink-api",
        "version": "1.0.0",
        "checks": {
            "db": db_status,
            "redis": redis_status,
        },
    }

    status_code = 200 if all_ok else 503
    return JSONResponse(content=body, status_code=status_code)
