"""
Tests pour Row-Level Security (RLS).

Ces tests vérifient que l'isolation multi-tenant fonctionne correctement
au niveau PostgreSQL.

IMPORTANT: Ces tests nécessitent une base PostgreSQL (pas SQLite).

Architecture:
- Chaque test crée ses propres données avec get_db_for_super_admin()
- Le cleanup est fait dans un bloc finally pour garantir la suppression
- Les identifiants sont uniques (UUID) pour éviter les conflits
"""

import uuid
from contextlib import contextmanager

import pytest

# -----Note-----
# tests RLS nécessitent une vraie base PostgreSQL configurée (le RLS ne fonctionne pas avec SQLite).
# Solution possible: Marquer ces tests comme "integration": permet de skipper automatiquement si PostgreSQL n'est pas disponible
pytestmark = pytest.mark.integration

# Commande: pytest -v -m "not integration"
# -------------

from sqlalchemy import text

from app.database.session import SessionLocal
from app.database.session_rls import (
    configure_tenant_context,
    get_db_for_tenant,
    get_db_for_super_admin,
)
from app.models.enums import TenantStatus, TenantType
from app.models.organization.entity import Entity
from app.models.patient.patient import Patient
from app.models.tenants.tenant import Tenant


# =============================================================================
# HELPERS
# =============================================================================

def unique_id() -> str:
    """Génère un identifiant unique court."""
    return uuid.uuid4().hex[:8]


@contextmanager
def create_test_data():
    """
    Context manager qui crée les données de test et les nettoie à la fin.

    Utilise get_db_for_super_admin() pour bypasser RLS pendant le setup/cleanup.

    Yields:
        dict avec tenant1, tenant2, entity1, entity2, patient1, patient2, patient3
    """
    uid = unique_id()
    data = {}

    # Setup avec super-admin
    with get_db_for_super_admin() as db:
        # Créer les tenants
        tenant1 = Tenant(
            code=f"rls-t1-{uid}",
            name=f"Tenant RLS 1 - {uid}",
            tenant_type=TenantType.SSIAD,
            status=TenantStatus.ACTIVE,
            contact_email=f"t1-{uid}@test.fr",
            encryption_key_id=f"key-t1-{uid}",
            max_users=100,
            max_patients=1000,
        )
        tenant2 = Tenant(
            code=f"rls-t2-{uid}",
            name=f"Tenant RLS 2 - {uid}",
            tenant_type=TenantType.SSIAD,
            status=TenantStatus.ACTIVE,
            contact_email=f"t2-{uid}@test.fr",
            encryption_key_id=f"key-t2-{uid}",
            max_users=100,
            max_patients=1000,
        )
        db.add_all([tenant1, tenant2])
        db.commit()
        db.refresh(tenant1)
        db.refresh(tenant2)

        # Créer les entités
        entity1 = Entity(
            name=f"entity-rls-1-{uid}",
            entity_type="SSIAD",
            tenant_id=tenant1.id,
            country_id=1,
        )
        entity2 = Entity(
            name=f"entity-rls-2-{uid}",
            entity_type="SSIAD",
            tenant_id=tenant2.id,
            country_id=1,
        )
        db.add_all([entity1, entity2])
        db.commit()
        db.refresh(entity1)
        db.refresh(entity2)

        # Créer les patients
        patient1 = Patient(
            first_name_encrypted=f"p1-{uid}",
            last_name_encrypted="Tenant1",
            tenant_id=tenant1.id,
            entity_id=entity1.id,
        )
        patient2 = Patient(
            first_name_encrypted=f"p2-{uid}",
            last_name_encrypted="Tenant2",
            tenant_id=tenant2.id,
            entity_id=entity2.id,
        )
        patient3 = Patient(
            first_name_encrypted=f"p3-{uid}",
            last_name_encrypted="Tenant1",
            tenant_id=tenant1.id,
            entity_id=entity1.id,
        )
        db.add_all([patient1, patient2, patient3])
        db.commit()
        db.refresh(patient1)
        db.refresh(patient2)
        db.refresh(patient3)

        data = {
            'tenant1': tenant1,
            'tenant2': tenant2,
            'entity1': entity1,
            'entity2': entity2,
            'patient1': patient1,
            'patient2': patient2,
            'patient3': patient3,
            # Stocker les IDs pour le cleanup
            'tenant1_id': tenant1.id,
            'tenant2_id': tenant2.id,
            'entity1_id': entity1.id,
            'entity2_id': entity2.id,
            'patient1_id': patient1.id,
            'patient2_id': patient2.id,
            'patient3_id': patient3.id,
        }

    try:
        yield data
    finally:
        # Cleanup avec super-admin
        with get_db_for_super_admin() as db:
            try:
                # Supprimer dans l'ordre inverse des dépendances
                db.execute(text(f"DELETE FROM patients WHERE id IN ({data['patient1_id']}, {data['patient2_id']}, {data['patient3_id']})"))
                db.execute(text(f"DELETE FROM entities WHERE id IN ({data['entity1_id']}, {data['entity2_id']})"))
                db.execute(text(f"DELETE FROM tenants WHERE id IN ({data['tenant1_id']}, {data['tenant2_id']})"))
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Cleanup error (ignoré): {e}")


# =============================================================================
# TESTS - ISOLATION BASIQUE
# =============================================================================

class TestRLSBasicIsolation:
    """Tests de l'isolation basique par tenant."""

    def test_tenant1_sees_only_own_patients(self):
        """Tenant 1 ne voit que ses propres patients."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                patients = db.query(Patient).all()
                patient_ids = [p.id for p in patients]

                # Doit voir patient1 et patient3 (tenant1)
                assert data['patient1_id'] in patient_ids
                assert data['patient3_id'] in patient_ids

                # Ne doit PAS voir patient2 (tenant2)
                assert data['patient2_id'] not in patient_ids

    def test_tenant2_sees_only_own_patients(self):
        """Tenant 2 ne voit que ses propres patients."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant2_id']) as db:
                patients = db.query(Patient).all()
                patient_ids = [p.id for p in patients]

                # Doit voir uniquement patient2 (tenant2)
                assert data['patient2_id'] in patient_ids

                # Ne doit PAS voir patient1 et patient3 (tenant1)
                assert data['patient1_id'] not in patient_ids
                assert data['patient3_id'] not in patient_ids

    def test_super_admin_sees_all_patients(self):
        """Super-admin voit tous les patients."""
        with create_test_data() as data:
            with get_db_for_super_admin() as db:
                patients = db.query(Patient).all()
                patient_ids = [p.id for p in patients]

                # Doit voir TOUS les patients
                assert data['patient1_id'] in patient_ids
                assert data['patient2_id'] in patient_ids
                assert data['patient3_id'] in patient_ids


# =============================================================================
# TESTS - ISOLATION INSERT
# =============================================================================

class TestRLSInsertIsolation:
    """Tests de l'isolation lors des insertions."""

    def test_cannot_insert_patient_in_other_tenant(self):
        """Un utilisateur ne peut pas créer un patient dans un autre tenant."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                # Tenter de créer un patient dans le tenant2 (interdit)
                patient = Patient(
                    first_name_encrypted=f"hacker-{unique_id()}",
                    last_name_encrypted="Test",
                    tenant_id=data['tenant2_id'],  # Autre tenant!
                    entity_id=data['entity2_id'],
                )
                db.add(patient)

                # Le commit doit échouer (RLS policy violation)
                with pytest.raises(Exception):
                    db.commit()

                db.rollback()

    def test_can_insert_patient_in_own_tenant(self):
        """Un utilisateur peut créer un patient dans son propre tenant."""
        with create_test_data() as data:
            new_patient_id = None
            with get_db_for_tenant(data['tenant1_id']) as db:
                patient = Patient(
                    first_name_encrypted=f"valid-{unique_id()}",
                    last_name_encrypted="Patient",
                    tenant_id=data['tenant1_id'],  # Même tenant - OK
                    entity_id=data['entity1_id'],
                )
                db.add(patient)
                db.commit()  # Doit réussir

                assert patient.id is not None
                new_patient_id = patient.id

            # Cleanup du patient créé
            if new_patient_id:
                with get_db_for_super_admin() as db:
                    db.execute(text(f"DELETE FROM patients WHERE id = {new_patient_id}"))
                    db.commit()


# =============================================================================
# TESTS - ISOLATION UPDATE
# =============================================================================

class TestRLSUpdateIsolation:
    """Tests de l'isolation lors des modifications."""

    def test_cannot_update_patient_in_other_tenant(self):
        """Un utilisateur ne peut pas modifier un patient d'un autre tenant."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                # Tenter de modifier patient2 (tenant2)
                result = db.query(Patient).filter(Patient.id == data['patient2_id']).update(
                    {"first_name_encrypted": "Hacked"}
                )

                # Aucune ligne ne doit être modifiée (RLS l'empêche)
                assert result == 0

    def test_can_update_patient_in_own_tenant(self):
        """Un utilisateur peut modifier un patient de son tenant."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                result = db.query(Patient).filter(Patient.id == data['patient1_id']).update(
                    {"first_name_encrypted": "Updated"}
                )

                # Une ligne doit être modifiée
                assert result == 1
                db.commit()

    def test_cannot_change_tenant_id(self):
        """Un utilisateur ne peut pas changer le tenant_id d'un patient."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                # Tenter de changer le tenant_id doit échouer
                with pytest.raises(Exception):
                    db.query(Patient).filter(Patient.id == data['patient1_id']).update(
                        {"tenant_id": data['tenant2_id']}
                    )
                    db.commit()

                db.rollback()


# =============================================================================
# TESTS - ISOLATION DELETE
# =============================================================================

class TestRLSDeleteIsolation:
    """Tests de l'isolation lors des suppressions."""

    def test_cannot_delete_patient_in_other_tenant(self):
        """Un utilisateur ne peut pas supprimer un patient d'un autre tenant."""
        with create_test_data() as data:
            with get_db_for_tenant(data['tenant1_id']) as db:
                result = db.query(Patient).filter(Patient.id == data['patient2_id']).delete()

                # Aucune ligne ne doit être supprimée
                assert result == 0


# =============================================================================
# TESTS - CONTEXTE NON DÉFINI
# =============================================================================

class TestRLSNoContext:
    """Tests quand aucun contexte tenant n'est défini."""

    def test_no_context_returns_no_data(self):
        """Sans contexte tenant, aucune donnée n'est visible."""
        with create_test_data() as data:
            db = SessionLocal()
            try:
                # Configurer sans tenant_id (NULL) et sans super-admin
                configure_tenant_context(db, tenant_id=None, is_super_admin=False)

                # Chercher nos patients de test
                patients = db.query(Patient).filter(
                    Patient.id.in_([data['patient1_id'], data['patient2_id'], data['patient3_id']])
                ).all()

                # Aucun ne doit être visible
                assert len(patients) == 0
            finally:
                db.close()


# =============================================================================
# TESTS - FONCTIONS SQL
# =============================================================================

class TestRLSSQLFunctions:
    """Tests des fonctions SQL créées pour RLS."""

    def test_get_current_tenant_id_returns_correct_value(self):
        """get_current_tenant_id() retourne la bonne valeur."""
        with create_test_data() as data:
            db = SessionLocal()
            try:
                configure_tenant_context(db, tenant_id=data['tenant1_id'], is_super_admin=False)

                result = db.execute(text("SELECT get_current_tenant_id()")).scalar()
                assert result == data['tenant1_id']
            finally:
                db.close()

    def test_is_super_admin_returns_correct_value(self):
        """is_super_admin() retourne la bonne valeur."""
        db = SessionLocal()
        try:
            # Test avec super_admin=False
            configure_tenant_context(db, tenant_id=1, is_super_admin=False)
            result = db.execute(text("SELECT is_super_admin()")).scalar()
            assert result is False

            # Test avec super_admin=True
            configure_tenant_context(db, tenant_id=None, is_super_admin=True)
            result = db.execute(text("SELECT is_super_admin()")).scalar()
            assert result is True
        finally:
            db.close()

    def test_check_tenant_access(self):
        """check_tenant_access() retourne TRUE/FALSE correctement."""
        with create_test_data() as data:
            db = SessionLocal()
            try:
                configure_tenant_context(db, tenant_id=data['tenant1_id'], is_super_admin=False)

                # Accès à son propre tenant
                result = db.execute(
                    text(f"SELECT check_tenant_access({data['tenant1_id']})")
                ).scalar()
                assert result is True

                # Accès à un autre tenant
                result = db.execute(
                    text(f"SELECT check_tenant_access({data['tenant2_id']})")
                ).scalar()
                assert result is False
            finally:
                db.close()