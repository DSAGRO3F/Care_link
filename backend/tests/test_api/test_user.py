"""
Tests API pour le module User - Architecture v4.3

Ce module teste les endpoints :
- /api/v1/professions : CRUD Professions (données partagées)
- /api/v1/roles : CRUD Rôles (multi-tenant + Permission/RolePermission)
- /api/v1/users : CRUD Utilisateurs (multi-tenant)
- /api/v1/users/{id}/roles : Gestion des rôles utilisateur
- /api/v1/users/{id}/entities : Gestion des rattachements
- /api/v1/users/{id}/availabilities : Gestion des disponibilités

Architecture v4.3:
- Permissions normalisées (Permission + RolePermission)
- Multi-tenant avec tenant_id obligatoire
- Authentification mockée pour les tests
"""

from datetime import date, time
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import (
    User, Role, Profession, UserRole, UserEntity, UserAvailability, Entity, )
from app.models.enums import EntityType, ContractType


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

    Override les dépendances pour :
    - Utiliser db_session (SQLite) au lieu de PostgreSQL
    - Bypasser l'authentification JWT
    - Retourner user_admin comme utilisateur courant

    Note: require_role("ADMIN") utilise get_current_user en interne,
    donc l'override de get_current_user suffit pour les routes admin.
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

    # Override les dépendances de base de données
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    # Override l'authentification - require_role utilise cette dépendance en interne
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

    Utilisé pour tester les restrictions d'accès (403 Forbidden).
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.core.auth.user_auth import get_current_user

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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Client de test sans authentification (pour tester les 401).
    """
    from app.database.session_rls import get_db, get_db_no_rls

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    # Pas d'override de get_current_user → authentification requise

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# TESTS PROFESSION ENDPOINTS
# =============================================================================

class TestProfessionEndpoints:
    """Tests des endpoints /api/v1/professions."""

    def test_list_professions(self, authenticated_client, profession_infirmier):
        """Liste des professions."""
        response = authenticated_client.get("/api/v1/professions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_professions_filter_by_category(self, authenticated_client, profession_infirmier):
        """Filtrage par catégorie."""
        response = authenticated_client.get(
            "/api/v1/professions",
            params={"category": profession_infirmier.category}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["category"] == profession_infirmier.category

    def test_get_profession(self, authenticated_client, profession_infirmier):
        """Récupération d'une profession par ID."""
        response = authenticated_client.get(f"/api/v1/professions/{profession_infirmier.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == profession_infirmier.id
        assert data["name"] == profession_infirmier.name

    def test_get_profession_not_found(self, authenticated_client):
        """Erreur 404 si profession inexistante."""
        response = authenticated_client.get("/api/v1/professions/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_profession(self, authenticated_client):
        """Création d'une profession (admin)."""
        response = authenticated_client.post(
            "/api/v1/professions",
            json={
                "name": "Nouvelle Profession Test",
                "code": "NPT",
                "category": "PARAMEDICAL",
                "requires_rpps": False
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Nouvelle Profession Test"
        assert data["code"] == "NPT"

    def test_create_profession_duplicate_name(self, authenticated_client, profession_infirmier):
        """Erreur 409 si nom déjà utilisé."""
        response = authenticated_client.post(
            "/api/v1/professions",
            json={
                "name": profession_infirmier.name,
                "category": "MEDICAL"
            }
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_profession(self, authenticated_client, profession_infirmier):
        """Mise à jour d'une profession_infirmier."""
        response = authenticated_client.patch(
            f"/api/v1/professions/{profession_infirmier.id}",
            json={"name": "Nom Modifié"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Nom Modifié"

    def test_delete_profession(self, authenticated_client, db_session, tenant):
        """Suppression d'une profession_infirmier."""
        # Créer une profession à supprimer
        prof = Profession(
            name="Profession à Supprimer",
            code="PAS",
            category="ADMINISTRATIVE"
        )
        db_session.add(prof)
        db_session.flush()

        response = authenticated_client.delete(f"/api/v1/professions/{prof.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS ROLE ENDPOINTS
# =============================================================================

class TestRoleEndpoints:
    """Tests des endpoints /api/v1/roles."""

    def test_list_roles(self, authenticated_client, role_admin):
        """Liste des rôles."""
        response = authenticated_client.get("/api/v1/roles")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_roles_filter_system(self, authenticated_client, role_admin):
        """Filtrage par rôle système."""
        response = authenticated_client.get(
            "/api/v1/roles",
            params={"is_system_role": True}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_role(self, authenticated_client, role_admin):
        """Récupération d'un rôle."""
        response = authenticated_client.get(f"/api/v1/roles/{role_admin.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == role_admin.name

    def test_create_role(self, authenticated_client, db_session, tenant):
        """Création d'un rôle personnalisé."""
        response = authenticated_client.post(
            "/api/v1/roles",
            json={
                "name": "CUSTOM_ROLE",
                "description": "Rôle personnalisé de test"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "CUSTOM_ROLE"
        assert data["is_system_role"] is False

    def test_create_role_duplicate_name(self, authenticated_client, role_admin):
        """Erreur 409 si nom de rôle déjà utilisé."""
        response = authenticated_client.post(
            "/api/v1/roles",
            json={
                "name": role_admin.name,
                "description": "Duplicate"
            }
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_system_role_description_allowed(self, authenticated_client, role_admin):
        """Modification de la description d'un rôle système autorisée."""
        response = authenticated_client.patch(
            f"/api/v1/roles/{role_admin.id}",
            json={"description": "Nouvelle description"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description"] == "Nouvelle description"

    def test_update_system_role_name_forbidden(self, authenticated_client, role_admin):
        """Modification du nom d'un rôle système interdite."""
        response = authenticated_client.patch(
            f"/api/v1/roles/{role_admin.id}",
            json={"name": "NEW_NAME"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_system_role_forbidden(self, authenticated_client, role_admin):
        """Suppression d'un rôle système interdite."""
        response = authenticated_client.delete(f"/api/v1/roles/{role_admin.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_custom_role(self, authenticated_client, db_session, tenant):
        """Suppression d'un rôle personnalisé autorisée."""
        # Créer un rôle à supprimer
        role = Role(
            name="ROLE_TO_DELETE",
            tenant_id=tenant.id,
            is_system_role=False
        )
        db_session.add(role)
        db_session.flush()

        response = authenticated_client.delete(f"/api/v1/roles/{role.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS USER ENDPOINTS
# =============================================================================

class TestUserEndpoints:
    """Tests des endpoints /api/v1/users."""

    def test_list_users(self, authenticated_client, user_admin):
        """Liste des utilisateurs."""
        response = authenticated_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_users_filter_by_profession(
        self, authenticated_client, user_infirmier, profession_infirmier
    ):
        """Filtrage par profession."""
        response = authenticated_client.get(
            "/api/v1/users",
            params={"profession_id": profession_infirmier.id}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_list_users_search(self, authenticated_client, user_infirmier):
        """Recherche textuelle."""
        response = authenticated_client.get(
            "/api/v1/users",
            params={"search": user_infirmier.email[:5]}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_current_user(self, authenticated_client, user_admin):
        """Récupération du profil utilisateur courant."""
        response = authenticated_client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_admin.id
        assert data["email"] == user_admin.email

    def test_get_user(self, authenticated_client, user_infirmier):
        """Récupération d'un utilisateur par ID."""
        response = authenticated_client.get(f"/api/v1/users/{user_infirmier.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == user_infirmier.id

    def test_get_user_not_found(self, authenticated_client):
        """Erreur 404 si utilisateur inexistant."""
        response = authenticated_client.get("/api/v1/users/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_user(self, authenticated_client, profession_infirmier):
        """Création d'un utilisateur."""
        response = authenticated_client.post(
            "/api/v1/users",
            json={
                "email": "nouveau@test.fr",
                "first_name": "Nouveau",
                "last_name": "Utilisateur",
                "profession_id": profession_infirmier.id
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "nouveau@test.fr"
        assert data["is_active"] is True

    def test_create_user_duplicate_email(self, authenticated_client, user_admin):
        """Erreur 409 si email déjà utilisé."""
        response = authenticated_client.post(
            "/api/v1/users",
            json={
                "email": user_admin.email,
                "first_name": "Duplicate",
                "last_name": "User"
            }
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_user(self, authenticated_client, user_infirmier):
        """Mise à jour d'un utilisateur."""
        response = authenticated_client.patch(
            f"/api/v1/users/{user_infirmier.id}",
            json={"first_name": "Prénom Modifié"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["first_name"] == "Prénom Modifié"

    def test_update_own_profile(self, authenticated_client_user, user_infirmier):
        """Un utilisateur peut modifier son propre profil."""
        response = authenticated_client_user.patch(
            f"/api/v1/users/{user_infirmier.id}",
            json={"phone_number": "0612345678"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_other_profile_forbidden(self, authenticated_client_user, user_admin):
        """Un non-admin ne peut pas modifier le profil d'un autre."""
        response = authenticated_client_user.patch(
            f"/api/v1/users/{user_admin.id}",
            json={"first_name": "Hack"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_is_admin_requires_admin(self, authenticated_client_user, user_infirmier):
        """Modifier is_admin requiert d'être admin."""
        response = authenticated_client_user.patch(
            f"/api/v1/users/{user_infirmier.id}",
            json={"is_admin": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user(self, authenticated_client, db_session, tenant, profession_infirmier):
        """Suppression d'un utilisateur (désactivation)."""
        # Créer un utilisateur à supprimer
        user = User(
            email="to_delete@test.fr",
            first_name="To",
            last_name="Delete",
            tenant_id=tenant.id,
            profession_id=profession_infirmier.id
        )
        db_session.add(user)
        db_session.flush()

        response = authenticated_client.delete(f"/api/v1/users/{user.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS USER ROLES ENDPOINTS
# =============================================================================

class TestUserRolesEndpoints:
    """Tests des endpoints /api/v1/users/{id}/roles."""

    def test_get_user_roles(self, authenticated_client, user_admin, role_admin):
        """Liste des rôles d'un utilisateur."""
        response = authenticated_client.get(f"/api/v1/users/{user_admin.id}/roles")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_add_role_to_user(
        self, authenticated_client, db_session, user_infirmier, tenant
    ):
        """Attribution d'un rôle à un utilisateur."""
        # Créer un rôle pour le test
        role = Role(
            name="TEST_ROLE_ADD",
            tenant_id=tenant.id,
            is_system_role=False
        )
        db_session.add(role)
        db_session.flush()

        response = authenticated_client.post(
            f"/api/v1/users/{user_infirmier.id}/roles",
            json={"role_id": role.id}
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_duplicate_role_fails(
        self, authenticated_client, db_session, user_infirmier, role_admin, tenant
    ):
        """Erreur 409 si le rôle est déjà attribué."""
        # Ajouter le rôle une première fois
        user_role = UserRole(
            user_id=user_infirmier.id,
            role_id=role_admin.id,
            assigned_by=user_infirmier.id,
            tenant_id=tenant.id
        )
        db_session.add(user_role)
        db_session.flush()

        # Tenter d'ajouter le même rôle
        response = authenticated_client.post(
            f"/api/v1/users/{user_infirmier.id}/roles",
            json={"role_id": role_admin.id}
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_remove_role_from_user(
        self, authenticated_client, db_session, user_infirmier, tenant
    ):
        """Retrait d'un rôle d'un utilisateur."""
        # Créer et attribuer un rôle
        role = Role(
            name="ROLE_TO_REMOVE",
            tenant_id=tenant.id,
            is_system_role=False
        )
        db_session.add(role)
        db_session.flush()

        user_role = UserRole(
            user_id=user_infirmier.id,
            role_id=role.id,
            assigned_by=user_infirmier.id,
            tenant_id=tenant.id
        )
        db_session.add(user_role)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/users/{user_infirmier.id}/roles/{role.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS USER ENTITIES ENDPOINTS
# =============================================================================

class TestUserEntitiesEndpoints:
    """Tests des endpoints /api/v1/users/{id}/entities."""

    def test_get_user_entities(self, authenticated_client, user_admin):
        """Liste des entités d'un utilisateur."""
        response = authenticated_client.get(f"/api/v1/users/{user_admin.id}/entities")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_add_entity_to_user(
        self, authenticated_client, db_session, user_infirmier, tenant, country
    ):
        """Rattachement à une entité."""
        # Créer une entité
        entity = Entity(
            name="Nouvelle Entité Test",
            entity_type=EntityType.SSIAD,
            tenant_id=tenant.id,
            country_id=country.id
        )
        db_session.add(entity)
        db_session.flush()

        response = authenticated_client.post(
            f"/api/v1/users/{user_infirmier.id}/entities",
            json={
                "entity_id": entity.id,
                "contract_type": "SALARIE",  # CORRIGÉ: CDI n'existe pas
                "start_date": str(date.today()),
                "is_primary": True
            }
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_duplicate_entity_fails(
        self, authenticated_client, user_infirmier, entity
    ):
        """Erreur 409 si déjà rattaché à l'entité."""
        # Rattacher deux fois à la même entité
        response = authenticated_client.post(
            f"/api/v1/users/{user_infirmier.id}/entities",
            json={
                "entity_id": entity.id,
                "contract_type": "SALARIE",  # CORRIGÉ: CDI n'existe pas
                "start_date": str(date.today())
            }
        )
        # Première fois: OK ou déjà existant

        response2 = authenticated_client.post(
            f"/api/v1/users/{user_infirmier.id}/entities",
            json={
                "entity_id": entity.id,
                "contract_type": "SALARIE",  # CORRIGÉ: CDD n'existe pas
                "start_date": str(date.today())
            }
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

    def test_update_user_entity(
        self, authenticated_client, db_session, user_infirmier, tenant, country
    ):
        """Mise à jour du rattachement."""
        # Créer une entité dédiée à ce test pour éviter les conflits
        test_entity = Entity(
            name="Entité Update Test",
            entity_type=EntityType.SSIAD,
            tenant_id=tenant.id,
            country_id=country.id
        )
        db_session.add(test_entity)
        db_session.flush()

        # Créer le rattachement
        user_entity = UserEntity(
            user_id=user_infirmier.id,
            entity_id=test_entity.id,  # CORRIGÉ: utiliser la nouvelle entité
            tenant_id=tenant.id,
            contract_type=ContractType.SALARIE,  # CORRIGÉ: CDI n'existe pas
            start_date=date.today(),
            is_primary=False
        )
        db_session.add(user_entity)
        db_session.flush()

        response = authenticated_client.patch(
            f"/api/v1/users/{user_infirmier.id}/entities/{test_entity.id}",
            json={"is_primary": True}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_primary"] is True

    def test_remove_entity_from_user(
        self, authenticated_client, db_session, user_infirmier, tenant, country
    ):
        """Détachement d'une entité."""
        # Créer entité et rattachement
        new_entity = Entity(
            name="Entity to Remove",
            entity_type=EntityType.SAAD,
            tenant_id=tenant.id,
            country_id=country.id
        )
        db_session.add(new_entity)
        db_session.flush()

        user_entity = UserEntity(
            user_id=user_infirmier.id,
            entity_id=new_entity.id,
            tenant_id=tenant.id,
            contract_type=ContractType.SALARIE,  # CORRIGÉ: CDD n'existe pas
            start_date=date.today()
        )
        db_session.add(user_entity)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/users/{user_infirmier.id}/entities/{new_entity.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS USER AVAILABILITIES ENDPOINTS
# =============================================================================

class TestUserAvailabilitiesEndpoints:
    """Tests des endpoints /api/v1/users/{id}/availabilities."""

    def test_get_user_availabilities(self, authenticated_client, user_admin):
        """Liste des disponibilités d'un utilisateur."""
        response = authenticated_client.get(
            f"/api/v1/users/{user_admin.id}/availabilities"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_availabilities_filter_by_day(
        self, authenticated_client, user_infirmier, user_availability
    ):
        """Filtrage par jour de la semaine."""
        response = authenticated_client.get(
            f"/api/v1/users/{user_infirmier.id}/availabilities",
            params={"day_of_week": 1}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_create_availability(self, authenticated_client, user_admin, entity):
        """Création d'une disponibilité."""
        response = authenticated_client.post(
            f"/api/v1/users/{user_admin.id}/availabilities",
            json={
                "entity_id": entity.id,
                "day_of_week": 2,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "is_recurring": True,
                "is_active": True
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["day_of_week"] == 2

    def test_create_availability_for_other_user_forbidden(
        self, authenticated_client_user, user_admin, entity
    ):
        """Création de disponibilité pour un autre utilisateur interdite."""
        response = authenticated_client_user.post(
            f"/api/v1/users/{user_admin.id}/availabilities",
            json={
                "day_of_week": 3,
                "start_time": "08:00:00",
                "end_time": "12:00:00"
            }
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_availability_invalid_time_range(
        self, authenticated_client, user_admin
    ):
        """Erreur 422 si heure de fin avant heure de début."""
        response = authenticated_client.post(
            f"/api/v1/users/{user_admin.id}/availabilities",
            json={
                "day_of_week": 1,
                "start_time": "14:00:00",
                "end_time": "10:00:00"  # Avant start_time
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_availability(
        self, authenticated_client, db_session, user_admin, entity, tenant
    ):
        """Mise à jour d'une disponibilité."""
        # Créer une disponibilité
        availability = UserAvailability(
            user_id=user_admin.id,
            entity_id=entity.id,
            tenant_id=tenant.id,
            day_of_week=4,
            start_time=time(8, 0),
            end_time=time(12, 0),
            is_active=True
        )
        db_session.add(availability)
        db_session.flush()

        response = authenticated_client.patch(
            f"/api/v1/users/{user_admin.id}/availabilities/{availability.id}",
            json={"max_patients": 5}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["max_patients"] == 5

    def test_delete_availability(
        self, authenticated_client, db_session, user_admin, entity, tenant
    ):
        """Suppression d'une disponibilité."""
        availability = UserAvailability(
            user_id=user_admin.id,
            entity_id=entity.id,
            tenant_id=tenant.id,
            day_of_week=5,
            start_time=time(8, 0),
            end_time=time(12, 0),
            is_active=True
        )
        db_session.add(availability)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/users/{user_admin.id}/availabilities/{availability.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# TESTS VALIDATION
# =============================================================================

class TestValidation:
    """Tests de validation des données entrantes."""

    def test_invalid_email(self, authenticated_client, profession_infirmier):
        """Rejet d'un email invalide."""
        response = authenticated_client.post(
            "/api/v1/users",
            json={
                "email": "not-an-email",
                "first_name": "Test",
                "last_name": "Invalid",
                "profession_id": profession_infirmier.id
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_profession_category(self, authenticated_client):
        """Rejet d'une catégorie de profession invalide."""
        response = authenticated_client.post(
            "/api/v1/professions",
            json={
                "name": "Test Profession",
                "category": "INVALID_CATEGORY"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_day_of_week(self, authenticated_client, user_admin):
        """Rejet d'un jour de semaine invalide."""
        response = authenticated_client.post(
            f"/api/v1/users/{user_admin.id}/availabilities",
            json={
                "day_of_week": 8,  # Max 7
                "start_time": "08:00:00",
                "end_time": "12:00:00"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_contract_type(self, authenticated_client, user_admin, entity):
        """Rejet d'un type de contrat invalide."""
        response = authenticated_client.post(
            f"/api/v1/users/{user_admin.id}/entities",
            json={
                "entity_id": entity.id,
                "contract_type": "INVALID_TYPE",
                "start_date": str(date.today())
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# TESTS AUTHENTIFICATION
# =============================================================================

class TestAuthentication:
    """Tests d'authentification (accès sans token)."""

    def test_list_users_requires_auth(self, unauthenticated_client):
        """Liste des utilisateurs requiert authentification."""
        response = unauthenticated_client.get("/api/v1/users")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_user_requires_auth(self, unauthenticated_client):
        """Création d'utilisateur requiert authentification."""
        response = unauthenticated_client.post(
            "/api/v1/users",
            json={
                "email": "test@test.fr",
                "first_name": "Test",
                "last_name": "User"
            }
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_role_requires_admin(self, authenticated_client_user):
        """Création de rôle requiert privilèges admin."""
        response = authenticated_client_user.post(
            "/api/v1/roles",
            json={
                "name": "UNAUTHORIZED_ROLE",
                "description": "Should fail"
            }
        )
        # Soit 401 (pas auth) soit 403 (pas admin)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]