"""
Tests API pour le module Organization - Architecture v4.3

Ce module teste les endpoints :
- /api/v1/organizations/countries : CRUD Pays (données de référence)
- /api/v1/organizations/entities : CRUD Entités (multi-tenant)
- /api/v1/organizations/hierarchy : Arborescence des entités

Architecture v4.3:
- Multi-tenant avec tenant_id obligatoire
- Authentification mockée pour les tests
"""

from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User
from app.models.enums import EntityType
from app.models.organization.entity import Entity
from app.models.reference.country import Country


# =============================================================================
# FIXTURES LOCALES - Authentification mockée
# =============================================================================

@pytest.fixture
def authenticated_client(
    db_session: Session,
    user_admin: User
) -> Generator[TestClient, None, None]:
    """
    Client de test avec authentification mockée (admin).
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.core.auth.user_auth import get_current_user


    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return user_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client_user(
    db_session: Session,
    user_infirmier: User
) -> Generator[TestClient, None, None]:
    """
    Client de test authentifié en tant qu'utilisateur standard (non-admin).
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.core.auth.user_auth import get_current_user
    from app.core.dependencies import get_current_user as get_current_user_old

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return user_infirmier

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_old] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Client de test sans authentification (pour tester les 401/403).
    """
    from app.database.session_rls import get_db, get_db_no_rls

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# COUNTRY TESTS
# =============================================================================

class TestCountryEndpoints:
    """Tests des endpoints /api/v1/organizations/countries."""

    def test_list_countries(self, authenticated_client, country):
        """Liste des pays existants."""
        response = authenticated_client.get("/api/v1/organizations/countries")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert any(c["country_code"] == "FR" for c in data["items"])

    def test_list_countries_pagination(self, authenticated_client, country):
        """Test de la pagination."""
        response = authenticated_client.get(
            "/api/v1/organizations/countries?page=1&size=10"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    def test_create_country(self, authenticated_client):
        """Création d'un pays."""
        response = authenticated_client.post(
            "/api/v1/organizations/countries",
            json={
                "name": "Belgique",
                "country_code": "BE",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Belgique"
        assert data["country_code"] == "BE"
        assert "id" in data
        assert "created_at" in data

    def test_create_country_duplicate_code(self, authenticated_client, country):
        """Erreur 409 si code pays déjà utilisé."""
        response = authenticated_client.post(
            "/api/v1/organizations/countries",
            json={"name": "Autre France", "country_code": "FR"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_country_code_normalized(self, authenticated_client):
        """Le code pays est normalisé en majuscules."""
        response = authenticated_client.post(
            "/api/v1/organizations/countries",
            json={"name": "Suisse", "country_code": "ch"},  # minuscules
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["country_code"] == "CH"  # Normalisé

    def test_get_country(self, authenticated_client, country):
        """Récupération d'un pays par ID."""
        response = authenticated_client.get(
            f"/api/v1/organizations/countries/{country.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["country_code"] == "FR"
        assert data["name"] == "France"

    def test_get_country_not_found(self, authenticated_client):
        """Erreur 404 si pays inexistant."""
        response = authenticated_client.get("/api/v1/organizations/countries/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_country(self, authenticated_client, country):
        """Mise à jour partielle d'un pays."""
        response = authenticated_client.patch(
            f"/api/v1/organizations/countries/{country.id}",
            json={"name": "République Française"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "République Française"
        assert data["country_code"] == "FR"  # Inchangé

    def test_delete_country(self, authenticated_client, db_session):
        """Suppression d'un pays."""
        # Créer un pays spécifique à supprimer
        new_country = Country(name="Test Delete", country_code="TD")
        db_session.add(new_country)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/organizations/countries/{new_country.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unauthorized_without_token(self, unauthenticated_client):
        """Erreur 401/403 sans authentification."""
        response = unauthenticated_client.get("/api/v1/organizations/countries")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# =============================================================================
# ENTITY TESTS
# =============================================================================

class TestEntityEndpoints:
    """Tests des endpoints /api/v1/organizations/entities."""

    def test_list_entities(self, authenticated_client, entity):
        """Liste des entités existantes."""
        response = authenticated_client.get("/api/v1/organizations/entities")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_entities_with_filters(self, authenticated_client, entity):
        """Filtrage des entités par type."""
        response = authenticated_client.get(
            "/api/v1/organizations/entities?entity_type=SSIAD"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["entity_type"] == "SSIAD"

    def test_search_entities(self, authenticated_client, entity):
        """Recherche d'entités par nom."""
        response = authenticated_client.get(
            "/api/v1/organizations/entities?search=Test"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1

    def test_create_entity(self, authenticated_client, country):
        """Création d'une entité."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Nouveau SSIAD Unique",
                "short_name": "NSSIAD",
                "entity_type": "SSIAD",
                "integration_type": "MANAGED",
                "siret": "98765432100099",
                "finess_et": "750099998",
                "authorized_capacity": 25,
                "address": "123 rue du Test",
                "postal_code": "75001",
                "city": "Paris",
                "phone": "0100000000",
                "email": "nouveau@ssiad.fr",
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Nouveau SSIAD Unique"
        assert data["entity_type"] == "SSIAD"
        assert "id" in data

    def test_create_entity_duplicate_finess(self, authenticated_client, entity, country):
        """Erreur 409 si FINESS déjà utilisé."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Autre SSIAD",
                "entity_type": "SSIAD",
                "finess_et": entity.finess_et,  # Déjà utilisé
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_get_entity(self, authenticated_client, entity):
        """Récupération d'une entité par ID."""
        response = authenticated_client.get(
            f"/api/v1/organizations/entities/{entity.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == entity.id
        assert data["entity_type"] == "SSIAD"

    def test_get_entity_not_found(self, authenticated_client):
        """Erreur 404 si entité inexistante."""
        response = authenticated_client.get("/api/v1/organizations/entities/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_entity(self, authenticated_client, entity):
        """Mise à jour d'une entité."""
        response = authenticated_client.patch(
            f"/api/v1/organizations/entities/{entity.id}",
            json={"authorized_capacity": 50},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["authorized_capacity"] == 50

    def test_delete_entity(self, authenticated_client, db_session, country, tenant):
        """Suppression d'une entité."""
        new_entity = Entity(
            name="Entity to Delete",
            entity_type=EntityType.SAAD,
            country_id=country.id,
            tenant_id=tenant.id,
        )
        db_session.add(new_entity)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/organizations/entities/{new_entity.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# HIERARCHY TESTS
# =============================================================================

class TestEntityHierarchy:
    """Tests de la hiérarchie des entités."""

    def test_create_child_entity(self, authenticated_client, entity, country):
        """Création d'une entité enfant."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Agence Paris 13",
                "entity_type": "SSIAD",
                "parent_entity_id": entity.id,
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["parent_entity_id"] == entity.id

    def test_get_entity_children(self, authenticated_client, db_session, entity, country, tenant):
        """Récupération des entités enfants."""
        child = Entity(
            name="Agence Test Child",
            entity_type=EntityType.SSIAD,
            parent_entity_id=entity.id,
            country_id=country.id,
            tenant_id=tenant.id,
        )
        db_session.add(child)
        db_session.flush()

        response = authenticated_client.get(
            f"/api/v1/organizations/entities/{entity.id}/children"
        )
        assert response.status_code == status.HTTP_200_OK
        children = response.json()
        assert len(children) >= 1
        assert any(c["name"] == "Agence Test Child" for c in children)

    def test_get_hierarchy(self, authenticated_client, entity):
        """Récupération de l'arborescence."""
        response = authenticated_client.get("/api/v1/organizations/hierarchy")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_hierarchy_from_root(self, authenticated_client, entity):
        """Récupération de l'arborescence depuis une racine."""
        response = authenticated_client.get(
            f"/api/v1/organizations/hierarchy?root_id={entity.id}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_prevent_circular_hierarchy(self, authenticated_client, entity):
        """Empêcher une entité d'être son propre parent."""
        response = authenticated_client.patch(
            f"/api/v1/organizations/entities/{entity.id}",
            json={"parent_entity_id": entity.id},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests de validation Pydantic."""

    def test_invalid_siret_format(self, authenticated_client, country):
        """SIRET avec caractères non numériques."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "siret": "1234ABC8901234",
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_siret_length(self, authenticated_client, country):
        """SIRET trop court."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "siret": "12345",
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_finess_length(self, authenticated_client, country):
        """FINESS avec mauvaise longueur."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "finess_et": "75001",  # Trop court (doit être 9)
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_entity_type(self, authenticated_client, country):
        """Type d'entité invalide."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "INVALID_TYPE",
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_email(self, authenticated_client, country):
        """Email invalide."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "email": "not-an-email",
                "country_id": country.id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_country_code_length(self, authenticated_client):
        """Code pays trop long."""
        response = authenticated_client.post(
            "/api/v1/organizations/countries",
            json={
                "name": "Test",
                "country_code": "FRA",  # Doit être 2 caractères
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_country_code_non_alpha(self, authenticated_client):
        """Code pays avec chiffres."""
        response = authenticated_client.post(
            "/api/v1/organizations/countries",
            json={
                "name": "Test",
                "country_code": "F1",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_country_not_found_on_entity_creation(self, authenticated_client):
        """Erreur si le pays référencé n'existe pas."""
        response = authenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "country_id": 99999,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestAuthentication:
    """Tests d'authentification."""

    def test_list_countries_requires_auth(self, unauthenticated_client):
        """Liste des pays requiert authentification."""
        response = unauthenticated_client.get("/api/v1/organizations/countries")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_entities_requires_auth(self, unauthenticated_client):
        """Liste des entités requiert authentification."""
        response = unauthenticated_client.get("/api/v1/organizations/entities")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_entity_requires_auth(self, unauthenticated_client):
        """Création d'entité requiert authentification."""
        response = unauthenticated_client.post(
            "/api/v1/organizations/entities",
            json={
                "name": "Test",
                "entity_type": "SSIAD",
                "country_id": 1,
            },
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# =============================================================================
# HEALTH CHECK TEST
# =============================================================================

class TestHealthCheck:
    """Test du endpoint health check."""

    def test_health_check(self, unauthenticated_client):
        """Le health check fonctionne sans auth."""
        response = unauthenticated_client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api_version"] == "v1"