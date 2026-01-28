"""
Tests unitaires pour le modèle ScheduledIntervention.

Gère le planning des interventions futures (RDV concrets).
"""

from datetime import date, time, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import ScheduledIntervention, CarePlanService, Patient, User, CoordinationEntry
from app.models.enums import InterventionStatus, CoordinationCategory


class TestScheduledIntervention:
    """Tests pour le modèle ScheduledIntervention."""

    def test_create_scheduled_intervention(
            self,
            db_session: Session,
            tenant,
            care_plan_service: CarePlanService,
            patient: Patient,
            user_infirmier: User
    ):
        """Test création d'une intervention planifiée."""
        intervention = ScheduledIntervention(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            care_plan_service_id=care_plan_service.id,
            patient_id=patient.id,
            user_id=user_infirmier.id,
            scheduled_date=date.today(),
            scheduled_start_time=time(9, 0),
            scheduled_end_time=time(9, 45),
            status=InterventionStatus.SCHEDULED
        )
        db_session.add(intervention)
        db_session.flush()

        assert intervention.id is not None
        assert intervention.status == InterventionStatus.SCHEDULED
        assert intervention.created_at is not None

    def test_intervention_relations(
            self,
            scheduled_intervention: ScheduledIntervention,
            care_plan_service: CarePlanService,
            patient: Patient,
            user_infirmier: User
    ):
        """Test relations ScheduledIntervention → CarePlanService, Patient, User."""
        assert scheduled_intervention.care_plan_service == care_plan_service
        assert scheduled_intervention.patient == patient
        assert scheduled_intervention.user == user_infirmier
        assert scheduled_intervention in care_plan_service.scheduled_interventions
        assert scheduled_intervention in patient.scheduled_interventions

    def test_intervention_scheduled_duration(self, scheduled_intervention: ScheduledIntervention):
        """Test calcul de la durée prévue."""
        # La fixture a 8h00-8h45 = 45 minutes
        assert scheduled_intervention.scheduled_duration_minutes == 45
        assert scheduled_intervention.scheduled_duration_hours == 0.75

    def test_intervention_time_slot_display(self, scheduled_intervention: ScheduledIntervention):
        """Test affichage du créneau horaire."""
        display = scheduled_intervention.time_slot_display
        assert "08:00" in display
        assert "08:45" in display

    def test_intervention_full_display(self, scheduled_intervention: ScheduledIntervention):
        """Test affichage complet."""
        display = scheduled_intervention.full_display
        assert "08:00-08:45" in display
        assert "SCHEDULED" in display

    def test_intervention_is_pending(self, scheduled_intervention: ScheduledIntervention):
        """Test propriété is_pending."""
        assert scheduled_intervention.is_pending is True
        assert scheduled_intervention.is_completed is False
        assert scheduled_intervention.is_cancelled is False

    def test_intervention_can_be_started(self, scheduled_intervention: ScheduledIntervention):
        """Test propriété can_be_started."""
        assert scheduled_intervention.can_be_started is True

    def test_intervention_is_terminal(self, scheduled_intervention: ScheduledIntervention):
        """Test propriété is_terminal."""
        assert scheduled_intervention.is_terminal is False

    def test_intervention_confirm(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test confirmation d'une intervention."""
        scheduled_intervention.confirm()
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.CONFIRMED
        assert scheduled_intervention.is_confirmed is True
        assert scheduled_intervention.is_pending is True  # Encore en attente de réalisation

    def test_intervention_start(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test démarrage d'une intervention."""
        start_time = time(8, 5)

        scheduled_intervention.start(actual_start=start_time)
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.IN_PROGRESS
        assert scheduled_intervention.is_in_progress is True
        assert scheduled_intervention.actual_start_time == start_time
        assert scheduled_intervention.can_be_started is False

    def test_intervention_complete(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test complétion d'une intervention."""
        # Démarrer d'abord
        scheduled_intervention.start(actual_start=time(8, 0))
        db_session.flush()

        # Puis compléter
        scheduled_intervention.complete(
            actual_end=time(8, 50),
            notes="RAS, patient en forme"
        )
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.COMPLETED
        assert scheduled_intervention.is_completed is True
        assert scheduled_intervention.actual_end_time == time(8, 50)
        assert scheduled_intervention.actual_duration_minutes == 50  # 8h00 à 8h50
        assert scheduled_intervention.completion_notes == "RAS, patient en forme"
        assert scheduled_intervention.is_terminal is True

    def test_intervention_cancel(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test annulation d'une intervention."""
        scheduled_intervention.cancel(reason="Patient absent")
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.CANCELLED
        assert scheduled_intervention.is_cancelled is True
        assert scheduled_intervention.cancellation_reason == "Patient absent"
        assert scheduled_intervention.is_terminal is True

    def test_intervention_mark_missed(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test marquage comme manquée."""
        scheduled_intervention.mark_missed(reason="Porte fermée")
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.MISSED
        assert scheduled_intervention.is_missed is True
        assert scheduled_intervention.cancellation_reason == "Porte fermée"

    def test_intervention_mark_missed_default_reason(self, db_session: Session,
                                                     scheduled_intervention: ScheduledIntervention):
        """Test marquage manquée avec raison par défaut."""
        scheduled_intervention.mark_missed()
        db_session.flush()

        assert scheduled_intervention.cancellation_reason == "Intervention non réalisée"

    def test_intervention_reschedule(
            self,
            db_session: Session,
            tenant,
            scheduled_intervention: ScheduledIntervention,
            care_plan_service: CarePlanService,
            patient: Patient,
            user_infirmier: User
    ):
        """Test reprogrammation d'une intervention."""
        # Créer la nouvelle intervention
        new_intervention = ScheduledIntervention(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            care_plan_service_id=care_plan_service.id,
            patient_id=patient.id,
            user_id=user_infirmier.id,
            scheduled_date=date.today(),
            scheduled_start_time=time(14, 0),
            scheduled_end_time=time(14, 45),
            status=InterventionStatus.SCHEDULED
        )
        db_session.add(new_intervention)
        db_session.flush()

        # Reprogrammer
        scheduled_intervention.reschedule(new_intervention, reason="Report à l'après-midi")
        db_session.flush()

        assert scheduled_intervention.status == InterventionStatus.RESCHEDULED
        assert scheduled_intervention.is_rescheduled is True
        assert scheduled_intervention.rescheduled_to_id == new_intervention.id
        assert new_intervention.rescheduled_from_id == scheduled_intervention.id
        assert scheduled_intervention.cancellation_reason == "Report à l'après-midi"

    def test_intervention_duration_variance(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test calcul de l'écart de durée."""
        # Avant réalisation
        assert scheduled_intervention.duration_variance_minutes is None

        # Réaliser l'intervention (plus long que prévu)
        scheduled_intervention.start(actual_start=time(8, 0))
        scheduled_intervention.complete(actual_end=time(9, 0))  # 60 min au lieu de 45
        db_session.flush()

        # Écart = 60 - 45 = +15 minutes
        assert scheduled_intervention.duration_variance_minutes == 15

    def test_intervention_effective_duration(self, db_session: Session, scheduled_intervention: ScheduledIntervention):
        """Test durée effective."""
        # Avant réalisation
        assert scheduled_intervention.effective_duration_minutes is None

        # Réaliser l'intervention
        scheduled_intervention.start(actual_start=time(8, 0))
        scheduled_intervention.complete(actual_end=time(8, 40))
        db_session.flush()

        assert scheduled_intervention.effective_duration_minutes == 40

    def test_intervention_link_to_coordination_entry(
            self,
            db_session: Session,
            tenant,
            scheduled_intervention: ScheduledIntervention,
            patient: Patient,
            user_infirmier: User
    ):
        """Test liaison avec une entrée de coordination."""
        # Créer une entrée de coordination
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.HYGIENE.value,  # Utiliser .value
            intervention_type="Toilette",
            description="Aide à la toilette réalisée",
            performed_at=datetime.now(timezone.utc),
            duration_minutes=45
        )
        db_session.add(entry)
        db_session.flush()

        # Lier l'intervention
        scheduled_intervention.link_to_coordination_entry(entry)
        db_session.flush()

        assert scheduled_intervention.coordination_entry_id == entry.id
        assert scheduled_intervention.coordination_entry == entry

    def test_intervention_cannot_start_completed(self, db_session: Session,
                                                 scheduled_intervention: ScheduledIntervention):
        """Test qu'une intervention terminée ne peut pas être démarrée."""
        scheduled_intervention.start(actual_start=time(8, 0))
        scheduled_intervention.complete(actual_end=time(8, 45))
        db_session.flush()

        with pytest.raises(ValueError):
            scheduled_intervention.start()

    def test_intervention_cannot_cancel_completed(self, db_session: Session,
                                                  scheduled_intervention: ScheduledIntervention):
        """Test qu'une intervention terminée ne peut pas être annulée."""
        scheduled_intervention.start(actual_start=time(8, 0))
        scheduled_intervention.complete(actual_end=time(8, 45))
        db_session.flush()

        with pytest.raises(ValueError):
            scheduled_intervention.cancel(reason="Test")

    def test_intervention_cannot_complete_not_started(self, db_session: Session,
                                                      scheduled_intervention: ScheduledIntervention):
        """Test qu'une intervention non démarrée ne peut pas être terminée."""
        with pytest.raises(ValueError):
            scheduled_intervention.complete()

    def test_intervention_str(self, scheduled_intervention: ScheduledIntervention):
        """Test représentation string."""
        result = str(scheduled_intervention)
        assert "08:00" in result
        assert "SCHEDULED" in result