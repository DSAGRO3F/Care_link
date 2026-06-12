# app/api/v1/dependencies_rls.py
"""
Dépendance RLS centralisée (option B — DT-RLS).

Point d'application UNIQUE du contexte RLS PostgreSQL, destiné à être monté
app-level sur le groupe de routeurs *tenant-scoped* (cf. S2). Là où,
historiquement, chaque route devait « penser » à appeler get_current_tenant_id
pour re-tamponner la session après l'authentification, cette dépendance pose
tenant_id + user_id + flag super-admin en un seul endroit, APRÈS
get_current_user, sur la session que la route utilise réellement.

Garantie d'ordre : le cache de dépendances FastAPI assure que le `db` injecté
ici est la MÊME instance de Session que celle injectée dans la route → le
contexte est posé sur la bonne session, après l'auth, quel que soit l'ordre
des paramètres de la route. C'est précisément ce que l'ancien mécanisme,
dépendant de l'ordre des paramètres, ne garantissait pas (dette DT-RLS).

⚠️ Ce module n'est PAS encore monté : S1 = création isolée. Le montage
app-level intervient en S2 (router.py).

Réf. : plan_DT_RLS_11_06_2026.md (verrou B1) · audit_S0_DT_RLS_12_06_2026.md §6.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.auth.user_auth import get_current_user
from app.database import get_db
from app.database.session_rls import configure_tenant_context
from app.models.user.user import User


def bind_rls_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Applique le contexte RLS (tenant_id + user_id) sur la session de la requête.

    Dépendance à effet de bord, sans valeur de retour : destinée à être montée
    au niveau du groupe de routeurs tenant-scoped (S2), pas appelée par valeur.

    configure_tenant_context positionne les variables de session PostgreSQL
    (app.current_tenant_id, app.current_user_id, app.is_super_admin) ET mémorise
    le contexte dans db.info["rls_context"] pour ré-application automatique par
    le listener after_begin à chaque nouvelle transaction.

    Note : aucun garde 403 « non rattaché à un tenant » ici (conforme au verrou
    B1) — si tenant_id est None, configure_tenant_context pose '' → RLS aveugle
    fail-closed. Le garde 403 reste porté par get_current_tenant_id (inchangé
    en S1, réduit à pur fournisseur de valeur en S3).

    Args:
        current_user: utilisateur authentifié (injecté APRÈS résolution du JWT).
        db: session RLS de la requête (même instance que celle de la route,
            garantie par le cache de dépendances FastAPI).
    """
    configure_tenant_context(db, current_user.tenant_id, current_user.id, False)
