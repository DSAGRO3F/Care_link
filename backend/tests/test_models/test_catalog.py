"""
Tests unitaires pour les modèles du catalogue de services.

- ServiceTemplate : Catalogue national des prestations
- EntityService : Services activés par chaque entité
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ServiceTemplate, EntityService, Entity, Profession
from app.models.enums import ServiceCategory


class TestServiceTemplate:
    """Tests pour le modèle ServiceTemplate."""

    def test_create_service_template(self, db_session: Session, profession_aide_soignant: Profession):
        """Test création d'un template de service."""
        template = ServiceTemplate(
            code="TEST_SERVICE",
            name="Service de test",
            category=ServiceCategory.SOINS,
            description="Description du service de test",
            required_profession_id=profession_aide_soignant.id,
            default_duration_minutes=30,
            requires_prescription=False,
            is_medical_act=False,
            apa_eligible=True,
            display_order=100,
            status="active"
        )
        db_session.add(template)
        db_session.flush()

        assert template.id is not None
        assert template.code == "TEST_SERVICE"
        assert template.category == ServiceCategory.SOINS
        assert template.created_at is not None

    def test_service_template_unique_code(self, db_session: Session, service_template_toilette: ServiceTemplate):
        """Test contrainte d'unicité sur le code."""
        duplicate = ServiceTemplate(
            code="TOILETTE_COMPLETE",  # Même code que la fixture
            name="Autre toilette",
            category=ServiceCategory.HYGIENE,
            default_duration_minutes=30,
            requires_prescription=False,
            is_medical_act=False,
            apa_eligible=True,
            display_order=100,
            status="active"
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_service_template_relation_profession(self, service_template_toilette: ServiceTemplate,
                                                  profession_aide_soignant: Profession):
        """Test relation ServiceTemplate → Profession."""
        assert service_template_toilette.required_profession == profession_aide_soignant
        assert service_template_toilette in profession_aide_soignant.service_templates

    def test_service_template_polyvalent(self, service_template_courses: ServiceTemplate):
        """Test service polyvalent (sans profession requise)."""
        assert service_template_courses.required_profession_id is None
        assert service_template_courses.required_profession is None

    def test_service_template_is_active(self, service_template_toilette: ServiceTemplate):
        """Test propriété is_active."""
        assert service_template_toilette.is_active is True

    def test_service_template_requires_professional(self, service_template_toilette: ServiceTemplate,
                                                    service_template_courses: ServiceTemplate):
        """Test propriété requires_professional."""
        # Toilette nécessite une profession
        assert service_template_toilette.requires_professional is True

        # Courses ne nécessitent pas de profession spécifique
        assert service_template_courses.requires_professional is False

    def test_service_template_deactivate(self, db_session: Session, service_template_toilette: ServiceTemplate):
        """Test désactivation d'un service."""
        service_template_toilette.deactivate()
        db_session.flush()

        assert service_template_toilette.status == "inactive"
        assert service_template_toilette.is_active is False

    def test_service_template_activate(self, db_session: Session, service_template_toilette: ServiceTemplate):
        """Test réactivation d'un service."""
        service_template_toilette.status = "inactive"
        db_session.flush()

        service_template_toilette.activate()
        db_session.flush()

        assert service_template_toilette.status == "active"
        assert service_template_toilette.is_active is True


class TestEntityService:
    """Tests pour le modèle EntityService."""

    def test_create_entity_service(self, db_session: Session, tenant, entity: Entity,
                                   service_template_injection: ServiceTemplate):
        """Test création d'un service d'entité."""
        entity_service = EntityService(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            entity_id=entity.id,
            service_template_id=service_template_injection.id,
            is_active=True,
            price_euros=Decimal("15.00"),
            max_capacity_week=200,
            notes="Service d'injection"
        )
        db_session.add(entity_service)
        db_session.flush()

        assert entity_service.id is not None
        assert entity_service.is_active is True
        assert entity_service.price_euros == Decimal("15.00")

    def test_entity_service_unique_constraint(self, db_session: Session, tenant, entity_service_toilette: EntityService,
                                              entity: Entity, service_template_toilette: ServiceTemplate):
        """Test contrainte d'unicité (entity_id, service_template_id)."""
        duplicate = EntityService(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            entity_id=entity.id,
            service_template_id=service_template_toilette.id,  # Même combinaison
            is_active=True
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_entity_service_relations(self, entity_service_toilette: EntityService, entity: Entity,
                                      service_template_toilette: ServiceTemplate):
        """Test relations EntityService → Entity, ServiceTemplate."""
        assert entity_service_toilette.entity == entity
        assert entity_service_toilette.service_template == service_template_toilette
        assert entity_service_toilette in entity.entity_services
        assert entity_service_toilette in service_template_toilette.entity_services

    def test_entity_service_effective_duration_custom(self, entity_service_toilette: EntityService):
        """Test durée effective avec durée personnalisée."""
        # La fixture a custom_duration_minutes=50
        assert entity_service_toilette.custom_duration_minutes == 50
        assert entity_service_toilette.effective_duration_minutes == 50

    def test_entity_service_effective_duration_default(self, db_session: Session, tenant, entity: Entity,
                                                       service_template_injection: ServiceTemplate):
        """Test durée effective sans durée personnalisée (utilise le template)."""
        entity_service = EntityService(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            entity_id=entity.id,
            service_template_id=service_template_injection.id,
            is_active=True,
            custom_duration_minutes=None  # Pas de durée personnalisée
        )
        db_session.add(entity_service)
        db_session.flush()

        # Doit utiliser la durée du template (15 minutes)
        assert entity_service.effective_duration_minutes == 15

    def test_entity_service_has_custom_duration(self, entity_service_toilette: EntityService):
        """Test propriété has_custom_duration."""
        assert entity_service_toilette.has_custom_duration is True

    def test_entity_service_has_custom_price(self, entity_service_toilette: EntityService):
        """Test propriété has_custom_price."""
        assert entity_service_toilette.has_custom_price is True

    def test_entity_service_str(self, entity_service_toilette: EntityService):
        """Test représentation string."""
        result = str(entity_service_toilette)
        assert "SSIAD Test Paris" in result
        assert "Aide à la toilette" in result