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
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.session.tenant_context import (
    get_current_tenant_id,
    get_current_user_id,
    get_is_super_admin,
)
from app.database.session import SessionLocal


# Message d'erreur réutilisé
_DB_UNAVAILABLE_DETAIL = (
    "Base de données indisponible. "
    "Vérifiez que PostgreSQL est démarré et accessible sur le port configuré."
)


def configure_tenant_context(
    db: Session,
    tenant_id: int | None,
    user_id: int | None = None,
    is_super_admin: bool = False,
) -> None:
    """
    Configure les variables de session PostgreSQL pour RLS.

    Ces variables sont lues par les fonctions PostgreSQL:
    - get_current_tenant_id()
    - get_current_user_id()  🆕 B40-J1 (RLS atypique notifications/family_referent_links)
    - is_super_admin()

    Le contexte est également stocké dans `db.info["rls_context"]` afin que
    l'event listener `after_begin` (cf. bas du module) puisse le ré-appliquer
    automatiquement à chaque nouvelle transaction. Ceci protège contre la
    perte de contexte après un commit() suivi d'un nouvel accès DB sur la
    même session, lorsque le pool de connexions peut servir une connexion
    différente sur laquelle les variables n'ont jamais été positionnées.

    Args:
        db: Session SQLAlchemy
        tenant_id: ID du tenant courant (None = pas de tenant)
        user_id: 🆕 B40-J1 — ID de l'utilisateur courant (None = anonyme/système).
                 Utilisé par les policies RLS atypiques sur notifications
                 (RLS par recipient_user_id) et family_referent_links
                 (SELECT en double policy : par user_id OU par tenant_id).
        is_super_admin: Si True, bypass le RLS
    """
    # Stocker le contexte dans session.info pour ré-application automatique
    # par le listener after_begin à chaque nouvelle transaction.
    db.info["rls_context"] = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "is_super_admin": is_super_admin,
    }

    # Application immédiate (la transaction courante a déjà commencé,
    # le listener after_begin ne sera invoqué que pour les suivantes)
    _apply_rls_context(db, tenant_id, user_id, is_super_admin)


def _apply_rls_context(
    db: Session,
    tenant_id: int | None,
    user_id: int | None,
    is_super_admin: bool,
) -> None:
    """
    Applique effectivement les SET PostgreSQL pour le contexte RLS.

    Helper interne utilisé à la fois par configure_tenant_context()
    (application initiale) et par le listener after_begin (ré-application
    après chaque commit / nouvelle transaction).
    """
    # Définir le tenant_id dans la session PostgreSQL
    if tenant_id is not None:
        db.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
    else:
        db.execute(text("SET app.current_tenant_id = ''"))

    # 🆕 B40-J1 — Définir le user_id pour les policies RLS atypiques
    if user_id is not None:
        db.execute(text(f"SET app.current_user_id = '{user_id}'"))
    else:
        db.execute(text("SET app.current_user_id = ''"))

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
        user_id = get_current_user_id()  # 🆕 B40-J1
        super_admin = get_is_super_admin()

        # Configurer le contexte PostgreSQL pour RLS
        configure_tenant_context(db, tenant_id, user_id, super_admin)

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


# =============================================================================
# EVENT LISTENER : ré-application automatique du contexte RLS
# =============================================================================
#
# Bug historique (12/04/2026) : configure_tenant_context() exécute des `SET`
# (non-LOCAL) qui sont attachés à la connexion Postgres courante. Après un
# `commit()` SQLAlchemy, la transaction suivante ouverte par la même session
# peut récupérer une connexion différente du pool — sur laquelle ces variables
# n'ont jamais été positionnées. Résultat : RLS aveugle le SELECT post-commit
# et SQLAlchemy lève "Could not refresh instance".
#
# Correctif : à chaque BEGIN d'une nouvelle transaction sur n'importe quelle
# Session, on relit le contexte stocké dans `session.info["rls_context"]`
# (positionné par configure_tenant_context) et on ré-exécute les `SET`. Le
# listener bénéficie aux 4 factories du module (get_db, get_db_no_rls,
# get_db_for_tenant, get_db_for_super_admin) sans modification supplémentaire.
#
# NB : il s'agit d'un filet de sécurité défensif. Le correctif idiomatique
# complémentaire est d'éviter les `commit() + refresh()` intermédiaires dans
# les services en privilégiant `flush()` (commit final délégué à get_db_*).


@event.listens_for(Session, "after_begin")
def _reapply_rls_context_after_begin(session, transaction, connection):
    """
    Ré-applique les variables RLS PostgreSQL à chaque nouvelle transaction.

    Lit le contexte mémorisé dans `session.info["rls_context"]` (positionné
    par configure_tenant_context lors de l'ouverture de la session) et
    réémet les `SET` correspondants sur la connexion qui vient d'être
    associée à la nouvelle transaction.

    Si aucun contexte n'a été positionné (sessions hors RLS, scripts adhoc,
    tests), le listener ne fait rien.
    """
    rls_context = session.info.get("rls_context")
    if rls_context is None:
        return

    tenant_id = rls_context.get("tenant_id")
    user_id = rls_context.get("user_id")  # 🆕 B40-J1
    is_super_admin = rls_context.get("is_super_admin", False)

    if tenant_id is not None:
        connection.exec_driver_sql(f"SET app.current_tenant_id = '{tenant_id}'")
    else:
        connection.exec_driver_sql("SET app.current_tenant_id = ''")

    # 🆕 B40-J1 — Ré-application user_id pour RLS atypique notifications/family
    if user_id is not None:
        connection.exec_driver_sql(f"SET app.current_user_id = '{user_id}'")
    else:
        connection.exec_driver_sql("SET app.current_user_id = ''")

    connection.exec_driver_sql(f"SET app.is_super_admin = '{str(is_super_admin).lower()}'")
