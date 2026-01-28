"""
Tests pour le module CarePlan API.

Utilise les fixtures définies dans conftest.py.
Tests pour: care_plans, care_plan_services, assignments.
"""
from datetime import date

from fastapi import status

from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService
from app.models.enums import CarePlanStatus, FrequencyType, ServicePriority, AssignmentStatus


# =============================================================================
# CARE PLAN TESTS
# =============================================================================

class TestCarePlanEndpoints:
    """Tests des endpoints /api/v1/care-plans."""

    def test_list_care_plans(self, client, admin_token_headers, care_plan):
        """Liste des plans d'aide."""
        response = client.get(
            "/api/v1/care-plans",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert "items" in data

    def test_list_plans_filter_by_patient(self, client, admin_token_headers, care_plan, patient):
        """Filtrage par patient."""
        response = client.get(
            f"/api/v1/care-plans?patient_id={patient.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["patient_id"] == patient.id

    def test_list_plans_filter_by_status(self, client, admin_token_headers, care_plan):
        """Filtrage par statut."""
        response = client.get(
            "/api/v1/care-plans?status=DRAFT",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_care_plan(self, client, admin_token_headers, care_plan):
        """Récupération d'un plan par ID."""
        response = client.get(
            f"/api/v1/care-plans/{care_plan.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == care_plan.id
        assert "services" in data

    def test_get_care_plan_not_found(self, client, admin_token_headers):
        """Erreur 404 si plan inexistant."""
        response = client.get(
            "/api/v1/care-plans/99999",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_care_plan(self, client, admin_token_headers, patient, entity):
        """Création d'un plan d'aide."""
        response = client.post(
            "/api/v1/care-plans",
            headers=admin_token_headers,
            json={
                "patient_id": patient.id,
                "entity_id": entity.id,
                "title": "Nouveau plan d'aide 2024",
                "start_date": str(date.today()),
                "total_hours_week": 15.5,
                "gir_at_creation": 4,
                "notes": "Plan initial suite à évaluation",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["patient_id"] == patient.id
        assert data["status"] == "DRAFT"
        assert data["is_draft"] is True
        assert data["is_editable"] is True

    def test_create_care_plan_with_services(self, client, admin_token_headers, patient, entity,
                                            service_template_toilette):
        """Création d'un plan avec services initiaux."""
        response = client.post(
            "/api/v1/care-plans",
            headers=admin_token_headers,
            json={
                "patient_id": patient.id,
                "entity_id": entity.id,
                "title": "Plan avec services",
                "start_date": str(date.today()),
                "services": [
                    {
                        "service_template_id": service_template_toilette.id,
                        "quantity_per_week": 5,
                        "frequency_type": "SPECIFIC_DAYS",
                        "frequency_days": [1, 2, 3, 4, 5],
                        "duration_minutes": 45,
                        "priority": "HIGH",
                    }
                ],
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["services_count"] == 1

    def test_create_care_plan_patient_not_found(self, client, admin_token_headers, entity):
        """Erreur 404 si patient inexistant."""
        response = client.post(
            "/api/v1/care-plans",
            headers=admin_token_headers,
            json={
                "patient_id": 99999,
                "entity_id": entity.id,
                "title": "Test",
                "start_date": str(date.today()),
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_care_plan(self, client, admin_token_headers, care_plan):
        """Mise à jour d'un plan."""
        response = client.patch(
            f"/api/v1/care-plans/{care_plan.id}",
            headers=admin_token_headers,
            json={"title": "Titre modifié"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Titre modifié"

    def test_delete_care_plan_draft(self, client, admin_token_headers, db_session, patient, entity, user_admin, tenant):
        """Suppression d'un plan en brouillon."""
        plan = CarePlan(
            tenant_id=tenant.id,  # ← AJOUTÉ
            patient_id=patient.id,
            entity_id=entity.id,
            title="À supprimer",
            start_date=date.today(),
            status=CarePlanStatus.DRAFT,
            created_by=user_admin.id,
        )
        db_session.add(plan)
        db_session.flush()

        response = client.delete(
            f"/api/v1/care-plans/{plan.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_care_plan_active_fails(self, client, admin_token_headers, db_session, patient, entity, user_admin, tenant):
        """Erreur 409 si suppression d'un plan actif."""
        plan = CarePlan(
            tenant_id=tenant.id,  # ← AJOUTÉ
            patient_id=patient.id,
            entity_id=entity.id,
            title="Plan actif",
            start_date=date.today(),
            status=CarePlanStatus.ACTIVE,
            created_by=user_admin.id,
        )
        db_session.add(plan)
        db_session.flush()

        response = client.delete(
            f"/api/v1/care-plans/{plan.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# CARE PLAN WORKFLOW TESTS
# =============================================================================

class TestCarePlanWorkflow:
    """Tests du workflow des plans d'aide."""

    def test_submit_for_validation(self, client, admin_token_headers, care_plan):
        """Soumission pour validation."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/submit",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "PENDING_VALIDATION"

    def test_validate_care_plan(self, client, admin_token_headers, care_plan):
        """Validation d'un plan."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/validate",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ACTIVE"
        assert data["is_validated"] is True
        assert data["validated_by_id"] is not None

    def test_suspend_care_plan(self, client, admin_token_headers, db_session, patient, entity, user_admin, tenant):
        """Suspension d'un plan actif."""
        plan = CarePlan(
            tenant_id=tenant.id,  # ← AJOUTÉ
            patient_id=patient.id,
            entity_id=entity.id,
            title="Plan actif",
            start_date=date.today(),
            status=CarePlanStatus.ACTIVE,
            created_by=user_admin.id,
        )
        db_session.add(plan)
        db_session.flush()

        response = client.post(
            f"/api/v1/care-plans/{plan.id}/suspend",
            headers=admin_token_headers,
            json={"reason": "Hospitalisation du patient"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "SUSPENDED"

    def test_reactivate_care_plan(self, client, admin_token_headers, db_session, patient, entity, user_admin, tenant):
        """Réactivation d'un plan suspendu."""
        plan = CarePlan(
            tenant_id=tenant.id,  # ← AJOUTÉ
            patient_id=patient.id,
            entity_id=entity.id,
            title="Plan suspendu",
            start_date=date.today(),
            status=CarePlanStatus.SUSPENDED,
            created_by=user_admin.id,
        )
        db_session.add(plan)
        db_session.flush()

        response = client.post(
            f"/api/v1/care-plans/{plan.id}/reactivate",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ACTIVE"

    def test_complete_care_plan(self, client, admin_token_headers, db_session, patient, entity, user_admin, tenant):
        """Terminer un plan."""
        plan = CarePlan(
            tenant_id=tenant.id,  # ← AJOUTÉ
            patient_id=patient.id,
            entity_id=entity.id,
            title="Plan à terminer",
            start_date=date.today(),
            status=CarePlanStatus.ACTIVE,
            created_by=user_admin.id,
        )
        db_session.add(plan)
        db_session.flush()

        response = client.post(
            f"/api/v1/care-plans/{plan.id}/complete",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "COMPLETED"

    def test_cancel_care_plan(self, client, admin_token_headers, care_plan):
        """Annulation d'un plan."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/cancel",
            headers=admin_token_headers,
            json={"reason": "Demande de la famille"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "CANCELLED"


# =============================================================================
# CARE PLAN SERVICE TESTS
# =============================================================================

class TestCarePlanServiceEndpoints:
    """Tests des endpoints /api/v1/care-plans/{id}/services."""

    def test_list_plan_services(self, client, admin_token_headers, care_plan, care_plan_service):
        """Liste des services d'un plan."""
        response = client.get(
            f"/api/v1/care-plans/{care_plan.id}/services",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    def test_get_plan_service(self, client, admin_token_headers, care_plan, care_plan_service):
        """Récupération d'un service."""
        response = client.get(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == care_plan_service.id
        assert "frequency_display" in data
        assert "time_slot_display" in data

    def test_create_plan_service(self, client, admin_token_headers, care_plan, service_template_toilette):
        """Ajout d'un service au plan."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
                "quantity_per_week": 3,
                "frequency_type": "WEEKLY",
                "duration_minutes": 30,
                "priority": "MEDIUM",
                "special_instructions": "Préférence douche",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["care_plan_id"] == care_plan.id
        assert data["quantity_per_week"] == 3

    def test_update_plan_service(self, client, admin_token_headers, care_plan, care_plan_service):
        """Mise à jour d'un service."""
        response = client.patch(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}",
            headers=admin_token_headers,
            json={"priority": "CRITICAL"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["priority"] == "CRITICAL"

    def test_delete_plan_service(self, client, admin_token_headers, care_plan, db_session, service_template_toilette, tenant):
        """Suppression d'un service."""
        service = CarePlanService(
            tenant_id=tenant.id,  # ← AJOUTÉ
            care_plan_id=care_plan.id,
            service_template_id=service_template_toilette.id,
            quantity_per_week=1,
            frequency_type=FrequencyType.WEEKLY,
            duration_minutes=30,
            priority=ServicePriority.LOW,
        )
        db_session.add(service)
        db_session.flush()

        response = client.delete(
            f"/api/v1/care-plans/{care_plan.id}/services/{service.id}",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# SERVICE ASSIGNMENT TESTS
# =============================================================================

class TestServiceAssignment:
    """Tests de l'affectation des services."""

    def test_assign_service(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier):
        """Affectation d'un service à un professionnel."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/assign",
            headers=admin_token_headers,
            json={
                "user_id": user_infirmier.id,
                "mode": "assign",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["assigned_user_id"] == user_infirmier.id
        assert data["assignment_status"] == "ASSIGNED"
        assert data["is_assigned"] is True

    def test_propose_service(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier):
        """Proposition d'un service (en attente de confirmation)."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/assign",
            headers=admin_token_headers,
            json={
                "user_id": user_infirmier.id,
                "mode": "propose",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["assignment_status"] == "PENDING"

    def test_unassign_service(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier,
                              db_session):
        """Retrait de l'affectation."""
        # D'abord affecter
        care_plan_service.assigned_user_id = user_infirmier.id
        care_plan_service.assignment_status = AssignmentStatus.ASSIGNED
        db_session.flush()

        response = client.delete(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/assign",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["assigned_user_id"] is None
        assert data["assignment_status"] == "UNASSIGNED"

    def test_confirm_assignment(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier,
                                db_session):
        """Confirmation de l'affectation par le professionnel."""
        # Mettre en attente
        care_plan_service.assigned_user_id = user_infirmier.id
        care_plan_service.assignment_status = AssignmentStatus.PENDING
        db_session.flush()

        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/confirm",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["assignment_status"] == "CONFIRMED"
        assert response.json()["is_confirmed"] is True

    def test_reject_assignment(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier,
                               db_session):
        """Rejet de l'affectation par le professionnel."""
        # Mettre en attente
        care_plan_service.assigned_user_id = user_infirmier.id
        care_plan_service.assignment_status = AssignmentStatus.PENDING
        db_session.flush()

        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/reject",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["assignment_status"] == "REJECTED"

    def test_reject_non_pending_fails(self, client, admin_token_headers, care_plan, care_plan_service):
        """Erreur 409 si rejet d'un service non en attente."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/reject",
            headers=admin_token_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests de validation des données."""

    def test_invalid_frequency_type(self, client, admin_token_headers, care_plan, service_template_toilette):
        """Type de fréquence invalide."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
                "quantity_per_week": 3,
                "frequency_type": "INVALID",
                "duration_minutes": 30,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_priority(self, client, admin_token_headers, care_plan, service_template_toilette):
        """Priorité invalide."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
                "quantity_per_week": 3,
                "frequency_type": "WEEKLY",
                "duration_minutes": 30,
                "priority": "INVALID",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_frequency_days(self, client, admin_token_headers, care_plan, service_template_toilette):
        """Jours de fréquence invalides."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services",
            headers=admin_token_headers,
            json={
                "service_template_id": service_template_toilette.id,
                "quantity_per_week": 3,
                "frequency_type": "SPECIFIC_DAYS",
                "frequency_days": [0, 8],  # Invalide: doit être 1-7
                "duration_minutes": 30,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_gir_score(self, client, admin_token_headers, patient, entity):
        """Score GIR invalide."""
        response = client.post(
            "/api/v1/care-plans",
            headers=admin_token_headers,
            json={
                "patient_id": patient.id,
                "entity_id": entity.id,
                "title": "Test",
                "start_date": str(date.today()),
                "gir_at_creation": 10,  # Invalide: doit être 1-6
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_assignment_mode(self, client, admin_token_headers, care_plan, care_plan_service, user_infirmier):
        """Mode d'affectation invalide."""
        response = client.post(
            f"/api/v1/care-plans/{care_plan.id}/services/{care_plan_service.id}/assign",
            headers=admin_token_headers,
            json={
                "user_id": user_infirmier.id,
                "mode": "invalid_mode",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY