# app/api/v1/tenants/routes.py
"""
Routes CRUD pour les Tenants.

Toutes les routes sont réservées aux SuperAdmins (équipe CareLink).
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

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
from app.models.tenants.tenant import Tenant
from app.models.enums import TenantStatus, TenantType
from .schemas import (
    TenantCreate,
    TenantUpdate,
    TenantStatusUpdate,
    TenantResponse,
    TenantSummary,
    TenantWithStats,
    PaginatedTenants,
    ParentTenantInfo,
    MemberTenantInfo,
    FederationView,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# =============================================================================
# HELPERS — Validation fédération
# =============================================================================

def validate_federation_parent(
        db: Session,
        parent_tenant_id: Optional[int],
        tenant_id: Optional[int] = None,  # None pour create, renseigné pour update
) -> Optional[Tenant]:
    """
    Vérifie la cohérence du rattachement à un groupement fédérateur.

    Retourne le tenant parent si valide, None si pas de rattachement.
    Lève HTTPException si incohérent.
    """
    if parent_tenant_id is None:
        return None

    # Auto-référence
    if tenant_id is not None and parent_tenant_id == tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un tenant ne peut pas être son propre parent."
        )

    # Le parent existe-t-il ?
    parent = db.query(Tenant).filter(Tenant.id == parent_tenant_id).first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Groupement fédérateur introuvable (id={parent_tenant_id})."
        )

    # Le parent est-il un GCSMS ou GTSMS ?
    if parent.tenant_type not in (TenantType.GCSMS, TenantType.GTSMS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le tenant '{parent.name}' (type={parent.tenant_type.value}) "
                f"n'est pas un groupement fédérateur. "
                f"Seuls les GCSMS et GTSMS peuvent avoir des membres."
            )
        )

    # Le parent est-il actif ?
    if parent.status == TenantStatus.TERMINATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le groupement '{parent.name}' est résilié et ne peut plus accueillir de membres."
        )

    return parent


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

    # Valider le rattachement fédération ──
    validate_federation_parent(db, tenant_data.parent_tenant_id)

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

    # ── NOUVEAU : Logique fédération ──
    if "parent_tenant_id" in update_data:
        new_parent_id = update_data["parent_tenant_id"]

        if new_parent_id is not None:
            # === RATTACHEMENT ou CHANGEMENT de parent ===

            # Un GCSMS/GTSMS ne peut pas être rattaché
            if tenant.is_federation_parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Le tenant '{tenant.name}' est un groupement fédérateur "
                        f"({tenant.tenant_type.value}) et ne peut pas être rattaché à un parent."
                    )
                )

            # Valider le parent (existence, type, statut)
            validate_federation_parent(db, new_parent_id, tenant_id=tenant_id)

            # integration_type obligatoire pour un rattachement
            new_integration_type = update_data.get("integration_type")
            current_integration_type = tenant.integration_type

            if new_integration_type is None and current_integration_type is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Le type d'intégration (integration_type) est obligatoire "
                        "lors du rattachement à un groupement."
                    )
                )

        else:
            # === DÉTACHEMENT : parent_tenant_id envoyé comme null ===
            # Nettoyer les champs liés pour respecter ck_integration_type_requires_parent
            update_data["integration_type"] = None
            update_data["federation_date"] = None

    # ── NOUVEAU : Empêcher le changement de type vers GCSMS/GTSMS si rattaché ──
    if "tenant_type" in update_data:
        new_type = update_data["tenant_type"]
        effective_parent = update_data.get("parent_tenant_id", tenant.parent_tenant_id)
        if new_type in (TenantType.GCSMS, TenantType.GTSMS) and effective_parent is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Impossible de changer le type en {new_type.value} "
                    f"car ce tenant est rattaché à un groupement. Détachez-le d'abord."
                )
            )

    # Appliquer les modifications
    for field, value in update_data.items():
        setattr(tenant, field, value)

    # Log d'audit (enrichi)
    audit_details = {
        "old_values": {k: str(v) for k, v in old_values.items()},
        "new_values": {k: str(v) for k, v in update_data.items()},
    }

    audit_log = PlatformAuditLog.create_log(
        super_admin_id=admin.id,
        action=AuditAction.TENANT_UPDATED,
        target_tenant_id=tenant_id,
        details=audit_details,
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

    if tenant.is_federation_parent and tenant.member_tenants:
        active_members = [m for m in tenant.member_tenants if m.status != TenantStatus.TERMINATED]
        if active_members:
            member_names = ", ".join(m.name for m in active_members[:5])
            suffix = f" et {len(active_members) - 5} autres" if len(active_members) > 5 else ""
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ce groupement a encore {len(active_members)} membre(s) actif(s) : "
                    f"{member_names}{suffix}. "
                    f"Détachez ou résiliez les membres avant de résilier le groupement."
                )
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


# =============================================================================
# FEDERATION ENDPOINTS
# =============================================================================

@router.get(
    "/{tenant_id}/members",
    response_model=List[MemberTenantInfo],
    summary="Membres d'un groupement",
    description="Liste les tenants membres d'un groupement fédérateur (GCSMS/GTSMS).",
)
async def list_tenant_members(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
    status_filter: Optional[TenantStatus] = Query(None, alias="status"),
):
    """Liste les membres d'un groupement fédérateur."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    if not tenant.is_federation_parent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le tenant '{tenant.name}' (type={tenant.tenant_type.value}) "
                f"n'est pas un groupement fédérateur."
            )
        )

    members = tenant.member_tenants

    # Filtre optionnel par statut
    if status_filter:
        members = [m for m in members if m.status == status_filter]

    return [MemberTenantInfo.model_validate(m) for m in members]


@router.get(
    "/{tenant_id}/federation",
    response_model=FederationView,
    summary="Vue fédération",
    description="Vue arborescente d'un groupement : le parent et tous ses membres avec stats.",
)
async def get_federation_view(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Vue complète d'une fédération (groupement + membres + stats)."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    # Si c'est un membre, remonter au parent
    if tenant.is_federation_member:
        tenant = tenant.parent_tenant
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Groupement fédérateur introuvable"
            )

    # Si c'est un tenant indépendant, pas de fédération
    if not tenant.is_federation_parent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le tenant '{tenant.name}' n'appartient à aucune fédération."
            )
        )

    members = tenant.member_tenants
    active_members = [m for m in members if m.status != TenantStatus.TERMINATED]

    # Stats consolidées
    total_patients = len(tenant.patients) if tenant.patients else 0
    total_users = len(tenant.users) if tenant.users else 0
    for member in active_members:
        total_patients += len(member.patients) if member.patients else 0
        total_users += len(member.users) if member.users else 0

    return FederationView(
        parent=ParentTenantInfo.model_validate(tenant),
        members=[MemberTenantInfo.model_validate(m) for m in members],
        total_members=len(members),
        active_members=len(active_members),
        total_patients=total_patients,
        total_users=total_users,
    )


@router.get(
    "/{tenant_id}/stats",
    response_model=TenantWithStats,
    summary="Statistiques d'un tenant",
    description="Statistiques détaillées incluant les données fédération si groupement.",
)
async def get_tenant_stats(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Statistiques d'un tenant, avec consolidation fédération si applicable."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )

    # Stats propres au tenant
    current_patients = len(tenant.patients) if tenant.patients else 0
    current_users = len(tenant.users) if tenant.users else 0

    # Stats fédération (si groupement)
    federation_patients = 0
    federation_users = 0
    members_count = 0

    if tenant.is_federation_parent:
        active_members = [m for m in tenant.member_tenants if m.status != TenantStatus.TERMINATED]
        members_count = len(active_members)
        for member in active_members:
            federation_patients += len(member.patients) if member.patients else 0
            federation_users += len(member.users) if member.users else 0

    response_data = {
        **{c.name: getattr(tenant, c.name) for c in tenant.__table__.columns},
        "current_patients_count": current_patients,
        "current_users_count": current_users,
        "current_storage_used_mb": 0,  # TODO: Calculer le stockage réel
        "active_subscription": None,   # TODO: Charger l'abonnement actif
        "federation_patients_count": federation_patients,
        "federation_users_count": federation_users,
        "members_count": members_count,
    }

    return TenantWithStats.model_validate(response_data)
