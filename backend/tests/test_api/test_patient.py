"""
Tests API pour le module Patient - Architecture v4.3

Ce module teste les endpoints :
- /api/v1/patients : CRUD Patients
- /api/v1/patients/{id}/access : Gestion des accès RGPD
- /api/v1/patients/{id}/evaluations : Évaluations AGGIR
- /api/v1/patients/{id}/thresholds : Seuils d'alerte
- /api/v1/patients/{id}/vitals : Constantes vitales
- /api/v1/patients/{id}/devices : Devices connectés
- /api/v1/patients/{id}/documents : Documents

Architecture v4.3:
- Multi-tenant avec tenant_id obligatoire
- Authentification mockée pour les tests
"""

from datetime import date, datetime, timezone
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User
from app.models.enums import AccessType, VitalType, VitalSource
from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.patient_vitals import PatientThreshold, PatientVitals


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
# PATIENT TESTS
# =============================================================================

class TestPatientEndpoints:
    """Tests des endpoints /api/v1/patients."""

    def test_list_patients(self, authenticated_client, patient):
        """Liste des patients."""
        response = authenticated_client.get("/api/v1/patients")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert "items" in data

    def test_list_patients_filter_by_entity(self, authenticated_client, patient, entity):
        """Filtrage par entité."""
        response = authenticated_client.get(f"/api/v1/patients?entity_id={entity.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_list_patients_filter_by_status(self, authenticated_client, patient):
        """Filtrage par statut."""
        response = authenticated_client.get("/api/v1/patients?status=ACTIVE")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "ACTIVE"

    def test_get_patient(self, authenticated_client, patient):
        """Récupération d'un patient par ID."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == patient.id

    def test_get_patient_not_found(self, authenticated_client):
        """Erreur 404 si patient inexistant."""
        response = authenticated_client.get("/api/v1/patients/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_patient(self, authenticated_client, entity, user_medecin):
        """Création d'un patient."""
        response = authenticated_client.post(
            "/api/v1/patients",
            json={
                "entity_id": entity.id,
                "medecin_traitant_id": user_medecin.id,
                "first_name": "Jean",
                "last_name": "Nouveau",
                "birth_date": "1940-05-15",
                "address": "10 rue du Test, 75001 Paris",
                "phone": "0601020304",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["entity_id"] == entity.id
        assert data["status"] == "ACTIVE"

    def test_create_patient_entity_not_found(self, authenticated_client):
        """Erreur 404 si entité inexistante."""
        response = authenticated_client.post(
            "/api/v1/patients",
            json={
                "entity_id": 99999,
                "first_name": "Test",
                "last_name": "Test",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_patient(self, authenticated_client, patient):
        """Mise à jour d'un patient."""
        response = authenticated_client.patch(
            f"/api/v1/patients/{patient.id}",
            json={"phone": "0699887766"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_patient_archives(self, authenticated_client, db_session, entity, tenant):
        """La suppression archive le patient."""
        patient = Patient(
            tenant_id=tenant.id,
            entity_id=entity.id,
            first_name_encrypted="ToDelete",
            last_name_encrypted="Patient",
        )
        db_session.add(patient)
        db_session.flush()

        response = authenticated_client.delete(f"/api/v1/patients/{patient.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        db_session.refresh(patient)
        assert patient.status == "ARCHIVED"


# =============================================================================
# PATIENT ACCESS TESTS
# =============================================================================

class TestPatientAccessEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/access."""

    def test_list_patient_access(self, authenticated_client, patient, patient_access):
        """Liste des accès d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/access")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_grant_patient_access(self, authenticated_client, patient, user_infirmier):
        """Accorder un accès à un utilisateur."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/access",
            json={
                "user_id": user_infirmier.id,
                "access_type": "WRITE",  # CORRIGÉ: CARE_TEAM n'existe pas
                "reason": "Prise en charge du patient dans le cadre du plan de soins",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["access_type"] == "WRITE"
        assert data["is_active"] is True

    def test_grant_access_patient_not_found(self, authenticated_client, user_infirmier):
        """Erreur 404 si patient inexistant."""
        response = authenticated_client.post(
            "/api/v1/patients/99999/access",
            json={
                "user_id": user_infirmier.id,
                "access_type": "WRITE",  # CORRIGÉ
                "reason": "Test raison suffisamment longue",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_grant_access_reason_required(self, authenticated_client, patient, user_infirmier):
        """La raison d'accès est obligatoire."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/access",
            json={
                "user_id": user_infirmier.id,
                "access_type": "WRITE",  # CORRIGÉ
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_revoke_patient_access(self, authenticated_client, patient, db_session, user_infirmier, tenant, user_admin):
        """Révoquer un accès."""
        access = PatientAccess(
            patient_id=patient.id,
            user_id=user_infirmier.id,
            tenant_id=tenant.id,
            access_type=AccessType.WRITE.value,  # CORRIGÉ: CARE_TEAM n'existe pas
            reason="Test access to revoke",
            granted_by=user_admin.id,  # AJOUTÉ: champ obligatoire
            # is_active=True,  # SUPPRIMÉ: c'est une @property sans setter
        )
        db_session.add(access)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/access/{access.id}"
        )
        # L'API retourne 200 OK avec le contenu mis à jour (pas 204)
        assert response.status_code == status.HTTP_200_OK

        db_session.refresh(access)
        assert access.is_active is False


# =============================================================================
# PATIENT EVALUATION TESTS
# =============================================================================

class TestPatientEvaluationEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/evaluations."""

    def test_list_patient_evaluations(self, authenticated_client, patient, patient_evaluation):
        """Liste des évaluations d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/evaluations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_get_patient_evaluation(self, authenticated_client, patient, patient_evaluation):
        """Récupération d'une évaluation par ID."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/evaluations/{patient_evaluation.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == patient_evaluation.id

    def test_create_patient_evaluation(self, authenticated_client, patient):
        """Création d'une évaluation AGGIR."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/evaluations",
            json={
                "schema_type": "aggir_only",
                "schema_version": "v1",
                "evaluation_date": str(date.today()),
                # gir_score retiré - calculé automatiquement
                "evaluation_data": {
                    "coherence": "B",
                    "orientation": "B",
                    "toilette": "C",
                    "habillage": "C",
                    "alimentation": "B",
                    "elimination": "B",
                    "transferts": "B",
                    "deplacement_interieur": "B",
                    "deplacement_exterieur": "C",
                    "communication": "A",
                },
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_validated"] is False
        # Le gir_score sera None ou calculé automatiquement
        assert data["status"] == "DRAFT"

    def test_update_patient_evaluation(self, authenticated_client, patient, patient_evaluation):
        """Mise à jour d'une évaluation non validée."""
        response = authenticated_client.patch(
            f"/api/v1/patients/{patient.id}/evaluations/{patient_evaluation.id}",
            json={
                "evaluation_data": {
                    "coherence": "C",  # Modifier une variable AGGIR
                    "orientation": "B",
                    "toilette": "C",
                    "habillage": "C",
                    "alimentation": "B",
                    "elimination": "B",
                    "transferts": "B",
                    "deplacement_interieur": "B",
                    "deplacement_exterieur": "C",
                    "communication": "A",
                }
            },
        )
        assert response.status_code == status.HTTP_200_OK
        # Vérifier que l'évaluation a été mise à jour
        assert response.json()["version"] > 0

    def test_update_validated_evaluation_fails(
            self, authenticated_client, patient, db_session, user_admin, tenant
    ):
        """Impossible de modifier une évaluation validée."""
        evaluation = PatientEvaluation(
            patient_id=patient.id,
            evaluator_id=user_admin.id,
            tenant_id=tenant.id,
            schema_type="aggir_only",
            schema_version="v1",
            evaluation_date=date.today(),
            gir_score=4,
            evaluation_data={},
            status="VALIDATED",  # ← AJOUTER CETTE LIGNE
            validated_at=datetime.now(timezone.utc),
            validated_by=user_admin.id,
        )
        db_session.add(evaluation)
        db_session.flush()

        response = authenticated_client.patch(
            f"/api/v1/patients/{patient.id}/evaluations/{evaluation.id}",
            json={"evaluation_data": {"coherence": "A"}},  # Modifier le payload aussi
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_validate_patient_evaluation(self, authenticated_client, patient, patient_evaluation):
        """Validation d'une évaluation."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/evaluations/{patient_evaluation.id}/validate"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_validated"] is True
        assert data["validated_at"] is not None

    def test_delete_non_validated_evaluation(
        self, authenticated_client, patient, db_session, tenant, user_admin
    ):
        """Suppression d'une évaluation non validée."""
        # CORRIGÉ: is_validated est une @property, evaluator_id est obligatoire
        evaluation = PatientEvaluation(
            patient_id=patient.id,
            evaluator_id=user_admin.id,  # AJOUTÉ: champ obligatoire
            tenant_id=tenant.id,
            schema_type="aggir_only",
            schema_version="v1",
            evaluation_date=date.today(),
            gir_score=5,
            evaluation_data={},
            # validated_at=None → is_validated sera False
        )
        db_session.add(evaluation)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/evaluations/{evaluation.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_validated_evaluation_fails(
        self, authenticated_client, patient, db_session, user_admin, tenant
    ):
        """Impossible de supprimer une évaluation validée."""
        # CORRIGÉ: is_validated est une @property, evaluator_id est obligatoire
        evaluation = PatientEvaluation(
            patient_id=patient.id,
            evaluator_id=user_admin.id,  # AJOUTÉ: champ obligatoire
            tenant_id=tenant.id,
            schema_type="aggir_only",
            schema_version="v1",
            evaluation_date=date.today(),
            gir_score=4,
            evaluation_data={},
            validated_at=datetime.now(timezone.utc),  # is_validated sera True
            validated_by=user_admin.id,
        )
        db_session.add(evaluation)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/evaluations/{evaluation.id}"
        )
        # L'API retourne 409 Conflict pour une évaluation déjà validée
        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# PATIENT THRESHOLD TESTS
# =============================================================================

class TestPatientThresholdEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/thresholds."""

    def test_list_patient_thresholds(self, authenticated_client, patient, patient_threshold):
        """Liste des seuils d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/thresholds")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_create_patient_threshold(self, authenticated_client, patient):
        """Création d'un seuil d'alerte."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/thresholds",
            json={
                "vital_type": "TA_SYS",  # CORRIGÉ: TENSION_SYSTOLIQUE n'existe pas
                "unit": "mmHg",  # AJOUTÉ: champ obligatoire
                "min_value": 100,
                "max_value": 140,
                "critical_min": 90,
                "critical_max": 180,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["vital_type"] == "TA_SYS"
        # Note: is_active n'est pas retourné par l'API

    def test_create_threshold_duplicate_fails(
        self, authenticated_client, patient, patient_threshold
    ):
        """Erreur 409 si seuil déjà existant pour ce type."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/thresholds",
            json={
                "vital_type": patient_threshold.vital_type,
                "unit": patient_threshold.unit,  # AJOUTÉ: champ obligatoire
                "min_value": 50,
                "max_value": 100,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_patient_threshold(self, authenticated_client, patient, patient_threshold):
        """Mise à jour d'un seuil."""
        response = authenticated_client.patch(
            f"/api/v1/patients/{patient.id}/thresholds/{patient_threshold.id}",
            json={"max_value": 90},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["max_value"] == 90

    def test_delete_patient_threshold(self, authenticated_client, patient, db_session, tenant):
        """Suppression d'un seuil."""
        threshold = PatientThreshold(
            patient_id=patient.id,
            tenant_id=tenant.id,
            vital_type=VitalType.TEMPERATURE.value,
            unit="°C",  # AJOUTÉ: champ obligatoire
            min_value=36,
            max_value=38,
        )
        db_session.add(threshold)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/thresholds/{threshold.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# PATIENT VITALS TESTS
# =============================================================================

class TestPatientVitalsEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/vitals."""

    def test_list_patient_vitals(self, authenticated_client, patient, patient_vitals):
        """Liste des mesures d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/vitals")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_vitals_filter_by_type(self, authenticated_client, patient, patient_vitals):
        """Filtrage par type de constante."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/vitals?vital_type={patient_vitals.vital_type}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_latest_vital_by_type(self, authenticated_client, patient, patient_vitals):
        """Récupération de la dernière mesure par type."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/vitals/latest/{patient_vitals.vital_type}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["vital_type"] == patient_vitals.vital_type

    def test_get_latest_vital_not_found(self, authenticated_client, patient):
        """404 si pas de mesure pour ce type."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/vitals/latest/GLYCEMIE"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_patient_vital(self, authenticated_client, patient):
        """Création d'une mesure."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/vitals",
            json={
                "vital_type": "POIDS",
                "value": 72.5,
                "unit": "kg",
                "source": "MANUAL",
                "measured_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["vital_type"] == "POIDS"
        assert data["value"] == 72.5

    def test_create_vital_with_threshold_check(
        self, authenticated_client, patient, patient_threshold
    ):
        """La mesure est comparée aux seuils."""
        # CORRIGÉ: Convertir Decimal en float pour éviter erreur JSON
        max_val = float(patient_threshold.max_value) if patient_threshold.max_value else 100
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/vitals",
            json={
                "vital_type": patient_threshold.vital_type,
                "value": max_val + 10,  # CORRIGÉ: float au lieu de Decimal
                "unit": patient_threshold.unit,
                "source": "MANUAL",
                "measured_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] in ["HIGH", "CRITICAL"]

    def test_delete_patient_vital(self, authenticated_client, patient, db_session, tenant):
        """Suppression d'une mesure."""
        vital = PatientVitals(
            patient_id=patient.id,
            tenant_id=tenant.id,
            vital_type=VitalType.POIDS.value,
            value=75.5,
            unit="kg",
            source=VitalSource.MANUAL.value,
            measured_at=datetime.now(timezone.utc),
        )
        db_session.add(vital)
        db_session.flush()

        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/vitals/{vital.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# PATIENT DEVICE TESTS
# =============================================================================

class TestPatientDeviceEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/devices."""

    def test_list_patient_devices(self, authenticated_client, patient, patient_device):
        """Liste des devices d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/devices")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_create_patient_device(self, authenticated_client, patient):
        """Enregistrement d'un device."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/devices",
            json={
                "device_type": "WITHINGS_SCALE",
                "device_identifier": "WBS01-NEW12345",
                "device_name": "Balance Withings",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["device_type"] == "WITHINGS_SCALE"
        assert data["is_active"] is True

    def test_create_device_duplicate_fails(self, authenticated_client, patient, patient_device):
        """Erreur 409 si device déjà enregistré."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/devices",
            json={
                "device_type": patient_device.device_type,
                "device_identifier": patient_device.device_identifier,
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_update_patient_device(self, authenticated_client, patient, patient_device):
        """Mise à jour d'un device."""
        response = authenticated_client.patch(
            f"/api/v1/patients/{patient.id}/devices/{patient_device.id}",
            json={"device_name": "Ma balance connectée"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["device_name"] == "Ma balance connectée"

    def test_delete_patient_device_deactivates(self, authenticated_client, patient, patient_device, db_session):
        """La suppression désactive le device."""
        response = authenticated_client.delete(
            f"/api/v1/patients/{patient.id}/devices/{patient_device.id}"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        db_session.refresh(patient_device)
        assert patient_device.is_active is False


# =============================================================================
# PATIENT DOCUMENT TESTS
# =============================================================================

class TestPatientDocumentEndpoints:
    """Tests des endpoints /api/v1/patients/{id}/documents."""

    def test_list_patient_documents(self, authenticated_client, patient, patient_document):
        """Liste des documents d'un patient."""
        response = authenticated_client.get(f"/api/v1/patients/{patient.id}/documents")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_documents_filter_by_type(self, authenticated_client, patient, patient_document):
        """Filtrage par type de document."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/documents?document_type={patient_document.document_type}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_patient_document(self, authenticated_client, patient, patient_document):
        """Récupération d'un document par ID."""
        response = authenticated_client.get(
            f"/api/v1/patients/{patient.id}/documents/{patient_document.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == patient_document.id

    def test_delete_patient_document_admin_only(self, authenticated_client_user, patient, patient_document):
        """Seul un admin peut supprimer un document."""
        response = authenticated_client_user.delete(
            f"/api/v1/patients/{patient.id}/documents/{patient_document.id}"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests de validation des données."""

    def test_invalid_access_type(self, authenticated_client, patient, user_infirmier):
        """Type d'accès invalide."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/access",
            json={
                "user_id": user_infirmier.id,
                "access_type": "INVALID",
                "reason": "Test raison suffisamment longue",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_vital_type(self, authenticated_client, patient):
        """Type de constante invalide."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/vitals",
            json={
                "vital_type": "INVALID",
                "value": 100,
                "unit": "test",
                "source": "MANUAL",
                "measured_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_device_type(self, authenticated_client, patient):
        """Type de device invalide."""
        response = authenticated_client.post(
            f"/api/v1/patients/{patient.id}/devices",
            json={
                "device_type": "INVALID_DEVICE",
                "device_identifier": "TEST123",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestAuthentication:
    """Tests d'authentification."""

    def test_list_patients_requires_auth(self, unauthenticated_client):
        """Liste des patients requiert authentification."""
        response = unauthenticated_client.get("/api/v1/patients")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_patient_requires_auth(self, unauthenticated_client):
        """Création de patient requiert authentification."""
        response = unauthenticated_client.post(
            "/api/v1/patients",
            json={
                "entity_id": 1,
                "first_name": "Test",
                "last_name": "Patient",
            },
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]