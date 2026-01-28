"""
Tests pour le module Catalog API.

Utilise les fixtures définies dans conftest.py.
Tests pour: service_templates, entity_services.
"""
from fastapi import status

from app.models.catalog.service_template import ServiceTemplate
from app.models.enums import ServiceCategory


# =============================================================================
# SERVICE TEMPLATE TESTS
# =============================================================================

class TestServiceTemplateEndpoints:
    """Tests des endpoints /api/v1/service-templates."""

    def test_list_service_templates(self, client, admin_token_headers, service_template_toilette):
        """Liste des service templates."""
        response = client.get(
            "/api/v1/service-templates",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert "items" in data

    def test_list_templates_filter_by_category(self, client, admin_token_headers, service_template_toilette):
        """Filtrage par catégorie."""
        response = client.get(
            "/api/v1/service-templates?category=HYGIENE",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "HYGIENE"

    def test_list_templates_filter_medical_act(self, client, admin_token_headers, db_session):
        """Filtrage par acte médical."""
        # Créer un service médical
        template = ServiceTemplate(
            code="INJECTION_TEST",
            name="Injection test",
            category=ServiceCategory.SOINS,
            default_duration_minutes=15,
            is_medical_act=True,
            requires_prescription=True,
            status="active",
        )
        db_session.add(template)
        db_session.flush()

        response = client.get(
            "/api/v1/service-templates?is_medical_act=true",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["is_medical_act"] is True

    def test_list_templates_search(self, client, admin_token_headers, service_template_toilette):
        """Recherche sur code ou nom."""
        response = client.get(
            "/api/v1/service-templates?search=toilette",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_get_categories(self, client, admin_token_headers):
        """Liste des catégories disponibles."""
        response = client.get(
            "/api/v1/service-templates/categories",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "categories" in data
        category_codes = [c["code"] for c in data["categories"]]
        assert "SOINS" in category_codes
        assert "HYGIENE" in category_codes

    def test_get_templates_by_category(self, client, admin_token_headers, service_template_toilette):
        """Récupération par catégorie."""
        response = client.get(
            "/api/v1/service-templates/by-category/HYGIENE",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["category"] == "HYGIENE"

    def test_get_service_template(self, client, admin_token_headers, service_template_toilette):
        """Récupération par ID."""
        response = client.get(
            f"/api/v1/service-templates/{service_template_toilette.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == service_template_toilette.id
        assert data["code"] == service_template_toilette.code

    def test_get_service_template_not_found(self, client, admin_token_headers):
        """Erreur 404 si template inexistant."""
        response = client.get(
            "/api/v1/service-templates/99999",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_service_template_by_code(self, client, admin_token_headers, service_template_toilette):
        """Récupération par code."""
        response = client.get(
            f"/api/v1/service-templates/code/{service_template_toilette.code}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["code"] == service_template_toilette.code

    def test_create_service_template(self, client, admin_token_headers):
        """Création d'un service template (admin)."""
        response = client.post(
            "/api/v1/service-templates",
            headers=admin_token_headers,
            json={
                "code": "NEW_SERVICE",
                "name": "Nouveau service test",
                "category": "SOCIAL",
                "description": "Description du nouveau service",
                "default_duration_minutes": 45,
                "is_medical_act": False,
                "apa_eligible": True,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "NEW_SERVICE"
        assert data["category"] == "SOCIAL"
        assert data["is_active"] is True

    def test_create_template_duplicate_code(self, client, admin_token_headers, service_template_toilette):
        """Erreur 409 si code déjà existant."""
        response = client.post(
            "/api/v1/service-templates",
            headers=admin_token_headers,
            json={
                "code": service_template_toilette.code,
                "name": "Doublon",
                "category": "HYGIENE",
                "default_duration_minutes": 30,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_template_unauthorized(self, client_as_user):
        """Erreur 403 si non-admin."""
        # client_as_user utilise user_infirmier (is_admin=False)
        # Pas besoin de headers car l'utilisateur est mocké directement
        response = client_as_user.post(
            "/api/v1/service-templates",
            json={
                "code": "UNAUTHORIZED",
                "name": "Test",
                "category": "AUTRE",
                "default_duration_minutes": 30,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_service_template(self, client, admin_token_headers, service_template_toilette):
        """Mise à jour d'un service template (admin)."""
        response = client.patch(
            f"/api/v1/service-templates/{service_template_toilette.id}",
            headers=admin_token_headers,
            json={"default_duration_minutes": 60},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["default_duration_minutes"] == 60

    def test_delete_service_template(self, client, admin_token_headers, db_session):
        """Désactivation d'un service template (soft delete)."""
        template = ServiceTemplate(
            code="TO_DELETE",
            name="À supprimer",
            category=ServiceCategory.AUTRE,
            default_duration_minutes=30,
            status="active",
        )
        db_session.add(template)
        db_session.flush()

        response = client.delete(
            f"/api/v1/service-templates/{template.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Vérifier que le template est désactivé
        db_session.refresh(template)
        assert template.status == "inactive"


# =============================================================================
# ENTITY SERVICE TESTS
# =============================================================================

class TestEntityServiceEndpoints:
    """Tests des endpoints /api/v1/entities/{id}/services."""

    def test_list_entity_services(self, client, admin_token_headers, entity, entity_service_toilette):
        """Liste des services d'une entité."""
        response = client.get(
            f"/api/v1/entities/{entity.id}/services",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_entity_services_all(self, client, admin_token_headers, entity, entity_service_toilette, db_session):
        """Liste incluant les services inactifs."""
        # Désactiver le service
        entity_service_toilette.is_active = False
        db_session.flush()

        # Sans active_only
        response = client.get(
            f"/api/v1/entities/{entity.id}/services?active_only=false",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_get_entity_service(self, client, admin_token_headers, entity, entity_service_toilette):
        """Récupération d'un service d'entité."""
        response = client.get(
            f"/api/v1/entities/{entity.id}/services/{entity_service_toilette.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == entity_service_toilette.id
        assert data["entity_id"] == entity.id

    def test_get_entity_service_wrong_entity(self, client, admin_token_headers, entity_service_toilette):
        """Erreur 404 si mauvaise entité."""
        response = client.get(
            f"/api/v1/entities/99999/services/{entity_service_toilette.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_entity_service(self, client, admin_token_headers, entity, db_session):
        """Activation d'un service pour une entité."""
        # Créer un nouveau template
        template = ServiceTemplate(
            code="NEW_FOR_ENTITY",
            name="Nouveau pour entité",
            category=ServiceCategory.SOCIAL,
            default_duration_minutes=30,
            status="active",
        )
        db_session.add(template)
        db_session.flush()

        response = client.post(
            f"/api/v1/entities/{entity.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": template.id,
                "is_active": True,
                "price_euros": 35.50,
                "max_capacity_week": 50,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["entity_id"] == entity.id
        assert data["service_template_id"] == template.id
        assert float(data["price_euros"]) == 35.50

    def test_create_entity_service_duplicate(self, client, admin_token_headers, entity, entity_service_toilette,
                                             service_template_toilette):
        """Erreur 409 si service déjà activé."""
        response = client.post(
            f"/api/v1/entities/{entity.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_entity_service_entity_not_found(self, client, admin_token_headers, service_template_toilette):
        """Erreur 404 si entité inexistante."""
        response = client.post(
            "/api/v1/entities/99999/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_entity_service_template_not_found(self, client, admin_token_headers, entity):
        """Erreur 404 si template inexistant."""
        response = client.post(
            f"/api/v1/entities/{entity.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": 99999,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_entity_service(self, client, admin_token_headers, entity, entity_service_toilette):
        """Mise à jour d'un service d'entité."""
        response = client.patch(
            f"/api/v1/entities/{entity.id}/services/{entity_service_toilette.id}",
            headers=admin_token_headers,
            json={
                "price_euros": 45.00,
                "custom_duration_minutes": 60,
                "notes": "Tarif révisé",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert float(data["price_euros"]) == 45.00
        assert data["custom_duration_minutes"] == 60
        assert data["has_custom_duration"] is True

    def test_delete_entity_service(self, client, admin_token_headers, entity, entity_service_toilette, db_session):
        """Désactivation d'un service d'entité."""
        response = client.delete(
            f"/api/v1/entities/{entity.id}/services/{entity_service_toilette.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Vérifier que le service est désactivé
        db_session.refresh(entity_service_toilette)
        assert entity_service_toilette.is_active is False

    def test_effective_duration_uses_custom(self, client, admin_token_headers, entity, entity_service_toilette,
                                            db_session):
        """La durée effective utilise la durée personnalisée si définie."""
        # Définir une durée personnalisée
        entity_service_toilette.custom_duration_minutes = 75
        db_session.flush()

        response = client.get(
            f"/api/v1/entities/{entity.id}/services/{entity_service_toilette.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["effective_duration_minutes"] == 75
        assert data["has_custom_duration"] is True


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests de validation des données."""

    def test_invalid_category(self, client, admin_token_headers):
        """Catégorie invalide."""
        response = client.post(
            "/api/v1/service-templates",
            headers=admin_token_headers,
            json={
                "code": "INVALID_CAT",
                "name": "Test",
                "category": "INVALID_CATEGORY",
                "default_duration_minutes": 30,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_duration_too_short(self, client, admin_token_headers):
        """Durée trop courte."""
        response = client.post(
            "/api/v1/service-templates",
            headers=admin_token_headers,
            json={
                "code": "SHORT_DURATION",
                "name": "Test",
                "category": "AUTRE",
                "default_duration_minutes": 2,  # Min = 5
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_duration_too_long(self, client, admin_token_headers):
        """Durée trop longue."""
        response = client.post(
            "/api/v1/service-templates",
            headers=admin_token_headers,
            json={
                "code": "LONG_DURATION",
                "name": "Test",
                "category": "AUTRE",
                "default_duration_minutes": 500,  # Max = 480
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_price_negative(self, client, admin_token_headers, entity, service_template_toilette):
        """Prix négatif."""
        response = client.post(
            f"/api/v1/entities/{entity.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
                "price_euros": -10,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY