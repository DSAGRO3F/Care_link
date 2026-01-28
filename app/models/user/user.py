"""
Modèle User - Utilisateurs/Professionnels de santé.

Ce module définit la table `users` qui représente les utilisateurs
de CareLink (professionnels de santé et administratifs).
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Set

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user.profession import Profession
    from app.models.user.role import Role
    from app.models.user.permission import Permission
    from app.models.organization.entity import Entity
    from app.models.patient.patient import Patient
    from app.models.user.user_associations import UserRole, UserEntity
    from app.models.careplan.care_plan import CarePlan
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.user.user_availability import UserAvailability
    from app.models.coordination.scheduled_intervention import ScheduledIntervention
    from app.models.tenants.tenant import Tenant
    from app.models.user.user_tenant_assignment import UserTenantAssignment


class User(TimestampMixin, Base):
    """
    Représente un utilisateur (professionnel de santé ou administratif).

    Les utilisateurs sont identifiés de manière unique par leur email
    et optionnellement par leur numéro RPPS (professionnels de santé).

    Attributes:
        id: Identifiant unique
        email: Email de connexion (unique)
        first_name: Prénom
        last_name: Nom de famille
        rpps: Numéro RPPS (11 chiffres, optionnel)
        profession: Profession réglementée
        roles: Rôles fonctionnels (many-to-many)
        entities: Entités de rattachement (many-to-many)
        is_admin: Est administrateur système
        is_active: Compte actif
    """

    __tablename__ = "users"
    __table_args__ = {
        "comment": "Table des utilisateurs (professionnels de santé et administratifs)"
    }

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'utilisateur",
        info={"description": "Clé primaire auto-incrémentée"}
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Adresse email unique de connexion",
        info={
            "description": "Email professionnel",
            "format": "email",
            "pii": True,
            "example": "marie.dupont@ssiad.fr"
        }
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Prénom de l'utilisateur",
        info={"description": "Prénom", "pii": True, "example": "Marie"}
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom de famille de l'utilisateur",
        info={"description": "Nom de famille", "pii": True, "example": "Dupont"}
    )

    rpps: Mapped[str | None] = mapped_column(
        String(11),
        unique=True,
        nullable=True,
        index=True,
        doc="Numéro RPPS du professionnel de santé",
        info={
            "description": "Répertoire Partagé des Professionnels de Santé (11 chiffres)",
            "pattern": "^[0-9]{11}$",
            "example": "12345678901"
        }
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Hash bcrypt du mot de passe (si authentification locale)",
        info={"description": "Hash du mot de passe pour auth locale", "sensitive": True}
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="L'utilisateur est-il administrateur système ?",
        info={"description": "True = accès administrateur complet", "default": False}
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Le compte utilisateur est-il actif ?",
        info={"description": "False = compte désactivé, connexion impossible", "default": True}
    )

    last_login: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date et heure de dernière connexion",
        info={"description": "Timestamp de la dernière authentification réussie"}
    )

    # === Clés étrangères ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID du tenant propriétaire",
        info={
            "description": "Référence vers le tenant (client) propriétaire de cette entité"
        }
    )

    profession_id: Mapped[int | None] = mapped_column(
        ForeignKey("professions.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de la profession réglementée",
        info={"description": "Référence vers la profession"}
    )

    # === Relations ===

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
        doc="Tenant propriétaire de cet utilisateur"
    )

    profession: Mapped["Profession | None"] = relationship(
        "Profession",
        back_populates="users",
        doc="Profession réglementée de l'utilisateur"
    )

    # IMPORTANT: foreign_keys spécifié car UserRole a 2 FK vers users (user_id et assigned_by)
    role_associations: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[UserRole.user_id]",
        doc="Associations avec les rôles (via table de jonction)"
    )

    entity_associations: Mapped[List["UserEntity"]] = relationship(
        "UserEntity",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Associations avec les entités (via table de jonction)"
    )

    # Patients dont cet utilisateur est médecin traitant
    patients_as_medecin: Mapped[List["Patient"]] = relationship(
        "Patient",
        back_populates="medecin_traitant",
        foreign_keys="[Patient.medecin_traitant_id]",
        doc="Patients dont cet utilisateur est le médecin traitant"
    )

    validated_care_plans: Mapped[List["CarePlan"]] = relationship(
        "CarePlan",
        foreign_keys="[CarePlan.validated_by_id]",
        back_populates="validated_by",
        doc="Plans d'aide validés par cet utilisateur"
    )

    assigned_services: Mapped[List["CarePlanService"]] = relationship(
        "CarePlanService",
        foreign_keys="[CarePlanService.assigned_user_id]",
        back_populates="assigned_user",
        doc="Services de plans d'aide affectés à cet utilisateur"
    )

    availabilities: Mapped[List["UserAvailability"]] = relationship(
        "UserAvailability",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Disponibilités de cet utilisateur"
    )

    scheduled_interventions: Mapped[List["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        foreign_keys="[ScheduledIntervention.user_id]",
        back_populates="user",
        doc="Interventions planifiées pour cet utilisateur"
    )

    # Rattachements à d'autres tenants (cross-tenant)
    tenant_assignments: Mapped[List["UserTenantAssignment"]] = relationship(
        "UserTenantAssignment",
        foreign_keys="[UserTenantAssignment.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Rattachements à d'autres tenants (missions temporaires, remplacements)"
    )

    # === Propriétés ===

    @property
    def full_name(self) -> str:
        """Nom complet (Prénom Nom)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Nom d'affichage avec titre professionnel si applicable."""
        if self.profession and self.profession.name == "Médecin":
            return f"Dr. {self.last_name}"
        return self.full_name

    @property
    def roles(self) -> List["Role"]:
        """Liste des rôles de l'utilisateur."""
        return [ra.role for ra in self.role_associations]

    @property
    def role_names(self) -> List[str]:
        """Liste des noms de rôles de l'utilisateur."""
        return [r.name for r in self.roles]

    @property
    def entities(self) -> List["Entity"]:
        """Liste des entités actives de l'utilisateur."""
        return [ea.entity for ea in self.entity_associations if ea.end_date is None]

    @property
    def primary_entity(self) -> "Entity | None":
        """Entité principale de rattachement."""
        for ea in self.entity_associations:
            if ea.is_primary and ea.end_date is None:
                return ea.entity
        # Si pas de primaire, retourne la première active
        active = [ea for ea in self.entity_associations if ea.end_date is None]
        return active[0].entity if active else None

    @property
    def permissions(self) -> List["Permission"]:
        """
        Liste de toutes les permissions de l'utilisateur (via ses rôles).
        
        Returns:
            Liste des objets Permission uniques
        """
        seen_ids: Set[int] = set()
        permissions: List["Permission"] = []
        
        for role in self.roles:
            for perm in role.permissions:
                if perm.id not in seen_ids:
                    seen_ids.add(perm.id)
                    permissions.append(perm)
        
        return permissions

    @property
    def all_permissions(self) -> Set[str]:
        """
        Ensemble de tous les codes de permissions de l'utilisateur.
        
        Utilise les relations normalisées (Role → RolePermission → Permission).
        
        Returns:
            Set des codes de permissions (ex: {"PATIENT_VIEW", "USER_EDIT"})
        """
        permission_codes: Set[str] = set()
        
        for role in self.roles:
            permission_codes.update(role.permission_codes)
        
        return permission_codes

    @property
    def all_tenant_ids(self) -> List[int]:
        """
        Liste tous les tenant_ids accessibles par cet utilisateur.

        Inclut :
        - Le tenant principal (users.tenant_id)
        - Les tenants via user_tenant_assignments (si valides)

        Returns:
            Liste des tenant_ids accessibles
        """
        tenant_ids = [self.tenant_id]  # Tenant principal
        for assignment in self.tenant_assignments:
            if assignment.is_valid:
                tenant_ids.append(assignment.tenant_id)
        return tenant_ids

    def has_access_to_tenant(self, target_tenant_id: int) -> bool:
        """
        Vérifie si l'utilisateur a accès à un tenant spécifique.

        Args:
            target_tenant_id: ID du tenant à vérifier

        Returns:
            True si l'utilisateur a accès
        """
        return target_tenant_id in self.all_tenant_ids

    # === Méthodes ===

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', rpps='{self.rpps}')>"

    def __str__(self) -> str:
        return self.full_name

    def has_permission(self, permission_code: str) -> bool:
        """
        Vérifie si l'utilisateur possède une permission spécifique.
        
        Args:
            permission_code: Code de la permission à vérifier
            
        Returns:
            True si l'utilisateur a la permission
        """
        if self.is_admin:
            return True

        # ADMIN_FULL donne toutes les permissions
        if "ADMIN_FULL" in self.all_permissions:
            return True

        return permission_code in self.all_permissions

    def has_any_permission(self, permission_codes: List[str]) -> bool:
        """
        Vérifie si l'utilisateur possède au moins une des permissions.
        
        Args:
            permission_codes: Liste des codes de permissions à vérifier
            
        Returns:
            True si l'utilisateur a au moins une des permissions
        """
        if self.is_admin:
            return True
            
        if "ADMIN_FULL" in self.all_permissions:
            return True

        return any(code in self.all_permissions for code in permission_codes)

    def has_all_permissions(self, permission_codes: List[str]) -> bool:
        """
        Vérifie si l'utilisateur possède toutes les permissions.
        
        Args:
            permission_codes: Liste des codes de permissions à vérifier
            
        Returns:
            True si l'utilisateur a toutes les permissions
        """
        if self.is_admin:
            return True
            
        if "ADMIN_FULL" in self.all_permissions:
            return True

        return all(code in self.all_permissions for code in permission_codes)

    def has_role(self, role_name: str) -> bool:
        """Vérifie si l'utilisateur a un rôle spécifique."""
        return role_name in self.role_names

    def belongs_to_entity(self, entity_id: int) -> bool:
        """Vérifie si l'utilisateur appartient à une entité."""
        return any(e.id == entity_id for e in self.entities)
