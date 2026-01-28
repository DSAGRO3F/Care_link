# app/api/v1/user/tenant_users_security.py
"""
Sécurité multi-tenant pour les utilisateurs clients (professionnels de santé).

Ce module gère :
- Extraction du tenant_id depuis le contexte utilisateur
- Vérification des accès cross-tenant
- Contexte de sécurité TenantContext pour les routes métier

Note: Pour la sécurité SuperAdmin (équipe CareLink),
voir app/api/v1/platform/super_admin_security.py
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status

from app.core.auth.user_auth import get_current_user
from app.models.user.user import User


# =============================================================================
# TENANT DEPENDENCIES (MULTI-TENANT SUPPORT)
# =============================================================================

def get_current_tenant_id(
    current_user: User = Depends(get_current_user)
) -> int:
    """
    Extrait le tenant_id principal de l'utilisateur courant.

    Raises:
        HTTPException 403: Si l'utilisateur n'est pas rattaché à un tenant
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur non rattaché à un tenant"
        )
    return current_user.tenant_id


def get_optional_tenant_id(
    current_user: User = Depends(get_current_user)
) -> Optional[int]:
    """
    Extrait le tenant_id de l'utilisateur courant (optionnel).

    Pour les super-admins qui peuvent voir tous les tenants.
    Retourne None si l'utilisateur n'a pas de tenant (super-admin).
    """
    return current_user.tenant_id


def get_active_tenant_id(
    current_user: User = Depends(get_current_user)
) -> int:
    """
    Récupère le tenant_id actif pour la requête.

    Pour l'instant, retourne simplement le tenant_id de l'utilisateur.
    Peut être étendu pour supporter le switch de tenant via header X-Tenant-Id.

    Raises:
        HTTPException 403: Si l'utilisateur n'est pas rattaché à un tenant
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur non rattaché à un tenant"
        )
    return current_user.tenant_id


class TenantContext:
    """
    Contexte multi-tenant pour les routes.

    Fournit un accès pratique au tenant_id actif et à l'utilisateur
    dans un seul objet de dépendance.

    Usage:
        @router.get("/patients")
        async def list_patients(
            ctx: TenantContext = Depends(),
            db: Session = Depends(get_db)
        ):
            query = db.query(Patient).filter(Patient.tenant_id == ctx.tenant_id)
            # ctx.user est aussi disponible
            ...
    """

    def __init__(
        self,
        current_user: User = Depends(get_current_user),
        active_tenant_id: int = Depends(get_active_tenant_id)
    ):
        self.user = current_user
        self.tenant_id = active_tenant_id
        self.user_id = current_user.id

    @property
    def is_cross_tenant(self) -> bool:
        """True si l'utilisateur accède à un tenant différent de son tenant principal."""
        return self.tenant_id != self.user.tenant_id

    def can_write(self) -> bool:
        """
        Vérifie si l'utilisateur peut écrire dans le tenant actif.

        En cross-tenant, vérifier les permissions spécifiques de l'assignment.
        """
        # Sur son tenant principal, l'utilisateur peut écrire
        if not self.is_cross_tenant:
            return True

        # En cross-tenant, vérifier les permissions de l'assignment
        for assignment in self.user.tenant_assignments:
            if assignment.tenant_id == self.tenant_id and assignment.is_valid:
                if assignment.permissions:
                    return "WRITE" in assignment.permissions or "FULL" in assignment.permissions
                # Pas de permissions spécifiques = lecture seule
                return False

        # Pas d'assignment trouvé = pas d'accès
        return False


def verify_write_permission():
    """
    Dépendance qui vérifie que l'utilisateur peut écrire dans le tenant actif.

    À utiliser sur les routes POST, PUT, PATCH, DELETE.

    Example:
        @router.post("/patients")
        async def create_patient(
            ctx: TenantContext = Depends(),
            _: None = Depends(verify_write_permission()),
            patient_data: PatientCreate,
            db: Session = Depends(get_db)
        ):
            ...
    """
    def checker(ctx: TenantContext = Depends()):
        if not ctx.can_write():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès en lecture seule sur ce tenant"
            )

    return checker


# =============================================================================
# TYPE ALIASES
# =============================================================================

CurrentTenantId = Annotated[int, Depends(get_current_tenant_id)]
ActiveTenantId = Annotated[int, Depends(get_active_tenant_id)]
OptionalTenantId = Annotated[Optional[int], Depends(get_optional_tenant_id)]
TenantCtx = Annotated[TenantContext, Depends()]