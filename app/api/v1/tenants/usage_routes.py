# app/api/v1/tenants/usage_routes.py
"""
Routes pour consulter la consommation (SubscriptionUsage).

Lecture seule - les enregistrements sont créés par des jobs batch.
Toutes les routes sont réservées aux SuperAdmins (équipe CareLink).
"""

from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.database.session_rls import get_db_no_rls
from app.models.tenants.tenant import Tenant
from app.models.tenants.subscription import Subscription
from app.models.tenants.subscription_usage import SubscriptionUsage
from app.models.enums import SubscriptionStatus
from app.models.patient.patient import Patient
from app.models.user.user import User
from app.models.platform.super_admin import SuperAdmin

from app.api.v1.platform.super_admin_security import (
    require_super_admin_permission,
    SuperAdminPermissions,
)

from .schemas import (
    UsageResponse,
    CurrentUsageResponse,
    PaginatedUsage,
)

router = APIRouter(prefix="/tenants/{tenant_id}/usage", tags=["Usage & Billing"])


# =============================================================================
# HELPERS
# =============================================================================

def get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    """Récupère un tenant ou lève une 404."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trouvé"
        )
    return tenant


def get_active_subscription_or_404(db: Session, tenant_id: int) -> Subscription:
    """Récupère l'abonnement actif d'un tenant ou lève une 404."""
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun abonnement actif pour ce tenant"
        )
    return subscription


# =============================================================================
# LIST USAGE HISTORY
# =============================================================================

@router.get(
    "",
    response_model=PaginatedUsage,
    summary="Historique de consommation",
    description="Liste l'historique de consommation mensuelle du tenant.",
)
async def list_usage(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
    year: Optional[int] = Query(None, description="Filtrer par année"),
    invoiced: Optional[bool] = Query(None, description="Filtrer par statut facturation"),
):
    """Liste l'historique de consommation."""

    # Vérifier que le tenant existe
    get_tenant_or_404(db, tenant_id)

    # Récupérer l'abonnement actif
    subscription = get_active_subscription_or_404(db, tenant_id)

    query = db.query(SubscriptionUsage).filter(
        SubscriptionUsage.subscription_id == subscription.id
    )

    if year:
        query = query.filter(extract('year', SubscriptionUsage.period_start) == year)

    if invoiced is not None:
        query = query.filter(SubscriptionUsage.invoiced == invoiced)

    usage_records = query.order_by(SubscriptionUsage.period_start.desc()).all()

    return PaginatedUsage(
        items=[UsageResponse.model_validate(u) for u in usage_records],
        total=len(usage_records),
        page=1,
        size=len(usage_records),
        pages=1
    )


# =============================================================================
# GET CURRENT USAGE (REAL-TIME)
# =============================================================================

@router.get(
    "/current",
    response_model=CurrentUsageResponse,
    summary="Consommation actuelle",
    description="Récupère la consommation en temps réel du tenant.",
)
async def get_current_usage(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Récupère la consommation actuelle."""

    tenant = get_tenant_or_404(db, tenant_id)
    subscription = get_active_subscription_or_404(db, tenant_id)

    # Compter les patients et utilisateurs actifs
    current_patients = db.query(Patient).filter(
        Patient.tenant_id == tenant_id
    ).count()

    current_users = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.is_active == True
    ).count()

    # TODO: Calculer le stockage réel (documents, etc.)
    current_storage_mb = 0

    # Calculer les pourcentages
    patients_pct = (
        (current_patients / subscription.included_patients * 100)
        if subscription.included_patients > 0
        else 0
    )

    users_pct = None
    if subscription.included_users:
        users_pct = (current_users / subscription.included_users * 100)

    storage_pct = None
    if subscription.included_storage_gb:
        storage_pct = (current_storage_mb / (subscription.included_storage_gb * 1024) * 100)

    return CurrentUsageResponse(
        tenant_id=tenant_id,
        tenant_name=tenant.name,

        included_patients=subscription.included_patients,
        included_users=subscription.included_users,
        included_storage_gb=subscription.included_storage_gb,

        current_patients=current_patients,
        current_users=current_users,
        current_storage_mb=current_storage_mb,

        patients_usage_percent=round(patients_pct, 1),
        users_usage_percent=round(users_pct, 1) if users_pct is not None else None,
        storage_usage_percent=round(storage_pct, 1) if storage_pct is not None else None,

        is_over_patient_limit=current_patients > subscription.included_patients,
        is_over_user_limit=bool(
            subscription.included_users and current_users > subscription.included_users
        ),
        is_over_storage_limit=bool(
            subscription.included_storage_gb and current_storage_mb > subscription.included_storage_gb * 1024
        ),
    )


# =============================================================================
# GET USAGE DETAIL
# =============================================================================

@router.get(
    "/{usage_id}",
    response_model=UsageResponse,
    summary="Détails d'une période",
    description="Récupère les détails d'une période de consommation spécifique.",
)
async def get_usage_detail(
    tenant_id: int,
    usage_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Récupère les détails d'une période de consommation."""

    # Vérifier que le tenant existe
    get_tenant_or_404(db, tenant_id)

    usage = db.query(SubscriptionUsage).filter(
        SubscriptionUsage.id == usage_id
    ).first()

    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enregistrement de consommation non trouvé"
        )

    # Vérifier que ça appartient bien au tenant
    if usage.subscription.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enregistrement de consommation non trouvé"
        )

    return UsageResponse.model_validate(usage)


# =============================================================================
# MARK AS INVOICED (pour intégration facturation)
# =============================================================================

@router.post(
    "/{usage_id}/mark-invoiced",
    response_model=UsageResponse,
    summary="Marquer comme facturé",
    description="Marque une période de consommation comme facturée.",
)
async def mark_usage_invoiced(
    tenant_id: int,
    usage_id: int,
    invoice_id: str = Query(..., description="Référence de la facture"),
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Marque une période comme facturée."""

    # Vérifier que le tenant existe
    get_tenant_or_404(db, tenant_id)

    usage = db.query(SubscriptionUsage).filter(
        SubscriptionUsage.id == usage_id
    ).first()

    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enregistrement de consommation non trouvé"
        )

    # Vérifier que ça appartient bien au tenant
    if usage.subscription.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enregistrement de consommation non trouvé"
        )

    if usage.invoiced:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cette période est déjà facturée (facture: {usage.invoice_id})"
        )

    usage.mark_as_invoiced(invoice_id)

    db.commit()
    db.refresh(usage)

    return UsageResponse.model_validate(usage)