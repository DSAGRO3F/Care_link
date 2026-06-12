"""
Services métier pour le module Catalog.

Contient la logique CRUD pour :
- ServiceTemplateService (catalogue national - global, pas de tenant)
- EntityServiceService (services par entité - multi-tenant)

Version multi-tenant : EntityServiceService filtre par tenant_id.
v4.17 — Ajout get_by_domain(), get_domains_with_counts(), filtre domain.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.catalog.schemas import (
    CATEGORY_LABELS,
    DOMAIN_LABELS,
    # Phase 3B — Consolidated Catalog
    BestTarifInfo,
    ConsolidatedCatalogResponse,
    ConsolidatedCatalogSummary,
    ConsolidatedEntitySummary,
    ConsolidatedPrestationResponse,
    EntityOfferResponse,
    EntityServiceCreate,
    EntityServiceUpdate,
    ServiceTemplateCreate,
    ServiceTemplateFilters,
    ServiceTemplateUpdate,
)
from app.models.catalog.entity_service import EntityService
from app.models.catalog.service_template import ServiceTemplate
from app.models.organization.entity import Entity
from app.models.user.profession import Profession


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ServiceTemplateNotFoundError(Exception):
    """Service template non trouvé."""


class EntityServiceNotFoundError(Exception):
    """Service d'entité non trouvé."""


class EntityNotFoundError(Exception):
    """Entité non trouvée."""


class ProfessionNotFoundError(Exception):
    """Profession non trouvée."""


class DuplicateServiceCodeError(Exception):
    """Code de service déjà existant."""


class DuplicateEntityServiceError(Exception):
    """Service déjà activé pour cette entité."""


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
        filters: ServiceTemplateFilters | None = None,
    ) -> tuple[list[ServiceTemplate], int]:
        """Liste les service templates avec pagination et filtres."""
        query = select(ServiceTemplate)

        if filters:
            if filters.domain:
                query = query.where(ServiceTemplate.domain == filters.domain.upper())

            if filters.category:
                query = query.where(ServiceTemplate.category == filters.category.upper())

            if filters.is_medical_act is not None:
                query = query.where(ServiceTemplate.is_medical_act == filters.is_medical_act)

            if filters.requires_prescription is not None:
                query = query.where(
                    ServiceTemplate.requires_prescription == filters.requires_prescription
                )

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
    def get_by_code(db: Session, code: str) -> ServiceTemplate | None:
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
            domain=data.domain,
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
        if update_data.get("required_profession_id"):
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
    def get_by_category(db: Session, category: str) -> list[ServiceTemplate]:
        """Récupère tous les services actifs d'une catégorie."""
        query = (
            select(ServiceTemplate)
            .where(
                ServiceTemplate.category == category.upper(),
                ServiceTemplate.status == "active",
            )
            .order_by(ServiceTemplate.display_order)
        )

        return list(db.execute(query).scalars().all())

    @staticmethod
    def get_by_domain(db: Session, domain: str) -> list[ServiceTemplate]:
        """Récupère tous les services actifs d'un domaine."""
        query = (
            select(ServiceTemplate)
            .where(
                ServiceTemplate.domain == domain.upper(),
                ServiceTemplate.status == "active",
            )
            .order_by(ServiceTemplate.category, ServiceTemplate.display_order)
        )

        return list(db.execute(query).scalars().all())

    @staticmethod
    def get_domains_with_counts(db: Session) -> list[dict]:
        """
        Retourne les domaines avec compteur de services actifs.

        Returns:
            Liste de dicts {domain, active_count, total_count}
        """
        query = select(
            ServiceTemplate.domain,
            func.count().label("total_count"),
            func.count().filter(ServiceTemplate.status == "active").label("active_count"),
        ).group_by(ServiceTemplate.domain)

        rows = db.execute(query).all()
        return [
            {
                "domain": row.domain.value if hasattr(row.domain, "value") else str(row.domain),
                "total_count": row.total_count,
                "active_count": row.active_count,
            }
            for row in rows
        ]

    @staticmethod
    def get_categories_with_counts(db: Session) -> list[dict]:
        """
        Retourne les catégories avec compteur de services actifs.

        Returns:
            Liste de dicts {category, domain, active_count, total_count}
        """
        query = (
            select(
                ServiceTemplate.category,
                ServiceTemplate.domain,
                func.count().label("total_count"),
                func.count().filter(ServiceTemplate.status == "active").label("active_count"),
            )
            .group_by(ServiceTemplate.category, ServiceTemplate.domain)
            .order_by(ServiceTemplate.domain, ServiceTemplate.category)
        )

        rows = db.execute(query).all()
        return [
            {
                "category": row.category.value
                if hasattr(row.category, "value")
                else str(row.category),
                "domain": row.domain.value if hasattr(row.domain, "value") else str(row.domain),
                "total_count": row.total_count,
                "active_count": row.active_count,
            }
            for row in rows
        ]

    @staticmethod
    def get_consolidated_catalog(db: Session, tenant_id: int) -> ConsolidatedCatalogResponse:
        """
        Vue consolidée cross-entités du catalogue.

        Phase 3B — Agrège tous les entity_services actifs de toutes les entités
        du tenant avec le référentiel national. Filtre explicite par tenant_id
        (cohérent avec EntityServiceService — ne pas se reposer uniquement sur RLS).

        Args:
            db: Session SQLAlchemy (avec RLS actif)
            tenant_id: ID du tenant pour filtrage explicite

        Returns:
            ConsolidatedCatalogResponse avec prestations groupées et summary.
        """
        # 1. Charger tous les templates actifs du référentiel national
        #    selectinload pour la relation profession (évite lazy load)
        templates_query = (
            select(ServiceTemplate)
            .where(ServiceTemplate.status == "active")
            .options(selectinload(ServiceTemplate.required_profession))
            .order_by(
                ServiceTemplate.domain,
                ServiceTemplate.category,
                ServiceTemplate.display_order,
            )
        )
        templates = list(db.execute(templates_query).scalars().all())

        # 2. Charger les entity_services actifs avec leur entité
        #    Filtre explicite tenant_id (cohérent avec EntityServiceService)
        es_query = (
            select(EntityService, Entity)
            .join(Entity, EntityService.entity_id == Entity.id)
            .where(
                EntityService.is_active == True,  # noqa: E712
                EntityService.tenant_id == tenant_id,  # filtre explicite
            )
            .options(selectinload(EntityService.service_template))
        )
        entity_services_rows = db.execute(es_query).all()

        # 3. Indexer les offres par service_template_id
        offers_by_template: dict[int, list[EntityOfferResponse]] = {}
        entity_stats: dict[int, dict] = {}

        for es, entity in entity_services_rows:
            template_id = es.service_template_id
            entity_type_str = (
                entity.entity_type.value
                if hasattr(entity.entity_type, "value")
                else str(entity.entity_type)
            )

            offer = EntityOfferResponse(
                entity_id=entity.id,
                entity_name=entity.name,
                entity_type=entity_type_str,
                custom_tarif=(float(es.price_euros) if es.price_euros is not None else None),
                custom_duree=es.custom_duration_minutes,
                is_active=es.is_active,
            )

            if template_id not in offers_by_template:
                offers_by_template[template_id] = []
            offers_by_template[template_id].append(offer)

            # Compteur par entité
            if entity.id not in entity_stats:
                entity_stats[entity.id] = {
                    "name": entity.name,
                    "entity_type": entity_type_str,
                    "count": 0,
                }
            entity_stats[entity.id]["count"] += 1

        # 4. Construire les prestations consolidées
        prestations: list[ConsolidatedPrestationResponse] = []
        active_prestations_count = 0

        for tmpl in templates:
            offers = offers_by_template.get(tmpl.id, [])
            offer_count = len(offers)

            if offer_count > 0:
                active_prestations_count += 1

            # Calcul du meilleur tarif
            best_tarif = None
            tarifs = [(o.custom_tarif, o.entity_name) for o in offers if o.custom_tarif is not None]
            if tarifs:
                min_tarif, min_entity = min(tarifs, key=lambda t: t[0])
                best_tarif = BestTarifInfo(value=min_tarif, entity_name=min_entity)

            # Nom de la profession requise
            profession_name = None
            if tmpl.required_profession:
                profession_name = tmpl.required_profession.name

            domain_str = tmpl.domain.value if hasattr(tmpl.domain, "value") else str(tmpl.domain)
            category_str = (
                tmpl.category.value if hasattr(tmpl.category, "value") else str(tmpl.category)
            )

            prestations.append(
                ConsolidatedPrestationResponse(
                    template_id=tmpl.id,
                    code=tmpl.code,
                    name=tmpl.name,
                    domain=domain_str,
                    domain_label=DOMAIN_LABELS.get(domain_str, domain_str),
                    category=category_str,
                    category_label=CATEGORY_LABELS.get(category_str, category_str),
                    description=tmpl.description,
                    required_profession_name=profession_name,
                    default_duration_minutes=tmpl.default_duration_minutes,
                    requires_prescription=tmpl.requires_prescription,
                    is_medical_act=tmpl.is_medical_act,
                    apa_eligible=tmpl.apa_eligible,
                    offers=offers,
                    offer_count=offer_count,
                    best_tarif=best_tarif,
                )
            )

        # 5. Summary
        entities_summary = [
            ConsolidatedEntitySummary(
                id=eid,
                name=info["name"],
                entity_type=info["entity_type"],
                active_services_count=info["count"],
            )
            for eid, info in entity_stats.items()
        ]

        summary = ConsolidatedCatalogSummary(
            total_national=len(templates),
            total_active_prestations=active_prestations_count,
            entities_count=len(entity_stats),
            entities=entities_summary,
        )

        return ConsolidatedCatalogResponse(
            prestations=prestations,
            summary=summary,
        )


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
            Entity.id == entity_id, Entity.tenant_id == self.tenant_id
        )
        entity = self.db.execute(entity_query).scalar_one_or_none()
        if not entity:
            raise EntityNotFoundError(f"Entité {entity_id} non trouvée")
        return entity

    def get_all_for_entity(
        self,
        entity_id: int,
        active_only: bool = True,
    ) -> list[EntityService]:
        """Liste les services activés pour une entité."""
        # Vérifier que l'entité appartient au tenant
        self._verify_entity_belongs_to_tenant(entity_id)

        query = (
            self._base_query()
            .where(EntityService.entity_id == entity_id)
            .options(selectinload(EntityService.service_template))
        )

        if active_only:
            query = query.where(EntityService.is_active == True)  # noqa: E712

        query = query.order_by(EntityService.id)
        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, entity_service_id: int) -> EntityService:
        """Récupère un service d'entité par son ID."""
        query = (
            self._base_query()
            .where(EntityService.id == entity_service_id)
            .options(selectinload(EntityService.service_template))
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
            raise DuplicateEntityServiceError("Ce service est déjà activé pour cette entité")

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
        self.db.flush()
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

        self.db.flush()
        return entity_service

    def delete(self, entity_service_id: int) -> None:
        """Désactive un service d'entité."""
        entity_service = self.get_by_id(entity_service_id)
        entity_service.is_active = False
        self.db.flush()

    def get_entities_for_service(
        self,
        service_template_id: int,
        active_only: bool = True,
    ) -> list[EntityService]:
        """Liste les entités du tenant proposant un service donné."""
        query = (
            self._base_query()
            .where(EntityService.service_template_id == service_template_id)
            .options(selectinload(EntityService.entity))
        )

        if active_only:
            query = query.where(EntityService.is_active == True)  # noqa: E712

        return list(self.db.execute(query).scalars().all())
