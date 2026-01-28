"""
Tests pour le module Coordination API - Architecture v4.3.

Ce fichier utilise les fixtures définies dans tests/conftest.py.
L'authentification est bypassée via l'override de get_current_user.

Tests pour: coordination_entries, scheduled_interventions, planning.
"""
from datetime import date, datetime, timezone

from fastapi import status


# =============================================================================
# COORDINATION ENTRY TESTS
# =============================================================================

class TestCoordinationEntryEndpoints:
    """Tests des endpoints /api/v1/coordination-entries."""

    def test_list_coordination_entries(self, client, coordination_entry):
        """Liste des entrées de coordination."""
        response = client.get("/api/v1/coordination-entries")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert "items" in data

    def test_list_entries_filter_by_patient(self, client, coordination_entry, patient):
        """Filtrage par patient."""
        response = client.get(f"/api/v1/coordination-entries?patient_id={patient.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["patient_id"] == patient.id

    def test_list_entries_filter_by_category(self, client, coordination_entry):
        """Filtrage par catégorie."""
        response = client.get("/api/v1/coordination-entries?category=SOINS")
        assert response.status_code == status.HTTP_200_OK

    def test_get_coordination_entry(self, client, coordination_entry):
        """Récupération d'une entrée."""
        response = client.get(f"/api/v1/coordination-entries/{coordination_entry.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == coordination_entry.id

    def test_get_entry_not_found(self, client):
        """Erreur 404 si entrée inexistante."""
        response = client.get("/api/v1/coordination-entries/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_coordination_entry(self, client, patient):
        """Création d'une entrée de coordination."""
        response = client.post(
            "/api/v1/coordination-entries",
            json={
                "patient_id": patient.id,
                "category": "SOINS",
                "intervention_type": "Pansement",
                "description": "Réfection du pansement jambe droite",
                "observations": "Plaie en bonne évolution",
                "next_actions": "Refaire dans 48h",
                "performed_at": datetime.now(timezone.utc).isoformat(),
                "duration_minutes": 25,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["patient_id"] == patient.id
        assert data["category"] == "SOINS"

    def test_create_entry_patient_not_found(self, client):
        """Erreur 404 si patient inexistant."""
        response = client.post(
            "/api/v1/coordination-entries",
            json={
                "patient_id": 99999,
                "category": "SOINS",
                "intervention_type": "Test",
                "description": "Test description",
                "performed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_coordination_entry(self, client, coordination_entry):
        """Mise à jour d'une entrée."""
        response = client.patch(
            f"/api/v1/coordination-entries/{coordination_entry.id}",
            json={"observations": "Observations mises à jour"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["observations"] == "Observations mises à jour"

    def test_delete_coordination_entry(self, client, coordination_entry):
        """Suppression d'une entrée (soft delete)."""
        response = client.delete(f"/api/v1/coordination-entries/{coordination_entry.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# SCHEDULED INTERVENTION TESTS
# =============================================================================

class TestScheduledInterventionEndpoints:
    """Tests des endpoints /api/v1/scheduled-interventions."""

    def test_list_scheduled_interventions(self, client, scheduled_intervention):
        """Liste des interventions planifiées."""
        response = client.get("/api/v1/scheduled-interventions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_list_interventions_filter_by_date(self, client, scheduled_intervention):
        """Filtrage par date."""
        today = date.today().isoformat()
        response = client.get(f"/api/v1/scheduled-interventions?scheduled_date={today}")
        assert response.status_code == status.HTTP_200_OK

    def test_list_interventions_filter_by_patient(self, client, scheduled_intervention, patient):
        """Filtrage par patient."""
        response = client.get(f"/api/v1/scheduled-interventions?patient_id={patient.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["patient_id"] == patient.id

    def test_list_interventions_filter_by_user(self, client, scheduled_intervention, user_infirmier):
        """Filtrage par intervenant."""
        response = client.get(f"/api/v1/scheduled-interventions?user_id={user_infirmier.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_get_scheduled_intervention(self, client, scheduled_intervention):
        """Récupération d'une intervention."""
        response = client.get(f"/api/v1/scheduled-interventions/{scheduled_intervention.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == scheduled_intervention.id
        assert data["status"] == "SCHEDULED"

    def test_start_intervention(self, client, scheduled_intervention):
        """Démarrage d'une intervention."""
        response = client.post(f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/start")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["actual_start_time"] is not None

    def test_complete_intervention(self, client, scheduled_intervention):
        """Complétion d'une intervention."""
        # D'abord démarrer
        client.post(f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/start")

        # Puis compléter
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/complete",
            json={
                "notes": "Intervention terminée avec succès",
                "observations": "RAS",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["actual_end_time"] is not None

    def test_cancel_intervention(self, client, scheduled_intervention):
        """Annulation d'une intervention."""
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/cancel",
            json={"reason": "Patient hospitalisé"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "CANCELLED"

    def test_mark_intervention_missed(self, client, scheduled_intervention):
        """Marquer une intervention comme manquée."""
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/missed?reason=Patient%20absent"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "MISSED"

    def test_reschedule_intervention(self, client, scheduled_intervention):
        """Reprogrammation d'une intervention."""
        tomorrow = date.today()
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/reschedule",
            json={
                "new_date": tomorrow.isoformat(),
                "new_start_time": "10:00:00",
                "new_end_time": "10:45:00",
                "reason": "Demande du patient",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "SCHEDULED"
        assert data["rescheduled_from_id"] == scheduled_intervention.id

    def test_complete_without_in_progress_fails(self, client, scheduled_intervention):
        """Erreur si on termine une intervention non démarrée."""
        response = client.post(f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/complete")
        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# PLANNING TESTS
# =============================================================================

class TestPlanningEndpoints:
    """Tests des endpoints de planning."""

    def test_get_daily_planning(self, client, scheduled_intervention, user_infirmier):
        """Récupération du planning journalier."""
        today = date.today().isoformat()
        response = client.get(f"/api/v1/planning/daily/{user_infirmier.id}?planning_date={today}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == user_infirmier.id
        assert "interventions" in data
        assert "total_scheduled_minutes" in data
        assert "total_interventions" in data

    def test_get_my_daily_planning(self, client):
        """Récupération de mon planning."""
        response = client.get("/api/v1/planning/my-day")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "interventions" in data
        assert "total_scheduled_minutes" in data


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests de validation des données."""

    def test_invalid_category(self, client, patient):
        """Catégorie invalide."""
        response = client.post(
            "/api/v1/coordination-entries",
            json={
                "patient_id": patient.id,
                "category": "INVALID_CATEGORY",
                "intervention_type": "Test",
                "description": "Test",
                "performed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_cancel_without_reason_fails(self, client, scheduled_intervention):
        """Annulation sans raison."""
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/cancel",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_cancel_reason_too_short(self, client, scheduled_intervention):
        """Raison d'annulation trop courte."""
        response = client.post(
            f"/api/v1/scheduled-interventions/{scheduled_intervention.id}/cancel",
            json={"reason": "ok"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# TESTS MULTI-TENANT (Isolation des données)
# =============================================================================

class TestMultiTenantIsolation:
    """Tests d'isolation multi-tenant pour la coordination."""

    def test_cannot_access_other_tenant_entry(
        self, client, db_session, tenant_ssiad, country, user_admin
    ):
        """Vérifie qu'on ne peut pas accéder aux entrées d'un autre tenant."""
        from app.models import Entity, Patient, CoordinationEntry
        from app.models.enums import EntityType, PatientStatus, CoordinationCategory

        # Créer une entité dans l'autre tenant
        other_entity = Entity(
            tenant_id=tenant_ssiad.id,
            country_id=country.id,
            name="Autre SSIAD",
            entity_type=EntityType.SSIAD,
            status="active",
        )
        db_session.add(other_entity)
        db_session.flush()

        # Créer un patient dans l'autre tenant
        other_patient = Patient(
            tenant_id=tenant_ssiad.id,
            entity_id=other_entity.id,
            first_name_encrypted="Autre",
            last_name_encrypted="Patient",
            birth_date_encrypted="1950-01-01",
            status=PatientStatus.ACTIVE.value,
            created_by=user_admin.id,
        )
        db_session.add(other_patient)
        db_session.flush()

        # Créer une entrée dans l'autre tenant
        other_entry = CoordinationEntry(
            tenant_id=tenant_ssiad.id,
            patient_id=other_patient.id,
            user_id=user_admin.id,
            category=CoordinationCategory.SOINS,
            intervention_type="Test",
            description="Entrée autre tenant",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(other_entry)
        db_session.flush()

        # Tenter d'accéder à l'entrée de l'autre tenant
        response = client.get(f"/api/v1/coordination-entries/{other_entry.id}")
        # Devrait être 404 car filtré par tenant
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_list_only_shows_current_tenant_entries(
        self, client, coordination_entry, db_session, tenant_ssiad, country, user_admin
    ):
        """Vérifie que la liste ne montre que les entrées du tenant courant."""
        from app.models import Entity, Patient, CoordinationEntry
        from app.models.enums import EntityType, PatientStatus, CoordinationCategory

        # Créer des données dans l'autre tenant
        other_entity = Entity(
            tenant_id=tenant_ssiad.id,
            country_id=country.id,
            name="Troisième SSIAD",
            entity_type=EntityType.SSIAD,
            status="active",
        )
        db_session.add(other_entity)
        db_session.flush()

        other_patient = Patient(
            tenant_id=tenant_ssiad.id,
            entity_id=other_entity.id,
            first_name_encrypted="Troisième",
            last_name_encrypted="Patient",
            birth_date_encrypted="1960-06-15",
            status=PatientStatus.ACTIVE.value,
            created_by=user_admin.id,
        )
        db_session.add(other_patient)
        db_session.flush()

        other_entry = CoordinationEntry(
            tenant_id=tenant_ssiad.id,
            patient_id=other_patient.id,
            user_id=user_admin.id,
            category=CoordinationCategory.HYGIENE,
            intervention_type="Autre",
            description="Ne devrait pas apparaître",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(other_entry)
        db_session.flush()

        # Lister les entrées
        response = client.get("/api/v1/coordination-entries")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Vérifier que seules les entrées du tenant courant sont retournées
        for item in data["items"]:
            assert item["id"] != other_entry.id