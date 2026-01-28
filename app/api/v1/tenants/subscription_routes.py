# app/api/v1/tenants/subscription_routes.py
"""
Routes CRUD pour les Subscriptions.

Toutes les routes sont réservées aux SuperAdmins (équipe CareLink).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session_rls import get_db_no_rls
from app.models.tenants.tenant import Tenant
from app.models.tenants.subscription import Subscription
from app.models.enums import SubscriptionStatus
from app.models.platform.super_admin import SuperAdmin

from app.api.v1.platform.super_admin_security import (
    require_super_admin_permission,
    SuperAdminPermissions,
)

from .schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionStatusUpdate,
    SubscriptionResponse,
    SubscriptionSummary,
    PaginatedSubscriptions,
)

router = APIRouter(prefix="/tenants/{tenant_id}/subscriptions", tags=["Subscriptions"])


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


def get_subscription_or_404(db: Session, tenant_id: int, subscription_id: int) -> Subscription:
    """Récupère un abonnement ou lève une 404."""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.tenant_id == tenant_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abonnement non trouvé"
        )
    return subscription


# =============================================================================
# LIST
# =============================================================================

@router.get(
    "",
    response_model=PaginatedSubscriptions,
    summary="Historique des abonnements",
    description="Liste tous les abonnements d'un tenant (historique).",
)
async def list_subscriptions(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
    status_filter: Optional[SubscriptionStatus] = Query(None, alias="status"),
):
    """Liste les abonnements d'un tenant."""

    # Vérifier que le tenant existe
    get_tenant_or_404(db, tenant_id)

    query = db.query(Subscription).filter(Subscription.tenant_id == tenant_id)

    if status_filter:
        query = query.filter(Subscription.status == status_filter)

    subscriptions = query.order_by(Subscription.started_at.desc()).all()

    return PaginatedSubscriptions(
        items=[SubscriptionSummary.model_validate(s) for s in subscriptions],
        total=len(subscriptions),
        page=1,
        size=len(subscriptions),
        pages=1
    )


# =============================================================================
# GET ACTIVE
# =============================================================================

@router.get(
    "/active",
    response_model=SubscriptionResponse,
    summary="Abonnement actif",
    description="Récupère l'abonnement actuellement actif du tenant.",
)
async def get_active_subscription(
    tenant_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Récupère l'abonnement actif."""

    # Vérifier que le tenant existe
    get_tenant_or_404(db, tenant_id)

    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun abonnement actif pour ce tenant"
        )

    return SubscriptionResponse.model_validate(subscription)


# =============================================================================
# GET BY ID
# =============================================================================

@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Détails d'un abonnement",
    description="Récupère les détails d'un abonnement spécifique.",
)
async def get_subscription(
    tenant_id: int,
    subscription_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_VIEW)),
    db: Session = Depends(get_db_no_rls),
):
    """Récupère un abonnement par son ID."""

    subscription = get_subscription_or_404(db, tenant_id, subscription_id)
    return SubscriptionResponse.model_validate(subscription)


# =============================================================================
# CREATE
# =============================================================================

@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un abonnement",
    description="Crée un nouvel abonnement pour le tenant. Désactive automatiquement l'abonnement actif précédent.",
)
async def create_subscription(
    tenant_id: int,
    subscription_data: SubscriptionCreate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Crée un abonnement."""

    # Vérifier que le tenant existe
    tenant = get_tenant_or_404(db, tenant_id)

    # Désactiver l'abonnement actif existant
    active_sub = db.query(Subscription).filter(
        Subscription.tenant_id == tenant_id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()

    if active_sub:
        active_sub.status = SubscriptionStatus.CANCELLED

    # Créer le nouvel abonnement
    subscription = Subscription(
        tenant_id=tenant_id,
        **subscription_data.model_dump()
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


# =============================================================================
# UPDATE
# =============================================================================

@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Modifier un abonnement",
    description="Modifie les informations d'un abonnement.",
)
async def update_subscription(
    tenant_id: int,
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Met à jour un abonnement."""

    subscription = get_subscription_or_404(db, tenant_id, subscription_id)

    update_data = subscription_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


# =============================================================================
# STATUS CHANGES
# =============================================================================

@router.post(
    "/{subscription_id}/activate",
    response_model=SubscriptionResponse,
    summary="Activer un abonnement",
    description="Active un abonnement (passage de TRIAL à ACTIVE par exemple).",
)
async def activate_subscription(
    tenant_id: int,
    subscription_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Active un abonnement."""

    subscription = get_subscription_or_404(db, tenant_id, subscription_id)

    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'activer un abonnement annulé. Créez un nouvel abonnement."
        )

    subscription.status = SubscriptionStatus.ACTIVE

    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Annuler un abonnement",
    description="Annule un abonnement.",
)
async def cancel_subscription(
    tenant_id: int,
    subscription_id: int,
    data: SubscriptionStatusUpdate,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Annule un abonnement."""

    subscription = get_subscription_or_404(db, tenant_id, subscription_id)

    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet abonnement est déjà annulé"
        )

    subscription.status = SubscriptionStatus.CANCELLED

    # Ajouter la raison dans les notes si fournie
    if data.reason:
        existing_notes = subscription.notes or ""
        subscription.notes = f"{existing_notes}\n[Annulation] {data.reason}".strip()

    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/{subscription_id}/mark-past-due",
    response_model=SubscriptionResponse,
    summary="Marquer en retard de paiement",
    description="Marque un abonnement comme ayant un paiement en retard.",
)
async def mark_subscription_past_due(
    tenant_id: int,
    subscription_id: int,
    admin: SuperAdmin = Depends(require_super_admin_permission(SuperAdminPermissions.TENANTS_UPDATE)),
    db: Session = Depends(get_db_no_rls),
):
    """Marque un abonnement comme en retard de paiement."""

    subscription = get_subscription_or_404(db, tenant_id, subscription_id)

    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un abonnement actif peut être marqué en retard de paiement"
        )

    subscription.status = SubscriptionStatus.PAST_DUE

    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse.model_validate(subscription)