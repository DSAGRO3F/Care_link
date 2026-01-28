# app/api/v1/tenants/routes.py
"""
Routes CRUD pour les Tenants.

Toutes les routes sont réservées aux SuperAdmins (équipe CareLink).
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies import PaginationParams
from app.api.v1.platform.super_admin_security import (
    require_super_admin_permission,
    SuperAdminPermissions,
)
from app.database.session_rls import get_db_no_rls
from app.models.platform.platform_audit_log import PlatformAuditLog, AuditAction
from app.models.platform.super_admin import SuperAdmin
from app.models.tenants.tenant import Tenant, TenantStatus
from .schemas import (
    TenantCreate,
    TenantUpdate,
    TenantStatusUpdate,
    TenantResponse,
    TenantSummary,
    TenantWithStats,
    PaginatedTenants,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# =============================================================================
# LIST / SEARCH
# =============================================================================

@router.get(
    "",
    response_model=PaginatedTenants,
    summary="Lister les tenants",
    description="Liste paginée de tous les tenants. Filtrable par statut et type.",
)
async def list_tenants(
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
    pagination: PaginationParams = Depends(),
    status_filter: Optional[TenantStatus] = Query(None, alias="status", description="Filtrer par statut"),
    tenant_type: Optional[str] = Query(None, description="Filtrer par type"),
    search: Optional[str] = Query(None, description="Recherche par nom ou code"),
):
    """Liste tous les tenants avec pagination et filtres."""

    query = db.query(Tenant)

    # Filtres
    if status_filter:
        query = query.filter(Tenant.status == status_filter)
    if tenant_type:
        query = query.filter(Tenant.tenant_type == tenant_type)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Tenant.name.ilike(search_filter)) |
            (Tenant.code.ilike(search_filter))
        )

    # Total
    total = query.count()

    # Tri
    if pagination.sort_by:
        sort_column = getattr(Tenant, pagination.sort_by, None)
        if sort_column:
            if pagination.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Tenant.created_at.desc())

    # Pagination
    tenants = query.offset(pagination.offset).limit(pagination.limit).all()

    return PaginatedTenants(
        items=[TenantSummary.model_validate(t) for t in tenants],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=(total + pagination.size - 1) // pagination.size if total > 0 else 0
    )


# =============================================================================
# CREATE
# =============================================================================

@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tenant",
    description="Crée un nouveau tenant (client CareLink). Réservé aux PLATFORM_ADMIN.",
)
async def create_tenant(
    tenant_data: TenantCreate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_CREATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Crée un nouveau tenant."""

    # Vérifier unicité du code
    existing = db.query(Tenant).filter(Tenant.code == tenant_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le code '{tenant_data.code}' est déjà utilisé"
        )

    # Vérifier unicité du SIRET si fourni
    if tenant_data.siret:
        existing_siret = db.query(Tenant).filter(Tenant.siret == tenant_data.siret).first()
        if existing_siret:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le SIRET '{tenant_data.siret}' est déjà utilisé"
            )

    # Générer une référence de clé de chiffrement
    encryption_key_id = f"tenant-key-{uuid.uuid4().hex[:16]}"

    # Créer le tenant
    tenant = Tenant(
        **tenant_data.model_dump(),
        encryption_key_id=encryption_key_id,
    )

    db.add(tenant)
    db.flush()  # Pour obtenir l'ID

    # Log d'audit
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_CREATED,
        target_tenant_id=tenant.id,
        details={
            "code": tenant.code,
            "name": tenant.name,
            "type": tenant.tenant_type.value,
        }
    )
    db.add(audit_log)

    db.commit()
    db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


# =============================================================================
# READ
# =============================================================================

@router.get(
    "/{tenant_id}",
    response_model=TenantWithStats,
    summary="Détails d'un tenant",
    description="Récupère les détails complets d'un tenant avec statistiques.",
)
async def get_tenant(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Récupère un tenant par son ID."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    # Log d'audit (consultation)
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_VIEWED,
        target_tenant_id=tenant_id,
    )
    db.add(audit_log)
    db.commit()

    # Construire la réponse avec stats
    response_data = {
        **{c.name: getattr(tenant, c.name) for c in tenant.__table__.columns},
        "current_patients_count": len(tenant.patients) if tenant.patients else 0,
        "current_users_count": len(tenant.users) if tenant.users else 0,
        "current_storage_used_mb": 0,  # TODO: Calculer le stockage réel
        "active_subscription": None,  # TODO: Charger l'abonnement actif
    }

    return TenantWithStats.model_validate(response_data)


# =============================================================================
# UPDATE
# =============================================================================

@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Modifier un tenant",
    description="Modifie les informations d'un tenant.",
)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Met à jour un tenant."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    # Sauvegarder les anciennes valeurs pour l'audit
    update_data = tenant_data.model_dump(exclude_unset=True)
    old_values = {k: getattr(tenant, k) for k in update_data.keys()}

    # Vérifier unicité du SIRET si modifié
    if "siret" in update_data and update_data["siret"]:
        existing_siret = db.query(Tenant).filter(
            Tenant.siret == update_data["siret"],
            Tenant.id != tenant_id
        ).first()
        if existing_siret:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le SIRET '{update_data['siret']}' est déjà utilisé"
            )

    # Appliquer les modifications
    for field, value in update_data.items():
        setattr(tenant, field, value)

    # Log d'audit
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_UPDATED,
        target_tenant_id=tenant_id,
        details={
            "old_values": {k: str(v) for k, v in old_values.items()},
            "new_values": {k: str(v) for k, v in update_data.items()},
        }
    )
    db.add(audit_log)

    db.commit()
    db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


# =============================================================================
# STATUS CHANGE (actions spécifiques)
# =============================================================================

@router.post(
    "/{tenant_id}/suspend",
    response_model=TenantResponse,
    summary="Suspendre un tenant",
    description="Suspend un tenant (accès bloqué mais données conservées).",
)
async def suspend_tenant(
    tenant_id: int,
    data: TenantStatusUpdate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_SUSPEND)),
    db: Session = Depends(get_db_no_rls),
):
    """Suspend un tenant."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    if tenant.status == TenantStatus.TERMINATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de suspendre un tenant résilié"
        )

    old_status = tenant.status
    tenant.status = TenantStatus.SUSPENDED

    # Log d'audit
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_SUSPENDED,
        target_tenant_id=tenant_id,
        details={
            "reason": data.reason,
            "old_status": old_status.value,
        }
    )
    db.add(audit_log)

    db.commit()
    db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    summary="Activer un tenant",
    description="Active ou réactive un tenant suspendu.",
)
async def activate_tenant(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Active un tenant."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    if tenant.status == TenantStatus.TERMINATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de réactiver un tenant résilié"
        )

    old_status = tenant.status
    tenant.status = TenantStatus.ACTIVE

    if not tenant.activated_at:
        tenant.activated_at = datetime.now(timezone.utc)

    # Log d'audit
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_ACTIVATED,
        target_tenant_id=tenant_id,
        details={"old_status": old_status.value}
    )
    db.add(audit_log)

    db.commit()
    db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


# =============================================================================
# DELETE (soft delete via TERMINATED)
# =============================================================================

@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Résilier un tenant",
    description="Résilie définitivement un tenant. Action irréversible.",
)
async def terminate_tenant(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_DELETE)),
    db: Session = Depends(get_db_no_rls),
    confirm: bool = Query(False, description="Confirmation requise"),
):
    """Résilie un tenant (soft delete)."""

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation requise: ajoutez ?confirm=true à l'URL"
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    if tenant.status == TenantStatus.TERMINATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce tenant est déjà résilié"
        )

    old_status = tenant.status
    tenant.status = TenantStatus.TERMINATED
    tenant.terminated_at = datetime.now(timezone.utc)

    # Log d'audit
    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_DELETED,
        target_tenant_id=tenant_id,
        details={
            "code": tenant.code,
            "name": tenant.name,
            "old_status": old_status.value,
        }
    )
    db.add(audit_log)

    db.commit()

    return None