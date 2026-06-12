"""
Routes FastAPI pour le module Notifications (Phase 4 bis — B40-J2).

Endpoints pour :
- /notifications                 : liste paginée des notifications de l'utilisateur
- /notifications/unread-count    : compteur badge (polling 30s côté frontend)
- /notifications/{id}/mark-read  : marquer une notification comme lue
- /notifications/mark-all-read   : marquer toutes comme lues

Swagger tag : « Notifications » (Stratégie B — tag sur sub-router).

Pas de gating par permission (`Depends(require_permission(...))`) : la RLS
atypique #130 sur la table `notifications` filtre par `recipient_user_id`,
chaque utilisateur ne voit que ses propres notifications. Le contrôle d'accès
est porté en base, pas au niveau endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.api.v1.validation.schemas import (
    NotificationList,
    NotificationResponse,
    NotificationUnreadCount,
)
from app.api.v1.validation.services import (
    NotificationNotFoundError,
    NotificationService,
)
from app.core.auth.user_auth import get_current_user
from app.database.session_rls import get_db
from app.models.user.user import User


# =============================================================================
# ROUTER
# =============================================================================

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


# =============================================================================
# ENDPOINTS
# =============================================================================


@notifications_router.get("", response_model=NotificationList)
def list_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste paginée des notifications de l'utilisateur courant.

    Ordre antéchronologique. Filtrage RLS atypique #130 par destinataire :
    l'utilisateur ne voit que ses propres notifications, indépendamment du tenant.
    """
    service = NotificationService(db, tenant_id)
    items, total = service.list_for_user(
        user_id=current_user.id, page=page, size=size, unread_only=unread_only
    )
    pages = (total + size - 1) // size if total else 0
    responses = [NotificationResponse.model_validate(n) for n in items]
    return NotificationList(items=responses, total=total, page=page, size=size, pages=pages)


@notifications_router.get("/unread-count", response_model=NotificationUnreadCount)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Compteur de notifications non lues (badge — polling 30s côté frontend, D22 β)."""
    service = NotificationService(db, tenant_id)
    return NotificationUnreadCount(unread_count=service.count_unread(current_user.id))


@notifications_router.patch("/{notification_id}/mark-read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Marque une notification comme lue (idempotent).

    La méthode service vérifie que la notification appartient bien au destinataire
    courant (RLS atypique #130 — le filtre est porté en SQL).
    """
    service = NotificationService(db, tenant_id)
    try:
        notif = service.mark_read(notification_id, current_user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NotificationResponse.model_validate(notif)


@notifications_router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Marque toutes les notifications non lues du destinataire comme lues.

    Retourne le nombre de notifications effectivement marquées.
    """
    service = NotificationService(db, tenant_id)
    count = service.mark_all_read(current_user.id)
    return {"marked_count": count}
