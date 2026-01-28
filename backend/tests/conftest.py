"""
Fixtures pytest partagées pour les tests CareLink.

Ce module fournit :
- Une base de données SQLite en mémoire pour les tests (rapide, isolé)
- Des fixtures pour créer des objets de test (Country, Tenant, Entity, User, etc.)

IMPORTANT - Multi-tenant:
- Seuls Entity, User et Patient ont tenant_id
- Role, Profession, Country, ServiceTemplate sont partagés (pas de tenant_id)
- CarePlan hérite du tenant via patient_id et entity_id

Changelog v4.3:
- Architecture permissions normalisée (Permission + RolePermission)
- Suppression de l'argument permissions=[] dans les constructeurs Role
"""

from datetime import date, time, datetime, timezone, timedelta
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security.jwt import create_access_token
# Import de la Base et des modèles
from app.database.base_class import Base
from app.main import app
from app.models import (
    # Reference
    Country,
    # Tenant (Multi-tenant)
    Tenant,
    Subscription,
    SubscriptionUsage,
    # Organization
    Entity,
    # User
    Profession,
    Role,
    Permission,  # AJOUT v4.3
    RolePermission,  # AJOUT v4.3
    User,
    UserRole,
    UserEntity,
    UserAvailability,
    # Patient
    Patient,
    PatientAccess,
    PatientDocument,
    PatientEvaluation,
    PatientThreshold,
    PatientVitals,
    PatientDevice,
    # Catalog
    ServiceTemplate,
    EntityService,
    # CarePlan
    CarePlan,
    CarePlanService,
    # Coordination
    CoordinationEntry,
    ScheduledIntervention,
    # Constants
)
from app.models.enums import (
    # Tenant
    TenantType,
    TenantStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
    # Organization
    EntityType,
    # User
    RoleName,
    ContractType,
    PermissionCategory,  # AJOUT v4.3
    # Patient
    AccessType,
    VitalType,
    VitalSource,
    EvaluationSchemaType,
    # Catalog
    ServiceCategory,
    # CarePlan
    CarePlanStatus,
    FrequencyType,
    ServicePriority,
    AssignmentStatus,
    # Coordination
    InterventionStatus,
    CoordinationCategory,
)


# =============================================================================
# HELPER FUNCTION - Création des permissions pour les tests (v4.3)
# =============================================================================

def create_role_with_permissions(
    db_session: Session,
    role_name: str,
    description: str,
    permission_codes: list[str],
    is_system_role: bool = True
) -> Role:
    """
    Helper pour créer un rôle avec ses permissions (architecture v4.3).

    Args:
        db_session: Session SQLAlchemy
        role_name: Nom du rôle (ex: "ADMIN")
        description: Description du rôle
        permission_codes: Liste des codes de permissions
        is_system_role: True si rôle système

    Returns:
        Role créé avec ses permissions
    """
    # Créer le rôle
    role = Role(
        name=role_name,
        description=description,
        is_system_role=is_system_role
    )
    db_session.add(role)
    db_session.flush()

    # Créer les permissions et associations
    for code in permission_codes:
        # Chercher la permission existante ou la créer
        perm = db_session.query(Permission).filter_by(code=code).first()
        if not perm:
            perm = Permission(
                code=code,
                name=code.replace("_", " ").title(),
                description=f"Permission {code}",
                category=PermissionCategory.ADMIN if code.startswith("ADMIN") else PermissionCategory.PATIENT
            )
            db_session.add(perm)
            db_session.flush()

        # Créer l'association RolePermission
        role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
        db_session.add(role_perm)

    db_session.flush()
    return role


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def engine():
    """
    Crée un engine SQLite en mémoire pour les tests.

    Avantages :
    - Rapide (pas d'I/O disque)
    - Isolé (chaque test a sa propre base)
    - Pas besoin de PostgreSQL pour les tests unitaires
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Mettre True pour debug SQL
    )

    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Nettoyer
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """
    Fournit une session de base de données isolée pour chaque test.

    Utilise un SAVEPOINT pour permettre le rollback même après
    des commit() dans le code testé.
    """
    connection = engine.connect()

    # Démarrer une transaction externe
    transaction = connection.begin()

    # Créer la session liée à cette connexion
    session = Session(bind=connection)

    # Démarrer un SAVEPOINT (transaction imbriquée)
    nested = connection.begin_nested()

    # Intercepter les commit() pour utiliser des savepoints
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            # Recréer un savepoint après chaque commit
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        # Rollback la transaction externe (annule tout)
        transaction.rollback()
        connection.close()


# =============================================================================
# MODEL FIXTURES - Données de base (Country)
# =============================================================================

@pytest.fixture
def country(db_session: Session) -> Country:
    """Crée un pays de test (France)."""
    country = Country(
        name="France",
        country_code="FR",
        status="active"
    )
    db_session.add(country)
    db_session.flush()
    return country


# =============================================================================
# MODEL FIXTURES - Tenant (Multi-tenant)
# =============================================================================

@pytest.fixture
def tenant(db_session: Session, country: Country) -> Tenant:
    """Crée un tenant de test (GCSMS)."""
    tenant = Tenant(
        code="TEST-GCSMS-001",
        name="GCSMS Test Île-de-France",
        legal_name="Groupement de Coopération Test",
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
        encryption_key_id="test-key-001",
        timezone="Europe/Paris",
        locale="fr_FR",
        max_patients=500,
        max_users=50,
        max_storage_gb=100,
        settings={"theme": "default", "notifications": True},
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def tenant_ssiad(db_session: Session, country: Country) -> Tenant:
    """Crée un second tenant de test (SSIAD indépendant)."""
    tenant = Tenant(
        code="TEST-SSIAD-LYON",
        name="SSIAD Lyon Indépendant",
        tenant_type=TenantType.SSIAD,
        status=TenantStatus.ACTIVE,
        contact_email="contact@ssiad-lyon.fr",
        country_id=country.id,
        encryption_key_id="test-key-lyon",
        max_patients=200,
        max_users=20,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


@pytest.fixture
def tenant_suspended(db_session: Session, country: Country) -> Tenant:
    """Crée un tenant suspendu pour les tests."""
    tenant = Tenant(
        code="TEST-SUSPENDED",
        name="Tenant Suspendu Test",
        tenant_type=TenantType.SAAD,
        status=TenantStatus.SUSPENDED,
        contact_email="contact@suspended.fr",
        country_id=country.id,
        encryption_key_id="test-key-suspended",
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


# =============================================================================
# MODEL FIXTURES - Organisation (Entity) - AVEC tenant_id
# =============================================================================

@pytest.fixture
def entity(db_session: Session, country: Country, tenant: Tenant) -> Entity:
    """Crée une entité de test (SSIAD)."""
    entity = Entity(
        tenant_id=tenant.id,  # MULTI-TENANT
        name="SSIAD Test Paris",
        entity_type=EntityType.SSIAD,
        country_id=country.id,
        siren="123456789",
        siret="12345678900001",
        finess_et="750000001",
        address="1 rue de Test, 75001 Paris",
        phone="0100000001",
        email="test@ssiad-paris.fr",
        latitude=Decimal("48.8566"),
        longitude=Decimal("2.3522"),
        default_intervention_radius_km=25,
        status="active"
    )
    db_session.add(entity)
    db_session.flush()
    return entity


@pytest.fixture
def entity_saad(db_session: Session, country: Country, tenant: Tenant) -> Entity:
    """Crée une deuxième entité de test (SAAD)."""
    entity = Entity(
        tenant_id=tenant.id,  # MULTI-TENANT
        name="SAAD Test Paris",
        entity_type=EntityType.SAAD,
        country_id=country.id,
        siren="987654321",
        siret="98765432100001",
        address="2 rue du Service, 75002 Paris",
        phone="0100000002",
        email="test@saad-paris.fr",
        status="active"
    )
    db_session.add(entity)
    db_session.flush()
    return entity


# =============================================================================
# MODEL FIXTURES - Professions (PAS de tenant_id - données partagées)
# =============================================================================

@pytest.fixture
def profession_medecin(db_session: Session) -> Profession:
    """Crée la profession Médecin."""
    profession = Profession(
        name="Médecin",
        code="10",
        category="MEDICAL",
        requires_rpps=True
    )
    db_session.add(profession)
    db_session.flush()
    return profession


@pytest.fixture
def profession_infirmier(db_session: Session) -> Profession:
    """Crée la profession Infirmier."""
    profession = Profession(
        name="Infirmier",
        code="60",
        category="PARAMEDICAL",
        requires_rpps=True
    )
    db_session.add(profession)
    db_session.flush()
    return profession


@pytest.fixture
def profession_aide_soignant(db_session: Session) -> Profession:
    """Crée la profession Aide-soignant."""
    profession = Profession(
        name="Aide-soignant",
        code="93",
        category="PARAMEDICAL",
        requires_rpps=False
    )
    db_session.add(profession)
    db_session.flush()
    return profession


@pytest.fixture
def profession_admin(db_session: Session) -> Profession:
    """Crée la profession Administratif."""
    profession = Profession(
        name="Administratif",
        code=None,
        category="ADMINISTRATIVE",
        requires_rpps=False
    )
    db_session.add(profession)
    db_session.flush()
    return profession


# =============================================================================
# MODEL FIXTURES - Rôles (Architecture v4.3 - Permission + RolePermission)
# =============================================================================

@pytest.fixture
def role_admin(db_session: Session) -> Role:
    """Crée le rôle ADMIN avec ses permissions (v4.3)."""
    return create_role_with_permissions(
        db_session=db_session,
        role_name=RoleName.ADMIN.value,
        description="Administrateur système",
        permission_codes=["ADMIN_FULL"],
        is_system_role=True
    )


@pytest.fixture
def role_medecin(db_session: Session) -> Role:
    """Crée le rôle MEDECIN_TRAITANT avec ses permissions (v4.3)."""
    return create_role_with_permissions(
        db_session=db_session,
        role_name=RoleName.MEDECIN_TRAITANT.value,
        description="Médecin traitant référent",
        permission_codes=[
            "PATIENT_VIEW", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE", "EVALUATION_VALIDATE",
            "VITALS_VIEW", "VITALS_CREATE"
        ],
        is_system_role=True
    )


@pytest.fixture
def role_infirmier(db_session: Session) -> Role:
    """Crée le rôle INFIRMIERE avec ses permissions (v4.3)."""
    return create_role_with_permissions(
        db_session=db_session,
        role_name=RoleName.INFIRMIERE.value,
        description="Infirmier(ère)",
        permission_codes=[
            "PATIENT_VIEW", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE",
            "VITALS_VIEW", "VITALS_CREATE"
        ],
        is_system_role=True
    )


@pytest.fixture
def role_coordinateur(db_session: Session) -> Role:
    """Crée le rôle COORDINATEUR avec ses permissions (v4.3)."""
    return create_role_with_permissions(
        db_session=db_session,
        role_name=RoleName.COORDINATEUR.value,
        description="Coordinateur de parcours de soins",
        permission_codes=[
            "PATIENT_VIEW", "PATIENT_CREATE", "PATIENT_EDIT",
            "EVALUATION_VIEW", "EVALUATION_CREATE",
            "CARE_PLAN_VIEW", "CARE_PLAN_CREATE", "CARE_PLAN_VALIDATE",
            "SCHEDULE_VIEW", "SCHEDULE_MANAGE",
            "USER_VIEW",
            "ACCESS_GRANT", "ACCESS_REVOKE",
        ],
        is_system_role=True
    )


# =============================================================================
# MODEL FIXTURES - Utilisateurs (AVEC tenant_id)
# =============================================================================

@pytest.fixture
def user_admin(db_session: Session, tenant: Tenant, entity: Entity, role_admin: Role, profession_admin: Profession) -> User:
    """Crée un utilisateur admin de test."""
    user = User(
        tenant_id=tenant.id,  # MULTI-TENANT
        email="admin@test.fr",
        first_name="Admin",
        last_name="Test",
        rpps="00000000001",
        profession_id=profession_admin.id,
        is_admin=True,
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Associer le rôle
    user_role = UserRole(
        user_id=user.id,
        role_id=role_admin.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        assigned_by=user.id
    )
    db_session.add(user_role)

    # Associer l'entité
    user_entity = UserEntity(
        user_id=user.id,
        entity_id=entity.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        is_primary=True,
        contract_type=ContractType.SALARIE.value,
        start_date=date.today()
    )
    db_session.add(user_entity)
    db_session.flush()

    return user


@pytest.fixture
def user_medecin(db_session: Session, tenant: Tenant, entity: Entity, role_medecin: Role, profession_medecin: Profession) -> User:
    """Crée un utilisateur médecin de test."""
    user = User(
        tenant_id=tenant.id,  # MULTI-TENANT
        email="medecin@test.fr",
        first_name="Jean",
        last_name="Dupont",
        rpps="12345678901",
        profession_id=profession_medecin.id,
        is_admin=False,
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Associer le rôle
    user_role = UserRole(
        user_id=user.id,
        role_id=role_medecin.id,
        tenant_id=tenant.id  # MULTI-TENANT v4.3
    )
    db_session.add(user_role)

    # Associer l'entité
    user_entity = UserEntity(
        user_id=user.id,
        entity_id=entity.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        is_primary=True,
        contract_type=ContractType.LIBERAL.value,
        start_date=date.today()
    )
    db_session.add(user_entity)
    db_session.flush()

    return user


@pytest.fixture
def user_infirmier(db_session: Session, tenant: Tenant, entity: Entity, role_infirmier: Role, profession_infirmier: Profession) -> User:
    """Crée un utilisateur infirmier de test."""
    user = User(
        tenant_id=tenant.id,  # MULTI-TENANT
        email="infirmier@test.fr",
        first_name="Marie",
        last_name="Martin",
        rpps="98765432101",
        profession_id=profession_infirmier.id,
        is_admin=False,
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Associer le rôle
    user_role = UserRole(
        user_id=user.id,
        role_id=role_infirmier.id,
        tenant_id=tenant.id  # MULTI-TENANT v4.3
    )
    db_session.add(user_role)

    # Associer l'entité
    user_entity = UserEntity(
        user_id=user.id,
        entity_id=entity.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        is_primary=True,
        contract_type=ContractType.SALARIE.value,
        start_date=date.today()
    )
    db_session.add(user_entity)
    db_session.flush()

    return user


@pytest.fixture
def user_coordinateur(db_session: Session, tenant: Tenant, entity: Entity, role_coordinateur: Role, profession_admin: Profession) -> User:
    """Crée un utilisateur coordinateur de test."""
    user = User(
        tenant_id=tenant.id,  # MULTI-TENANT
        email="coordinateur@test.fr",
        first_name="Sophie",
        last_name="Durand",
        rpps="11111111111",
        profession_id=profession_admin.id,
        is_admin=False,
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Associer le rôle
    user_role = UserRole(
        user_id=user.id,
        role_id=role_coordinateur.id,
        tenant_id=tenant.id  # MULTI-TENANT v4.3
    )
    db_session.add(user_role)

    # Associer l'entité
    user_entity = UserEntity(
        user_id=user.id,
        entity_id=entity.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        is_primary=True,
        contract_type=ContractType.SALARIE.value,
        start_date=date.today()
    )
    db_session.add(user_entity)
    db_session.flush()

    return user


# =============================================================================
# MODEL FIXTURES - Patients (AVEC tenant_id)
# =============================================================================

@pytest.fixture
def patient(db_session: Session, tenant: Tenant, entity: Entity, user_medecin: User, user_admin: User) -> Patient:
    """Crée un patient de test."""
    patient = Patient(
        tenant_id=tenant.id,  # MULTI-TENANT
        nir_encrypted="encrypted_nir_123",
        ins_encrypted="encrypted_ins_456",
        first_name_encrypted="encrypted_Jean",
        last_name_encrypted="encrypted_Durand",
        birth_date_encrypted="encrypted_1945-03-15",
        address_encrypted="encrypted_10 rue du Test",
        phone_encrypted="encrypted_0600000001",
        email_encrypted="encrypted_patient@test.fr",
        latitude=Decimal("48.8600"),
        longitude=Decimal("2.3500"),
        medecin_traitant_id=user_medecin.id,
        entity_id=entity.id,
        status="ACTIVE",
        created_by=user_admin.id
    )
    db_session.add(patient)
    db_session.flush()
    return patient


# =============================================================================
# PATIENT ACCESS
# =============================================================================

@pytest.fixture
def patient_access(db_session: Session, tenant: Tenant, patient: Patient, user_infirmier: User, user_admin: User) -> PatientAccess:
    """Crée un accès patient de test."""
    access = PatientAccess(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        user_id=user_infirmier.id,
        access_type=AccessType.WRITE.value,
        reason="Prise en charge infirmière - soins quotidiens",
        granted_by=user_admin.id,
        granted_at=datetime.now(timezone.utc)
    )
    db_session.add(access)
    db_session.flush()
    return access


# =============================================================================
# PATIENT DEVICE FIXTURE
# =============================================================================

@pytest.fixture
def patient_device(db_session: Session, tenant: Tenant, patient: Patient) -> PatientDevice:
    """Crée un device patient de test."""
    device = PatientDevice(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        device_type="WITHINGS_SCALE",
        device_identifier="WS-123456",
        device_name="Balance Withings Body+",  # Nom personnalisé inclut marque/modèle
        is_active=True
        # Note: manufacturer et model n'existent pas dans le modèle
    )
    db_session.add(device)
    db_session.flush()
    return device


# =============================================================================
# PATIENT EVALUATION FIXTURE
# =============================================================================

@pytest.fixture
def patient_evaluation(db_session: Session, tenant: Tenant, patient: Patient, user_infirmier: User) -> PatientEvaluation:
    """Crée une évaluation patient de test."""
    evaluation = PatientEvaluation(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        evaluator_id=user_infirmier.id,
        schema_type=EvaluationSchemaType.EVALUATION_COMPLETE.value,
        schema_version="v1",  # Obligatoire
        evaluation_date=date.today(),
        evaluation_data={  # Correct: evaluation_data, pas data
            "aggir": {
                "coherence": "C",
                "orientation": "C",
                "toilette": "B",
                "habillage": "B",
                "alimentation": "A",
                "elimination": "A",
                "transferts": "B",
                "deplacement_interieur": "B",
                "deplacement_exterieur": "C",
                "communication": "A",
                "GIR": 4
            },
            "usager": {
                "nom": "Durand",
                "prenom": "Jean"
            }
        },
        gir_score=4  # Score GIR extrait pour requêtes rapides
        # Note: is_validated est une @property, pas une colonne
        # Note: notes n'existe pas dans le modèle
    )
    db_session.add(evaluation)
    db_session.flush()
    return evaluation


# =============================================================================
# PATIENT THRESHOLD FIXTURE
# =============================================================================

@pytest.fixture
def patient_threshold(db_session: Session, tenant: Tenant, patient: Patient) -> PatientThreshold:
    """Crée un seuil patient de test."""
    threshold = PatientThreshold(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        vital_type=VitalType.TA_SYS.value,
        min_value=Decimal("100"),  # Seuil bas
        max_value=Decimal("140"),  # Seuil haut
        unit="mmHg",
        surveillance_frequency="1x/jour"  # Correct: pas notes
        # Note: critical_min, critical_max, set_by, is_active n'existent pas
    )
    db_session.add(threshold)
    db_session.flush()
    return threshold


# =============================================================================
# PATIENT VITALS FIXTURE
# =============================================================================

@pytest.fixture
def patient_vitals(db_session: Session, tenant: Tenant, patient: Patient, user_infirmier: User) -> PatientVitals:
    """Crée des constantes vitales de test."""
    vitals = PatientVitals(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        vital_type=VitalType.TA_SYS.value,
        value=Decimal("125"),
        unit="mmHg",
        status="NORMAL",
        source=VitalSource.MANUAL.value,
        measured_at=datetime.now(timezone.utc),
        recorded_by=user_infirmier.id
    )
    db_session.add(vitals)
    db_session.flush()
    return vitals


# =============================================================================
# MODEL FIXTURES - Catalogue de services (PAS de tenant_id sur templates)
# =============================================================================

@pytest.fixture
def service_template_toilette(db_session: Session, profession_aide_soignant: Profession) -> ServiceTemplate:
    """Crée un template de service Toilette."""
    template = ServiceTemplate(
        code="TOILETTE_COMPLETE",
        name="Aide à la toilette complète",
        category=ServiceCategory.HYGIENE,
        description="Aide complète à la toilette au lit ou au lavabo",
        required_profession_id=profession_aide_soignant.id,
        default_duration_minutes=45,
        requires_prescription=False,
        is_medical_act=False,
        apa_eligible=True,
        display_order=10,
        status="active"
    )
    db_session.add(template)
    db_session.flush()
    return template


@pytest.fixture
def service_template_injection(db_session: Session, profession_infirmier: Profession) -> ServiceTemplate:
    """Crée un template de service Injection."""
    template = ServiceTemplate(
        code="INJECTION_SC",
        name="Injection sous-cutanée",
        category=ServiceCategory.SOINS,
        description="Injection sous-cutanée (insuline, anticoagulants...)",
        required_profession_id=profession_infirmier.id,
        default_duration_minutes=15,
        requires_prescription=True,
        is_medical_act=True,
        apa_eligible=False,
        display_order=20,
        status="active"
    )
    db_session.add(template)
    db_session.flush()
    return template


@pytest.fixture
def service_template_courses(db_session: Session) -> ServiceTemplate:
    """Crée un template de service Courses (polyvalent)."""
    template = ServiceTemplate(
        code="COURSES_ALIMENTATION",
        name="Courses alimentaires",
        category=ServiceCategory.COURSES,
        description="Aide aux courses alimentaires",
        required_profession_id=None,  # Polyvalent
        default_duration_minutes=60,
        requires_prescription=False,
        is_medical_act=False,
        apa_eligible=True,
        display_order=50,
        status="active"
    )
    db_session.add(template)
    db_session.flush()
    return template


@pytest.fixture
def entity_service_toilette(db_session: Session, tenant: Tenant, entity: Entity, service_template_toilette: ServiceTemplate) -> EntityService:
    """Crée un service d'entité pour la toilette."""
    entity_service = EntityService(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        entity_id=entity.id,
        service_template_id=service_template_toilette.id,
        is_active=True,
        price_euros=Decimal("28.50"),
        max_capacity_week=100,
        custom_duration_minutes=50,  # Durée personnalisée
        notes="Service principal du SSIAD"
    )
    db_session.add(entity_service)
    db_session.flush()
    return entity_service


# =============================================================================
# MODEL FIXTURES - Plans d'aide (PAS de tenant_id - hérite via patient/entity)
# =============================================================================

@pytest.fixture
def care_plan(db_session: Session, tenant: Tenant, patient: Patient, entity: Entity, patient_evaluation: PatientEvaluation, user_coordinateur: User) -> CarePlan:
    """Crée un plan d'aide de test."""
    care_plan = CarePlan(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        entity_id=entity.id,
        source_evaluation_id=patient_evaluation.id,
        title="Plan d'aide 2024 - Maintien à domicile",
        reference_number="PA-2024-00001",
        status=CarePlanStatus.DRAFT,
        start_date=date.today(),
        end_date=None,
        total_hours_week=Decimal("12.50"),
        gir_at_creation=4,
        notes="Plan initial suite à évaluation GIR 4",
        created_by=user_coordinateur.id
    )
    db_session.add(care_plan)
    db_session.flush()
    return care_plan


@pytest.fixture
def care_plan_service(db_session: Session, tenant: Tenant, care_plan: CarePlan, service_template_toilette: ServiceTemplate) -> CarePlanService:
    """Crée un service de plan d'aide de test."""
    service = CarePlanService(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        care_plan_id=care_plan.id,
        service_template_id=service_template_toilette.id,
        quantity_per_week=5,
        frequency_type=FrequencyType.SPECIFIC_DAYS,
        frequency_days=[1, 2, 3, 4, 5],  # Lun-Ven
        preferred_time_start=time(7, 0),
        preferred_time_end=time(9, 0),
        duration_minutes=45,
        priority=ServicePriority.HIGH,
        assignment_status=AssignmentStatus.UNASSIGNED,
        special_instructions="Patient préfère toilette au lavabo",
        status="active"
    )
    db_session.add(service)
    db_session.flush()
    return service


# =============================================================================
# MODEL FIXTURES - Disponibilités
# =============================================================================

@pytest.fixture
def user_availability(db_session: Session, tenant: Tenant, user_infirmier: User, entity: Entity) -> UserAvailability:
    """Crée une disponibilité de test."""
    availability = UserAvailability(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        user_id=user_infirmier.id,
        entity_id=entity.id,
        day_of_week=1,  # Lundi
        start_time=time(7, 0),
        end_time=time(12, 0),
        is_recurring=True,
        valid_from=date.today(),
        valid_until=None,
        max_patients=8,
        notes="Disponible le matin",
        is_active=True
    )
    db_session.add(availability)
    db_session.flush()
    return availability


# =============================================================================
# MODEL FIXTURES - Interventions planifiées
# =============================================================================

@pytest.fixture
def scheduled_intervention(
    db_session: Session,
    tenant: Tenant,
    care_plan_service: CarePlanService,
    patient: Patient,
    user_infirmier: User
) -> ScheduledIntervention:
    """Crée une intervention planifiée de test."""
    intervention = ScheduledIntervention(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        care_plan_service_id=care_plan_service.id,
        patient_id=patient.id,
        user_id=user_infirmier.id,
        scheduled_date=date.today(),
        scheduled_start_time=time(8, 0),
        scheduled_end_time=time(8, 45),
        status=InterventionStatus.SCHEDULED
    )
    db_session.add(intervention)
    db_session.flush()
    return intervention


# =============================================================================
# MODEL FIXTURES - Coordination
# =============================================================================

@pytest.fixture
def coordination_entry(db_session: Session, tenant: Tenant, patient: Patient, user_infirmier: User) -> CoordinationEntry:
    """Crée une entrée de coordination de test."""
    entry = CoordinationEntry(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        user_id=user_infirmier.id,
        category=CoordinationCategory.SOINS,
        intervention_type="Toilette",
        description="Aide à la toilette complète réalisée",
        observations="RAS, patient en forme",
        next_actions="Continuer le protocole habituel",
        performed_at=datetime.now(timezone.utc),
        duration_minutes=45
    )
    db_session.add(entry)
    db_session.flush()
    return entry


# =============================================================================
# SUBSCRIPTION FIXTURES
# =============================================================================

@pytest.fixture
def subscription(db_session: Session, tenant: Tenant) -> Subscription:
    """Crée un abonnement actif pour le tenant principal."""
    subscription = Subscription(
        tenant_id=tenant.id,
        plan_code=SubscriptionPlan.L,
        plan_name="Plan Large - 500 patients",
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
def subscription_usage(db_session: Session, subscription: Subscription) -> SubscriptionUsage:
    """Crée un usage d'abonnement pour le mois en cours."""
    today = date.today()
    period_start = today.replace(day=1)
    # Calculer le dernier jour du mois
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    period_end = next_month - timedelta(days=1)

    usage = SubscriptionUsage(
        subscription_id=subscription.id,
        period_start=period_start,
        period_end=period_end,
        active_patients_count=245,
        active_users_count=28,
        storage_used_mb=15360,
        api_calls_count=125000,
        base_amount_cents=50000,
        overage_amount_cents=0,
        total_amount_cents=50000,
    )
    db_session.add(usage)
    db_session.flush()
    return usage


@pytest.fixture
def subscription_usage_with_overage(db_session: Session, subscription: Subscription) -> SubscriptionUsage:
    """Crée un usage avec dépassement."""
    today = date.today()
    # Mois précédent
    if today.month == 1:
        period_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        period_start = today.replace(month=today.month - 1, day=1)
    period_end = today.replace(day=1) - timedelta(days=1)

    usage = SubscriptionUsage(
        subscription_id=subscription.id,
        period_start=period_start,
        period_end=period_end,
        active_patients_count=650,  # Dépassement de 150
        active_users_count=45,
        storage_used_mb=85000,
        api_calls_count=350000,
        base_amount_cents=50000,
        overage_amount_cents=75000,  # 150 * 500 cents
        total_amount_cents=125000,
        invoiced=True,
        invoice_id="INV-2024-001",
    )
    db_session.add(usage)
    db_session.flush()
    return usage


# =============================================================================
# API TEST FIXTURES
# =============================================================================

@pytest.fixture
def client(db_session: Session, user_admin: User, tenant: Tenant) -> Generator[TestClient, None, None]:
    """
    Client de test FastAPI avec authentification mockée.

    Cette fixture :
    1. Override get_db et get_db_no_rls pour utiliser SQLite de test
    2. Override get_current_user pour bypasser l'authentification JWT
    3. Override get_current_tenant_id pour fournir le tenant de test
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.core.auth.user_auth import get_current_user
    from app.api.v1.user.tenant_users_security import get_current_tenant_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override authentification - retourne directement l'utilisateur admin
    def override_get_current_user():
        return user_admin

    # Override tenant_id - retourne le tenant de test
    def override_get_current_tenant_id():
        return tenant.id

    # Appliquer tous les overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_as_user(db_session: Session, user_infirmier: User, tenant: Tenant) -> Generator[TestClient, None, None]:
    """
    Client de test authentifié en tant qu'utilisateur standard (infirmier).

    Utile pour tester les permissions et restrictions d'accès.
    """
    from app.database.session_rls import get_db, get_db_no_rls
    from app.core.auth.user_auth import get_current_user
    from app.api.v1.user.tenant_users_security import get_current_tenant_id

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return user_infirmier

    def override_get_current_tenant_id():
        return tenant.id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_rls] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Les fixtures de token ne sont plus nécessaires pour les tests API
# mais on les garde pour la rétrocompatibilité avec d'autres tests

@pytest.fixture
def admin_token(user_admin: User) -> str:
    """Token JWT pour l'admin (pour tests spécifiques JWT)."""
    return create_access_token(data={
        "sub": str(user_admin.id),
        "email": user_admin.email,
        "is_admin": user_admin.is_admin,
        "tenant_id": user_admin.tenant_id,
    })


@pytest.fixture
def admin_token_headers(admin_token: str) -> dict:
    """Headers avec token admin (pour rétrocompatibilité)."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_token(user_infirmier: User) -> str:
    """Token JWT pour utilisateur standard."""
    return create_access_token(data={
        "sub": str(user_infirmier.id),
        "email": user_infirmier.email,
        "is_admin": user_infirmier.is_admin,
        "tenant_id": user_infirmier.tenant_id,
    })


@pytest.fixture
def user_token_headers(user_token: str) -> dict:
    """Headers avec token utilisateur."""
    return {"Authorization": f"Bearer {user_token}"}

# --- Instructions de lancement des tests --- #
"""
Pour lancer les tests :
   pytest tests/test_models/ -v --tb=short
   pytest tests/test_api/ -v --tb=short
   pytest tests/ -v
"""

@pytest.fixture
def patient_document(db_session: Session, tenant: Tenant, patient: Patient, user_admin: User) -> "PatientDocument":
    """Crée un document patient de test."""
    from datetime import datetime, timezone
    from app.models.patient.patient_document import PatientDocument
    from app.models.enums import DocumentType, DocumentFormat

    document = PatientDocument(
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        patient_id=patient.id,
        document_type=DocumentType.PPA.value,
        title="PPA - Test Patient",
        description="Plan personnalisé d'accompagnement de test",
        file_path="/documents/patients/1/ppa_test.pdf",
        file_format=DocumentFormat.PDF.value,
        file_size_bytes=125000,
        generated_by=user_admin.id,
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add(document)
    db_session.flush()
    return document


@pytest.fixture
def subscription_enterprise(db_session: Session, tenant: Tenant) -> "Subscription":
    """Crée un abonnement Enterprise avec date d'expiration."""
    from datetime import date, timedelta
    from app.models.tenants.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, BillingCycle

    subscription = Subscription(
        tenant_id=tenant.id,
        plan_code=SubscriptionPlan.ENTERPRISE,
        plan_name="Plan Enterprise - Illimité",
        status=SubscriptionStatus.ACTIVE,
        started_at=date.today() - timedelta(days=90),
        expires_at=date.today() + timedelta(days=275),
        base_price_cents=200000,
        currency="EUR",
        billing_cycle=BillingCycle.YEARLY,
        included_patients=10000,
        included_users=500,
        included_storage_gb=1000,
    )
    db_session.add(subscription)
    db_session.flush()
    return subscription