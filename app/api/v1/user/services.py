"""
Services métier pour le module User.

Contient la logique CRUD pour :
- ProfessionService (données partagées - pas de tenant)
- RoleService (données par tenant)
- UserService (données par tenant)
- UserAvailabilityService (hérite du tenant via user)

MULTI-TENANT: Les opérations sur User et Role sont filtrées par tenant_id.

v4.3: Architecture permissions normalisée (Permission + RolePermission)
"""
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.user.user import User
from app.models.user.role import Role
from app.models.user.profession import Profession
from app.models.user.user_associations import UserRole, UserEntity
from app.models.user.user_availability import UserAvailability
from app.models.user.permission import Permission  # AJOUT v4.3
from app.models.user.role_permission import RolePermission  # AJOUT v4.3
from app.models.enums import PermissionCategory  # AJOUT v4.3

from app.api.v1.user.schemas import (
    ProfessionCreate, ProfessionUpdate,
    RoleCreate, RoleUpdate,
    UserCreate, UserUpdate, UserFilters,
    UserEntityCreate, UserEntityUpdate,
    UserRoleCreate,
    UserAvailabilityCreate, UserAvailabilityUpdate,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""
    pass


class RoleNotFoundError(Exception):
    """Rôle non trouvé."""
    pass


class ProfessionNotFoundError(Exception):
    """Profession non trouvée."""
    pass


class AvailabilityNotFoundError(Exception):
    """Disponibilité non trouvée."""
    pass


class EntityNotFoundError(Exception):
    """Entité non trouvée."""
    pass


class DuplicateEmailError(Exception):
    """Email déjà utilisé."""
    pass


class DuplicateRPPSError(Exception):
    """RPPS déjà utilisé."""
    pass


class DuplicateProfessionNameError(Exception):
    """Nom de profession déjà utilisé."""
    pass


class DuplicateProfessionCodeError(Exception):
    """Code de profession déjà utilisé."""
    pass


class DuplicateRoleNameError(Exception):
    """Nom de rôle déjà utilisé."""
    pass


class SystemRoleModificationError(Exception):
    """Tentative de modification d'un rôle système."""
    pass


class UserAlreadyHasRoleError(Exception):
    """L'utilisateur a déjà ce rôle."""
    pass


class UserEntityAlreadyExistsError(Exception):
    """L'utilisateur est déjà rattaché à cette entité."""
    pass


# =============================================================================
# PROFESSION SERVICE (DONNÉES PARTAGÉES - PAS DE TENANT)
# =============================================================================

class ProfessionService:
    """
    Service pour la gestion des professions.

    NOTE: Les professions sont des données de référence partagées entre tous les tenants
    (pas de filtrage par tenant_id).
    """

    @staticmethod
    def get_all(
            db: Session,
            page: int = 1,
            size: int = 50,
            category: Optional[str] = None,
    ) -> Tuple[List[Profession], int]:
        """Liste toutes les professions avec pagination."""
        query = select(Profession)

        if category:
            query = query.where(Profession.category == category.upper())

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar() or 0

        # Pagination
        query = query.order_by(Profession.name)
        query = query.offset((page - 1) * size).limit(size)

        items = db.execute(query).scalars().all()
        return list(items), total

    @staticmethod
    def get_by_id(db: Session, profession_id: int) -> Profession:
        """Récupère une profession par son ID."""
        profession = db.get(Profession, profession_id)
        if not profession:
            raise ProfessionNotFoundError(f"Profession {profession_id} non trouvée")
        return profession

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[Profession]:
        """Récupère une profession par son code."""
        query = select(Profession).where(Profession.code == code)
        return db.execute(query).scalar_one_or_none()

    @staticmethod
    def create(db: Session, data: ProfessionCreate) -> Profession:
        """Crée une nouvelle profession."""
        # Vérifier unicité du nom
        existing = db.execute(
            select(Profession).where(Profession.name == data.name)
        ).scalar_one_or_none()
        if existing:
            raise DuplicateProfessionNameError(f"Profession '{data.name}' existe déjà")

        # Vérifier unicité du code
        if data.code:
            existing_code = db.execute(
                select(Profession).where(Profession.code == data.code)
            ).scalar_one_or_none()
            if existing_code:
                raise DuplicateProfessionCodeError(f"Code '{data.code}' déjà utilisé")

        profession = Profession(**data.model_dump())
        db.add(profession)
        db.commit()
        db.refresh(profession)
        return profession

    @staticmethod
    def update(db: Session, profession_id: int, data: ProfessionUpdate) -> Profession:
        """Met à jour une profession."""
        profession = ProfessionService.get_by_id(db, profession_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier unicité du nom
        if "name" in update_data and update_data["name"] != profession.name:
            existing = db.execute(
                select(Profession).where(Profession.name == update_data["name"])
            ).scalar_one_or_none()
            if existing:
                raise DuplicateProfessionNameError(f"Profession '{update_data['name']}' existe déjà")

        # Vérifier unicité du code
        if "code" in update_data and update_data["code"] != profession.code:
            if update_data["code"]:
                existing_code = db.execute(
                    select(Profession).where(Profession.code == update_data["code"])
                ).scalar_one_or_none()
                if existing_code:
                    raise DuplicateProfessionCodeError(f"Code '{update_data['code']}' déjà utilisé")

        for field, value in update_data.items():
            setattr(profession, field, value)

        db.commit()
        db.refresh(profession)
        return profession

    @staticmethod
    def delete(db: Session, profession_id: int) -> None:
        """Supprime une profession."""
        profession = ProfessionService.get_by_id(db, profession_id)
        db.delete(profession)
        db.commit()


# =============================================================================
# ROLE SERVICE (MULTI-TENANT)
# =============================================================================

class RoleService:
    """
    Service pour la gestion des rôles.

    MULTI-TENANT: Les rôles sont filtrés par tenant_id.
    Les rôles système (is_system_role=True) sont partagés.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """
        Retourne une requête de base.

        Inclut les rôles du tenant ET les rôles système partagés.
        """
        return select(Role).where(
            or_(
                Role.tenant_id == self.tenant_id,
                Role.is_system_role == True  # Rôles système partagés
            )
        )

    def get_all(
            self,
            page: int = 1,
            size: int = 50,
            is_system_role: Optional[bool] = None,
    ) -> Tuple[List[Role], int]:
        """Liste tous les rôles avec pagination."""
        query = self._base_query()

        if is_system_role is not None:
            query = query.where(Role.is_system_role == is_system_role)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Pagination
        query = query.order_by(Role.name)
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, role_id: int) -> Role:
        """Récupère un rôle par son ID."""
        query = self._base_query().where(Role.id == role_id)
        role = self.db.execute(query).scalar_one_or_none()
        if not role:
            raise RoleNotFoundError(f"Rôle {role_id} non trouvé")
        return role

    def get_by_name(self, name: str) -> Optional[Role]:
        """Récupère un rôle par son nom."""
        query = self._base_query().where(Role.name == name)
        return self.db.execute(query).scalar_one_or_none()

    def create(self, data: RoleCreate) -> Role:
        """
        Crée un nouveau rôle.

        MULTI-TENANT: Injecte automatiquement le tenant_id.
        v4.3: Les permissions sont gérées via RolePermission.
        """
        # Vérifier unicité du nom (dans le tenant + rôles système)
        existing = self.get_by_name(data.name)
        if existing:
            raise DuplicateRoleNameError(f"Rôle '{data.name}' existe déjà")

        # Extraire permissions avant création (v4.3)
        role_data = data.model_dump()
        permission_codes = role_data.pop("permissions", [])

        # Créer le rôle sans permissions
        role = Role(
            tenant_id=self.tenant_id,  # AUTO-INJECTION DU TENANT
            **role_data
        )
        self.db.add(role)
        self.db.flush()  # Pour obtenir l'ID

        # Créer les associations RolePermission (v4.3)
        self._set_role_permissions(role, permission_codes)

        self.db.commit()
        self.db.refresh(role)
        return role

    def _get_or_create_permission(self, code: str) -> Permission:
        """Récupère ou crée une permission (v4.3)."""
        perm = self.db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            # Déterminer la catégorie selon le préfixe
            if code.startswith("PATIENT") or code.startswith("EVALUATION") or code.startswith("VITALS"):
                cat = PermissionCategory.PATIENT
            elif code.startswith("USER"):
                cat = PermissionCategory.USER
            elif code.startswith("ENTITY"):
                cat = PermissionCategory.ORGANIZATION
            elif code.startswith("CAREPLAN"):
                cat = PermissionCategory.CAREPLAN
            elif code.startswith("COORDINATION"):
                cat = PermissionCategory.COORDINATION
            elif code.startswith("ADMIN"):
                cat = PermissionCategory.ADMIN
            else:
                cat = PermissionCategory.SYSTEM

            perm = Permission(
                code=code,
                name=code.replace("_", " ").title(),
                description=f"Permission {code}",
                category=cat
            )
            self.db.add(perm)
            self.db.flush()
        return perm

    def _set_role_permissions(self, role: Role, permission_codes: List[str]) -> None:
        """Définit les permissions d'un rôle (v4.3)."""
        # Supprimer les anciennes associations
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role.id
        ).delete()

        # Créer les nouvelles associations
        for code in permission_codes:
            perm = self._get_or_create_permission(code)
            role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
            self.db.add(role_perm)

    def update(self, role_id: int, data: RoleUpdate) -> Role:
        """Met à jour un rôle (v4.3)."""
        role = self.get_by_id(role_id)

        # Protection des rôles système
        if role.is_system_role:
            # On autorise uniquement la modification de la description
            update_data = data.model_dump(exclude_unset=True)
            allowed = {"description"}
            forbidden = set(update_data.keys()) - allowed
            if forbidden:
                raise SystemRoleModificationError(
                    f"Les rôles système ne peuvent pas être modifiés (champs: {forbidden})"
                )

        update_data = data.model_dump(exclude_unset=True)

        # Extraire permissions si présentes (v4.3)
        permission_codes = update_data.pop("permissions", None)

        # Vérifier unicité du nom
        if "name" in update_data and update_data["name"] != role.name:
            existing = self.get_by_name(update_data["name"])
            if existing:
                raise DuplicateRoleNameError(f"Rôle '{update_data['name']}' existe déjà")

        # Mettre à jour les champs simples
        for field, value in update_data.items():
            setattr(role, field, value)

        # Mettre à jour les permissions si spécifiées (v4.3)
        if permission_codes is not None:
            self._set_role_permissions(role, permission_codes)

        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role_id: int) -> None:
        """Supprime un rôle."""
        role = self.get_by_id(role_id)

        if role.is_system_role:
            raise SystemRoleModificationError("Les rôles système ne peuvent pas être supprimés")

        self.db.delete(role)
        self.db.commit()


# =============================================================================
# USER SERVICE (MULTI-TENANT)
# =============================================================================

class UserService:
    """
    Service pour la gestion des utilisateurs.

    MULTI-TENANT: Toutes les opérations sont filtrées par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant."""
        return select(User).where(User.tenant_id == self.tenant_id)

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            sort_by: str = "last_name",
            sort_order: str = "asc",
            filters: Optional[UserFilters] = None,
    ) -> Tuple[List[User], int]:
        """
        Liste les utilisateurs avec pagination et filtres.

        MULTI-TENANT: Filtre automatiquement par tenant_id.
        """
        query = self._base_query().options(
            selectinload(User.profession),
            selectinload(User.role_associations).selectinload(UserRole.role),
        )

        if filters:
            if filters.profession_id:
                query = query.where(User.profession_id == filters.profession_id)

            if filters.is_active is not None:
                query = query.where(User.is_active == filters.is_active)

            if filters.is_admin is not None:
                query = query.where(User.is_admin == filters.is_admin)

            if filters.entity_id:
                query = query.join(User.entity_associations).where(
                    UserEntity.entity_id == filters.entity_id,
                    UserEntity.end_date.is_(None)
                )

            if filters.role_name:
                query = query.join(User.role_associations).join(UserRole.role).where(
                    Role.name == filters.role_name
                )

            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                        User.email.ilike(search_term),
                        User.rpps.ilike(search_term),
                    )
                )

        # Count
        count_subquery = query.with_only_columns(User.id).distinct().subquery()
        count_query = select(func.count()).select_from(count_subquery)
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(User, sort_by, User.last_name)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().unique().all()
        return list(items), total

    def get_by_id(self, user_id: int, load_relations: bool = True) -> User:
        """
        Récupère un utilisateur par son ID.

        MULTI-TENANT: Vérifie que l'utilisateur appartient au tenant courant.
        """
        if load_relations:
            query = self._base_query().options(
                selectinload(User.profession),
                selectinload(User.role_associations).selectinload(UserRole.role),
                selectinload(User.entity_associations).selectinload(UserEntity.entity),
            ).where(User.id == user_id)
            user = self.db.execute(query).scalar_one_or_none()
        else:
            query = self._base_query().where(User.id == user_id)
            user = self.db.execute(query).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email (dans le tenant)."""
        query = self._base_query().where(User.email == email)
        return self.db.execute(query).scalar_one_or_none()

    def get_by_rpps(self, rpps: str) -> Optional[User]:
        """Récupère un utilisateur par son RPPS (dans le tenant)."""
        query = self._base_query().where(User.rpps == rpps)
        return self.db.execute(query).scalar_one_or_none()

    def create(self, data: UserCreate) -> User:
        """
        Crée un nouvel utilisateur.

        MULTI-TENANT: Injecte automatiquement le tenant_id.
        """
        # Vérifier unicité email (dans le tenant)
        if self.get_by_email(data.email):
            raise DuplicateEmailError(f"Email '{data.email}' déjà utilisé")

        # Vérifier unicité RPPS (dans le tenant)
        if data.rpps and self.get_by_rpps(data.rpps):
            raise DuplicateRPPSError(f"RPPS '{data.rpps}' déjà utilisé")

        # Vérifier profession existe
        if data.profession_id:
            profession = self.db.get(Profession, data.profession_id)
            if not profession:
                raise ProfessionNotFoundError(f"Profession {data.profession_id} non trouvée")

        # Créer l'utilisateur avec tenant_id auto-injecté
        user_data = data.model_dump(exclude={"password"})
        user = User(
            tenant_id=self.tenant_id,  # AUTO-INJECTION DU TENANT
            **user_data
        )

        # Hash du mot de passe si fourni
        if data.password:
            from app.core.hashing import hash_password
            user.password_hash = hash_password(data.password)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, data: UserUpdate) -> User:
        """Met à jour un utilisateur."""
        user = self.get_by_id(user_id, load_relations=False)

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})

        # Vérifier unicité email
        if "email" in update_data and update_data["email"] != user.email:
            if self.get_by_email(update_data["email"]):
                raise DuplicateEmailError(f"Email '{update_data['email']}' déjà utilisé")

        # Vérifier unicité RPPS
        if "rpps" in update_data and update_data["rpps"] != user.rpps:
            if update_data["rpps"] and self.get_by_rpps(update_data["rpps"]):
                raise DuplicateRPPSError(f"RPPS '{update_data['rpps']}' déjà utilisé")

        # Vérifier profession existe
        if "profession_id" in update_data and update_data["profession_id"]:
            profession = self.db.get(Profession, update_data["profession_id"])
            if not profession:
                raise ProfessionNotFoundError(f"Profession {update_data['profession_id']} non trouvée")

        for field, value in update_data.items():
            setattr(user, field, value)

        # Hash du mot de passe si fourni
        if data.password:
            from app.core.hashing import hash_password
            user.password_hash = hash_password(data.password)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> None:
        """Désactive un utilisateur (soft delete)."""
        user = self.get_by_id(user_id, load_relations=False)
        user.is_active = False
        self.db.commit()

    # --- Gestion des rôles ---

    def add_role(self, user_id: int, role_id: int, assigned_by: Optional[int] = None) -> UserRole:
        """Attribue un rôle à un utilisateur."""
        user = self.get_by_id(user_id, load_relations=False)

        # Le RoleService vérifie que le rôle appartient au tenant
        role_service = RoleService(self.db, self.tenant_id)
        role = role_service.get_by_id(role_id)

        # Vérifier si déjà attribué
        existing = self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        ).scalar_one_or_none()

        if existing:
            raise UserAlreadyHasRoleError(f"L'utilisateur a déjà le rôle '{role.name}'")

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            assigned_by=assigned_by,
            assigned_at=datetime.now(timezone.utc)
        )
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role

    def remove_role(self, user_id: int, role_id: int) -> None:
        """Retire un rôle à un utilisateur."""
        user_role = self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        ).scalar_one_or_none()

        if not user_role:
            raise RoleNotFoundError(f"L'utilisateur n'a pas ce rôle")

        self.db.delete(user_role)
        self.db.commit()

    # --- Gestion des entités ---

    def add_entity(self, user_id: int, data: UserEntityCreate) -> UserEntity:
        """Rattache un utilisateur à une entité."""
        from app.models.organization.entity import Entity

        user = self.get_by_id(user_id, load_relations=False)

        # Vérifier entité existe ET appartient au tenant
        entity = self.db.execute(
            select(Entity).where(
                Entity.id == data.entity_id,
                Entity.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier si déjà rattaché
        existing = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id,
                UserEntity.entity_id == data.entity_id
            )
        ).scalar_one_or_none()

        if existing:
            raise UserEntityAlreadyExistsError(
                f"L'utilisateur est déjà rattaché à cette entité"
            )

        # Si c'est la première entité ou marqué comme primaire, s'assurer qu'il n'y a qu'un seul primaire
        if data.is_primary:
            self.db.execute(
                select(UserEntity).where(
                    UserEntity.user_id == user_id,
                    UserEntity.is_primary == True
                )
            )
            # Retirer le flag primaire des autres
            for ue in self.db.execute(
                    select(UserEntity).where(
                        UserEntity.user_id == user_id,
                        UserEntity.is_primary == True
                    )
            ).scalars().all():
                ue.is_primary = False

        user_entity = UserEntity(
            user_id=user_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            **data.model_dump()
        )
        self.db.add(user_entity)
        self.db.commit()
        self.db.refresh(user_entity)
        return user_entity

    def update_entity(self, user_id: int, entity_id: int, data: UserEntityUpdate) -> UserEntity:
        """Met à jour le rattachement à une entité."""
        user_entity = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id,
                UserEntity.entity_id == entity_id
            )
        ).scalar_one_or_none()

        if not user_entity:
            raise EntityNotFoundError(f"Rattachement non trouvé")

        update_data = data.model_dump(exclude_unset=True)

        # Gérer le flag primaire
        if update_data.get("is_primary"):
            for ue in self.db.execute(
                    select(UserEntity).where(
                        UserEntity.user_id == user_id,
                        UserEntity.is_primary == True,
                        UserEntity.entity_id != entity_id
                    )
            ).scalars().all():
                ue.is_primary = False

        for field, value in update_data.items():
            setattr(user_entity, field, value)

        self.db.commit()
        self.db.refresh(user_entity)
        return user_entity

    def remove_entity(self, user_id: int, entity_id: int) -> None:
        """Détache un utilisateur d'une entité."""
        user_entity = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id,
                UserEntity.entity_id == entity_id
            )
        ).scalar_one_or_none()

        if not user_entity:
            raise EntityNotFoundError(f"Rattachement non trouvé")

        self.db.delete(user_entity)
        self.db.commit()


# =============================================================================
# USER AVAILABILITY SERVICE
# =============================================================================

class UserAvailabilityService:
    """
    Service pour la gestion des disponibilités.

    NOTE: Les disponibilités héritent du tenant via l'utilisateur.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _verify_user_access(self, user_id: int) -> User:
        """Vérifie que l'utilisateur appartient au tenant."""
        user = self.db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == self.tenant_id
            )
        ).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")
        return user

    def get_all_for_user(
            self,
            user_id: int,
            entity_id: Optional[int] = None,
            day_of_week: Optional[int] = None,
            is_active: Optional[bool] = None,
    ) -> List[UserAvailability]:
        """Liste les disponibilités d'un utilisateur."""
        # Vérifier que l'utilisateur appartient au tenant
        self._verify_user_access(user_id)

        query = select(UserAvailability).where(UserAvailability.user_id == user_id)

        if entity_id:
            query = query.where(UserAvailability.entity_id == entity_id)

        if day_of_week:
            query = query.where(UserAvailability.day_of_week == day_of_week)

        if is_active is not None:
            query = query.where(UserAvailability.is_active == is_active)

        query = query.order_by(UserAvailability.day_of_week, UserAvailability.start_time)

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, availability_id: int, user_id: int) -> UserAvailability:
        """Récupère une disponibilité par son ID."""
        # Vérifier que l'utilisateur appartient au tenant
        self._verify_user_access(user_id)

        availability = self.db.get(UserAvailability, availability_id)
        if not availability or availability.user_id != user_id:
            raise AvailabilityNotFoundError(f"Disponibilité {availability_id} non trouvée")
        return availability

    def create(self, user_id: int, data: UserAvailabilityCreate) -> UserAvailability:
        """Crée une disponibilité pour un utilisateur."""
        # Vérifier utilisateur appartient au tenant
        self._verify_user_access(user_id)

        # Vérifier entité existe et appartient au tenant si spécifiée
        if data.entity_id:
            from app.models.organization.entity import Entity
            entity = self.db.execute(
                select(Entity).where(
                    Entity.id == data.entity_id,
                    Entity.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()
            if not entity:
                raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        availability = UserAvailability(
            user_id=user_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            **data.model_dump()
        )
        self.db.add(availability)
        self.db.commit()
        self.db.refresh(availability)
        return availability

    def update(self, availability_id: int, user_id: int, data: UserAvailabilityUpdate) -> UserAvailability:
        """Met à jour une disponibilité."""
        availability = self.get_by_id(availability_id, user_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier entité existe si modifiée
        if "entity_id" in update_data and update_data["entity_id"]:
            from app.models.organization.entity import Entity
            entity = self.db.execute(
                select(Entity).where(
                    Entity.id == update_data["entity_id"],
                    Entity.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()
            if not entity:
                raise EntityNotFoundError(f"Entité {update_data['entity_id']} non trouvée")

        for field, value in update_data.items():
            setattr(availability, field, value)

        self.db.commit()
        self.db.refresh(availability)
        return availability

    def delete(self, availability_id: int, user_id: int) -> None:
        """Supprime une disponibilité."""
        availability = self.get_by_id(availability_id, user_id)
        self.db.delete(availability)
        self.db.commit()