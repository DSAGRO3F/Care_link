# app/models/tenants/subscription.py
"""
Modèle Subscription - Abonnements des tenants.

Ce module définit la table `subscriptions` qui gère les abonnements
et la facturation des clients CareLink.
"""

from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

# from enum import Enum as PyEnum

# Imports conditionnels pour éviter les imports circulaires
if TYPE_CHECKING:
    from app.models.tenants.tenant import Tenant
    from app.models.tenants.subscription_usage import SubscriptionUsage

from app.models.enums import (
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
)


# =============================================================================
# MODÈLE
# =============================================================================

class Subscription(Base, TimestampMixin):
    """
    Représente un abonnement d'un tenant à CareLink.

    Un tenant peut avoir plusieurs abonnements au fil du temps
    (historique), mais un seul actif à la fois.

    La tarification est basée sur :
    - Un prix de base mensuel selon le plan (S, M, L, XL, Enterprise)
    - Un coût supplémentaire par patient au-delà du forfait inclus

    Attributes:
        id: Identifiant unique
        tenant_id: Tenant propriétaire de l'abonnement
        plan_code: Code du plan (S, M, L, XL, ENTERPRISE)
        status: Statut de l'abonnement (TRIAL, ACTIVE, PAST_DUE, CANCELLED)
        included_patients: Nombre de patients inclus dans le forfait
        base_price_cents: Prix de base en centimes d'euros

    Example:
        subscription = Subscription(
            tenant_id=1,
            plan_code=SubscriptionPlan.L,
            plan_name="Plan Large - 1500 patients",
            status=SubscriptionStatus.ACTIVE,
            started_at=date.today(),
            base_price_cents=50000,  # 500€
            included_patients=1500,
            billing_cycle=BillingCycle.MONTHLY
        )
    """

    __tablename__ = "subscriptions"
    __table_args__ = {
        "comment": "Abonnements et facturation des tenants"
    }

    # ========================
    # Clé primaire
    # ========================
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'abonnement"
    )

    # ========================
    # Clé étrangère
    # ========================
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID du tenant propriétaire",
        info={"description": "Référence vers le tenant"}
    )

    # ========================
    # Plan tarifaire
    # ========================
    plan_code: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscription_plan_enum", create_constraint=True),
        nullable=False,
        doc="Code du plan d'abonnement",
        info={
            "description": "S=Small, M=Medium, L=Large, XL=Extra-Large, ENTERPRISE=Sur mesure",
            "example": "L"
        }
    )

    plan_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Libellé du plan",
        info={
            "description": "Nom commercial du plan",
            "example": "Plan Large - 1500 patients"
        }
    )

    # ========================
    # Période
    # ========================
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status_enum", create_constraint=True),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        doc="Statut de l'abonnement",
        info={"description": "TRIAL, ACTIVE, PAST_DUE, CANCELLED"}
    )

    started_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début de l'abonnement",
        info={"description": "Date d'activation"}
    )

    expires_at: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Date d'expiration",
        info={"description": "NULL = pas d'expiration fixe"}
    )

    trial_ends_at: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Date de fin de la période d'essai",
        info={"description": "NULL = pas de période d'essai"}
    )

    # ========================
    # Tarification
    # ========================
    base_price_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Prix de base mensuel en centimes",
        info={
            "description": "Prix du forfait en centimes d'euros",
            "example": 50000  # 500€
        }
    )

    price_per_extra_patient_cents: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Coût par patient supplémentaire en centimes",
        info={
            "description": "Prix unitaire pour dépassement du forfait",
            "example": 500  # 5€ par patient supplémentaire
        }
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        doc="Code devise ISO 4217",
        info={"description": "EUR, USD, CHF...", "example": "EUR"}
    )

    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle_enum", create_constraint=True),
        nullable=False,
        default=BillingCycle.MONTHLY,
        doc="Cycle de facturation",
        info={"description": "MONTHLY, QUARTERLY, YEARLY"}
    )

    # ========================
    # Limites du plan
    # ========================
    included_patients: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Nombre de patients inclus dans le forfait",
        info={
            "description": "Quota de patients avant facturation supplémentaire",
            "example": 1500
        }
    )

    included_users: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Nombre d'utilisateurs inclus",
        info={"description": "NULL = illimité"}
    )

    included_storage_gb: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Stockage inclus en Go",
        info={"description": "Quota de stockage documents", "example": 50}
    )

    # ========================
    # Métadonnées
    # ========================
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Notes internes sur l'abonnement",
        info={"description": "Commentaires, conditions particulières..."}
    )

    # ========================
    # Relations
    # ========================
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="subscriptions",
        doc="Tenant propriétaire de cet abonnement"
    )

    usage_records: Mapped[List["SubscriptionUsage"]] = relationship(
        "SubscriptionUsage",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="desc(SubscriptionUsage.period_start)",
        doc="Historique de consommation mensuelle"
    )

    # ========================
    # Méthodes
    # ========================
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, tenant_id={self.tenant_id}, plan='{self.plan_code.value}', status='{self.status.value}')>"

    @property
    def is_active(self) -> bool:
        """Vérifie si l'abonnement est actif."""
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_trial(self) -> bool:
        """Vérifie si l'abonnement est en période d'essai."""
        return self.status == SubscriptionStatus.TRIAL

    @property
    def is_past_due(self) -> bool:
        """Vérifie si l'abonnement a un paiement en retard."""
        return self.status == SubscriptionStatus.PAST_DUE

    @property
    def base_price_euros(self) -> float:
        """Prix de base en euros."""
        return self.base_price_cents / 100

    @property
    def price_per_extra_patient_euros(self) -> Optional[float]:
        """Prix par patient supplémentaire en euros."""
        if self.price_per_extra_patient_cents:
            return self.price_per_extra_patient_cents / 100
        return None

    def calculate_monthly_cost(self, active_patients: int) -> int:
        """
        Calcule le coût mensuel en centimes selon le nombre de patients actifs.

        Args:
            active_patients: Nombre de patients actifs

        Returns:
            Coût total en centimes
        """
        if active_patients <= self.included_patients:
            return self.base_price_cents

        extra_patients = active_patients - self.included_patients
        extra_cost = extra_patients * (self.price_per_extra_patient_cents or 0)
        return self.base_price_cents + extra_cost