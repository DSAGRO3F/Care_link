"""
Services métier pour le module Organization.

Contient la logique business séparée des routes HTTP.
Utilise les modèles SQLAlchemy existants.

MULTI-TENANT: Toutes les opérations sont filtrées par tenant_id.
"""
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload

# Import des modèles existants
from app.models.organization.entity import Entity
from app.models.reference.country import Country
from .schemas import (
    EntityCreate,
    EntityUpdate,
    EntityFilters,
    CountryCreate,
    CountryUpdate,
)


# =============================================================================
# EXCEPTIONS MÉTIER
# =============================================================================

class EntityNotFoundError(HTTPException):
    """Entité introuvable."""

    def __init__(self, entity_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entité avec l'ID {entity_id} introuvable"
        )


class CountryNotFoundError(HTTPException):
    """Pays introuvable."""

    def __init__(self, country_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pays avec l'ID {country_id} introuvable"
        )


class DuplicateFINESSError(HTTPException):
    """FINESS déjà utilisé."""

    def __init__(self, finess: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le numéro FINESS {finess} est déjà utilisé par une autre entité"
        )


class DuplicateSIRETError(HTTPException):
    """SIRET déjà utilisé."""

    def __init__(self, siret: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le numéro SIRET {siret} est déjà utilisé par une autre entité"
        )


class DuplicateCountryCodeError(HTTPException):
    """Code pays déjà utilisé."""

    def __init__(self, code: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le code pays {code} est déjà utilisé"
        )


class CircularHierarchyError(HTTPException):
    """Hiérarchie circulaire détectée."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de créer une hiérarchie circulaire (une entité ne peut pas être son propre parent)"
        )


# =============================================================================
# COUNTRY SERVICE
# =============================================================================

class CountryService:
    """
    Service pour la gestion des pays.

    NOTE: Les pays sont des données de référence partagées entre tous les tenants
    (pas de filtrage par tenant_id).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all(
            self,
            *,
            page: int = 1,
            size: int = 20,
            is_active: Optional[bool] = None,
    ) -> Tuple[List[Country], int]:
        """
        Récupère la liste paginée des pays.

        Args:
            page: Numéro de page (1-indexed)
            size: Nombre d'éléments par page
            is_active: Filtrer par statut actif

        Returns:
            Tuple (items, total_count)
        """
        query = select(Country)

        if is_active is not None:
            query = query.where(Country.is_active == is_active)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Paginate et trier
        query = query.order_by(Country.name)
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, country_id: int) -> Country:
        """Récupère un pays par son ID."""
        country = self.db.get(Country, country_id)
        if not country:
            raise CountryNotFoundError(country_id)
        return country

    def get_by_code(self, country_code: str) -> Optional[Country]:
        """Récupère un pays par son code ISO."""
        query = select(Country).where(Country.country_code == country_code.upper())
        return self.db.execute(query).scalar_one_or_none()

    def create(self, data: CountryCreate) -> Country:
        """Crée un nouveau pays."""
        # Vérifier unicité du code
        existing = self.get_by_code(data.country_code)
        if existing:
            raise DuplicateCountryCodeError(data.country_code)

        country = Country(**data.model_dump())
        self.db.add(country)
        self.db.commit()
        self.db.refresh(country)
        return country

    def update(self, country_id: int, data: CountryUpdate) -> Country:
        """Met à jour un pays."""
        country = self.get_by_id(country_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier unicité du code si modifié
        if 'country_code' in update_data and update_data['country_code']:
            existing = self.get_by_code(update_data['country_code'])
            if existing and existing.id != country_id:
                raise DuplicateCountryCodeError(update_data['country_code'])

        for field, value in update_data.items():
            setattr(country, field, value)

        self.db.commit()
        self.db.refresh(country)
        return country

    def delete(self, country_id: int) -> None:
        """Supprime un pays (soft delete via is_active)."""
        country = self.get_by_id(country_id)
        country.is_active = False
        self.db.commit()


# =============================================================================
# ENTITY SERVICE
# =============================================================================

class EntityService:
    """
    Service pour la gestion des entités.

    MULTI-TENANT: Toutes les opérations sont filtrées par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant courant (extrait de l'utilisateur authentifié)
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant."""
        return select(Entity).where(Entity.tenant_id == self.tenant_id)

    def get_all(
            self,
            *,
            page: int = 1,
            size: int = 20,
            sort_by: Optional[str] = "name",
            sort_order: str = "asc",
            filters: Optional[EntityFilters] = None,
    ) -> Tuple[List[Entity], int]:
        """
        Récupère la liste paginée des entités avec filtres.

        MULTI-TENANT: Filtre automatiquement par tenant_id.

        Args:
            page: Numéro de page
            size: Éléments par page
            sort_by: Champ de tri
            sort_order: 'asc' ou 'desc'
            filters: Filtres optionnels

        Returns:
            Tuple (items, total_count)
        """
        query = self._base_query().options(
            selectinload(Entity.country),
            selectinload(Entity.parent_entity)
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

        # Paginate
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, entity_id: int, *, load_relations: bool = True) -> Entity:
        """
        Récupère une entité par son ID.

        MULTI-TENANT: Vérifie que l'entité appartient au tenant courant.
        """
        if load_relations:
            query = self._base_query().where(Entity.id == entity_id).options(
                selectinload(Entity.country),
                selectinload(Entity.parent_entity),
                selectinload(Entity.child_entities)
            )
            entity = self.db.execute(query).scalar_one_or_none()
        else:
            query = self._base_query().where(Entity.id == entity_id)
            entity = self.db.execute(query).scalar_one_or_none()

        if not entity:
            raise EntityNotFoundError(entity_id)
        return entity

    def get_by_finess(self, finess_et: str) -> Optional[Entity]:
        """Récupère une entité par son FINESS établissement (dans le tenant courant)."""
        query = self._base_query().where(Entity.finess_et == finess_et)
        return self.db.execute(query).scalar_one_or_none()

    def get_by_siret(self, siret: str) -> Optional[Entity]:
        """Récupère une entité par son SIRET (dans le tenant courant)."""
        query = self._base_query().where(Entity.siret == siret)
        return self.db.execute(query).scalar_one_or_none()

    def get_children(self, entity_id: int) -> List[Entity]:
        """Récupère les entités enfants d'une entité parente."""
        # Vérifier que l'entité parente existe et appartient au tenant
        self.get_by_id(entity_id, load_relations=False)

        query = self._base_query().where(Entity.parent_entity_id == entity_id)
        query = query.order_by(Entity.name)
        return list(self.db.execute(query).scalars().all())

    def get_roots(self) -> List[Entity]:
        """Récupère les entités racines (sans parent) du tenant."""
        query = self._base_query().where(Entity.parent_entity_id.is_(None))
        query = query.options(selectinload(Entity.child_entities))
        query = query.order_by(Entity.name)
        return list(self.db.execute(query).scalars().all())

    def create(self, data: EntityCreate) -> Entity:
        """
        Crée une nouvelle entité.

        MULTI-TENANT: Injecte automatiquement le tenant_id.
        """
        # Vérifier unicité FINESS (dans le tenant)
        if data.finess_et:
            existing = self.get_by_finess(data.finess_et)
            if existing:
                raise DuplicateFINESSError(data.finess_et)

        # Vérifier unicité SIRET (dans le tenant)
        if data.siret:
            existing = self.get_by_siret(data.siret)
            if existing:
                raise DuplicateSIRETError(data.siret)

        # Vérifier que le parent existe (et appartient au tenant)
        if data.parent_entity_id:
            self.get_by_id(data.parent_entity_id, load_relations=False)

        # Vérifier que le pays existe
        country_service = CountryService(self.db)
        country_service.get_by_id(data.country_id)

        # Créer l'entité avec tenant_id auto-injecté
        entity = Entity(
            tenant_id=self.tenant_id,  # AUTO-INJECTION DU TENANT
            **data.model_dump()
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)

        # Recharger avec les relations
        return self.get_by_id(entity.id)

    def update(self, entity_id: int, data: EntityUpdate) -> Entity:
        """Met à jour une entité."""
        entity = self.get_by_id(entity_id, load_relations=False)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier unicité FINESS si modifié
        if 'finess_et' in update_data and update_data['finess_et']:
            existing = self.get_by_finess(update_data['finess_et'])
            if existing and existing.id != entity_id:
                raise DuplicateFINESSError(update_data['finess_et'])

        # Vérifier unicité SIRET si modifié
        if 'siret' in update_data and update_data['siret']:
            existing = self.get_by_siret(update_data['siret'])
            if existing and existing.id != entity_id:
                raise DuplicateSIRETError(update_data['siret'])

        # Vérifier que le nouveau parent n'est pas l'entité elle-même
        if 'parent_entity_id' in update_data:
            if update_data['parent_entity_id'] == entity_id:
                raise CircularHierarchyError()
            # Vérifier que le nouveau parent existe (et appartient au tenant)
            if update_data['parent_entity_id']:
                self.get_by_id(update_data['parent_entity_id'], load_relations=False)

        # Vérifier que le pays existe si modifié
        if 'country_id' in update_data and update_data['country_id']:
            country_service = CountryService(self.db)
            country_service.get_by_id(update_data['country_id'])

        for field, value in update_data.items():
            setattr(entity, field, value)

        self.db.commit()
        self.db.refresh(entity)

        # Recharger avec les relations
        return self.get_by_id(entity.id)

    def delete(self, entity_id: int) -> None:
        """
        Supprime une entité (soft delete via is_active).

        Note: Les entités enfants ne sont pas modifiées automatiquement.
        """
        entity = self.get_by_id(entity_id, load_relations=False)
        entity.is_active = False
        self.db.commit()

    def get_hierarchy(self, root_id: Optional[int] = None) -> List[Entity]:
        """
        Récupère l'arborescence des entités du tenant.

        Args:
            root_id: Si fourni, retourne l'arborescence depuis cette racine.
                     Sinon, retourne toutes les entités racines avec leurs enfants.

        Returns:
            Liste d'entités avec leurs enfants chargés
        """
        if root_id:
            entity = self.get_by_id(root_id)
            return [entity]
        else:
            return self.get_roots()