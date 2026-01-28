# app/models/tenants/subscription_usage.py
"""
Modèle SubscriptionUsage - Suivi de consommation des abonnements.

Ce module définit la table `subscription_usage` qui enregistre
la consommation mensuelle de chaque abonnement pour la facturation.
"""

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

# Imports conditionnels pour éviter les imports circulaires
if TYPE_CHECKING:
    from app.models.tenants.subscription import Subscription


class SubscriptionUsage(Base, TimestampMixin):
    """
    Enregistre la consommation mensuelle d'un abonnement.

    Chaque mois, un enregistrement est créé pour suivre :
    - Le nombre de patients actifs
    - Le nombre d'utilisateurs actifs
    - Le stockage utilisé
    - Le nombre d'appels API

    Ces métriques permettent de calculer la facturation,
    notamment les dépassements de forfait.

    Attributes:
        id: Identifiant unique
        subscription_id: Abonnement concerné
        period_start: Début de la période (1er du mois)
        period_end: Fin de la période (dernier jour du mois)
        active_patients_count: Nombre de patients actifs sur la période
        total_amount_cents: Montant total facturé en centimes
        invoiced: True si facturé

    Example:
        usage = SubscriptionUsage(
            subscription_id=1,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            active_patients_count=1650,
            active_users_count=45,
            storage_used_mb=12500,
            base_amount_cents=50000,
            overage_amount_cents=7500,  # 150 patients * 5€
            total_amount_cents=57500
        )
    """

    __tablename__ = "subscription_usage"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "period_start",
            name="uq_subscription_usage_period"
        ),
        {"comment": "Suivi de consommation mensuelle des abonnements"}
    )

    # ========================
    # Clé primaire
    # ========================
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'enregistrement"
    )

    # ========================
    # Clé étrangère
    # ========================
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de l'abonnement concerné",
        info={"description": "Référence vers l'abonnement"}
    )

    # ========================
    # Période
    # ========================
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de début de la période",
        info={
            "description": "Premier jour de la période de facturation",
            "example": "2025-01-01"
        }
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Date de fin de la période",
        info={
            "description": "Dernier jour de la période de facturation",
            "example": "2025-01-31"
        }
    )

    # ========================
    # Métriques de consommation
    # ========================
    active_patients_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Nombre de patients actifs sur la période",
        info={
            "description": "Nombre maximal ou moyen de patients actifs",
            "example": 1650
        }
    )

    active_users_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Nombre d'utilisateurs actifs sur la période",
        info={
            "description": "Utilisateurs s'étant connectés au moins une fois",
            "example": 45
        }
    )

    storage_used_mb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Stockage utilisé en Mo",
        info={
            "description": "Espace disque consommé (documents, etc.)",
            "example": 12500
        }
    )

    api_calls_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Nombre d'appels API sur la période",
        info={
            "description": "Compteur d'appels API (pour monitoring)",
            "example": 150000
        }
    )

    # ========================
    # Calcul de facturation
    # ========================
    base_amount_cents: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Montant de base du forfait en centimes",
        info={
            "description": "Prix du forfait pour cette période",
            "example": 50000
        }
    )

    overage_amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Montant des dépassements en centimes",
        info={
            "description": "Coût des patients au-delà du forfait",
            "example": 7500
        }
    )

    total_amount_cents: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Montant total facturé en centimes",
        info={
            "description": "base_amount_cents + overage_amount_cents",
            "example": 57500
        }
    )

    # ========================
    # Statut de facturation
    # ========================
    invoiced: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="La période a-t-elle été facturée ?",
        info={"description": "True = facture émise"}
    )

    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Référence de la facture externe",
        info={
            "description": "ID dans le système de facturation (Stripe, etc.)",
            "example": "inv_1234567890"
        }
    )

    # ========================
    # Relations
    # ========================
    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        back_populates="usage_records",
        doc="Abonnement concerné"
    )

    # ========================
    # Méthodes
    # ========================
    def __repr__(self) -> str:
        return (
            f"<SubscriptionUsage(id={self.id}, "
            f"subscription_id={self.subscription_id}, "
            f"period='{self.period_start}' to '{self.period_end}', "
            f"patients={self.active_patients_count})>"
        )

    @property
    def total_amount_euros(self) -> Optional[float]:
        """Montant total en euros."""
        if self.total_amount_cents is not None:
            return self.total_amount_cents / 100
        return None

    @property
    def overage_amount_euros(self) -> float:
        """Montant des dépassements en euros."""
        return self.overage_amount_cents / 100

    @property
    def base_amount_euros(self) -> Optional[float]:
        """Montant de base en euros."""
        if self.base_amount_cents is not None:
            return self.base_amount_cents / 100
        return None

    @property
    def storage_used_gb(self) -> float:
        """Stockage utilisé en Go."""
        return self.storage_used_mb / 1024

    @property
    def period_label(self) -> str:
        """Libellé de la période (ex: 'Janvier 2025')."""
        months_fr = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        return f"{months_fr[self.period_start.month]} {self.period_start.year}"

    def calculate_total(self) -> int:
        """
        Calcule et met à jour le montant total.

        Returns:
            Montant total en centimes
        """
        base = self.base_amount_cents or 0
        overage = self.overage_amount_cents or 0
        self.total_amount_cents = base + overage
        return self.total_amount_cents

    def mark_as_invoiced(self, invoice_id: str) -> None:
        """
        Marque la période comme facturée.

        Args:
            invoice_id: Référence de la facture
        """
        self.invoiced = True
        self.invoice_id = invoice_id