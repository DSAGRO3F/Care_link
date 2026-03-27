"""
Service Platform Entity — Gestion des entités côté SuperAdmin.

Encapsule l'EntityService existant (module Organization) et ajoute
les validations spécifiques au contexte SuperAdmin :
- Vérification de l'existence du tenant avant toute opération
- Création de racines (GCSMS/GTSMS) avec unicité par tenant
- Protection contre la suppression de racines avec enfants
- Pas de RLS (session sans Row-Level Security)
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.organization.schemas import (
    EntityFilters,
    EntityUpdate,
)
from app.api.v1.platform.schemas import (
    ROOT_ENTITY_TYPES,
    PlatformEntityCreate,
)
from app.models.organization.entity import Entity
from app.models.reference.country import Country
from app.models.tenants.tenant import Tenant


# =============================================================================
# EXCEPTIONS MÉTIER (pattern Platform : exceptions classiques)
# =============================================================================


class TenantNotFoundForEntityError(Exception):
    """Tenant introuvable pour opération sur entité."""

    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant avec l'ID {tenant_id} introuvable")


class EntityNotFoundError(Exception):
    """Entité introuvable dans le tenant."""

    def __init__(self, entity_id: int, tenant_id: int):
        self.entity_id = entity_id
        self.tenant_id = tenant_id
        super().__init__(f"Entité {entity_id} introuvable dans le tenant {tenant_id}")


class RootAlreadyExistsError(Exception):
    """Le tenant a déjà une entité racine."""

    def __init__(self, tenant_id: int, existing_root_name: str):
        self.tenant_id = tenant_id
        self.existing_root_name = existing_root_name
        super().__init__(f"Le tenant {tenant_id} a déjà une entité racine : '{existing_root_name}'")


class CannotDeleteRootWithChildrenError(Exception):
    """Impossible de supprimer une racine qui a des enfants."""

    def __init__(self, entity_id: int, children_count: int):
        self.entity_id = entity_id
        self.children_count = children_count
        super().__init__(
            f"Impossible de supprimer l'entité racine {entity_id} : "
            f"elle a {children_count} entité(s) enfant(s). "
            f"Supprimez d'abord les enfants."
        )


class DuplicateFINESSError(Exception):
    """FINESS déjà utilisé."""

    def __init__(self, finess: str):
        self.finess = finess
        super().__init__(f"Le numéro FINESS {finess} est déjà utilisé par une autre entité")


class DuplicateSIRETError(Exception):
    """SIRET déjà utilisé."""

    def __init__(self, siret: str):
        self.siret = siret
        super().__init__(f"Le numéro SIRET {siret} est déjà utilisé par une autre entité")


class CountryNotFoundError(Exception):
    """Pays introuvable."""

    def __init__(self, country_id: int):
        self.country_id = country_id
        super().__init__(f"Pays avec l'ID {country_id} introuvable")


class CircularHierarchyError(Exception):
    """Hiérarchie circulaire détectée."""

    def __init__(self):
        super().__init__(
            "Impossible de créer une hiérarchie circulaire "
            "(une entité ne peut pas être son propre parent)"
        )


# =============================================================================
# SERVICE
# =============================================================================


class PlatformEntityService:
    """
    Service pour la gestion des entités d'un tenant, côté SuperAdmin.

    Contrairement à l'EntityService (module Organization) qui reçoit
    son tenant_id depuis l'utilisateur authentifié, ce service reçoit
    le tenant_id depuis l'URL (/platform/tenants/{tenant_id}/entities).

    Pas de RLS : le SuperAdmin accède à tous les tenants.

    Règles métier SuperAdmin :
    - 1 seule racine (GCSMS/GTSMS) par tenant
    - Les enfants sont auto-rattachés à la racine si parent non spécifié
    - Suppression d'une racine interdite si elle a des enfants
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        # Vérifier que le tenant existe dès l'instanciation
        self._verify_tenant_exists()

    # =========================================================================
    # VÉRIFICATIONS INTERNES
    # =========================================================================

    def _verify_tenant_exists(self) -> None:
        """Vérifie que le tenant existe et lève une exception sinon."""
        tenant = self.db.get(Tenant, self.tenant_id)
        if not tenant:
            raise TenantNotFoundForEntityError(self.tenant_id)

    def _base_query(self):
        """Requête de base filtrée par tenant_id."""
        return select(Entity).where(Entity.tenant_id == self.tenant_id)

    def _get_root_entity(self) -> Entity | None:
        """
        Récupère l'entité racine du tenant (si elle existe).

        Une racine est une entité de type GCSMS ou GTSMS
        sans parent_entity_id.
        """
        query = (
            self._base_query()
            .where(Entity.entity_type.in_([t.value for t in ROOT_ENTITY_TYPES]))
            .where(Entity.parent_entity_id.is_(None))
        )
        return self.db.execute(query).scalar_one_or_none()

    def _check_finess_unique(self, finess_et: str, *, exclude_id: int | None = None) -> None:
        """Vérifie l'unicité du FINESS ET (global, pas juste dans le tenant)."""
        query = select(Entity).where(Entity.finess_et == finess_et)
        if exclude_id:
            query = query.where(Entity.id != exclude_id)
        existing = self.db.execute(query).scalar_one_or_none()
        if existing:
            raise DuplicateFINESSError(finess_et)

    def _check_siret_unique(self, siret: str, *, exclude_id: int | None = None) -> None:
        """Vérifie l'unicité du SIRET (global)."""
        query = select(Entity).where(Entity.siret == siret)
        if exclude_id:
            query = query.where(Entity.id != exclude_id)
        existing = self.db.execute(query).scalar_one_or_none()
        if existing:
            raise DuplicateSIRETError(siret)

    def _check_country_exists(self, country_id: int) -> None:
        """Vérifie que le pays existe."""
        country = self.db.get(Country, country_id)
        if not country:
            raise CountryNotFoundError(country_id)

    def _count_children(self, entity_id: int) -> int:
        """Compte le nombre d'enfants directs d'une entité."""
        query = (
            select(func.count())
            .select_from(Entity)
            .where(Entity.parent_entity_id == entity_id)
            .where(Entity.tenant_id == self.tenant_id)
        )
        return self.db.execute(query).scalar_one()

    # =========================================================================
    # LECTURE
    # =========================================================================

    def get_all(
        self,
        *,
        page: int = 1,
        size: int = 20,
        sort_by: str | None = "name",
        sort_order: str = "asc",
        filters: EntityFilters | None = None,
    ) -> tuple[list[Entity], int]:
        """
        Liste paginée des entités du tenant avec filtres.

        Réplique la logique d'EntityService.get_all mais sans RLS.
        """
        query = self._base_query().options(
            selectinload(Entity.country),
            selectinload(Entity.parent_entity),
        )

        # Appliquer les filtres
        if filters:
            if filters.entity_type:
                query = query.where(Entity.entity_type == filters.entity_type)
            if filters.integration_type:
                query = query.where(Entity.integration_type == filters.integration_type)
            if filters.parent_entity_id:
                query = query.where(Entity.parent_entity_id == filters.parent_entity_id)
            if filters.country_id:
                query = query.where(Entity.country_id == filters.country_id)
            if filters.city:
                query = query.where(Entity.city.ilike(f"%{filters.city}%"))
            if filters.postal_code:
                query = query.where(Entity.postal_code.startswith(filters.postal_code))
            if filters.is_active is not None:
                query = query.where(Entity.is_active == filters.is_active)
            if filters.search:
                from sqlalchemy import or_

                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        Entity.name.ilike(search_term),
                        Entity.short_name.ilike(search_term),
                        Entity.finess_et.ilike(search_term),
                        Entity.finess_ej.ilike(search_term),
                        Entity.siret.ilike(search_term),
                    )
                )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Tri
        if sort_by and hasattr(Entity, sort_by):
            order_col = getattr(Entity, sort_by)
            if sort_order == "desc":
                order_col = order_col.desc()
            query = query.order_by(order_col)
        else:
            query = query.order_by(Entity.name)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, entity_id: int) -> Entity:
        """Récupère une entité par ID, avec ses relations."""
        query = (
            self._base_query()
            .where(Entity.id == entity_id)
            .options(
                selectinload(Entity.country),
                selectinload(Entity.parent_entity),
                selectinload(Entity.child_entities),
            )
        )
        entity = self.db.execute(query).scalar_one_or_none()
        if not entity:
            raise EntityNotFoundError(entity_id, self.tenant_id)
        return entity

    def get_children(self, entity_id: int) -> list[Entity]:
        """Récupère les enfants directs d'une entité."""
        # Vérifier que le parent existe dans ce tenant
        self.get_by_id(entity_id)

        query = self._base_query().where(Entity.parent_entity_id == entity_id).order_by(Entity.name)
        return list(self.db.execute(query).scalars().all())

    # =========================================================================
    # CRÉATION
    # =========================================================================

    def create(self, data: PlatformEntityCreate) -> Entity:
        """
        Crée une entité dans le tenant.

        Règles SuperAdmin :
        - Si type racine → vérifier qu'il n'y a pas déjà de racine
        - Si type enfant sans parent → auto-rattacher à la racine
        - Vérifier unicité FINESS/SIRET (global)
        - Vérifier existence du pays
        """
        is_root = data.entity_type in ROOT_ENTITY_TYPES

        # --- Validation racine unique ---
        if is_root:
            existing_root = self._get_root_entity()
            if existing_root:
                raise RootAlreadyExistsError(self.tenant_id, existing_root.name)

        # --- Auto-rattachement à la racine pour les enfants ---
        parent_entity_id = data.parent_entity_id
        if not is_root and parent_entity_id is None:
            root = self._get_root_entity()
            if root:
                parent_entity_id = root.id

        # --- Vérifier parent existe (si spécifié) ---
        if parent_entity_id is not None:
            self.get_by_id(parent_entity_id)

        # --- Unicité FINESS / SIRET ---
        if data.finess_et:
            self._check_finess_unique(data.finess_et)
        if data.siret:
            self._check_siret_unique(data.siret)

        # --- Vérifier pays ---
        self._check_country_exists(data.country_id)

        # --- Créer l'entité ---
        entity_data = data.model_dump(exclude={"parent_entity_id"})
        entity = Entity(
            tenant_id=self.tenant_id,
            parent_entity_id=parent_entity_id,  # Peut être modifié par auto-rattachement
            **entity_data,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)

        # Recharger avec relations
        return self.get_by_id(entity.id)

    # =========================================================================
    # MISE À JOUR
    # =========================================================================

    def update(self, entity_id: int, data: EntityUpdate) -> Entity:
        """
        Met à jour une entité.

        Mêmes validations que l'EntityService + protection du type racine.
        """
        entity = self.get_by_id(entity_id)
        update_data = data.model_dump(exclude_unset=True)

        # --- Interdire le changement de type d'une racine ---
        if entity.entity_type in ROOT_ENTITY_TYPES and "entity_type" in update_data:
            new_type = update_data["entity_type"]
            if new_type not in ROOT_ENTITY_TYPES:
                raise ValueError(
                    f"Impossible de changer le type d'une entité racine "
                    f"de {entity.entity_type.value} vers {new_type}"
                )

        # --- Vérifier unicité FINESS si modifié ---
        if update_data.get("finess_et"):
            self._check_finess_unique(update_data["finess_et"], exclude_id=entity_id)

        # --- Vérifier unicité SIRET si modifié ---
        if update_data.get("siret"):
            self._check_siret_unique(update_data["siret"], exclude_id=entity_id)

        # --- Vérifier hiérarchie circulaire ---
        if "parent_entity_id" in update_data:
            if update_data["parent_entity_id"] == entity_id:
                raise CircularHierarchyError()
            if update_data["parent_entity_id"] is not None:
                self.get_by_id(update_data["parent_entity_id"])

        # --- Vérifier pays si modifié ---
        if update_data.get("country_id"):
            self._check_country_exists(update_data["country_id"])

        # --- Appliquer les modifications ---
        for field, value in update_data.items():
            setattr(entity, field, value)

        self.db.commit()
        self.db.refresh(entity)

        # Recharger avec relations
        return self.get_by_id(entity.id)

    # =========================================================================
    # SUPPRESSION
    # =========================================================================

    def delete(self, entity_id: int) -> None:
        """
        Supprime une entité (soft delete via is_active=False).

        Règle SuperAdmin : une racine ne peut pas être supprimée
        si elle a des enfants.
        """
        entity = self.get_by_id(entity_id)

        # Protection racine avec enfants
        if entity.entity_type in ROOT_ENTITY_TYPES:
            children_count = self._count_children(entity_id)
            if children_count > 0:
                raise CannotDeleteRootWithChildrenError(entity_id, children_count)

        entity.is_active = False
        self.db.commit()
