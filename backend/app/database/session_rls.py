"""
Gestion des sessions de base de données avec support RLS.

Ce module fournit les dépendances FastAPI pour obtenir une session
de base de données configurée avec le contexte tenant pour RLS.

Usage:
    @router.get("/patients")
    async def get_patients(db: Session = Depends(get_db)):
        # Les requêtes sont automatiquement filtrées par tenant
        return db.query(Patient).all()

🔧 S4.2 : Gestion gracieuse OperationalError
   Si PostgreSQL est indisponible, get_db() et get_db_no_rls() lèvent
   HTTPException 503 au lieu de laisser remonter un 500 avec stacktrace.
"""

from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.session.tenant_context import (
    get_current_tenant_id,
    get_is_super_admin,
)
from app.database.session import SessionLocal


# Message d'erreur réutilisé
_DB_UNAVAILABLE_DETAIL = (
    "Base de données indisponible. "
    "Vérifiez que PostgreSQL est démarré et accessible sur le port configuré."
)


def configure_tenant_context(
    db: Session, tenant_id: int | None, is_super_admin: bool = False
) -> None:
    """
    Configure les variables de session PostgreSQL pour RLS.

    Ces variables sont lues par les fonctions PostgreSQL:
    - get_current_tenant_id()
    - is_super_admin()

    Args:
        db: Session SQLAlchemy
        tenant_id: ID du tenant courant (None = pas de tenant)
        is_super_admin: Si True, bypass le RLS
    """
    # Définir le tenant_id dans la session PostgreSQL
    if tenant_id is not None:
        db.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
    else:
        db.execute(text("SET app.current_tenant_id = ''"))

    # Définir le flag super-admin
    db.execute(text(f"SET app.is_super_admin = '{str(is_super_admin).lower()}'"))


def get_db() -> Generator[Session]:
    """
    Dépendance FastAPI pour obtenir une session DB avec contexte RLS.

    Configure automatiquement les variables PostgreSQL selon le contexte
    de la requête (tenant_id, super_admin).

    🔧 S4.2 : OperationalError (DB indisponible) → HTTPException 503

    Yields:
        Session: Session SQLAlchemy configurée avec RLS
    """
    db = SessionLocal()
    try:
        # Récupérer le contexte depuis les ContextVars
        tenant_id = get_current_tenant_id()
        super_admin = get_is_super_admin()

        # Configurer le contexte PostgreSQL pour RLS
        configure_tenant_context(db, tenant_id, super_admin)

        yield db

        # Commit si tout s'est bien passé
        db.commit()
    except OperationalError:
        # 🔧 S4.2 : PostgreSQL indisponible → 503 propre (pas de stacktrace exposée)
        db.rollback()
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL) from None
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_no_rls() -> Generator[Session]:
    """
    Session DB SANS contexte RLS (pour super-admins et tâches système).

    ⚠️ ATTENTION: Cette fonction bypass complètement le RLS.
    À utiliser uniquement pour:
    - Authentification super-admin
    - Tâches de maintenance
    - Scripts de migration

    🔧 S4.2 : OperationalError (DB indisponible) → HTTPException 503

    Yields:
        Session: Session avec bypass RLS (is_super_admin = true)
    """
    db = SessionLocal()
    try:
        # Configurer comme super-admin pour bypasser RLS
        configure_tenant_context(db, tenant_id=None, is_super_admin=True)

        yield db
        db.commit()
    except OperationalError:
        # 🔧 S4.2 : PostgreSQL indisponible → 503 propre
        db.rollback()
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE_DETAIL) from None
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_for_tenant(tenant_id: int) -> Generator[Session]:
    """
    Context manager pour obtenir une session pour un tenant spécifique.

    Utile pour les tâches de fond, workers, scripts.

    Args:
        tenant_id: ID du tenant cible

    Yields:
        Session: Session configurée pour le tenant spécifié

    Example:
        with get_db_for_tenant(tenant_id=42) as db:
            patients = db.query(Patient).all()  # Patients du tenant 42 uniquement
    """
    db = SessionLocal()
    try:
        configure_tenant_context(db, tenant_id, is_super_admin=False)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_for_super_admin() -> Generator[Session]:
    """
    Context manager pour session super-admin (bypass RLS).

    Yields:
        Session: Session avec bypass RLS complet

    Example:
        with get_db_for_super_admin() as db:
            # Accès à TOUS les tenants
            all_patients = db.query(Patient).all()
    """
    db = SessionLocal()
    try:
        configure_tenant_context(db, tenant_id=None, is_super_admin=True)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
