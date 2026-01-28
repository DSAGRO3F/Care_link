"""
Tests unitaires pour les modèles de plans d'aide.

- CarePlan : Plan d'aide global patient
- CarePlanService : Services individuels du plan
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CarePlan, CarePlanService, Patient, Entity, User, ServiceTemplate
from app.models.enums import (
    CarePlanStatus,
    FrequencyType,
    ServicePriority,
    AssignmentStatus,
)


class TestCarePlan:
    """Tests pour le modèle CarePlan."""

    def test_create_care_plan(self, db_session: Session, tenant, patient: Patient, entity: Entity, user_coordinateur: User):
        """Test création d'un plan d'aide."""
        care_plan = CarePlan(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            entity_id=entity.id,
            title="Plan d'aide test",
            status=CarePlanStatus.DRAFT,
            start_date=date.today(),
            total_hours_week=Decimal("10.00"),
            gir_at_creation=3,
            created_by=user_coordinateur.id
        )
        db_session.add(care_plan)
        db_session.flush()

        assert care_plan.id is not None
        assert care_plan.status == CarePlanStatus.DRAFT
        assert care_plan.created_at is not None

    def test_care_plan_unique_reference(self, db_session: Session, tenant, care_plan: CarePlan, patient: Patient,
                                        entity: Entity, user_coordinateur: User):
        """Test contrainte d'unicité sur reference_number."""
        duplicate = CarePlan(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            entity_id=entity.id,
            title="Autre plan",
            reference_number="PA-2024-00001",  # Même référence que la fixture
            status=CarePlanStatus.DRAFT,
            start_date=date.today(),
            created_by=user_coordinateur.id
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_care_plan_relations(self, care_plan: CarePlan, patient: Patient, entity: Entity, patient_evaluation):
        """Test relations CarePlan → Patient, Entity, Evaluation."""
        assert care_plan.patient == patient
        assert care_plan.entity == entity
        assert care_plan.source_evaluation == patient_evaluation
        assert care_plan in patient.care_plans
        assert care_plan in entity.care_plans

    def test_care_plan_is_draft(self, care_plan: CarePlan):
        """Test propriété is_draft."""
        assert care_plan.is_draft is True
        assert care_plan.is_active is False

    def test_care_plan_is_editable(self, care_plan: CarePlan):
        """Test propriété is_editable."""
        # Un plan DRAFT est éditable
        assert care_plan.is_editable is True

    def test_care_plan_submit_for_validation(self, db_session: Session, care_plan: CarePlan):
        """Test soumission pour validation."""
        care_plan.submit_for_validation()
        db_session.flush()

        assert care_plan.status == CarePlanStatus.PENDING_VALIDATION
        assert care_plan.is_editable is True  # Encore éditable

    def test_care_plan_validate(self, db_session: Session, care_plan: CarePlan, user_coordinateur: User):
        """Test validation d'un plan."""
        care_plan.validate(user_coordinateur)
        db_session.flush()

        assert care_plan.status == CarePlanStatus.ACTIVE
        assert care_plan.is_active is True
        assert care_plan.is_validated is True
        assert care_plan.validated_by_id == user_coordinateur.id
        assert care_plan.validated_at is not None

    def test_care_plan_suspend(self, db_session: Session, care_plan: CarePlan, user_coordinateur: User):
        """Test suspension d'un plan."""
        care_plan.validate(user_coordinateur)
        db_session.flush()

        care_plan.suspend(reason="Hospitalisation du patient")
        db_session.flush()

        assert care_plan.status == CarePlanStatus.SUSPENDED
        assert care_plan.is_active is False
        assert "Hospitalisation" in care_plan.notes

    def test_care_plan_reactivate(self, db_session: Session, care_plan: CarePlan, user_coordinateur: User):
        """Test réactivation d'un plan suspendu."""
        care_plan.validate(user_coordinateur)
        care_plan.suspend()
        db_session.flush()

        care_plan.reactivate()
        db_session.flush()

        assert care_plan.status == CarePlanStatus.ACTIVE
        assert care_plan.is_active is True

    def test_care_plan_complete(self, db_session: Session, care_plan: CarePlan, user_coordinateur: User):
        """Test complétion d'un plan."""
        care_plan.validate(user_coordinateur)
        db_session.flush()

        care_plan.complete()
        db_session.flush()

        assert care_plan.status == CarePlanStatus.COMPLETED

    def test_care_plan_cancel(self, db_session: Session, care_plan: CarePlan):
        """Test annulation d'un plan."""
        care_plan.cancel(reason="Changement de structure")
        db_session.flush()

        assert care_plan.status == CarePlanStatus.CANCELLED
        assert "Changement de structure" in care_plan.notes

    def test_care_plan_services_count(self, care_plan: CarePlan, care_plan_service: CarePlanService):
        """Test comptage des services."""
        assert care_plan.services_count == 1

    def test_care_plan_assignment_completion_rate(self, care_plan: CarePlan, care_plan_service: CarePlanService):
        """Test taux de complétion des affectations."""
        # Le service n'est pas encore affecté
        assert care_plan.assigned_services_count == 0
        assert care_plan.assignment_completion_rate == 0.0
        assert care_plan.is_fully_assigned is False


class TestCarePlanService:
    """Tests pour le modèle CarePlanService."""

    def test_create_care_plan_service(self, db_session: Session, tenant, care_plan: CarePlan,
                                      service_template_injection: ServiceTemplate):
        """Test création d'un service de plan."""
        service = CarePlanService(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            care_plan_id=care_plan.id,
            service_template_id=service_template_injection.id,
            quantity_per_week=7,
            frequency_type=FrequencyType.DAILY,
            duration_minutes=15,
            priority=ServicePriority.CRITICAL,
            assignment_status=AssignmentStatus.UNASSIGNED,
            status="active"
        )
        db_session.add(service)
        db_session.flush()

        assert service.id is not None
        assert service.frequency_type == FrequencyType.DAILY
        assert service.priority == ServicePriority.CRITICAL

    def test_care_plan_service_relations(self, care_plan_service: CarePlanService, care_plan: CarePlan,
                                         service_template_toilette: ServiceTemplate):
        """Test relations CarePlanService → CarePlan, ServiceTemplate."""
        assert care_plan_service.care_plan == care_plan
        assert care_plan_service.service_template == service_template_toilette
        assert care_plan_service in care_plan.services

    def test_care_plan_service_is_assigned(self, care_plan_service: CarePlanService):
        """Test propriété is_assigned."""
        assert care_plan_service.is_assigned is False
        assert care_plan_service.assignment_status == AssignmentStatus.UNASSIGNED

    def test_care_plan_service_assign_to(self, db_session: Session, care_plan_service: CarePlanService,
                                         user_infirmier: User, user_coordinateur: User):
        """Test affectation d'un service."""
        care_plan_service.assign_to(user_infirmier, user_coordinateur)
        db_session.flush()

        assert care_plan_service.is_assigned is True
        assert care_plan_service.assigned_user_id == user_infirmier.id
        assert care_plan_service.assigned_by_id == user_coordinateur.id
        assert care_plan_service.assigned_at is not None
        assert care_plan_service.assignment_status == AssignmentStatus.ASSIGNED

    def test_care_plan_service_propose_to(self, db_session: Session, care_plan_service: CarePlanService,
                                          user_infirmier: User, user_coordinateur: User):
        """Test proposition d'un service (en attente de confirmation)."""
        care_plan_service.propose_to(user_infirmier, user_coordinateur)
        db_session.flush()

        assert care_plan_service.is_pending is True
        assert care_plan_service.assignment_status == AssignmentStatus.PENDING

    def test_care_plan_service_confirm_assignment(self, db_session: Session, care_plan_service: CarePlanService,
                                                  user_infirmier: User, user_coordinateur: User):
        """Test confirmation d'une affectation."""
        care_plan_service.assign_to(user_infirmier, user_coordinateur)
        db_session.flush()

        care_plan_service.confirm_assignment()
        db_session.flush()

        assert care_plan_service.is_confirmed is True
        assert care_plan_service.assignment_status == AssignmentStatus.CONFIRMED

    def test_care_plan_service_reject_assignment(self, db_session: Session, care_plan_service: CarePlanService,
                                                 user_infirmier: User, user_coordinateur: User):
        """Test rejet d'une proposition."""
        care_plan_service.propose_to(user_infirmier, user_coordinateur)
        db_session.flush()

        care_plan_service.reject_assignment()
        db_session.flush()

        assert care_plan_service.assignment_status == AssignmentStatus.REJECTED

    def test_care_plan_service_unassign(self, db_session: Session, care_plan_service: CarePlanService,
                                        user_infirmier: User, user_coordinateur: User):
        """Test désaffectation d'un service."""
        care_plan_service.assign_to(user_infirmier, user_coordinateur)
        db_session.flush()

        care_plan_service.unassign()
        db_session.flush()

        assert care_plan_service.is_assigned is False
        assert care_plan_service.assigned_user_id is None
        assert care_plan_service.assignment_status == AssignmentStatus.UNASSIGNED

    def test_care_plan_service_time_slot_display(self, care_plan_service: CarePlanService):
        """Test affichage du créneau horaire."""
        display = care_plan_service.time_slot_display
        assert "07:00" in display
        assert "09:00" in display

    def test_care_plan_service_days_display(self, care_plan_service: CarePlanService):
        """Test affichage des jours."""
        display = care_plan_service.days_display
        assert "Lun" in display
        assert "Ven" in display
        assert "Sam" not in display

    def test_care_plan_service_frequency_display(self, care_plan_service: CarePlanService):
        """Test affichage de la fréquence."""
        display = care_plan_service.frequency_display
        assert "5x/semaine" in display

    def test_care_plan_service_total_weekly_minutes(self, care_plan_service: CarePlanService):
        """Test calcul du total minutes par semaine."""
        # 5 fois x 45 minutes = 225 minutes
        assert care_plan_service.total_weekly_minutes == 225

    def test_care_plan_service_total_weekly_hours(self, care_plan_service: CarePlanService):
        """Test calcul du total heures par semaine."""
        # 225 minutes = 3.75 heures
        assert care_plan_service.total_weekly_hours == 3.75

    def test_care_plan_service_pause_resume(self, db_session: Session, care_plan_service: CarePlanService):
        """Test pause et reprise d'un service."""
        care_plan_service.pause()
        db_session.flush()

        assert care_plan_service.is_paused is True
        assert care_plan_service.status == "paused"

        care_plan_service.resume()
        db_session.flush()

        assert care_plan_service.is_active is True
        assert care_plan_service.status == "active"

    def test_care_plan_service_complete(self, db_session: Session, care_plan_service: CarePlanService):
        """Test complétion d'un service."""
        care_plan_service.complete()
        db_session.flush()

        assert care_plan_service.status == "completed"