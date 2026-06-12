"""
Table de jonction Role ↔ Permission.

Ce module définit la table `role_permissions` qui associe les rôles
à leurs permissions de manière normalisée.

Avantages :
- Traçabilité : qui a accordé quelle permission, quand
- Intégrité : contraintes FK empêchent les données orphelines
- Requêtes efficaces : index sur les FK
- Multi-tenant : permissions héritées ou spécifiques
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base


if TYPE_CHECKING:
    from app.models.tenants.tenant import Tenant
    from app.models.user.permission import Permission
    from app.models.user.role import Role
    from app.models.user.user import User


class RolePermission(Base):
    """
    Association entre un rôle et une permission.

    Table de jonction many-to-many entre `roles` et `permissions`.
    Inclut des métadonnées de traçabilité.

    Attributes:
        role_id: ID du rôle
        permission_id: ID de la permission
        tenant_id: Tenant propriétaire de cette association
        granted_at: Date d'attribution de la permission au rôle
        granted_by_id: Utilisateur ayant accordé cette permission

    Notes:
        - Pour les rôles système (tenant_id=NULL sur le rôle), les associations
          sont aussi sans tenant_id et sont partagées par tous.
        - Un tenant peut créer des rôles custom avec ses propres associations.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        {"comment": "Table de jonction Role ↔ Permission (many-to-many)"},
    )

    # === Clé primaire ===
    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'association",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # === Clés étrangères ===

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID du rôle",
        info={"description": "Référence vers le rôle"},
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID de la permission",
        info={"description": "Référence vers la permission"},
    )

    # === Multi-tenant ===
    # NULL pour les associations des rôles système
    tenant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Tenant propriétaire (NULL = association système)",
        info={"description": "Clé étrangère vers le tenant"},
    )

    # === Traçabilité ===

    granted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Date et heure d'attribution de la permission",
        info={"description": "Timestamp de l'attribution", "auto_generated": True},
    )

    granted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant accordé cette permission",
        info={"description": "Référence vers l'administrateur (NULL = système)"},
    )

    # === Relations ===

    role: Mapped["Role"] = relationship(
        "Role", back_populates="permission_associations", doc="Rôle concerné"
    )

    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_associations", doc="Permission accordée"
    )

    granted_by: Mapped["User | None"] = relationship(
        "User", doc="Utilisateur ayant accordé cette permission"
    )

    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant", doc="Tenant propriétaire de cette association"
    )

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"

    def __str__(self) -> str:
        return f"{self.role.name} → {self.permission.code}"


# =============================================================================
# ASSOCIATIONS INITIALES - Rôles fonctionnels ↔ Permissions (S3)
# =============================================================================
# 5 rôles fonctionnels purs. Les permissions de base liées au diplôme
# seront portées par les professions (S4, via profession_permissions).
# Format: role_name -> liste des codes de permissions

INITIAL_ROLE_PERMISSIONS = {
    "ADMIN": [
        "ADMIN_FULL"  # Donne accès à tout — court-circuit appliqué dans User.effective_permission_codes
    ],
    "COORDINATEUR": [
        "PATIENT_VIEW",
        "PATIENT_CREATE",
        "PATIENT_EDIT",
        "EVALUATION_VIEW",
        "EVALUATION_CREATE",
        "COORDINATION_VIEW",
        "COORDINATION_CREATE",
        "COORDINATION_EDIT",
        "CAREPLAN_VIEW",
        "CAREPLAN_CREATE",
        "CAREPLAN_EDIT",
        "CAREPLAN_VALIDATE",
        "USER_VIEW",
        "ACCESS_GRANT",
        "ACCESS_REVOKE",
        "ROLE_VIEW",
        "ROLE_ASSIGN",
        # 🆕 B48 Palier 0 — Orchestration planning + lecture catalogue
        "CATALOG_VIEW",
        "SCHEDULE_VIEW",
        "SCHEDULE_CREATE",
        "SCHEDULE_EDIT",
        "SCHEDULE_EXECUTE",
        # 🆕 B40-J1 — Lecture du portail valideur (cf. cadrage Phase 4 bis §8)
        "VALIDATION_VIEW",
        # 🆕 B40-J2 — Soumission + retrait de soumission (cycle interne, D14 v2)
        "VALIDATION_SUBMIT",
        "VALIDATION_WITHDRAW",
    ],
    "REFERENT": [
        "PATIENT_VIEW",
        "PATIENT_EDIT",
        "EVALUATION_VIEW",
        "EVALUATION_CREATE",
        "COORDINATION_VIEW",
        "COORDINATION_CREATE",
        "COORDINATION_EDIT",
        "CAREPLAN_VIEW",
        # 🆕 B48 Palier 0 — Lecture catalogue + lecture planning des patients référés
        "CATALOG_VIEW",
        "SCHEDULE_VIEW",
        # 🆕 B40-J1 — Lecture du portail valideur (cf. cadrage Phase 4 bis §8)
        "VALIDATION_VIEW",
    ],
    "EVALUATEUR": [
        "PATIENT_VIEW",
        "EVALUATION_VIEW",
        "EVALUATION_CREATE",
        "EVALUATION_VALIDATE",
        "VITALS_VIEW",
        # 🆕 B48 Palier 0 — Consultation pendant évaluation
        "CATALOG_VIEW",
        "SCHEDULE_VIEW",
        # 🆕 B40-J1 — Lecture du portail valideur (cf. cadrage Phase 4 bis §8)
        "VALIDATION_VIEW",
    ],
    "INTERVENANT": [
        "PATIENT_VIEW",
        "VITALS_VIEW",
        "COORDINATION_VIEW",
        # 🆕 B48 Palier 0 — Lecture explicite (les actions EXECUTE viennent de la profession)
        "CATALOG_VIEW",
        "SCHEDULE_VIEW",
    ],
    # 🆕 B40-J1 — Profils externes Phase 4 bis (portail valideur générique)
    "VALIDATEUR_DEPARTMENT": [
        # Agent département : voit les demandes APA en FUNDING_REVIEW et tranche
        # (validation/refus/demande info). Pas d'accès à PATIENT/EVALUATION
        # complète — la fiche évaluation est consultée depuis ValidationRequest.
        "VALIDATION_VIEW",
        # 🆕 B40-J2 — Décision financement département. Gating uniforme par étape :
        # decide() vérifie VALIDATION_{stage}_REVIEW selon le stage de la VR
        # (cf. cadrage §8 / §7.3). Remplace la note J1 qui s'appuyait sur un
        # check stage-only dans le service, au profit d'une permission dédiée.
        "VALIDATION_FUNDING_REVIEW",
    ],
    "FAMILY_REFERENT": [
        # Compte famille : lecture minimisée d'un patient + notifications.
        # Le filtrage par patient est porté par family_referent_links (RLS).
        # PATIENT_VIEW_MINIMAL est défini en V1 comme un sous-ensemble logique
        # de PATIENT_VIEW — pour V1 on accorde PATIENT_VIEW et le service
        # backend applique la minimisation côté serializer (cf. plan B40-J7).
        "PATIENT_VIEW",
        "VALIDATION_VIEW",
    ],
}
