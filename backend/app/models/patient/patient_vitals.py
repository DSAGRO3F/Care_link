"""
Modèles pour la gestion des constantes vitales.

Ce module définit :
- PatientThreshold : Seuils personnalisés par patient
- PatientVitals : Mesures de constantes vitales
- PatientDevice : Devices connectés
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Numeric, Text, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import VitalType, VitalStatus, VitalSource, DeviceType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.patient.patient import Patient
    from app.models.user.user import User


# =============================================================================
# PatientThreshold - Seuils personnalisés
# =============================================================================

class PatientThreshold(TimestampMixin, Base):
    """
    Seuils personnalisés de constantes vitales pour un patient.
    
    Chaque patient peut avoir des seuils min/max spécifiques
    pour chaque type de constante, adaptés à son état de santé.
    
    Attributes:
        id: Identifiant unique
        patient_id: ID du patient
        vital_type: Type de constante (FC, TA_SYS, etc.)
        min_value: Valeur minimale acceptable
        max_value: Valeur maximale acceptable
        unit: Unité de mesure
        surveillance_frequency: Fréquence de surveillance
    
    Example:
        threshold = PatientThreshold(
            patient_id=42,
            vital_type=VitalType.TA_SYS,
            min_value=110,
            max_value=145,
            unit="mmHg",
            surveillance_frequency="1x/jour"
        )
    """
    
    __tablename__ = "patient_thresholds"
    __table_args__ = (
        UniqueConstraint("patient_id", "vital_type", name="uq_patient_vital_type"),
        {"comment": "Table des seuils personnalisés de constantes vitales"}
    )
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du seuil",
        info={"description": "Clé primaire auto-incrémentée"}
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
        doc="ID du patient",
        info={"description": "Référence vers le patient"}
    )
    
    vital_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type de constante vitale",
        info={
            "description": "Type de mesure",
            "enum": [e.value for e in VitalType],
            "example": "TA_SYS"
        }
    )
    
    min_value: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Valeur minimale acceptable",
        info={"description": "Seuil bas"}
    )
    
    max_value: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Valeur maximale acceptable",
        info={"description": "Seuil haut"}
    )
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Unité de mesure",
        info={"description": "Unité (mmHg, bpm, °C, kg, g/L...)", "example": "mmHg"}
    )
    
    surveillance_frequency: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Fréquence de surveillance recommandée",
        info={"description": "Ex: 1x/jour, 2x/jour, 1x/semaine"}
    )
    
    # === Relations ===
    
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="thresholds",
        doc="Patient concerné"
    )
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<PatientThreshold(patient={self.patient_id}, type={self.vital_type}, {self.min_value}-{self.max_value} {self.unit})>"
    
    def check_value(self, value: float) -> VitalStatus:
        """
        Vérifie si une valeur est dans les seuils.
        
        Args:
            value: Valeur à vérifier
            
        Returns:
            VitalStatus (normal, low, high, critical)
        """
        from decimal import Decimal
        value_dec = Decimal(str(value))
        
        if self.min_value is not None and value_dec < self.min_value:
            # Très en dessous = critical
            if value_dec < self.min_value * Decimal('0.9'):
                return VitalStatus.CRITICAL
            return VitalStatus.LOW
        
        if self.max_value is not None and value_dec > self.max_value:
            # Très au dessus = critical
            if value_dec > self.max_value * Decimal('1.1'):
                return VitalStatus.CRITICAL
            return VitalStatus.HIGH
        
        return VitalStatus.NORMAL


# =============================================================================
# PatientVitals - Mesures de constantes
# =============================================================================

class PatientVitals(TimestampMixin, Base):
    """
    Mesure d'une constante vitale pour un patient.
    
    Les mesures peuvent provenir de saisies manuelles ou
    de devices connectés (montres, capteurs...).
    
    Attributes:
        id: Identifiant unique
        patient_id: ID du patient
        vital_type: Type de constante (FC, TA_SYS, etc.)
        value: Valeur mesurée
        unit: Unité de mesure
        status: Statut par rapport aux seuils
        source: Source de la mesure (manual, device...)
        device_id: Device source si automatique
        measured_at: Horodatage de la mesure
        recorded_by: Professionnel ayant saisi (si manuel)
    
    Example:
        vital = PatientVitals(
            patient_id=42,
            vital_type=VitalType.TA_SYS,
            value=138,
            unit="mmHg",
            status=VitalStatus.NORMAL,
            source=VitalSource.MANUAL,
            measured_at=datetime.now(),
            recorded_by=nurse_id
        )
    """
    
    __tablename__ = "patient_vitals"
    __table_args__ = (
        Index("ix_patient_vitals_patient_type_date", "patient_id", "vital_type", "measured_at"),
        {"comment": "Table des mesures de constantes vitales"}
    )
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la mesure",
        info={"description": "Clé primaire auto-incrémentée"}
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
        doc="ID du patient",
        info={"description": "Référence vers le patient"}
    )
    
    vital_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type de constante vitale",
        info={
            "description": "Type de mesure",
            "enum": [e.value for e in VitalType]
        }
    )
    
    value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Valeur numérique de la mesure",
        info={"description": "Valeur mesurée"}
    )
    
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Unité de mesure",
        info={"description": "Unité de la valeur"}
    )
    
    status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Statut par rapport aux seuils personnalisés",
        info={
            "description": "Résultat de la comparaison aux seuils",
            "enum": [e.value for e in VitalStatus]
        }
    )
    
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Source de la mesure",
        info={
            "description": "Origine de la mesure",
            "enum": [e.value for e in VitalSource]
        }
    )
    
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_devices.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID du device source (si automatique)",
        info={"description": "Référence vers le device connecté"}
    )
    
    measured_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        doc="Date et heure de la mesure",
        info={"description": "Horodatage de la prise de mesure"}
    )
    
    recorded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID du professionnel ayant saisi la mesure",
        info={"description": "NULL si mesure automatique"}
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Notes et observations",
        info={"description": "Commentaires sur la mesure"}
    )
    
    # === Relations ===
    
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="vitals",
        doc="Patient concerné"
    )
    
    device: Mapped["PatientDevice | None"] = relationship(
        "PatientDevice",
        doc="Device source de la mesure"
    )
    
    recorder: Mapped["User | None"] = relationship(
        "User",
        doc="Professionnel ayant enregistré la mesure"
    )
    
    # === Propriétés ===
    
    @property
    def is_manual(self) -> bool:
        """Retourne True si la mesure est manuelle."""
        return self.source == VitalSource.MANUAL.value
    
    @property
    def is_abnormal(self) -> bool:
        """Retourne True si la mesure est hors normes."""
        return self.status in [VitalStatus.LOW.value, VitalStatus.HIGH.value, VitalStatus.CRITICAL.value]
    
    @property
    def is_critical(self) -> bool:
        """Retourne True si la mesure est critique."""
        return self.status == VitalStatus.CRITICAL.value
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        return f"<PatientVitals(patient={self.patient_id}, type={self.vital_type}, value={self.value}, status={self.status})>"


# =============================================================================
# PatientDevice - Devices connectés
# =============================================================================

class PatientDevice(TimestampMixin, Base):
    """
    Device connecté d'un patient (montre, balance, capteur...).
    
    Permet de recevoir automatiquement les mesures de constantes
    depuis des appareils connectés via leurs APIs.
    
    Attributes:
        id: Identifiant unique
        patient_id: ID du patient propriétaire
        device_type: Type de device (withings_scale, apple_watch...)
        device_identifier: Identifiant unique du device
        device_name: Nom donné par le patient
        api_credentials_encrypted: Tokens OAuth chiffrés
        is_active: Device actif ?
        last_sync_at: Dernière synchronisation
    
    Example:
        device = PatientDevice(
            patient_id=42,
            device_type=DeviceType.WITHINGS_SCALE,
            device_identifier="WBS01-12345678",
            device_name="Balance salle de bain",
            is_active=True
        )
    """
    
    __tablename__ = "patient_devices"
    __table_args__ = (
        UniqueConstraint("device_type", "device_identifier", name="uq_device_type_identifier"),
        Index("ix_patient_devices_patient", "patient_id"),
        {"comment": "Table des devices connectés des patients"}
    )
    
    # === Colonnes ===
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du device",
        info={"description": "Clé primaire auto-incrémentée"}
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
        doc="ID du patient propriétaire",
        info={"description": "Référence vers le patient"}
    )
    
    device_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Type de device",
        info={
            "description": "Marque/type du device",
            "enum": [e.value for e in DeviceType]
        }
    )
    
    device_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Identifiant unique du device",
        info={"description": "ID technique du device (numéro de série, MAC...)"}
    )
    
    device_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Nom personnalisé du device",
        info={"description": "Nom donné par le patient", "example": "Balance salle de bain"}
    )
    
    api_credentials_encrypted: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Credentials API chiffrés (tokens OAuth)",
        info={
            "description": "Tokens d'accès API chiffrés AES-256-GCM",
            "encrypted": True,
            "sensitive": True
        }
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Le device est-il actif ?",
        info={"description": "False = device désactivé, plus de sync"}
    )
    
    last_sync_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date de dernière synchronisation",
        info={"description": "Timestamp du dernier import de données"}
    )
    
    # === Relations ===
    
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="devices",
        doc="Patient propriétaire du device"
    )
    
    # === Méthodes ===
    
    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<PatientDevice(patient={self.patient_id}, type={self.device_type}, {status})>"
    
    def deactivate(self) -> None:
        """Désactive le device."""
        self.is_active = False
    
    def update_sync_time(self) -> None:
        """Met à jour le timestamp de dernière synchronisation."""
        self.last_sync_at = datetime.now(timezone.utc)