"""
Modèle PatientAccess - Traçabilité des accès patients (RGPD).

Ce module définit la table `patient_access` qui trace tous les accès
accordés aux dossiers patients, conformément au RGPD.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import AccessType

if TYPE_CHECKING:
    from app.models.patient.patient import Patient
    from app.models.user.user import User
    from app.models.tenants.tenant import Tenant


class PatientAccess(Base):
    """
    Trace un accès accordé à un dossier patient.
    
    Conformité RGPD : chaque accès est justifié et tracé.
    Un utilisateur peut avoir plusieurs enregistrements (historique).
    
    Attributes:
        id: Identifiant unique
        patient_id: ID du patient concerné
        user_id: ID de l'utilisateur ayant accès
        access_type: Type d'accès (READ, WRITE, FULL)
        reason: Justification obligatoire (RGPD)
        granted_by: Qui a accordé l'accès
        granted_at: Date d'attribution
        expires_at: Date d'expiration (None = permanent)
        revoked_at: Date de révocation (None = actif)
    
    Example:
        access = PatientAccess(
            patient_id=42,
            user_id=10,
            access_type=AccessType.WRITE,
            reason="Prise en charge infirmière - soins quotidiens",
            granted_by=admin_id
        )
    """
    
    __tablename__ = "patient_access"
    __table_args__ = (
        Index("ix_patient_access_patient_user", "patient_id", "user_id"),
        {"comment": "Table de traçabilité des accès patients (RGPD)"}
    )
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'enregistrement d'accès",
        info={
            "description": "Clé primaire auto-incrémentée"
        }
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement"
    )
    
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID du patient concerné",
        info={
            "description": "Référence vers le patient"
        }
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de l'utilisateur ayant accès",
        info={
            "description": "Référence vers l'utilisateur"
        }
    )
    
    access_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type d'accès accordé",
        info={
            "description": "Niveau d'accès",
            "enum": [e.value for e in AccessType],
            "example": "WRITE"
        }
    )
    
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Justification de l'accès (obligatoire RGPD)",
        info={
            "description": "Raison de l'accès - obligatoire pour conformité RGPD",
            "rgpd": True,
            "example": "Prise en charge infirmière - soins quotidiens"
        }
    )
    
    # --- Qui a accordé l'accès ---
    
    granted_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="ID de l'utilisateur ayant accordé l'accès",
        info={
            "description": "Administrateur ou coordinateur"
        }
    )
    
    granted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Date et heure d'attribution de l'accès",
        info={
            "description": "Timestamp de l'attribution",
            "auto_generated": True
        }
    )
    
    # --- Validité ---
    
    expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date d'expiration de l'accès (None = permanent)",
        info={
            "description": "Expiration automatique, NULL si permanent"
        }
    )
    
    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date de révocation de l'accès (None = actif)",
        info={
            "description": "NULL si l'accès est toujours actif"
        }
    )
    
    revoked_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant révoqué l'accès",
        info={
            "description": "Qui a révoqué l'accès"
        }
    )
    
    # === Relations ===
    
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="access_records",
        doc="Patient concerné"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        doc="Utilisateur ayant accès"
    )
    
    granter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[granted_by],
        doc="Utilisateur ayant accordé l'accès"
    )
    
    revoker: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[revoked_by],
        doc="Utilisateur ayant révoqué l'accès"
    )
    
    # === Propriétés ===
    
    @property
    def is_active(self) -> bool:
        """Retourne True si l'accès est actif (non révoqué et non expiré)."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.now(timezone.utc):
            return False
        return True
    
    @property
    def is_expired(self) -> bool:
        """Retourne True si l'accès a expiré."""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc)
    
    @property
    def is_revoked(self) -> bool:
        """Retourne True si l'accès a été révoqué."""
        return self.revoked_at is not None
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<PatientAccess(patient={self.patient_id}, user={self.user_id}, type={self.access_type}, {status})>"
    
    def revoke(self, revoked_by_user_id: int) -> None:
        """
        Révoque l'accès.
        
        Args:
            revoked_by_user_id: ID de l'utilisateur effectuant la révocation
        """
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by = revoked_by_user_id
    
    def can_read(self) -> bool:
        """Retourne True si l'accès permet la lecture."""
        return self.is_active and self.access_type in [
            AccessType.READ.value,
            AccessType.WRITE.value,
            AccessType.FULL.value
        ]
    
    def can_write(self) -> bool:
        """Retourne True si l'accès permet l'écriture."""
        return self.is_active and self.access_type in [
            AccessType.WRITE.value,
            AccessType.FULL.value
        ]
