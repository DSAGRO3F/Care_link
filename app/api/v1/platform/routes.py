"""
Routes API pour le module Platform.

Gestion au niveau plateforme (SuperAdmin) :
- /platform/tenants : CRUD des tenants
- /platform/super-admins : CRUD des super admins
- /platform/audit-logs : Consultation des logs
- /platform/assignments : Gestion des accès cross-tenant
- /platform/stats : Statistiques globales

IMPORTANT: Toutes ces routes nécessitent une authentification SuperAdmin.
"""
from typing import Optional, List
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session_rls import get_db_no_rls as get_db
from app.api.v1.platform.super_admin_security import (
    get_current_super_admin,
    require_super_admin_permission,
    SuperAdminPermissions,
)
from app.api.v1.platform.services import (
    TenantService,
    SuperAdminService,
    PlatformAuditLogService,
    UserTenantAssignmentService,
    PlatformStatsService,
    # Exceptions
    TenantNotFoundError,
    TenantCodeExistsError,
    SuperAdminNotFoundError,
    SuperAdminEmailExistsError,
    InvalidPasswordError,
    UserTenantAssignmentNotFoundError,
    UserNotFoundError,
    DuplicateAssignmentError,
    InvalidAssignmentError,
)
from app.api.v1.platform.schemas import (
    # Tenant
    TenantCreate, TenantUpdate, TenantResponse, TenantFilters,
    TenantStatusAPI, TenantTypeAPI, TenantStats,
    # SuperAdmin
    SuperAdminCreate, SuperAdminUpdate, SuperAdminResponse,
    SuperAdminPasswordChange,
    # AuditLog
    AuditLogResponse, AuditLogFilters,
    # Assignment
    UserTenantAssignmentCreate, UserTenantAssignmentUpdate,
    UserTenantAssignmentResponse, UserTenantAssignmentFilters, AssignmentTypeAPI,
    # Stats
    PlatformStats,
)
from app.models.platform.super_admin import SuperAdmin

import math


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(prefix="/platform", tags=["Platform Administration"])


# =============================================================================
# RESPONSE HELPERS
# =============================================================================

def paginated_response(items: list, total: int, page: int, size: int) -> dict:
    """Construit une réponse paginée standardisée."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if size > 0 else 0,
    }


# =============================================================================
# TENANTS
# =============================================================================

@router.get(
    "/tenants",
    summary="Liste des tenants",
    description="Liste tous les tenants avec pagination et filtres.",
)
def list_tenants(
        page: int = Query(1, ge=1, description="Numéro de page"),
        size: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
        sort_by: str = Query("created_at", description="Champ de tri"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Ordre de tri"),
        status: Optional[TenantStatusAPI] = Query(None, description="Filtrer par statut"),
        tenant_type: Optional[TenantTypeAPI] = Query(None, description="Filtrer par type"),
        search: Optional[str] = Query(None, description="Recherche textuelle"),
        city: Optional[str] = Query(None, description="Filtrer par ville"),
        country_id: Optional[int] = Query(None, description="Filtrer par pays"),
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)
        ),
):
    """Liste les tenants avec pagination et filtres."""
    filters = TenantFilters(
        status=status,
        tenant_type=tenant_type,
        search=search,
        city=city,
        country_id=country_id,
    )

    service = TenantService(db)
    items, total = service.get_all(
        page=page,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
    )

    return paginated_response(
        items=[TenantResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tenant",
)
def create_tenant(
        data: TenantCreate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_CREATE)
        ),
):
    """Crée un nouveau tenant."""
    service = TenantService(db)
    try:
        tenant = service.create(data, created_by_id=current_admin.id)
        return TenantResponse.model_validate(tenant)
    except TenantCodeExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Détails d'un tenant",
)
def get_tenant(
        tenant_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)
        ),
):
    """Récupère les détails d'un tenant."""
    service = TenantService(db)
    try:
        tenant = service.get_by_id(tenant_id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Modifier un tenant",
)
def update_tenant(
        tenant_id: int,
        data: TenantUpdate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)
        ),
):
    """Met à jour un tenant."""
    service = TenantService(db)
    try:
        tenant = service.update(tenant_id, data, updated_by_id=current_admin.id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un tenant",
)
def delete_tenant(
        tenant_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_DELETE)
        ),
):
    """Supprime un tenant (soft delete via status TERMINATED)."""
    service = TenantService(db)
    try:
        service.delete(tenant_id, deleted_by_id=current_admin.id)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/tenants/{tenant_id}/suspend",
    response_model=TenantResponse,
    summary="Suspendre un tenant",
)
def suspend_tenant(
        tenant_id: int,
        reason: str = Query(..., min_length=10, description="Raison de la suspension"),
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)
        ),
):
    """Suspend un tenant."""
    service = TenantService(db)
    try:
        tenant = service.suspend(tenant_id, reason, suspended_by_id=current_admin.id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAssignmentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/tenants/{tenant_id}/reactivate",
    response_model=TenantResponse,
    summary="Réactiver un tenant",
)
def reactivate_tenant(
        tenant_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)
        ),
):
    """Réactive un tenant suspendu."""
    service = TenantService(db)
    try:
        tenant = service.reactivate(tenant_id, reactivated_by_id=current_admin.id)
        return TenantResponse.model_validate(tenant)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAssignmentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/stats",
    response_model=TenantStats,
    summary="Statistiques d'un tenant",
)
def get_tenant_stats(
        tenant_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)
        ),
):
    """Récupère les statistiques d'utilisation d'un tenant."""
    service = TenantService(db)
    try:
        stats = service.get_stats(tenant_id)
        return TenantStats(**stats)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# SUPER ADMINS
# =============================================================================

@router.get(
    "/super-admins",
    summary="Liste des super admins",
)
def list_super_admins(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        include_inactive: bool = Query(False, description="Inclure les comptes désactivés"),
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.SUPERADMINS_VIEW)
        ),
):
    """Liste les super admins."""
    service = SuperAdminService(db)
    items, total = service.get_all(
        page=page,
        size=size,
        include_inactive=include_inactive,
    )

    return paginated_response(
        items=[SuperAdminResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/super-admins",
    response_model=SuperAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un super admin",
)
def create_super_admin(
        data: SuperAdminCreate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.SUPERADMINS_CREATE)
        ),
):
    """Crée un nouveau super admin."""
    service = SuperAdminService(db)
    try:
        admin = service.create(data, created_by_id=current_admin.id)
        return SuperAdminResponse.model_validate(admin)
    except SuperAdminEmailExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/super-admins/{admin_id}",
    response_model=SuperAdminResponse,
    summary="Détails d'un super admin",
)
def get_super_admin(
        admin_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.SUPERADMINS_VIEW)
        ),
):
    """Récupère les détails d'un super admin."""
    service = SuperAdminService(db)
    try:
        admin = service.get_by_id(admin_id)
        return SuperAdminResponse.model_validate(admin)
    except SuperAdminNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/super-admins/{admin_id}",
    response_model=SuperAdminResponse,
    summary="Modifier un super admin",
)
def update_super_admin(
        admin_id: int,
        data: SuperAdminUpdate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.SUPERADMINS_UPDATE)
        ),
):
    """Met à jour un super admin."""
    service = SuperAdminService(db)
    try:
        admin = service.update(admin_id, data, updated_by_id=current_admin.id)
        return SuperAdminResponse.model_validate(admin)
    except SuperAdminNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SuperAdminEmailExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/super-admins/{admin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un super admin",
)
def delete_super_admin(
        admin_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.SUPERADMINS_DELETE)
        ),
):
    """Désactive un super admin (soft delete)."""
    service = SuperAdminService(db)
    try:
        service.delete(admin_id, deleted_by_id=current_admin.id)
    except SuperAdminNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAssignmentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/super-admins/{admin_id}/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Changer le mot de passe",
)
def change_super_admin_password(
        admin_id: int,
        data: SuperAdminPasswordChange,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Change le mot de passe d'un super admin (soi-même uniquement)."""
    # Seul le super admin lui-même peut changer son mot de passe
    if current_admin.id != admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez changer que votre propre mot de passe"
        )

    service = SuperAdminService(db)
    try:
        service.change_password(admin_id, data)
    except SuperAdminNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# AUDIT LOGS
# =============================================================================

@router.get(
    "/audit-logs",
    summary="Liste des logs d'audit",
)
def list_audit_logs(
        page: int = Query(1, ge=1),
        size: int = Query(50, ge=1, le=200),
        super_admin_id: Optional[int] = Query(None, description="Filtrer par super admin"),
        action: Optional[str] = Query(None, description="Filtrer par action"),
        resource_type: Optional[str] = Query(None, description="Filtrer par type de ressource"),
        tenant_id: Optional[int] = Query(None, description="Filtrer par tenant"),
        date_from: Optional[datetime] = Query(None, description="Date de début"),
        date_to: Optional[datetime] = Query(None, description="Date de fin"),
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.AUDIT_VIEW)
        ),
):
    """Liste les logs d'audit avec pagination et filtres."""
    filters = AuditLogFilters(
        super_admin_id=super_admin_id,
        action=action,
        resource_type=resource_type,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
    )

    service = PlatformAuditLogService(db)
    items, total = service.get_all(page=page, size=size, filters=filters)

    # Enrichir les réponses avec les infos liées
    responses = []
    for item in items:
        response = AuditLogResponse.model_validate(item)
        # Ajouter email du super admin si disponible
        if item.super_admin:
            response.super_admin_email = item.super_admin.email
        # Ajouter code du tenant si disponible
        if item.target_tenant:
            response.tenant_code = item.target_tenant.code
        responses.append(response)

    return paginated_response(
        items=responses,
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/audit-logs/{log_id}",
    response_model=AuditLogResponse,
    summary="Détails d'un log d'audit",
)
def get_audit_log(
        log_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.AUDIT_VIEW)
        ),
):
    """Récupère les détails d'un log d'audit."""
    service = PlatformAuditLogService(db)
    try:
        log = service.get_by_id(log_id)
        response = AuditLogResponse.model_validate(log)
        if log.super_admin:
            response.super_admin_email = log.super_admin.email
        if log.target_tenant:
            response.tenant_code = log.target_tenant.code
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# USER TENANT ASSIGNMENTS (CROSS-TENANT ACCESS)
# =============================================================================

@router.get(
    "/assignments",
    summary="Liste des affectations cross-tenant",
)
def list_assignments(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        user_id: Optional[int] = Query(None, description="Filtrer par utilisateur"),
        tenant_id: Optional[int] = Query(None, description="Filtrer par tenant de destination"),
        assignment_type: Optional[AssignmentTypeAPI] = Query(None, description="Filtrer par type"),
        is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
        include_expired: bool = Query(False, description="Inclure les affectations expirées"),
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.ASSIGNMENTS_VIEW)
        ),
):
    """Liste les affectations cross-tenant."""
    filters = UserTenantAssignmentFilters(
        user_id=user_id,
        tenant_id=tenant_id,
        assignment_type=assignment_type,
        is_active=is_active,
        include_expired=include_expired,
    )

    service = UserTenantAssignmentService(db)
    items, total = service.get_all(page=page, size=size, filters=filters)

    # Enrichir les réponses
    responses = []
    for item in items:
        response = UserTenantAssignmentResponse.model_validate(item)
        if item.user:
            response.user_email = item.user.email
            response.user_full_name = f"{item.user.first_name} {item.user.last_name}"
        if item.tenant:
            response.tenant_code = item.tenant.code
            response.tenant_name = item.tenant.name
        # Ajouter propriétés calculées
        response.is_valid = item.is_valid
        response.days_remaining = item.days_remaining
        responses.append(response)

    return paginated_response(
        items=responses,
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/assignments",
    response_model=UserTenantAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une affectation cross-tenant",
)
def create_assignment(
        data: UserTenantAssignmentCreate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.ASSIGNMENTS_CREATE)
        ),
):
    """Crée une nouvelle affectation cross-tenant."""
    service = UserTenantAssignmentService(db)
    try:
        assignment = service.create(data, created_by_id=current_admin.id)
        response = UserTenantAssignmentResponse.model_validate(assignment)
        if assignment.user:
            response.user_email = assignment.user.email
            response.user_full_name = f"{assignment.user.first_name} {assignment.user.last_name}"
        if assignment.tenant:
            response.tenant_code = assignment.tenant.code
            response.tenant_name = assignment.tenant.name
        response.is_valid = assignment.is_valid
        response.days_remaining = assignment.days_remaining
        return response
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (DuplicateAssignmentError, InvalidAssignmentError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/assignments/{assignment_id}",
    response_model=UserTenantAssignmentResponse,
    summary="Détails d'une affectation",
)
def get_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.ASSIGNMENTS_VIEW)
        ),
):
    """Récupère les détails d'une affectation."""
    service = UserTenantAssignmentService(db)
    try:
        assignment = service.get_by_id(assignment_id)
        response = UserTenantAssignmentResponse.model_validate(assignment)
        if assignment.user:
            response.user_email = assignment.user.email
            response.user_full_name = f"{assignment.user.first_name} {assignment.user.last_name}"
        if assignment.tenant:
            response.tenant_code = assignment.tenant.code
            response.tenant_name = assignment.tenant.name
        response.is_valid = assignment.is_valid
        response.days_remaining = assignment.days_remaining
        return response
    except UserTenantAssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/assignments/{assignment_id}",
    response_model=UserTenantAssignmentResponse,
    summary="Modifier une affectation",
)
def update_assignment(
        assignment_id: int,
        data: UserTenantAssignmentUpdate,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.ASSIGNMENTS_UPDATE)
        ),
):
    """Met à jour une affectation."""
    service = UserTenantAssignmentService(db)
    try:
        assignment = service.update(assignment_id, data, updated_by_id=current_admin.id)
        response = UserTenantAssignmentResponse.model_validate(assignment)
        if assignment.user:
            response.user_email = assignment.user.email
            response.user_full_name = f"{assignment.user.first_name} {assignment.user.last_name}"
        if assignment.tenant:
            response.tenant_code = assignment.tenant.code
            response.tenant_name = assignment.tenant.name
        response.is_valid = assignment.is_valid
        response.days_remaining = assignment.days_remaining
        return response
    except UserTenantAssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une affectation",
)
def delete_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(
            require_super_admin_permission(SuperAdminPermissions.ASSIGNMENTS_DELETE)
        ),
):
    """Désactive une affectation (soft delete)."""
    service = UserTenantAssignmentService(db)
    try:
        service.delete(assignment_id, deleted_by_id=current_admin.id)
    except UserTenantAssignmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PLATFORM STATS
# =============================================================================

@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Statistiques globales de la plateforme",
)
def get_platform_stats(
        db: Session = Depends(get_db),
        current_admin: SuperAdmin = Depends(get_current_super_admin),
):
    """Récupère les statistiques globales de la plateforme."""
    service = PlatformStatsService(db)
    stats = service.get_platform_stats()
    return PlatformStats(**stats)