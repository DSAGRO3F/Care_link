"""
Modèle User - Utilisateurs/Professionnels de santé.

Ce module définit la table `users` qui représente les utilisateurs
de CareLink (professionnels de santé et administratifs).

Changement v4.8 : Harmonisation encryption
- Colonne `email` → `email_encrypted` (alignement convention BaseEncryptor)
- Colonne `rpps` → `rpps_encrypted` (alignement convention BaseEncryptor)
- Properties `email` / `rpps` ajoutées pour rétro-compatibilité transitoire
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base
from app.models.mixins import TimestampMixin
from app.models.user.profession_permissions import get_profession_permissions  # S4


if TYPE_CHECKING:
    from app.models.careplan.care_plan import CarePlan
    from app.models.careplan.care_plan_service import CarePlanService
    from app.models.coordination.scheduled_intervention import ScheduledIntervention
    from app.models.organization.entity import Entity
    from app.models.patient.patient import Patient
    from app.models.tenants.tenant import Tenant
    from app.models.user.permission import Permission
    from app.models.user.profession import Profession
    from app.models.user.role import Role
    from app.models.user.user_associations import UserEntity, UserRole
    from app.models.user.user_availability import UserAvailability
    from app.models.user.user_tenant_assignment import UserTenantAssignment


class User(TimestampMixin, Base):
    """
    Représente un utilisateur (professionnel de santé ou administratif).

    Les utilisateurs sont identifiés de manière unique par leur email
    et optionnellement par leur numéro RPPS (professionnels de santé).

    Convention de nommage (v4.8) :
    - Colonnes chiffrées : {field}_encrypted (ex: email_encrypted)
    - Colonnes blind index : {field}_blind (ex: email_blind)
    - Properties d'accès : {field} (ex: .email) — rétro-compatibilité

    Attributes:
        id: Identifiant unique
        email_encrypted: Email chiffré (AES-256-GCM)
        email_blind: Blind index email (HMAC-SHA256)
        first_name: Prénom
        last_name: Nom de famille
        rpps_encrypted: Numéro RPPS chiffré (AES-256-GCM)
        rpps_blind: Blind index RPPS (HMAC-SHA256)
        profession: Profession réglementée
        roles: Rôles fonctionnels (many-to-many)
        entities: Entités de rattachement (many-to-many)
        is_admin: Est administrateur système
        is_active: Compte actif
        must_change_password: Force le changement de mot de passe
    """

    __tablename__ = "users"
    __table_args__ = (
        # Unicité sur les blind indexes (par tenant)
        Index("ix_users_email_blind_tenant", "email_blind", "tenant_id", unique=True),
        Index(
            "ix_users_rpps_blind_tenant",
            "rpps_blind",
            "tenant_id",
            unique=True,
            postgresql_where=text("rpps_blind IS NOT NULL"),
        ),
        {"comment": "Table des utilisateurs (professionnels de santé et administratifs)"},
    )

    # === Colonnes ===

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Identifiant unique de l'utilisateur",
        info={"description": "Clé primaire auto-incrémentée"},
    )

    # --- Champs chiffrés (convention v4.8 : {field}_encrypted) ---

    email_encrypted: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Adresse email chiffrée (AES-256-GCM)",
        info={
            "description": "Email professionnel (chiffré)",
            "format": "email",
            "pii": True,
            "encrypted": True,
            "example": "marie.dupont@ssiad.fr",
        },
    )

    email_blind: Mapped[str | None] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Blind index de l'email pour recherche",
        info={
            "description": "HMAC-SHA256 de l'email normalisé pour recherche sans déchiffrement",
            "internal": True,
        },
    )

    rpps_encrypted: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Numéro RPPS chiffré (AES-256-GCM)",
        info={
            "description": "RPPS (chiffré)",
            "pattern": "^[0-9]{11}$",
            "encrypted": True,
            "example": "12345678901",
        },
    )

    rpps_blind: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Blind index du RPPS pour recherche",
        info={
            "description": "HMAC-SHA256 du RPPS pour recherche sans déchiffrement",
            "internal": True,
        },
    )

    # --- Champs en clair ---

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Prénom de l'utilisateur",
        info={"description": "Prénom", "pii": True, "example": "Marie"},
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom de famille de l'utilisateur",
        info={"description": "Nom de famille", "pii": True, "example": "Dupont"},
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Hash bcrypt du mot de passe (si authentification locale)",
        info={"description": "Hash du mot de passe pour auth locale", "sensitive": True},
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="L'utilisateur est-il administrateur système ?",
        info={"description": "True = accès administrateur complet", "default": False},
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Le compte utilisateur est-il actif ?",
        info={"description": "False = compte désactivé, connexion impossible", "default": True},
    )

    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        doc="Force le changement de mot de passe à la prochaine connexion",
        info={
            "description": "True = redirection vers changement de mot de passe au login",
            "default": False,
        },
    )

    last_login: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Date et heure de dernière connexion",
        info={"description": "Timestamp de la dernière authentification réussie"},
    )

    # === Sécurité anti-brute-force ===
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        server_default=text("0"),
        nullable=False,
        doc="Nombre de tentatives de connexion échouées",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Date jusqu'à laquelle le compte est verrouillé"
    )

    # === Clés étrangères ===

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="ID du tenant propriétaire",
        info={"description": "Référence vers le tenant (client) propriétaire de cette entité"},
    )

    profession_id: Mapped[int | None] = mapped_column(
        ForeignKey("professions.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de la profession réglementée",
        info={"description": "Référence vers la profession"},
    )

    # === Relations ===

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="users", doc="Tenant propriétaire de cet utilisateur"
    )

    profession: Mapped["Profession | None"] = relationship(
        "Profession", back_populates="users", doc="Profession réglementée de l'utilisateur"
    )

    # IMPORTANT: foreign_keys spécifié car UserRole a 2 FK vers users (user_id et assigned_by)
    role_associations: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[UserRole.user_id]",
        doc="Associations avec les rôles (via table de jonction)",
    )

    entity_associations: Mapped[list["UserEntity"]] = relationship(
        "UserEntity",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Associations avec les entités (via table de jonction)",
    )

    # Patients dont cet utilisateur est médecin traitant
    patients_as_medecin: Mapped[list["Patient"]] = relationship(
        "Patient",
        back_populates="medecin_traitant",
        foreign_keys="[Patient.medecin_traitant_id]",
        doc="Patients dont cet utilisateur est le médecin traitant",
    )

    validated_care_plans: Mapped[list["CarePlan"]] = relationship(
        "CarePlan",
        foreign_keys="[CarePlan.validated_by_id]",
        back_populates="validated_by",
        doc="Plans d'aide validés par cet utilisateur",
    )

    assigned_services: Mapped[list["CarePlanService"]] = relationship(
        "CarePlanService",
        foreign_keys="[CarePlanService.assigned_user_id]",
        back_populates="assigned_user",
        doc="Services de plans d'aide affectés à cet utilisateur",
    )

    availabilities: Mapped[list["UserAvailability"]] = relationship(
        "UserAvailability",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Disponibilités de cet utilisateur",
    )

    scheduled_interventions: Mapped[list["ScheduledIntervention"]] = relationship(
        "ScheduledIntervention",
        foreign_keys="[ScheduledIntervention.user_id]",
        back_populates="user",
        doc="Interventions planifiées pour cet utilisateur",
    )

    # Rattachements à d'autres tenants (cross-tenant)
    tenant_assignments: Mapped[list["UserTenantAssignment"]] = relationship(
        "UserTenantAssignment",
        foreign_keys="[UserTenantAssignment.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Rattachements à d'autres tenants (missions temporaires, remplacements)",
    )

    # =========================================================================
    # PROPERTIES DE RÉTRO-COMPATIBILITÉ (v4.8 transitoire)
    #
    # Ces properties permettent au code existant de continuer à utiliser
    # user.email et user.rpps pendant la transition. Elles seront retirées
    # progressivement au fil des sprints suivants.
    # =========================================================================

    @property
    def email(self) -> str:
        """
        Accès à l'email (rétro-compatibilité).

        ATTENTION : retourne la valeur brute de email_encrypted.
        - Après expunge+decrypt : contient le clair
        - En session active : contient le chiffré AES
        """
        return self.email_encrypted

    @email.setter
    def email(self, value: str):
        """Setter pour rétro-compatibilité (expunge+decrypt)."""
        self.email_encrypted = value

    @property
    def rpps(self) -> str | None:
        """Accès au RPPS (rétro-compatibilité)."""
        return self.rpps_encrypted

    @rpps.setter
    def rpps(self, value: str | None):
        """Setter pour rétro-compatibilité."""
        self.rpps_encrypted = value

    # =========================================================================
    # PROPRIÉTÉS MÉTIER
    # =========================================================================

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
    def roles(self) -> list["Role"]:
        """Liste des rôles de l'utilisateur."""
        return [ra.role for ra in self.role_associations]

    @property
    def role_names(self) -> list[str]:
        """Liste des noms de rôles de l'utilisateur."""
        return [r.name for r in self.roles]

    @property
    def entities(self) -> list["Entity"]:
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
    def permissions(self) -> list["Permission"]:
        """
        Liste de toutes les permissions de l'utilisateur (via ses rôles).

        Returns:
            Liste des objets Permission uniques
        """
        seen_ids: set[int] = set()
        permissions: list[Permission] = []

        for role in self.roles:
            for perm in role.permissions:
                if perm.id not in seen_ids:
                    seen_ids.add(perm.id)
                    permissions.append(perm)

        return permissions

    @property
    def all_permissions(self) -> set[str]:
        """
        Ensemble de tous les codes de permissions de l'utilisateur.

        Utilise les relations normalisées (Role → RolePermission → Permission).

        Returns:
            Set des codes de permissions (ex: {"PATIENT_VIEW", "USER_EDIT"})
        """
        permission_codes: set[str] = set()

        for role in self.roles:
            permission_codes.update(role.permission_codes)

        return permission_codes

    @property
    def effective_permission_codes(self) -> set[str]:
        """
        Permissions effectives = profession (base) ∪ rôles (additifs).

        S4 — Résolution complète des permissions :
            1. Permissions héritées de la profession (diplôme)
            2. + Permissions apportées par les rôles fonctionnels
            3. Court-circuit si ADMIN_FULL détecté

        Returns:
            Set des codes de permissions effectives
        """
        perms: set[str] = set()

        # 1. Permissions de la profession (socle métier)
        if self.profession:
            perms.update(get_profession_permissions(self.profession))

        # 2. Permissions des rôles fonctionnels (additifs)
        for role in self.roles:
            role_perm_codes = role.permission_codes
            if "ADMIN_FULL" in role_perm_codes:
                return {"ADMIN_FULL"}  # Court-circuit admin
            perms.update(role_perm_codes)

        return perms

    @property
    def effective_permissions(self) -> list[str]:
        """
        Alias listé pour sérialisation Pydantic (approche B, S4).

        - Post-expunge : retourne le cache calculé par le service
        - En session : calcule à la volée via effective_permission_codes
        """
        if hasattr(self, "_cached_effective_permissions"):
            return self._cached_effective_permissions
        return sorted(self.effective_permission_codes)

    @property
    def all_tenant_ids(self) -> list[int]:
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

    @property
    def is_locked(self) -> bool:
        """Vérifie si le compte est actuellement verrouillé."""
        if not self.locked_until:
            return False
        return datetime.now(UTC) < self.locked_until

    def record_login_success(self) -> None:
        """Enregistre une connexion réussie."""
        self.last_login = datetime.now(UTC)
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login_failure(self, max_attempts: int = 5, lock_duration_minutes: int = 30) -> None:
        """
        Enregistre une tentative de connexion échouée.

        Args:
            max_attempts: Nombre max d'échecs avant verrouillage
            lock_duration_minutes: Durée du verrouillage en minutes
        """
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now(UTC) + timedelta(minutes=lock_duration_minutes)

    # === Méthodes ===

    def __repr__(self) -> str:
        # v4.8 : ne plus logger de données chiffrées
        return f"<User(id={self.id}, name='{self.full_name}', tenant={self.tenant_id})>"

    def __str__(self) -> str:
        return self.full_name

    def has_permission(self, permission_code: str) -> bool:
        """
        Vérifie si l'utilisateur possède une permission spécifique.

        S4 : utilise effective_permission_codes (profession + rôles).

        Args:
            permission_code: Code de la permission à vérifier

        Returns:
            True si l'utilisateur a la permission
        """
        if self.is_admin:
            return True

        # ADMIN_FULL donne toutes les permissions
        effective = self.effective_permission_codes
        if "ADMIN_FULL" in effective:
            return True

        return permission_code in effective

    def has_any_permission(self, permission_codes: list[str]) -> bool:
        """
        Vérifie si l'utilisateur possède au moins une des permissions.

        S4 : utilise effective_permission_codes (profession + rôles).

        Args:
            permission_codes: Liste des codes de permissions à vérifier

        Returns:
            True si l'utilisateur a au moins une des permissions
        """
        if self.is_admin:
            return True

        effective = self.effective_permission_codes
        if "ADMIN_FULL" in effective:
            return True

        return any(code in effective for code in permission_codes)

    def has_all_permissions(self, permission_codes: list[str]) -> bool:
        """
        Vérifie si l'utilisateur possède toutes les permissions.

        S4 : utilise effective_permission_codes (profession + rôles).

        Args:
            permission_codes: Liste des codes de permissions à vérifier

        Returns:
            True si l'utilisateur a toutes les permissions
        """
        if self.is_admin:
            return True

        effective = self.effective_permission_codes
        if "ADMIN_FULL" in effective:
            return True

        return all(code in effective for code in permission_codes)

    def has_role(self, role_name: str) -> bool:
        """Vérifie si l'utilisateur a un rôle spécifique."""
        return role_name in self.role_names

    def belongs_to_entity(self, entity_id: int) -> bool:
        """Vérifie si l'utilisateur appartient à une entité."""
        return any(e.id == entity_id for e in self.entities)
