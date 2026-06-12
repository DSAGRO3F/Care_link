"""
Modèle ValidationRequest - Demandes de validation polymorphiques (Phase 4 bis B40-J1).

Ce module définit la table `validation_requests` qui matérialise une demande
de validation d'un document validable (évaluation AGGIR ou plan d'aide).

Polymorphique exclusif sur 2 documents validables V1 :
- Évaluation AGGIR seule (workflow AGGIR_FUNDING)
- Plan d'aide / Dossier de coordination (workflow COORDINATION_DOSSIER)

Une demande circule entre étapes (stage) et reçoit in fine une décision (decision)
ou un retrait par le soumetteur (withdrawn_at).

Référence : plan_B40_J1_27_05_2026.md §6 étape 4, décisions PS-9, PS-12.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.enums import (
    InvalidationReason,
    ValidationDecision,
    ValidationStage,
    ValidationWorkflowType,
)
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.patient.patient_evaluation import PatientEvaluation
    from app.models.tenants.tenant import Tenant
    from app.models.user.user import User
    from app.models.validation.validation_exchange import ValidationExchange


class ValidationRequest(TimestampMixin, Base):
    """
    Demande de validation polymorphique sur évaluation ou plan d'aide.

    Cycle de vie :
        submitted_at → assigned (stage=INTERNAL_REVIEW|MEDICAL_REVIEW|FUNDING_REVIEW)
        → decided_at avec decision=VALIDATED|INVALIDATED|MORE_INFO_REQUESTED
        OU withdrawn_at par le soumetteur tant qu'aucune décision n'est prise

    CHECK polymorphique exclusif (B40-J1 §6 étape 4 — décision PS-9) :
        - workflow_type=AGGIR_FUNDING ⇒ evaluation_id NOT NULL, care_plan_id NULL
        - workflow_type=COORDINATION_DOSSIER ⇒ care_plan_id NOT NULL, evaluation_id NULL

    Sécurité (B40-J1 §6 étape 8) : RLS par tenant standard. Les valideurs externes
    (médecins, agents département) sont rattachés au tenant GCSMS via
    user_tenant_assignments avec un rôle dédié.
    """

    __tablename__ = "validation_requests"
    __table_args__ = (
        CheckConstraint(
            "(evaluation_id IS NOT NULL AND care_plan_id IS NULL "
            "AND workflow_type = 'AGGIR_FUNDING') "
            "OR (care_plan_id IS NOT NULL AND evaluation_id IS NULL "
            "AND workflow_type = 'COORDINATION_DOSSIER')",
            name="ck_validation_requests_polymorphic_object",
        ),
        Index("ix_validation_requests_tenant_evaluation", "tenant_id", "evaluation_id"),
        Index("ix_validation_requests_tenant_care_plan", "tenant_id", "care_plan_id"),
        Index(
            "ix_validation_requests_assigned_validator",
            "assigned_validator_user_id",
            "decision",
        ),
        Index("ix_validation_requests_previous_vr", "previous_vr_id"),
        {"comment": "Demandes de validation polymorphiques (Phase 4 bis B40-J1)"},
    )

    # === Clé primaire ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de la demande de validation",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # === Multi-tenant ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant propriétaire de cet enregistrement",
    )

    # === Objet validable polymorphe (B40-J1 — décision PS-9) ===

    workflow_type: Mapped[ValidationWorkflowType] = mapped_column(
        SQLEnum(
            ValidationWorkflowType,
            name="validation_workflow_type_enum",
            create_constraint=True,
        ),
        nullable=False,
        doc="Type de workflow de validation",
        info={
            "description": "Détermine quel objet est validé (évaluation ou plan d'aide)",
            "enum": [e.value for e in ValidationWorkflowType],
        },
    )

    evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_evaluations.id", ondelete="CASCADE"),
        nullable=True,
        doc="Évaluation faisant l'objet de la demande (NULL si workflow plan d'aide)",
    )

    care_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("care_plans.id", ondelete="CASCADE"),
        nullable=True,
        doc="Plan d'aide faisant l'objet de la demande (NULL si workflow évaluation)",
    )

    previous_vr_id: Mapped[int | None] = mapped_column(
        ForeignKey("validation_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="VR précédente dans la chaîne (interne→médical→financement). NULL si VR initiale.",
        info={
            "description": (
                "Chaînage explicite du relais de validation. Renseigné par "
                "transmit_medical / transmit_funding à la création du nouveau maillon."
            ),
        },
    )

    # === Étape du workflow ===

    stage: Mapped[ValidationStage] = mapped_column(
        SQLEnum(
            ValidationStage,
            name="validation_stage_enum",
            create_constraint=True,
        ),
        nullable=False,
        doc="Étape courante du workflow",
        info={
            "description": (
                "INTERNAL_REVIEW (admin GCSMS), MEDICAL_REVIEW (médecin externe), "
                "FUNDING_REVIEW (département)"
            ),
            "enum": [e.value for e in ValidationStage],
        },
    )

    # === Acteurs ===

    submitted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        doc="Utilisateur ayant soumis la demande (IDEC en cas initial)",
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Date et heure de soumission",
    )

    assigned_validator_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Valideur assigné à cette étape (NULL si non encore assigné)",
    )

    # === Issue ===

    decision: Mapped[ValidationDecision | None] = mapped_column(
        SQLEnum(
            ValidationDecision,
            name="validation_decision_enum",
            create_constraint=True,
        ),
        nullable=True,
        doc="Décision finale du valideur (NULL tant que pas tranchée)",
        info={
            "description": "VALIDATED, INVALIDATED, MORE_INFO_REQUESTED, WITHDRAWN",
            "enum": [e.value for e in ValidationDecision],
        },
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure de la décision",
    )

    decided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc=(
            "Utilisateur ayant pris la décision (peut différer du valideur assigné en mode dégradé)"
        ),
    )

    decided_on_behalf_of: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc=("Nom du valideur externe au nom duquel l'admin GCSMS a saisi en mode dégradé"),
        info={
            "description": (
                "Mode dégradé département (roadmap §Workflow étape 7) : l'admin "
                "retranscrit une décision reçue par courrier/mail"
            ),
            "example": "Conseil Départemental de la Seine-Saint-Denis",
        },
    )

    # === Motifs ===

    decision_motif: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Motif libre de la décision (obligatoire en cas d'invalidation)",
    )

    invalidation_reason: Mapped[InvalidationReason | None] = mapped_column(
        SQLEnum(
            InvalidationReason,
            name="invalidation_reason_enum",
            create_constraint=True,
        ),
        nullable=True,
        doc="Catégorie structurée du motif d'invalidation",
        info={
            "description": "INCOMPLETE_INFO, CLINICAL_DISAGREEMENT, OUT_OF_SCOPE, OTHER",
            "enum": [e.value for e in InvalidationReason],
        },
    )

    info_request_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Message libre du valideur quand decision=MORE_INFO_REQUESTED",
    )

    # === Retrait (par le soumetteur tant qu'aucune décision) ===

    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date et heure du retrait par le soumetteur",
    )

    withdrawn_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Utilisateur ayant retiré la soumission (typiquement = submitted_by)",
    )

    withdrawal_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Motif libre du retrait (oubli, mauvais destinataire, données manquantes)",
    )

    # === Pièces jointes (B40-J1 — Option I, structure verrouillée en J5) ===

    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Pièces jointes du dossier de validation (preuves, CR examens, formulaires)",
        info={
            "description": (
                "Liste de descripteurs de fichiers. Structure exacte verrouillée en "
                "B40-J5. Cas d'usage V1 : preuve PDF en mode dégradé département, "
                "CR médecin spécialiste pour invalidation médicale, formulaire à "
                "remplir en MORE_INFO_REQUESTED, documents en appui de recours."
            ),
        },
    )

    # === Audit ===

    notes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
        doc="Notes d'audit horodatées (convention #109)",
    )

    # === Relations ===

    tenant: Mapped[Tenant] = relationship("Tenant", doc="Tenant propriétaire")

    evaluation: Mapped[PatientEvaluation | None] = relationship(
        "PatientEvaluation",
        foreign_keys=[evaluation_id],
        doc="Évaluation faisant l'objet de la demande",
    )

    care_plan: Mapped[CarePlan | None] = relationship(
        "CarePlan",
        foreign_keys=[care_plan_id],
        doc="Plan d'aide faisant l'objet de la demande",
    )

    previous_vr: Mapped[ValidationRequest | None] = relationship(
        "ValidationRequest",
        remote_side=[id],
        foreign_keys=[previous_vr_id],
        doc="Maillon précédent de la chaîne de validation",
    )

    exchanges: Mapped[list[ValidationExchange]] = relationship(
        "ValidationExchange",
        back_populates="validation_request",
        order_by="ValidationExchange.created_at",
        cascade="all, delete-orphan",
        doc="Entrées du fil d'échange rattachées à cette VR",
    )

    submitted_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[submitted_by_user_id],
        doc="Utilisateur ayant soumis la demande",
    )

    assigned_validator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_validator_user_id],
        doc="Valideur assigné à cette étape",
    )

    decided_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[decided_by_user_id],
        doc="Utilisateur ayant pris la décision",
    )

    withdrawn_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[withdrawn_by_user_id],
        doc="Utilisateur ayant retiré la soumission",
    )

    # === Propriétés ===

    @property
    def is_decided(self) -> bool:
        """Indique si une décision finale a été prise."""
        return self.decision is not None

    @property
    def is_withdrawn(self) -> bool:
        """Indique si la demande a été retirée par le soumetteur."""
        return self.withdrawn_at is not None

    @property
    def is_pending(self) -> bool:
        """Indique si la demande est en attente de décision."""
        return self.decision is None and self.withdrawn_at is None

    @property
    def is_polymorphic_target_evaluation(self) -> bool:
        """Indique si la cible est une évaluation."""
        return self.workflow_type == ValidationWorkflowType.AGGIR_FUNDING

    @property
    def is_polymorphic_target_care_plan(self) -> bool:
        """Indique si la cible est un plan d'aide."""
        return self.workflow_type == ValidationWorkflowType.COORDINATION_DOSSIER

    def __repr__(self) -> str:
        target = "eval" if self.is_polymorphic_target_evaluation else "plan"
        target_id = (
            self.evaluation_id if self.is_polymorphic_target_evaluation else self.care_plan_id
        )
        return (
            f"<ValidationRequest(id={self.id}, {target}_id={target_id}, stage={self.stage.value})>"
        )
