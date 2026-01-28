"""
Tests API pour le module Tenants - Architecture v4.3

Ce module teste les endpoints réservés aux SuperAdmins :
- /api/v1/tenants : CRUD Tenants
- /api/v1/tenants/{id}/subscriptions : Gestion des abonnements
- /api/v1/tenants/{id}/usage : Consultation de la consommation

================================================================================
STRUCTURE DU FICHIER
================================================================================

    Section                     | Contenu
    ----------------------------|------------------------------------------------
    Fixtures SuperAdmin         | super_admin_owner, super_admin_admin,
                                | super_admin_support, super_admin_inactive
    Fixtures Tenants            | tenant_gcsms, tenant_ssiad,
                                | tenant_suspended, tenant_terminated
    Fixtures Subscriptions      | subscription_active, subscription_trial,
                                | subscription_cancelled
    Fixtures Usage              | usage_current_month, usage_previous_month_invoiced
    Clients authentifiés        | authenticated_superadmin_client (owner),
                                | _admin, _support, unauthenticated_

================================================================================
TESTS COUVERTS (68 tests)
================================================================================

    Classe                      | Tests | Description
    ----------------------------|-------|------------------------------------------
    TestTenantList              |   7   | Pagination, filtres, auth
    TestTenantCreate            |   9   | Succès, doublons, validation, permissions
    TestTenantRead              |   3   | GET by ID, 404, permissions
    TestTenantUpdate            |   5   | PATCH, doublons SIRET, 403
    TestTenantStatusChanges     |   6   | Suspend, activate, cas limites
    TestTenantDelete            |   5   | Confirmation, already terminated, 403
    TestSubscriptionList        |   3   | Liste, filtres, tenant 404
    TestSubscriptionGetActive   |   3   | Active, trial, none
    TestSubscriptionGetById     |   2   | Succès, wrong tenant
    TestSubscriptionCreate      |   3   | Succès, annulation auto, 403
    TestSubscriptionUpdate      |   1   | PATCH
    TestSubscriptionStatusChanges|  6   | Activate, cancel, mark-past-due
    TestUsageList               |   4   | Liste, filtres year/invoiced
    TestUsageCurrent            |   2   | Current, no subscription
    TestUsageGetById            |   2   | Succès, wrong tenant
    TestUsageMarkInvoiced       |   3   | Succès, already invoiced, 403
    TestAuthentication          |   1   | Couverture multiple endpoints

================================================================================

Architecture de sécurité :
- Authentification SuperAdmin (pas User)
- Permissions basées sur SuperAdminRole
- Pas de RLS (get_db_no_rls)

Pattern de test :
- Override get_current_super_admin pour bypasser JWT
- Override get_db_no_rls pour utiliser SQLite de test
"""

from datetime import date, datetime, timezone, timedelta
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.enums import SubscriptionPlan, SubscriptionStatus, BillingCycle
from app.models.platform.super_admin import SuperAdmin, SuperAdminRole
from app.models.tenants.subscription import Subscription
from app.models.tenants.subscription_usage import SubscriptionUsage
from app.models.tenants.tenant import Tenant, TenantType, TenantStatus


# =============================================================================
# FIXTURES - SuperAdmin
# =============================================================================

@pytest.fixture
def super_admin_owner(db_session: Session) -> SuperAdmin:
    """
    Crée un SuperAdmin PLATFORM_OWNER (tous les droits).

    Utilisé pour tester les opérations qui nécessitent les droits maximaux.
    """
    admin = SuperAdmin(
        email="owner@carelink.fr",
        first_name="Platform",
        last_name="Owner",
        password_hash="$2b$12$fakehashfortest",  # Hash fictif pour tests
        role=SuperAdminRole.PLATFORM_OWNER,
        is_active=True,
        mfa_enabled=False,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


@pytest.fixture
def super_admin_admin(db_session: Session) -> SuperAdmin:
    """
    Crée un SuperAdmin PLATFORM_ADMIN (gestion tenants).

    Peut gérer les tenants mais pas les autres super-admins.
    """
    admin = SuperAdmin(
        email="admin@carelink.fr",
        first_name="Platform",
        last_name="Admin",
        password_hash="$2b$12$fakehashfortest",
        role=SuperAdminRole.PLATFORM_ADMIN,
        is_active=True,
        mfa_enabled=False,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


@pytest.fixture
def super_admin_support(db_session: Session) -> SuperAdmin:
    """
    Crée un SuperAdmin PLATFORM_SUPPORT (lecture seule).

    Utilisé pour tester les restrictions d'accès (403 Forbidden).
    """
    admin = SuperAdmin(
        email="support@carelink.fr",
        first_name="Platform",
        last_name="Support",
        password_hash="$2b$12$fakehashfortest",
        role=SuperAdminRole.PLATFORM_SUPPORT,
        is_active=True,
        mfa_enabled=False,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


@pytest.fixture
def super_admin_inactive(db_session: Session) -> SuperAdmin:
    """Crée un SuperAdmin inactif (pour tester le rejet)."""
    admin = SuperAdmin(
        email="inactive@carelink.fr",
        first_name="Inactive",
        last_name="Admin",
        password_hash="$2b$12$fakehashfortest",
        role=SuperAdminRole.PLATFORM_ADMIN,
        is_active=False,
        mfa_enabled=False,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


# =============================================================================
# FIXTURES - Tenants de test
# =============================================================================

@pytest.fixture
def tenant_gcsms(db_session: Session, country) -> Tenant:
    """Crée un tenant GCSMS pour les tests."""
    tenant = Tenant(
        code="TEST-GCSMS-001",
        name="GCSMS Test Île-de-France",
        legal_name="Groupement de Coopération Sanitaire Test",
        siret="12345678901234",
        tenant_type=TenantType.GCSMS,
        status=TenantStatus.ACTIVE,
        contact_email="contact@gcsms-test.fr",
        contact_phone="0100000000",
        billing_email="facturation@gcsms-test.fr",
        address_line1="1 rue du Test",
        postal_code="75001",
        city="Paris",
        country_id=country.id,
        encryption_key_id="tenant-key-test001",
        timezone="Europe/Paris",
        locale="fr_FR",
        max_patients=500,
        max_users=50,
        max_storage_gb=100,
        settings={"feature_flags": {"new_dashboard": True}},
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def tenant_ssiad(db_session: Session, country) -> Tenant:
    """Crée un tenant SSIAD pour les tests."""
    tenant = Tenant(
        code="TEST-SSIAD-001",
        name="SSIAD Test Lyon",
        tenant_type=TenantType.SSIAD,
        status=TenantStatus.ACTIVE,
        contact_email="contact@ssiad-test.fr",
        city="Lyon",
        country_id=country.id,
        encryption_key_id="tenant-key-test002",
        max_patients=100,
        max_users=15,
        max_storage_gb=25,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def tenant_suspended(db_session: Session, country) -> Tenant:
    """Crée un tenant suspendu."""
    tenant = Tenant(
        code="TEST-SUSPENDED-001",
        name="Tenant Suspendu Test",
        tenant_type=TenantType.SAAD,
        status=TenantStatus.SUSPENDED,
        contact_email="contact@suspended.fr",
        country_id=country.id,
        encryption_key_id="tenant-key-suspended",
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def tenant_terminated(db_session: Session, country) -> Tenant:
    """Crée un tenant résilié."""
    tenant = Tenant(
        code="TEST-TERMINATED-001",
        name="Tenant Résilié Test",
        tenant_type=TenantType.OTHER,
        status=TenantStatus.TERMINATED,
        contact_email="contact@terminated.fr",
        country_id=country.id,
        encryption_key_id="tenant-key-terminated",
        terminated_at=datetime.now(timezone.utc),
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


# =============================================================================
# FIXTURES - Subscriptions de test
# =============================================================================

@pytest.fixture
def subscription_active(db_session: Session, tenant_gcsms: Tenant) -> Subscription:
    """Crée un abonnement actif."""
    subscription = Subscription(
        tenant_id=tenant_gcsms.id,
        plan_code=SubscriptionPlan.M,
        plan_name="Plan Medium - GCSMS",
        status=SubscriptionStatus.ACTIVE,
        started_at=date.today() - timedelta(days=30),
        expires_at=date.today() + timedelta(days=335),
        base_price_cents=50000,
        price_per_extra_patient_cents=500,
        currency="EUR",
        billing_cycle=BillingCycle.MONTHLY,
        included_patients=500,
        included_users=50,
        included_storage_gb=100,
    )
    db_session.add(subscription)
    db_session.flush()
    return subscription


@pytest.fixture
def subscription_trial(db_session: Session, tenant_ssiad: Tenant) -> Subscription:
    """Crée un abonnement en période d'essai."""
    subscription = Subscription(
        tenant_id=tenant_ssiad.id,
        plan_code=SubscriptionPlan.S,
        plan_name="Plan Small - Essai",
        status=SubscriptionStatus.TRIAL,
        started_at=date.today(),
        trial_ends_at=date.today() + timedelta(days=30),
        base_price_cents=15000,
        currency="EUR",
        billing_cycle=BillingCycle.MONTHLY,
        included_patients=100,
        included_users=10,
    )
    db_session.add(subscription)
    db_session.flush()
    return subscription


@pytest.fixture
def subscription_cancelled(db_session: Session, tenant_gcsms: Tenant) -> Subscription:
    """Crée un abonnement annulé (historique)."""
    subscription = Subscription(
        tenant_id=tenant_gcsms.id,
        plan_code=SubscriptionPlan.S,
        plan_name="Plan Small - Ancien",
        status=SubscriptionStatus.CANCELLED,
        started_at=date.today() - timedelta(days=365),
        expires_at=date.today() - timedelta(days=30),
        base_price_cents=15000,
        currency="EUR",
        billing_cycle=BillingCycle.MONTHLY,
        included_patients=100,
        included_users=10,
    )
    db_session.add(subscription)
    db_session.flush()
    return subscription


# =============================================================================
# FIXTURES - Usage de test
# =============================================================================

@pytest.fixture
def usage_current_month(db_session: Session, subscription_active: Subscription) -> SubscriptionUsage:
    """Crée un enregistrement de consommation pour le mois en cours."""
    today = date.today()
    period_start = today.replace(day=1)

    # Calculer le dernier jour du mois
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    period_end = next_month - timedelta(days=1)

    usage = SubscriptionUsage(
        subscription_id=subscription_active.id,
        period_start=period_start,
        period_end=period_end,
        active_patients_count=245,
        active_users_count=28,
        storage_used_mb=15360,
        api_calls_count=125000,
        base_amount_cents=50000,
        overage_amount_cents=0,
        total_amount_cents=50000,
        invoiced=False,
    )
    db_session.add(usage)
    db_session.flush()
    return usage


@pytest.fixture
def usage_previous_month_invoiced(db_session: Session, subscription_active: Subscription) -> SubscriptionUsage:
    """Crée un enregistrement de consommation du mois précédent (facturé)."""
    today = date.today()

    # Mois précédent
    if today.month == 1:
        period_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        period_start = today.replace(month=today.month - 1, day=1)
    period_end = today.replace(day=1) - timedelta(days=1)

    usage = SubscriptionUsage(
        subscription_id=subscription_active.id,
        period_start=period_start,
        period_end=period_end,
        active_patients_count=230,
        active_users_count=25,
        storage_used_mb=14000,
        api_calls_count=110000,
        base_amount_cents=50000,
        overage_amount_cents=0,
        total_amount_cents=50000,
        invoiced=True,
        invoice_id="INV-2024-001",
    )
    db_session.add(usage)
    db_session.flush()
    return usage


# =============================================================================
# FIXTURES - Clients authentifiés SuperAdmin
# =============================================================================

@pytest.fixture
def authenticated_superadmin_client(
        db_session: Session,
        super_admin_owner: SuperAdmin
) -> Generator[TestClient, None, None]:
    """
    Client de test avec authentification SuperAdmin (PLATFORM_OWNER).

    Override les dépendances pour :
    - Utiliser db_session (SQLite) au lieu de PostgreSQL
    - Bypasser l'authentification JWT SuperAdmin
    - Retourner super_admin_owner comme admin courant
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.api.v1.platform.super_admin_security import get_current_super_admin

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_super_admin():
        return super_admin_owner

    # Override les dépendances
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_super_admin] = override_get_current_super_admin

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_superadmin_client_admin(
        db_session: Session,
        super_admin_admin: SuperAdmin
) -> Generator[TestClient, None, None]:
    """
    Client de test avec authentification SuperAdmin (PLATFORM_ADMIN).

    Peut gérer les tenants mais pas les super-admins.
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.api.v1.platform.super_admin_security import get_current_super_admin

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_super_admin():
        return super_admin_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_super_admin] = override_get_current_super_admin

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_superadmin_client_support(
        db_session: Session,
        super_admin_support: SuperAdmin
) -> Generator[TestClient, None, None]:
    """
    Client de test avec authentification SuperAdmin (PLATFORM_SUPPORT).

    Lecture seule - utilisé pour tester les 403 sur les mutations.
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.api.v1.platform.super_admin_security import get_current_super_admin

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_super_admin():
        return super_admin_support

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_super_admin] = override_get_current_super_admin

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_superadmin_client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Client de test sans authentification SuperAdmin.

    Utilisé pour tester les 401 Unauthorized.
    """
    from app.database.session_rls import get_db, get_db_no_rls

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    # Pas d'override de get_current_super_admin → authentification requise

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# TESTS TENANT ENDPOINTS - LIST
# =============================================================================

class TestTenantList:
    """Tests de l'endpoint GET /api/v1/tenants."""

    def test_list_tenants_success(
            self, authenticated_superadmin_client, tenant_gcsms, tenant_ssiad
    ):
        """Liste des tenants avec pagination."""
        response = authenticated_superadmin_client.get("/api/v1/tenants")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert data["total"] >= 2

    def test_list_tenants_filter_by_status(
            self, authenticated_superadmin_client, tenant_gcsms, tenant_suspended
    ):
        """Filtrage par statut."""
        response = authenticated_superadmin_client.get(
            "/api/v1/tenants",
            params={"status": "ACTIVE"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for item in data["items"]:
            assert item["status"] == "ACTIVE"

    def test_list_tenants_filter_by_type(
            self, authenticated_superadmin_client, tenant_gcsms, tenant_ssiad
    ):
        """Filtrage par type de tenant."""
        response = authenticated_superadmin_client.get(
            "/api/v1/tenants",
            params={"tenant_type": "GCSMS"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for item in data["items"]:
            assert item["tenant_type"] == "GCSMS"

    def test_list_tenants_search(
            self, authenticated_superadmin_client, tenant_gcsms
    ):
        """Recherche par nom ou code."""
        response = authenticated_superadmin_client.get(
            "/api/v1/tenants",
            params={"search": "GCSMS"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_tenants_pagination(
            self, authenticated_superadmin_client, tenant_gcsms, tenant_ssiad
    ):
        """Pagination des résultats."""
        response = authenticated_superadmin_client.get(
            "/api/v1/tenants",
            params={"page": 1, "size": 1}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["items"]) == 1
        assert data["size"] == 1

    def test_list_tenants_requires_auth(self, unauthenticated_superadmin_client):
        """Liste des tenants requiert authentification SuperAdmin."""
        response = unauthenticated_superadmin_client.get("/api/v1/tenants")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# TESTS TENANT ENDPOINTS - CREATE
# =============================================================================

class TestTenantCreate:
    """Tests de l'endpoint POST /api/v1/tenants."""

    def test_create_tenant_success(self, authenticated_superadmin_client, country):
        """Création d'un tenant avec données minimales."""
        payload = {
            "code": "NEW-TENANT-001",
            "name": "Nouveau Tenant Test",
            "tenant_type": "SSIAD",
            "contact_email": "contact@nouveau-tenant.fr",
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["code"] == "NEW-TENANT-001"
        assert data["name"] == "Nouveau Tenant Test"
        assert data["tenant_type"] == "SSIAD"
        assert data["status"] == "ACTIVE"

    def test_create_tenant_full_data(self, authenticated_superadmin_client, country):
        """Création d'un tenant avec toutes les données."""
        payload = {
            "code": "FULL-TENANT-001",
            "name": "Tenant Complet Test",
            "legal_name": "Société Tenant Complet SAS",
            "siret": "98765432109876",
            "tenant_type": "GCSMS",
            "contact_email": "contact@full-tenant.fr",
            "contact_phone": "0102030405",
            "billing_email": "billing@full-tenant.fr",
            "address_line1": "10 avenue des Tests",
            "postal_code": "69001",
            "city": "Lyon",
            "country_id": country.id,
            "timezone": "Europe/Paris",
            "locale": "fr_FR",
            "max_patients": 1000,
            "max_users": 100,
            "max_storage_gb": 200,
            "settings": {"custom_feature": True},
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["legal_name"] == "Société Tenant Complet SAS"
        assert data["siret"] == "98765432109876"
        assert data["max_patients"] == 1000
        assert data["settings"]["custom_feature"] is True

    def test_create_tenant_duplicate_code(
            self, authenticated_superadmin_client, tenant_gcsms
    ):
        """Erreur 409 si code déjà utilisé."""
        payload = {
            "code": tenant_gcsms.code,  # Code existant
            "name": "Autre Tenant",
            "tenant_type": "SSIAD",
            "contact_email": "autre@tenant.fr",
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "code" in response.json()["detail"].lower()

    def test_create_tenant_duplicate_siret(
            self, authenticated_superadmin_client, tenant_gcsms
    ):
        """Erreur 409 si SIRET déjà utilisé."""
        payload = {
            "code": "UNIQUE-CODE-999",
            "name": "Autre Tenant",
            "tenant_type": "SSIAD",
            "contact_email": "autre@tenant.fr",
            "siret": tenant_gcsms.siret,  # SIRET existant
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "siret" in response.json()["detail"].lower()

    def test_create_tenant_invalid_siret_format(self, authenticated_superadmin_client):
        """Erreur 422 si format SIRET invalide."""
        payload = {
            "code": "INVALID-SIRET-001",
            "name": "Tenant SIRET Invalide",
            "tenant_type": "SSIAD",
            "contact_email": "contact@test.fr",
            "siret": "123",  # SIRET doit avoir 14 chiffres
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_tenant_invalid_email(self, authenticated_superadmin_client):
        """Erreur 422 si email invalide."""
        payload = {
            "code": "INVALID-EMAIL-001",
            "name": "Tenant Email Invalide",
            "tenant_type": "SSIAD",
            "contact_email": "not-an-email",
        }

        response = authenticated_superadmin_client.post("/api/v1/tenants", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_tenant_support_forbidden(
            self, authenticated_superadmin_client_support
    ):
        """PLATFORM_SUPPORT ne peut pas créer de tenant."""
        payload = {
            "code": "FORBIDDEN-001",
            "name": "Tenant Interdit",
            "tenant_type": "SSIAD",
            "contact_email": "contact@interdit.fr",
        }

        response = authenticated_superadmin_client_support.post(
            "/api/v1/tenants", json=payload
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_tenant_admin_allowed(
            self, authenticated_superadmin_client_admin, country
    ):
        """PLATFORM_ADMIN peut créer un tenant."""
        payload = {
            "code": "ADMIN-CREATED-001",
            "name": "Tenant Créé par Admin",
            "tenant_type": "SAAD",
            "contact_email": "contact@admin-created.fr",
        }

        response = authenticated_superadmin_client_admin.post(
            "/api/v1/tenants", json=payload
        )

        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# TESTS TENANT ENDPOINTS - READ
# =============================================================================

class TestTenantRead:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}."""

    def test_get_tenant_success(self, authenticated_superadmin_client, tenant_gcsms):
        """Récupération d'un tenant par ID."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == tenant_gcsms.id
        assert data["code"] == tenant_gcsms.code
        assert data["name"] == tenant_gcsms.name
        # TenantWithStats inclut des stats
        assert "current_patients_count" in data
        assert "current_users_count" in data

    def test_get_tenant_not_found(self, authenticated_superadmin_client):
        """Erreur 404 si tenant inexistant."""
        response = authenticated_superadmin_client.get("/api/v1/tenants/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS TENANT ENDPOINTS - UPDATE
# =============================================================================

class TestTenantUpdate:
    """Tests de l'endpoint PATCH /api/v1/tenants/{tenant_id}."""

    def test_update_tenant_success(self, authenticated_superadmin_client, tenant_gcsms):
        """Mise à jour partielle d'un tenant."""
        payload = {
            "name": "GCSMS Renommé",
            "contact_phone": "0999999999",
        }

        response = authenticated_superadmin_client.patch(
            f"/api/v1/tenants/{tenant_gcsms.id}",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "GCSMS Renommé"
        assert data["contact_phone"] == "0999999999"
        # Les autres champs ne changent pas
        assert data["code"] == tenant_gcsms.code

    def test_update_tenant_limits(self, authenticated_superadmin_client, tenant_gcsms):
        """Mise à jour des limites d'un tenant."""
        payload = {
            "max_patients": 1000,
            "max_users": 100,
            "max_storage_gb": 500,
        }

        response = authenticated_superadmin_client.patch(
            f"/api/v1/tenants/{tenant_gcsms.id}",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["max_patients"] == 1000
        assert data["max_users"] == 100
        assert data["max_storage_gb"] == 500

    def test_update_tenant_duplicate_siret(
            self, authenticated_superadmin_client, tenant_gcsms, tenant_ssiad, db_session
    ):
        """Erreur 409 si mise à jour avec un SIRET déjà utilisé."""
        # Donner un SIRET au tenant SSIAD
        tenant_ssiad.siret = "11111111111111"
        db_session.flush()

        payload = {"siret": tenant_ssiad.siret}

        response = authenticated_superadmin_client.patch(
            f"/api/v1/tenants/{tenant_gcsms.id}",
            json=payload
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_tenant_not_found(self, authenticated_superadmin_client):
        """Erreur 404 si tenant inexistant."""
        response = authenticated_superadmin_client.patch(
            "/api/v1/tenants/99999",
            json={"name": "Test"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_tenant_support_forbidden(
            self, authenticated_superadmin_client_support, tenant_gcsms
    ):
        """PLATFORM_SUPPORT ne peut pas modifier un tenant."""
        payload = {"name": "Modification Interdite"}

        response = authenticated_superadmin_client_support.patch(
            f"/api/v1/tenants/{tenant_gcsms.id}",
            json=payload
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# TESTS TENANT ENDPOINTS - STATUS CHANGES
# =============================================================================

class TestTenantStatusChanges:
    """Tests des endpoints de changement de statut."""

    def test_suspend_tenant_success(
            self, authenticated_superadmin_client, tenant_gcsms
    ):
        """Suspension d'un tenant actif."""
        payload = {"status": "SUSPENDED", "reason": "Impayé"}

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/suspend",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "SUSPENDED"

    def test_suspend_tenant_already_terminated(
            self, authenticated_superadmin_client, tenant_terminated
    ):
        """Impossible de suspendre un tenant déjà résilié."""
        payload = {"status": "SUSPENDED", "reason": "Test"}

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_terminated.id}/suspend",
            json=payload
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_tenant_success(
            self, authenticated_superadmin_client, tenant_suspended
    ):
        """Activation d'un tenant suspendu."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_suspended.id}/activate"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ACTIVE"

    def test_activate_tenant_sets_activated_at(
            self, authenticated_superadmin_client, db_session, country
    ):
        """Première activation définit activated_at."""
        # Créer un nouveau tenant sans activated_at
        new_tenant = Tenant(
            code="NEW-ACTIVATE-001",
            name="Nouveau à Activer",
            tenant_type=TenantType.SSIAD,
            status=TenantStatus.SUSPENDED,  # Commencer suspendu
            contact_email="new@activate.fr",
            country_id=country.id,
            encryption_key_id="test-key",
        )
        db_session.add(new_tenant)
        db_session.flush()

        assert new_tenant.activated_at is None

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{new_tenant.id}/activate"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["activated_at"] is not None

    def test_activate_tenant_already_terminated(
            self, authenticated_superadmin_client, tenant_terminated
    ):
        """Impossible de réactiver un tenant résilié."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_terminated.id}/activate"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_suspend_tenant_support_forbidden(
            self, authenticated_superadmin_client_support, tenant_gcsms
    ):
        """PLATFORM_SUPPORT ne peut pas suspendre un tenant."""
        payload = {"status": "SUSPENDED", "reason": "Test"}

        response = authenticated_superadmin_client_support.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/suspend",
            json=payload
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# TESTS TENANT ENDPOINTS - DELETE
# =============================================================================

class TestTenantDelete:
    """Tests de l'endpoint DELETE /api/v1/tenants/{tenant_id}."""

    def test_terminate_tenant_success(
            self, authenticated_superadmin_client, tenant_ssiad
    ):
        """Résiliation d'un tenant avec confirmation."""
        response = authenticated_superadmin_client.delete(
            f"/api/v1/tenants/{tenant_ssiad.id}",
            params={"confirm": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_terminate_tenant_requires_confirmation(
            self, authenticated_superadmin_client, tenant_ssiad
    ):
        """Résiliation requiert confirmation explicite."""
        response = authenticated_superadmin_client.delete(
            f"/api/v1/tenants/{tenant_ssiad.id}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirm" in response.json()["detail"].lower()

    def test_terminate_tenant_already_terminated(
            self, authenticated_superadmin_client, tenant_terminated
    ):
        """Erreur si tenant déjà résilié."""
        response = authenticated_superadmin_client.delete(
            f"/api/v1/tenants/{tenant_terminated.id}",
            params={"confirm": True}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_terminate_tenant_not_found(self, authenticated_superadmin_client):
        """Erreur 404 si tenant inexistant."""
        response = authenticated_superadmin_client.delete(
            "/api/v1/tenants/99999",
            params={"confirm": True}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_terminate_tenant_support_forbidden(
            self, authenticated_superadmin_client_support, tenant_ssiad
    ):
        """PLATFORM_SUPPORT ne peut pas résilier un tenant."""
        response = authenticated_superadmin_client_support.delete(
            f"/api/v1/tenants/{tenant_ssiad.id}",
            params={"confirm": True}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - LIST
# =============================================================================

class TestSubscriptionList:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/subscriptions."""

    def test_list_subscriptions_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Liste des abonnements d'un tenant."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_subscriptions_filter_by_status(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            subscription_cancelled,
    ):
        """Filtrage par statut d'abonnement."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions",
            params={"status": "ACTIVE"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for item in data["items"]:
            assert item["status"] == "ACTIVE"

    def test_list_subscriptions_tenant_not_found(
            self, authenticated_superadmin_client
    ):
        """Erreur 404 si tenant inexistant."""
        response = authenticated_superadmin_client.get(
            "/api/v1/tenants/99999/subscriptions"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - GET ACTIVE
# =============================================================================

class TestSubscriptionGetActive:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/subscriptions/active."""

    def test_get_active_subscription_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Récupération de l'abonnement actif."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/active"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == subscription_active.id
        assert data["status"] in ["ACTIVE", "TRIAL"]

    def test_get_active_subscription_trial(
            self, authenticated_superadmin_client, tenant_ssiad, subscription_trial
    ):
        """L'abonnement TRIAL est aussi considéré comme actif."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_ssiad.id}/subscriptions/active"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "TRIAL"

    def test_get_active_subscription_none(
            self, authenticated_superadmin_client, tenant_suspended
    ):
        """Erreur 404 si pas d'abonnement actif."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_suspended.id}/subscriptions/active"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - GET BY ID
# =============================================================================

class TestSubscriptionGetById:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/subscriptions/{subscription_id}."""

    def test_get_subscription_by_id_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Récupération d'un abonnement par ID."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_active.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == subscription_active.id
        assert data["tenant_id"] == tenant_gcsms.id

    def test_get_subscription_wrong_tenant(
            self, authenticated_superadmin_client, tenant_ssiad, subscription_active
    ):
        """Erreur 404 si abonnement n'appartient pas au tenant."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_ssiad.id}/subscriptions/{subscription_active.id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - CREATE
# =============================================================================

class TestSubscriptionCreate:
    """Tests de l'endpoint POST /api/v1/tenants/{tenant_id}/subscriptions."""

    def test_create_subscription_success(
            self, authenticated_superadmin_client, tenant_suspended
    ):
        """Création d'un abonnement."""
        payload = {
            "plan_code": "M",
            "plan_name": "Plan Medium",
            "started_at": str(date.today()),
            "status": "ACTIVE",
            "base_price_cents": 30000,
            "billing_cycle": "MONTHLY",
            "included_patients": 200,
        }

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_suspended.id}/subscriptions",
            json=payload
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["plan_code"] == "M"
        assert data["base_price_cents"] == 30000

    def test_create_subscription_cancels_previous(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active, db_session
    ):
        """La création d'un nouvel abonnement annule l'ancien."""
        payload = {
            "plan_code": "L",
            "plan_name": "Plan Large - Upgrade",
            "started_at": str(date.today()),
            "status": "ACTIVE",
            "base_price_cents": 80000,
            "billing_cycle": "MONTHLY",
            "included_patients": 1000,
        }

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions",
            json=payload
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Vérifier que l'ancien abonnement est annulé
        db_session.refresh(subscription_active)
        assert subscription_active.status == SubscriptionStatus.CANCELLED

    def test_create_subscription_support_forbidden(
            self, authenticated_superadmin_client_support, tenant_suspended
    ):
        """PLATFORM_SUPPORT ne peut pas créer d'abonnement."""
        payload = {
            "plan_code": "S",
            "started_at": str(date.today()),
            "base_price_cents": 10000,
            "billing_cycle": "MONTHLY",
            "included_patients": 50,
        }

        response = authenticated_superadmin_client_support.post(
            f"/api/v1/tenants/{tenant_suspended.id}/subscriptions",
            json=payload
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - UPDATE
# =============================================================================

class TestSubscriptionUpdate:
    """Tests de l'endpoint PATCH /api/v1/tenants/{tenant_id}/subscriptions/{subscription_id}."""

    def test_update_subscription_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Mise à jour d'un abonnement."""
        payload = {
            "included_patients": 600,
            "notes": "Upgrade négocié",
        }

        response = authenticated_superadmin_client.patch(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_active.id}",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["included_patients"] == 600
        assert data["notes"] == "Upgrade négocié"


# =============================================================================
# TESTS SUBSCRIPTION ENDPOINTS - STATUS CHANGES
# =============================================================================

class TestSubscriptionStatusChanges:
    """Tests des endpoints de changement de statut d'abonnement."""

    def test_activate_subscription_from_trial(
            self, authenticated_superadmin_client, tenant_ssiad, subscription_trial
    ):
        """Activation d'un abonnement en période d'essai."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_ssiad.id}/subscriptions/{subscription_trial.id}/activate"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ACTIVE"

    def test_activate_subscription_cancelled_forbidden(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_cancelled
    ):
        """Impossible d'activer un abonnement annulé."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_cancelled.id}/activate"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_subscription_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Annulation d'un abonnement."""
        payload = {"status": "CANCELLED", "reason": "Client request"}

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_active.id}/cancel",
            json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "CANCELLED"

    def test_cancel_subscription_already_cancelled(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_cancelled
    ):
        """Erreur si abonnement déjà annulé."""
        payload = {"status": "CANCELLED"}

        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_cancelled.id}/cancel",
            json=payload
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_past_due_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Marquer un abonnement en retard de paiement."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/subscriptions/{subscription_active.id}/mark-past-due"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "PAST_DUE"

    def test_mark_past_due_inactive_forbidden(
            self, authenticated_superadmin_client, tenant_ssiad, subscription_trial
    ):
        """Impossible de marquer PAST_DUE un abonnement non-actif."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_ssiad.id}/subscriptions/{subscription_trial.id}/mark-past-due"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# TESTS USAGE ENDPOINTS - LIST
# =============================================================================

class TestUsageList:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/usage."""

    def test_list_usage_success(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
    ):
        """Liste de l'historique de consommation."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert data["total"] >= 1

    def test_list_usage_filter_by_year(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
    ):
        """Filtrage par année."""
        current_year = date.today().year

        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage",
            params={"year": current_year}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_list_usage_filter_by_invoiced(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
            usage_previous_month_invoiced,
    ):
        """Filtrage par statut de facturation."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage",
            params={"invoiced": True}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for item in data["items"]:
            assert item["invoiced"] is True

    def test_list_usage_no_subscription(
            self, authenticated_superadmin_client, tenant_suspended
    ):
        """Erreur 404 si pas d'abonnement actif."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_suspended.id}/usage"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS USAGE ENDPOINTS - CURRENT
# =============================================================================

class TestUsageCurrent:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/usage/current."""

    def test_get_current_usage_success(
            self, authenticated_superadmin_client, tenant_gcsms, subscription_active
    ):
        """Récupération de la consommation actuelle."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage/current"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["tenant_id"] == tenant_gcsms.id
        assert "current_patients" in data
        assert "current_users" in data
        assert "patients_usage_percent" in data
        assert "is_over_patient_limit" in data

    def test_get_current_usage_no_subscription(
            self, authenticated_superadmin_client, tenant_suspended
    ):
        """Erreur 404 si pas d'abonnement actif."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_suspended.id}/usage/current"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS USAGE ENDPOINTS - GET BY ID
# =============================================================================

class TestUsageGetById:
    """Tests de l'endpoint GET /api/v1/tenants/{tenant_id}/usage/{usage_id}."""

    def test_get_usage_by_id_success(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
    ):
        """Récupération des détails d'une période."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage/{usage_current_month.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == usage_current_month.id
        assert data["active_patients_count"] == usage_current_month.active_patients_count

    def test_get_usage_wrong_tenant(
            self,
            authenticated_superadmin_client,
            tenant_ssiad,
            usage_current_month,
    ):
        """Erreur 404 si usage n'appartient pas au tenant."""
        response = authenticated_superadmin_client.get(
            f"/api/v1/tenants/{tenant_ssiad.id}/usage/{usage_current_month.id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TESTS USAGE ENDPOINTS - MARK INVOICED
# =============================================================================

class TestUsageMarkInvoiced:
    """Tests de l'endpoint POST /api/v1/tenants/{tenant_id}/usage/{usage_id}/mark-invoiced."""

    def test_mark_invoiced_success(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
    ):
        """Marquer une période comme facturée."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage/{usage_current_month.id}/mark-invoiced",
            params={"invoice_id": "INV-2024-TEST"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["invoiced"] is True
        assert data["invoice_id"] == "INV-2024-TEST"

    def test_mark_invoiced_already_invoiced(
            self,
            authenticated_superadmin_client,
            tenant_gcsms,
            subscription_active,
            usage_previous_month_invoiced,
    ):
        """Erreur si déjà facturé."""
        response = authenticated_superadmin_client.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage/{usage_previous_month_invoiced.id}/mark-invoiced",
            params={"invoice_id": "INV-NEW"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_invoiced_support_forbidden(
            self,
            authenticated_superadmin_client_support,
            tenant_gcsms,
            subscription_active,
            usage_current_month,
    ):
        """PLATFORM_SUPPORT ne peut pas marquer comme facturé."""
        response = authenticated_superadmin_client_support.post(
            f"/api/v1/tenants/{tenant_gcsms.id}/usage/{usage_current_month.id}/mark-invoiced",
            params={"invoice_id": "INV-FORBIDDEN"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# TESTS AUTHENTICATION
# =============================================================================

class TestAuthentication:
    """Tests d'authentification SuperAdmin."""

    def test_tenant_endpoints_require_superadmin_auth(
            self, unauthenticated_superadmin_client
    ):
        """Les endpoints tenants requièrent authentification SuperAdmin."""
        endpoints = [
            ("GET", "/api/v1/tenants"),
            ("POST", "/api/v1/tenants"),
            ("GET", "/api/v1/tenants/1"),
            ("PATCH", "/api/v1/tenants/1"),
            ("DELETE", "/api/v1/tenants/1"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = unauthenticated_superadmin_client.get(url)
            elif method == "POST":
                response = unauthenticated_superadmin_client.post(url, json={})
            elif method == "PATCH":
                response = unauthenticated_superadmin_client.patch(url, json={})
            elif method == "DELETE":
                response = unauthenticated_superadmin_client.delete(url)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"{method} {url} should require authentication"