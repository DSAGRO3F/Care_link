"""
Modèle Patient - Dossiers patients.

Ce module définit la table `patients` qui contient les informations
des patients suivis dans CareLink.

IMPORTANT - SÉCURITÉ :
- Les données personnelles sont chiffrées AES-256-GCM
- Les blind indexes permettent la recherche sans déchiffrement
- Conforme RGPD et HDS (Hébergement Données de Santé)
- La clé de chiffrement est dans .env (ENCRYPTION_KEY)

Architecture de chiffrement:
- Colonnes *_encrypted : données chiffrées (AES-256-GCM)
- Colonnes *_blind : empreintes HMAC-SHA256 pour recherche
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import PatientStatus
from app.models.mixins import AuditMixin, TimestampMixin, VersionedMixin


if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.coordination.coordination_entry import CoordinationEntry
    from app.models.coordination.scheduled_intervention import ScheduledIntervention
    from app.models.organization.entity import Entity
    from app.models.patient.patient_access import PatientAccess
    from app.models.patient.patient_document import PatientDocument
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.patient.patient_vitals import PatientDevice, PatientThreshold, PatientVitals
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User


class Patient(VersionedMixin, TimestampMixin, AuditMixin, Base):
    """
    Représente un patient/usager suivi dans CareLink.

    ATTENTION : Les données personnelles sont stockées CHIFFRÉES.
    Utiliser PatientEncryptor pour chiffrer/déchiffrer les données.

    Champs chiffrés (AES-256-GCM):
    - nir_encrypted, ins_encrypted : Identifiants nationaux
    - first_name_encrypted, last_name_encrypted : Identification
    - birth_date_encrypted : Date de naissance
    - address_encrypted, phone_encrypted, email_encrypted : Coordonnées

    Blind indexes (HMAC-SHA256, pour recherche):
    - nir_blind, ins_blind : Recherche par identifiants
    - first_name_blind, last_name_blind : Recherche par nom
    """

    __tablename__ = "patients"
    __table_args__ = (
        # Index sur les blind indexes pour recherche performante
        Index("ix_patients_nir_blind", "nir_blind"),
        Index("ix_patients_ins_blind", "ins_blind"),
        Index("ix_patients_last_name_blind", "last_name_blind"),
        Index("ix_patients_first_name_blind", "first_name_blind"),
        # Index composé pour recherche nom + prénom
        Index("ix_patients_name_blind", "last_name_blind", "first_name_blind"),
        {
            "comment": "Table des patients (données chiffrées AES-256-GCM, blind indexes HMAC-SHA256)"
        },
    )

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique du patient",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # =========================================================================
    # DONNÉES CHIFFRÉES (AES-256-GCM)
    # =========================================================================

    nir_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Numéro NIR chiffré (N° Sécurité Sociale)",
        info={"description": "NIR chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    ins_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Identifiant National de Santé chiffré",
        info={"description": "INS chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    first_name_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Prénom du patient chiffré",
        info={"description": "Prénom chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    last_name_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Nom de famille du patient chiffré",
        info={"description": "Nom chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    birth_date_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Date de naissance du patient chiffrée",
        info={"description": "Date naissance chiffrée AES-256-GCM", "encrypted": True, "pii": True},
    )

    address_encrypted: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Adresse postale du patient chiffrée",
        info={"description": "Adresse chiffrée AES-256-GCM", "encrypted": True, "pii": True},
    )

    postal_code_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Code postal du patient chiffré",
        info={"description": "Code postal chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    city_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Ville du patient chiffrée",
        info={"description": "Ville chiffrée AES-256-GCM", "encrypted": True, "pii": True},
    )

    phone_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Numéro de téléphone du patient chiffré",
        info={"description": "Téléphone chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    email_encrypted: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Adresse email du patient chiffrée",
        info={"description": "Email chiffré AES-256-GCM", "encrypted": True, "pii": True},
    )

    # =========================================================================
    # BLIND INDEXES (HMAC-SHA256 pour recherche)
    # =========================================================================
    # Ces colonnes permettent de rechercher des patients sans déchiffrer
    # les données. L'empreinte est calculée avec une clé dérivée distincte.

    nir_blind: Mapped[str | None] = mapped_column(
        String(64),  # SHA256 = 64 caractères hex
        nullable=True,
        doc="Blind index du NIR pour recherche",
        info={
            "description": "HMAC-SHA256 du NIR normalisé",
            "blind_index": True,
            "searchable": True,
        },
    )

    ins_blind: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Blind index de l'INS pour recherche",
        info={
            "description": "HMAC-SHA256 de l'INS normalisé",
            "blind_index": True,
            "searchable": True,
        },
    )

    first_name_blind: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Blind index du prénom pour recherche",
        info={
            "description": "HMAC-SHA256 du prénom normalisé (minuscules, sans accents)",
            "blind_index": True,
            "searchable": True,
        },
    )

    last_name_blind: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Blind index du nom pour recherche",
        info={
            "description": "HMAC-SHA256 du nom normalisé (minuscules, sans accents)",
            "blind_index": True,
            "searchable": True,
        },
    )

    # =========================================================================
    # STATUT ET MÉTADONNÉES
    # =========================================================================

    status: Mapped[str] = mapped_column(
        String(20),
        default=PatientStatus.ACTIVE.value,
        doc="Statut du dossier patient",
        info={"description": "Statut actuel du dossier", "enum": [e.value for e in PatientStatus]},
    )

    # === Clés étrangères ===

    medecin_traitant_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID du médecin traitant référent",
        info={"description": "Référence vers le médecin traitant"},
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID du tenant propriétaire",
        info={"description": "Référence vers le tenant (client) propriétaire de cette entité"},
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID de l'entité de rattachement",
        info={"description": "Entité responsable du suivi"},
    )

    # --- Score GIR courant (mis à jour au submit/validate) ---
    current_gir: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Score GIR actuel du patient (1-6), mis à jour à chaque soumission d'évaluation",
        info={"description": "GIR courant pour affichage sidebar et filtres SQL"},
    )

    # === Relations ===
    # IMPORTANT: foreign_keys spécifié car Patient a plusieurs FK vers users
    # (medecin_traitant_id + created_by + updated_by via AuditMixin)

    medecin_traitant: Mapped["User | None"] = relationship(
        "User",
        back_populates="patients_as_medecin",
        foreign_keys="[Patient.medecin_traitant_id]",
        doc="Médecin traitant référent du patient",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="patients", doc="Tenant propriétaire de ce patient"
    )

    entity: Mapped["Entity"] = relationship(
        "Entity", back_populates="patients", doc="Entité de soins responsable du patient"
    )

    access_records: Mapped[list["PatientAccess"]] = relationship(
        "PatientAccess",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Historique des accès au dossier (RGPD)",
    )

    evaluations: Mapped[list["PatientEvaluation"]] = relationship(
        "PatientEvaluation",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(PatientEvaluation.evaluation_date)",
        doc="Évaluations du patient",
    )

    care_plans: Mapped[list["CarePlan"]] = relationship(
        "CarePlan",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Plans d'aide du patient",
    )

    scheduled_interventions: Mapped[list["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Interventions planifiées pour ce patient",
    )

    thresholds: Mapped[list["PatientThreshold"]] = relationship(
        "PatientThreshold",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Seuils personnalisés des constantes vitales",
    )

    vitals: Mapped[list["PatientVitals"]] = relationship(
        "PatientVitals",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(PatientVitals.measured_at)",
        doc="Mesures de constantes vitales",
    )

    devices: Mapped[list["PatientDevice"]] = relationship(
        "PatientDevice",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Devices connectés du patient",
    )

    # --- Relations - Documents générés ---
    documents: Mapped[list["PatientDocument"]] = relationship(
        "PatientDocument",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(PatientDocument.generated_at)",
        doc="Documents générés pour ce patient",
    )

    # --- Relations - Carnet de coordination ---
    coordination_entries: Mapped[list["CoordinationEntry"]] = relationship(
        "CoordinationEntry",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(CoordinationEntry.performed_at)",
        doc="Entrées du carnet de coordination",
    )

    # === Géolocalisation (pour calcul de distance) ===
    # Note: Coordonnées approximatives pour respecter RGPD tout en permettant
    # le calcul de distance. Précision réduite (~100m) recommandée.

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True, comment="Latitude du domicile (précision réduite pour RGPD)"
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True, comment="Longitude du domicile (précision réduite pour RGPD)"
    )

    geo_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="Date de dernière validation de la géolocalisation"
    )

    # === Propriétés ===

    @property
    def is_active(self) -> bool:
        """Retourne True si le dossier est actif."""
        return self.status == PatientStatus.ACTIVE.value

    @property
    def latest_evaluation(self) -> "PatientEvaluation | None":
        """Retourne la dernière évaluation du patient."""
        return self.evaluations[0] if self.evaluations else None

    @property
    def latest_ppa(self) -> "PatientDocument | None":
        """Retourne le dernier PPA généré."""
        for doc in self.documents:
            if doc.document_type == "PPA":
                return doc
        return None

    @property
    def latest_ppcs(self) -> "PatientDocument | None":
        """Retourne le dernier PPCS généré."""
        for doc in self.documents:
            if doc.document_type == "PPCS":
                return doc
        return None

    @property
    def recent_coordination_entries(self) -> list["CoordinationEntry"]:
        """Retourne les entrées de coordination des dernières 24h."""
        return [e for e in self.coordination_entries if e.is_recent and e.is_active]

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, entity_id={self.entity_id}, status='{self.status}')>"

    def archive(self) -> None:
        """Archive le dossier patient."""
        self.status = PatientStatus.ARCHIVED.value

    def mark_deceased(self) -> None:
        """Marque le patient comme décédé."""
        self.status = PatientStatus.DECEASED.value

    def get_active_access_for_user(self, user_id: int) -> "PatientAccess | None":
        """Retourne l'accès actif pour un utilisateur donné."""
        for access in self.access_records:
            if access.user_id == user_id and access.is_active:
                return access
        return None
