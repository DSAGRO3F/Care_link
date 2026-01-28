"""
Services métier pour le module Catalog.

Contient la logique CRUD pour :
- ServiceTemplateService (catalogue national - global, pas de tenant)
- EntityServiceService (services par entité - multi-tenant)

Version multi-tenant : EntityServiceService filtre par tenant_id.
"""
from typing import Optional, List, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.catalog.service_template import ServiceTemplate
from app.models.catalog.entity_service import EntityService
from app.models.organization.entity import Entity
from app.models.user.profession import Profession

from app.api.v1.catalog.schemas import (
    ServiceTemplateCreate, ServiceTemplateUpdate, ServiceTemplateFilters,
    EntityServiceCreate, EntityServiceUpdate,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ServiceTemplateNotFoundError(Exception):
    """Service template non trouvé."""
    pass


class EntityServiceNotFoundError(Exception):
    """Service d'entité non trouvé."""
    pass


class EntityNotFoundError(Exception):
    """Entité non trouvée."""
    pass


class ProfessionNotFoundError(Exception):
    """Profession non trouvée."""
    pass


class DuplicateServiceCodeError(Exception):
    """Code de service déjà existant."""
    pass


class DuplicateEntityServiceError(Exception):
    """Service déjà activé pour cette entité."""
    pass


# =============================================================================
# SERVICE TEMPLATE SERVICE (Catalogue national - Global, pas de tenant)
# =============================================================================

class ServiceTemplateService:
    """
    Service pour la gestion du catalogue de services.

    NOTE: Les ServiceTemplates sont des données de référence GLOBALES
    partagées entre tous les tenants (comme les professions, pays, etc.).
    Pas de filtrage par tenant_id.
    """

    @staticmethod
    def get_all(
            db: Session,
            page: int = 1,
            size: int = 50,
            sort_by: str = "display_order",
            sort_order: str = "asc",
            filters: Optional[ServiceTemplateFilters] = None,
    ) -> Tuple[List[ServiceTemplate], int]:
        """Liste les service templates avec pagination et filtres."""
        query = select(ServiceTemplate)

        if filters:
            if filters.category:
                query = query.where(ServiceTemplate.category == filters.category.upper())

            if filters.is_medical_act is not None:
                query = query.where(ServiceTemplate.is_medical_act == filters.is_medical_act)

            if filters.requires_prescription is not None:
                query = query.where(ServiceTemplate.requires_prescription == filters.requires_prescription)

            if filters.apa_eligible is not None:
                query = query.where(ServiceTemplate.apa_eligible == filters.apa_eligible)

            if filters.status:
                query = query.where(ServiceTemplate.status == filters.status.lower())

            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        ServiceTemplate.code.ilike(search_term),
                        ServiceTemplate.name.ilike(search_term),
                    )
                )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(ServiceTemplate, sort_by, ServiceTemplate.display_order)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = db.execute(query).scalars().all()
        return list(items), total

    @staticmethod
    def get_by_id(db: Session, template_id: int) -> ServiceTemplate:
        """Récupère un service template par son ID."""
        template = db.get(ServiceTemplate, template_id)
        if not template:
            raise ServiceTemplateNotFoundError(f"Service template {template_id} non trouvé")
        return template

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[ServiceTemplate]:
        """Récupère un service template par son code."""
        query = select(ServiceTemplate).where(ServiceTemplate.code == code.upper())
        return db.execute(query).scalar_one_or_none()

    @staticmethod
    def create(db: Session, data: ServiceTemplateCreate) -> ServiceTemplate:
        """Crée un nouveau service template."""
        # Vérifier unicité du code
        existing = ServiceTemplateService.get_by_code(db, data.code)
        if existing:
            raise DuplicateServiceCodeError(f"Le code '{data.code}' existe déjà")

        # Vérifier la profession si spécifiée (Profession est aussi global)
        if data.required_profession_id:
            profession = db.get(Profession, data.required_profession_id)
            if not profession:
                raise ProfessionNotFoundError(
                    f"Profession {data.required_profession_id} non trouvée"
                )

        template = ServiceTemplate(
            code=data.code.upper(),
            name=data.name,
            category=data.category,
            description=data.description,
            required_profession_id=data.required_profession_id,
            required_qualification=data.required_qualification,
            default_duration_minutes=data.default_duration_minutes,
            requires_prescription=data.requires_prescription,
            is_medical_act=data.is_medical_act,
            apa_eligible=data.apa_eligible,
            display_order=data.display_order,
            status="active",
        )

        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def update(db: Session, template_id: int, data: ServiceTemplateUpdate) -> ServiceTemplate:
        """Met à jour un service template."""
        template = ServiceTemplateService.get_by_id(db, template_id)

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier la profession si modifiée
        if "required_profession_id" in update_data and update_data["required_profession_id"]:
            profession = db.get(Profession, update_data["required_profession_id"])
            if not profession:
                raise ProfessionNotFoundError(
                    f"Profession {update_data['required_profession_id']} non trouvée"
                )

        for field, value in update_data.items():
            setattr(template, field, value)

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete(db: Session, template_id: int) -> None:
        """Désactive un service template (soft delete)."""
        template = ServiceTemplateService.get_by_id(db, template_id)
        template.status = "inactive"
        db.commit()

    @staticmethod
    def get_by_category(db: Session, category: str) -> List[ServiceTemplate]:
        """Récupère tous les services d'une catégorie."""
        query = select(ServiceTemplate).where(
            ServiceTemplate.category == category.upper(),
            ServiceTemplate.status == "active",
        ).order_by(ServiceTemplate.display_order)

        return list(db.execute(query).scalars().all())


# =============================================================================
# ENTITY SERVICE SERVICE (Multi-tenant)
# =============================================================================

class EntityServiceService:
    """
    Service pour la gestion des services par entité.

    Version multi-tenant : toutes les requêtes filtrent par tenant_id
    via la vérification que l'entité appartient au tenant.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec la session DB et le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant pour le filtrage multi-tenant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant_id."""
        return select(EntityService).where(EntityService.tenant_id == self.tenant_id)

    def _verify_entity_belongs_to_tenant(self, entity_id: int) -> Entity:
        """
        Vérifie qu'une entité appartient au tenant.

        Args:
            entity_id: ID de l'entité à vérifier

        Returns:
            Entity: L'entité si elle appartient au tenant

        Raises:
            EntityNotFoundError: Si l'entité n'existe pas ou n'appartient pas au tenant
        """
        entity_query = select(Entity).where(
            Entity.id == entity_id,
            Entity.tenant_id == self.tenant_id
        )
        entity = self.db.execute(entity_query).scalar_one_or_none()
        if not entity:
            raise EntityNotFoundError(f"Entité {entity_id} non trouvée")
        return entity

    def get_all_for_entity(
            self,
            entity_id: int,
            active_only: bool = True,
    ) -> List[EntityService]:
        """Liste les services activés pour une entité."""
        # Vérifier que l'entité appartient au tenant
        self._verify_entity_belongs_to_tenant(entity_id)

        query = self._base_query().where(
            EntityService.entity_id == entity_id
        ).options(
            selectinload(EntityService.service_template)
        )

        if active_only:
            query = query.where(EntityService.is_active == True)

        query = query.order_by(EntityService.id)
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, entity_service_id: int) -> EntityService:
        """Récupère un service d'entité par son ID."""
        query = self._base_query().where(
            EntityService.id == entity_service_id
        ).options(
            selectinload(EntityService.service_template)
        )
        entity_service = self.db.execute(query).scalar_one_or_none()
        if not entity_service:
            raise EntityServiceNotFoundError(f"Service d'entité {entity_service_id} non trouvé")
        return entity_service

    def create(
            self,
            entity_id: int,
            data: EntityServiceCreate,
    ) -> EntityService:
        """Active un service pour une entité."""
        # Vérifier que l'entité existe et appartient au tenant
        self._verify_entity_belongs_to_tenant(entity_id)

        # Vérifier que le service template existe (global, pas de tenant)
        template = self.db.get(ServiceTemplate, data.service_template_id)
        if not template:
            raise ServiceTemplateNotFoundError(
                f"Service template {data.service_template_id} non trouvé"
            )

        # Vérifier unicité (entity + service_template) dans le tenant
        existing = self.db.execute(
            self._base_query().where(
                EntityService.entity_id == entity_id,
                EntityService.service_template_id == data.service_template_id,
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateEntityServiceError(
                f"Ce service est déjà activé pour cette entité"
            )

        entity_service = EntityService(
            tenant_id=self.tenant_id,
            entity_id=entity_id,
            service_template_id=data.service_template_id,
            is_active=data.is_active,
            price_euros=data.price_euros,
            max_capacity_week=data.max_capacity_week,
            custom_duration_minutes=data.custom_duration_minutes,
            notes=data.notes,
        )

        self.db.add(entity_service)
        self.db.commit()
        self.db.refresh(entity_service)
        return entity_service

    def update(
            self,
            entity_service_id: int,
            data: EntityServiceUpdate,
    ) -> EntityService:
        """Met à jour un service d'entité."""
        entity_service = self.get_by_id(entity_service_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity_service, field, value)

        self.db.commit()
        self.db.refresh(entity_service)
        return entity_service

    def delete(self, entity_service_id: int) -> None:
        """Désactive un service d'entité."""
        entity_service = self.get_by_id(entity_service_id)
        entity_service.is_active = False
        self.db.commit()

    def get_entities_for_service(
            self,
            service_template_id: int,
            active_only: bool = True,
    ) -> List[EntityService]:
        """Liste les entités du tenant proposant un service donné."""
        query = self._base_query().where(
            EntityService.service_template_id == service_template_id
        ).options(
            selectinload(EntityService.entity)
        )

        if active_only:
            query = query.where(EntityService.is_active == True)

        return list(self.db.execute(query).scalars().all())