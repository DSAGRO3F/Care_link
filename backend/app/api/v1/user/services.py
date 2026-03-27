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

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.user.schemas import (
    ProfessionCreate,
    ProfessionUpdate,
    RoleCreate,
    RoleUpdate,
    UserAvailabilityCreate,
    UserAvailabilityUpdate,
    UserCreate,
    UserEntityCreate,
    UserEntityUpdate,
    UserFilters,
    UserUpdate,
)
from app.models.enums import PermissionCategory  # AJOUT v4.3
from app.models.user.permission import Permission  # AJOUT v4.3
from app.models.user.profession import Profession
from app.models.user.role import Role
from app.models.user.role_permission import RolePermission  # AJOUT v4.3
from app.models.user.user import User
from app.models.user.user_associations import UserEntity, UserRole
from app.models.user.user_availability import UserAvailability
from app.services.encryption import (
    get_user_search_blind,
    user_encryptor,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""


class RoleNotFoundError(Exception):
    """Rôle non trouvé."""


class ProfessionNotFoundError(Exception):
    """Profession non trouvée."""


class AvailabilityNotFoundError(Exception):
    """Disponibilité non trouvée."""


class EntityNotFoundError(Exception):
    """Entité non trouvée."""


class DuplicateEmailError(Exception):
    """Email déjà utilisé."""


class DuplicateRPPSError(Exception):
    """RPPS déjà utilisé."""


class DuplicateProfessionNameError(Exception):
    """Nom de profession déjà utilisé."""


class DuplicateProfessionCodeError(Exception):
    """Code de profession déjà utilisé."""


class DuplicateRoleNameError(Exception):
    """Nom de rôle déjà utilisé."""


class SystemRoleModificationError(Exception):
    """Tentative de modification d'un rôle système."""


class UserAlreadyHasRoleError(Exception):
    """L'utilisateur a déjà ce rôle."""


class UserEntityAlreadyExistsError(Exception):
    """L'utilisateur est déjà rattaché à cette entité."""


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
        category: str | None = None,
    ) -> tuple[list[Profession], int]:
        """Liste toutes les professions avec pagination."""
        query = select(Profession)

        if category:
            query = query.where(Profession.category == category.upper())

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar() or 0

        # Pagination
        query = query.order_by(Profession.display_order, Profession.name)
        query = query.offset((page - 1) * size).limit(size)

        items = db.execute(query).scalars().all()
        return list(items), total

    @staticmethod
    def get_by_id(db: Session, profession_id: int) -> Profession:
        """Récupère une profession par son ID."""
        profession: Profession | None = db.get(Profession, profession_id)
        if not profession:
            raise ProfessionNotFoundError(f"Profession {profession_id} non trouvée")
        return profession

    @staticmethod
    def get_by_code(db: Session, code: str) -> Profession | None:
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
                raise DuplicateProfessionNameError(
                    f"Profession '{update_data['name']}' existe déjà"
                )

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
                Role.is_system_role == True,  # Rôles système partagés
            )
        )

    def get_all(
        self,
        page: int = 1,
        size: int = 50,
        is_system_role: bool | None = None,
    ) -> tuple[list[Role], int]:
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

    def get_by_name(self, name: str) -> Role | None:
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
            **role_data,
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
            if code.startswith("PATIENT"):
                cat = PermissionCategory.PATIENT
            elif code.startswith("EVALUATION"):
                cat = PermissionCategory.EVALUATION
            elif code.startswith("VITALS"):
                cat = PermissionCategory.VITALS
            elif code.startswith("USER"):
                cat = PermissionCategory.USER
            elif code.startswith("ENTITY"):
                cat = PermissionCategory.ADMIN
            elif code.startswith("CAREPLAN"):
                cat = PermissionCategory.CAREPLAN
            elif code.startswith("COORDINATION"):
                cat = PermissionCategory.COORDINATION
            elif code.startswith("ADMIN"):
                cat = PermissionCategory.ADMIN
            else:
                cat = PermissionCategory.ADMIN

            perm = Permission(
                code=code,
                name=code.replace("_", " ").title(),
                description=f"Permission {code}",
                category=cat,
            )
            self.db.add(perm)
            self.db.flush()
        return perm

    def _set_role_permissions(self, role: Role, permission_codes: list[str]) -> None:
        """Définit les permissions d'un rôle (v4.3)."""
        # Supprimer les anciennes associations
        self.db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()

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

    def _get_raw(self, user_id: int, load_relations: bool = False) -> User:
        """
        Récupère un user chiffré, attaché à la session.
        Usage interne uniquement : mutations (update, delete, add_role, etc.)
        Ne PAS utiliser pour retourner à l'API → utiliser get_by_id() à la place.
        """
        query = self._base_query().where(User.id == user_id)
        if load_relations:
            query = query.options(
                selectinload(User.profession),
                selectinload(User.role_associations).selectinload(UserRole.role),
                selectinload(User.entity_associations).selectinload(UserEntity.entity),
            )
        user = self.db.execute(query).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")

        return user

    def _decrypt_and_detach(self, user: User) -> User:
        """
        Détache le user de la session SQLAlchemy, puis déchiffre email/rpps.
        L'objet retourné est READ-ONLY (ne plus faire de commit dessus).

        Pattern expunge+decrypt : empêche SQLAlchemy d'écraser le chiffré
        par le clair lors d'un autoflush.
        """
        self.db.expunge(user)
        decrypted = user_encryptor.decrypt_model(user)
        if decrypted.get("email"):
            user.email = decrypted["email"]
        if decrypted.get("rpps"):
            user.rpps = decrypted["rpps"]
        return user

    # ----------Lister les utilisateurs--------------

    def get_all(
        self,
        page: int = 1,
        size: int = 20,
        sort_by: str = "last_name",
        sort_order: str = "asc",
        filters: UserFilters | None = None,
    ) -> tuple[list[User], int]:
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
                    UserEntity.entity_id == filters.entity_id, UserEntity.end_date.is_(None)
                )

            if filters.role_name:
                query = (
                    query.join(User.role_associations)
                    .join(UserRole.role)
                    .where(Role.name == filters.role_name)
                )

            if filters.search:
                search_term = f"%{filters.search}%"
                # MODIFIÉ: Recherche textuelle uniquement sur nom/prénom (non chiffrés)
                # Email et RPPS sont chiffrés, on ne peut plus faire de recherche partielle
                # Email et RPPS -> supprimés de recherche sql
                query = query.where(
                    or_(
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
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

        # Expunge+decrypt chaque user pour le retour API
        decrypted_items = [self._decrypt_and_detach(user) for user in items]
        return decrypted_items, total

    # ----------Récupérer un utilisateur--------------

    def get_by_id(self, user_id: int, load_relations: bool = True) -> User:
        """
        Récupère un utilisateur par son ID.
        MULTI-TENANT: Vérifie que l'utilisateur appartient au tenant courant.
        CHIFFREMENT: email et rpps sont déchiffrés avant retour.
        """
        if load_relations:
            query = (
                self._base_query()
                .options(
                    selectinload(User.profession),
                    selectinload(User.role_associations).selectinload(UserRole.role),
                    selectinload(User.entity_associations).selectinload(UserEntity.entity),
                )
                .where(User.id == user_id)
            )
            user = self.db.execute(query).scalar_one_or_none()
        else:
            query = self._base_query().where(User.id == user_id)
            user = self.db.execute(query).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")

        # S4 : Calculer les permissions effectives AVANT expunge
        # (les relations profession/roles sont encore accessibles en session)
        user._cached_effective_permissions = sorted(user.effective_permission_codes)

        # Expunge+decrypt pour retour API sécurisé
        return self._decrypt_and_detach(user)

    # ----------Récupérer un utilisateur--------------

    def get_by_email(self, email: str) -> User | None:
        """
        Récupère un utilisateur par son email (dans le tenant).
        CHIFFREMENT: Utilise le blind index pour la recherche.
        """
        # Recherche par blind index
        email_blind = get_user_search_blind(email, "email", self.tenant_id)
        query = self._base_query().where(User.email_blind == email_blind)
        user = self.db.execute(query).scalar_one_or_none()

        if user:
            return self._decrypt_and_detach(user)
        return None

    # ----------Récupérer un utilisateur--------------

    def get_by_rpps(self, rpps: str) -> User | None:
        """
        Récupère un utilisateur par son RPPS (dans le tenant).
        CHIFFREMENT: Utilise le blind index pour la recherche.
        """
        # NOUVEAU: Recherche par blind index
        rpps_blind = get_user_search_blind(rpps, "rpps", self.tenant_id)
        query = self._base_query().where(User.rpps_blind == rpps_blind)
        user = self.db.execute(query).scalar_one_or_none()

        if user:
            return self._decrypt_and_detach(user)
        return None

    # ----------Créer un utilisateur--------------

    def create(self, data: UserCreate) -> User:
        """
        Crée un nouvel utilisateur.
        MULTI-TENANT: Injecte automatiquement le tenant_id.
        CHIFFREMENT: email et rpps sont chiffrés avant stockage.
        """
        # Vérifier unicité email (dans le tenant) - utilise blind index
        if self.get_by_email(data.email):
            raise DuplicateEmailError(f"Email '{data.email}' déjà utilisé")

        # Vérifier unicité RPPS (dans le tenant) - utilise blind index
        if data.rpps and self.get_by_rpps(data.rpps):
            raise DuplicateRPPSError(f"RPPS '{data.rpps}' déjà utilisé")

        # Vérifier profession existe
        if data.profession_id:
            profession: Profession | None = self.db.get(Profession, data.profession_id)
            if not profession:
                raise ProfessionNotFoundError(f"Profession {data.profession_id} non trouvée")

        # Préparer les données (exclure password)
        user_data = data.model_dump(exclude={"password"})

        # NOUVEAU: Chiffrer email et rpps + générer blind indexes
        encrypted_data = user_encryptor.encrypt_for_db(
            {"email": user_data.pop("email"), "rpps": user_data.pop("rpps", None)}, self.tenant_id
        )

        # Créer l'utilisateur avec données chiffrées
        user = User(
            tenant_id=self.tenant_id,
            **user_data,  # first_name, last_name, profession_id, etc.
            **encrypted_data,  # email (chiffré), email_blind, rpps (chiffré), rpps_blind
        )

        # Hash du mot de passe si fourni
        if data.password:
            from app.core.security.hashing import hash_password

            user.password_hash = hash_password(data.password)

        self.db.add(user)
        self.db.commit()

        # Recharger avec les relations nécessaires à la sérialisation
        user = self.db.execute(
            select(User)
            .options(
                selectinload(User.profession),
                selectinload(User.role_associations).selectinload(UserRole.role),
            )
            .where(User.id == user.id)
        ).scalar_one()

        # S4 : Calculer les permissions effectives AVANT expunge
        user._cached_effective_permissions = sorted(user.effective_permission_codes)

        # Expunge+decrypt pour le retour API
        return self._decrypt_and_detach(user)

    # ----------Mise à jour utilisateur--------------

    def update(self, user_id: int, data: UserUpdate) -> User:
        """
        Met à jour un utilisateur.
        CHIFFREMENT: Si email ou rpps modifiés, re-chiffrer avec nouveaux blind indexes.
        """
        # 1. Récupérer le user brut (chiffré, session-attached) — PAS de decrypt
        user = self._get_raw(user_id, load_relations=False)

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})

        # 2. Vérifier unicité email via blind index (comparaison par ID, pas par clair)
        if "email" in update_data:
            existing = self.get_by_email(update_data["email"])
            if existing and existing.id != user_id:
                raise DuplicateEmailError(f"Email '{update_data['email']}' déjà utilisé")

        # 3. Vérifier unicité RPPS via blind index (comparaison par ID)
        if update_data.get("rpps"):
            existing = self.get_by_rpps(update_data["rpps"])
            if existing and existing.id != user_id:
                raise DuplicateRPPSError(f"RPPS '{update_data['rpps']}' déjà utilisé")

        # 4. Vérifier profession existe
        if update_data.get("profession_id"):
            profession: Profession | None = self.db.get(Profession, update_data["profession_id"])
            if not profession:
                raise ProfessionNotFoundError(
                    f"Profession {update_data['profession_id']} non trouvée"
                )

        # 5. Chiffrer email/rpps si présents dans update_data
        if "email" in update_data or "rpps" in update_data:
            fields_to_encrypt = {}
            if "email" in update_data:
                fields_to_encrypt["email"] = update_data.pop("email")
            if "rpps" in update_data:
                fields_to_encrypt["rpps"] = update_data.pop("rpps")

            # Chiffrer + générer blind indexes
            encrypted_fields = user_encryptor.prepare_for_update(fields_to_encrypt, self.tenant_id)
            update_data.update(encrypted_fields)

        # 6. Appliquer les modifications (tout reste chiffré en session)
        for field, value in update_data.items():
            setattr(user, field, value)

        # Hash du mot de passe si fourni
        if data.password:
            from app.core.security.hashing import hash_password

            user.password_hash = hash_password(data.password)

        self.db.commit()

        # S4 : Recharger avec relations pour calculer effective_permissions
        # (remplace le simple refresh qui ne chargeait pas les relations)
        user = self.db.execute(
            select(User)
            .options(
                selectinload(User.profession),
                selectinload(User.role_associations).selectinload(UserRole.role),
            )
            .where(User.id == user.id)
        ).scalar_one()

        # S4 : Calculer les permissions effectives AVANT expunge
        user._cached_effective_permissions = sorted(user.effective_permission_codes)

        # 7. Détacher PUIS déchiffrer pour le retour API
        return self._decrypt_and_detach(user)

    # ----------Supprimer un utilisateur--------------

    def delete(self, user_id: int) -> None:
        """Désactive un utilisateur (soft delete)."""
        user = self._get_raw(user_id)
        user.is_active = False
        self.db.commit()

    # ----------Ajouter un rôle--------------

    def add_role(self, user_id: int, role_id: int, assigned_by: int | None = None) -> UserRole:
        """Attribue un rôle à un utilisateur."""
        self._get_raw(user_id)  # Vérifie existence + tenant

        # Le RoleService vérifie que le rôle appartient au tenant
        role_service = RoleService(self.db, self.tenant_id)
        role = role_service.get_by_id(role_id)

        # Vérifier si déjà attribué
        existing = self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        ).scalar_one_or_none()

        if existing:
            raise UserAlreadyHasRoleError(f"L'utilisateur a déjà le rôle '{role.name}'")

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            assigned_by=assigned_by,
            assigned_at=datetime.now(UTC),
        )
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role

    # ----------Enlever un rôle--------------

    def remove_role(self, user_id: int, role_id: int) -> None:
        """Retire un rôle à un utilisateur."""
        user_role = self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        ).scalar_one_or_none()

        if not user_role:
            raise RoleNotFoundError("L'utilisateur n'a pas ce rôle")

        self.db.delete(user_role)
        self.db.commit()

    # ----------Ajout entité--------------

    def add_entity(self, user_id: int, data: UserEntityCreate) -> UserEntity:
        """Rattache un utilisateur à une entité."""
        from app.models.organization.entity import Entity

        self._get_raw(user_id)  # Vérifie existence + tenant

        # Vérifier entité existe ET appartient au tenant
        entity = self.db.execute(
            select(Entity).where(Entity.id == data.entity_id, Entity.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier si déjà rattaché
        existing = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id, UserEntity.entity_id == data.entity_id
            )
        ).scalar_one_or_none()

        if existing:
            raise UserEntityAlreadyExistsError("L'utilisateur est déjà rattaché à cette entité")

        # Si c'est la première entité ou marqué comme primaire, s'assurer qu'il n'y a qu'un seul primaire
        if data.is_primary:
            self.db.execute(
                select(UserEntity).where(
                    UserEntity.user_id == user_id, UserEntity.is_primary == True
                )
            )
            # Retirer le flag primaire des autres
            for ue in (
                self.db.execute(
                    select(UserEntity).where(
                        UserEntity.user_id == user_id, UserEntity.is_primary == True
                    )
                )
                .scalars()
                .all()
            ):
                ue.is_primary = False

        user_entity = UserEntity(
            user_id=user_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            **data.model_dump(),
        )
        self.db.add(user_entity)
        self.db.commit()
        self.db.refresh(user_entity)
        return user_entity

    # ----------Mise à jour entité--------------

    def update_entity(self, user_id: int, entity_id: int, data: UserEntityUpdate) -> UserEntity:
        """Met à jour le rattachement à une entité."""
        user_entity = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id, UserEntity.entity_id == entity_id
            )
        ).scalar_one_or_none()

        if not user_entity:
            raise EntityNotFoundError("Rattachement non trouvé")

        update_data = data.model_dump(exclude_unset=True)

        # Gérer le flag primaire
        if update_data.get("is_primary"):
            for ue in (
                self.db.execute(
                    select(UserEntity).where(
                        UserEntity.user_id == user_id,
                        UserEntity.is_primary == True,
                        UserEntity.entity_id != entity_id,
                    )
                )
                .scalars()
                .all()
            ):
                ue.is_primary = False

        for field, value in update_data.items():
            setattr(user_entity, field, value)

        self.db.commit()
        self.db.refresh(user_entity)
        return user_entity

    # ----------Enlever entité--------------

    def remove_entity(self, user_id: int, entity_id: int) -> None:
        """Détache un utilisateur d'une entité."""
        user_entity = self.db.execute(
            select(UserEntity).where(
                UserEntity.user_id == user_id, UserEntity.entity_id == entity_id
            )
        ).scalar_one_or_none()

        if not user_entity:
            raise EntityNotFoundError("Rattachement non trouvé")

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
            select(User).where(User.id == user_id, User.tenant_id == self.tenant_id)
        ).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")
        return user

    def get_all_for_user(
        self,
        user_id: int,
        entity_id: int | None = None,
        day_of_week: int | None = None,
        is_active: bool | None = None,
    ) -> list[UserAvailability]:
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

        availability: UserAvailability | None = self.db.get(UserAvailability, availability_id)
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
                    Entity.id == data.entity_id, Entity.tenant_id == self.tenant_id
                )
            ).scalar_one_or_none()
            if not entity:
                raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        availability = UserAvailability(
            user_id=user_id,
            tenant_id=self.tenant_id,  # AJOUT v4.3
            **data.model_dump(),
        )
        self.db.add(availability)
        self.db.commit()
        self.db.refresh(availability)
        return availability

    def update(
        self, availability_id: int, user_id: int, data: UserAvailabilityUpdate
    ) -> UserAvailability:
        """Met à jour une disponibilité."""
        availability = self.get_by_id(availability_id, user_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier entité existe si modifiée
        if update_data.get("entity_id"):
            from app.models.organization.entity import Entity

            entity = self.db.execute(
                select(Entity).where(
                    Entity.id == update_data["entity_id"], Entity.tenant_id == self.tenant_id
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
