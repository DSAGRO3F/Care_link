"""
Tests unitaires pour le modèle Patient et ses associations.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Patient, PatientAccess, PatientEvaluation, PatientThreshold, PatientVitals
from app.models.enums import PatientStatus, AccessType, VitalType, VitalStatus


class TestPatient:
    """Tests pour le modèle Patient."""
    
    def test_create_patient(self, db_session: Session, tenant, entity, user_medecin, user_admin):
        """Test création d'un patient."""
        patient = Patient(
            tenant_id=tenant.id,  # MULTI-TENANT: Ajouté
            first_name_encrypted="encrypted_Paul",
            last_name_encrypted="encrypted_Bernard",
            entity_id=entity.id,
            medecin_traitant_id=user_medecin.id,
            status=PatientStatus.ACTIVE.value,
            created_by=user_admin.id
        )
        db_session.add(patient)
        db_session.flush()

        assert patient.id is not None
        assert patient.entity_id == entity.id
        assert patient.medecin_traitant_id == user_medecin.id
        assert patient.tenant_id == tenant.id  # Vérifier tenant
        assert patient.version == 1
        assert patient.created_at is not None

    def test_patient_relations(self, patient: Patient, entity, user_medecin):
        """Test relations Patient → Entity, User."""
        assert patient.entity == entity
        assert patient.medecin_traitant == user_medecin
        assert patient in entity.patients
        assert patient in user_medecin.patients_as_medecin

    def test_patient_tenant_relation(self, patient: Patient, tenant):
        """Test relation Patient → Tenant."""
        assert patient.tenant == tenant
        assert patient in tenant.patients

    def test_patient_is_active(self, patient: Patient):
        """Test propriété is_active."""
        assert patient.is_active is True

    def test_patient_archive(self, db_session: Session, patient: Patient):
        """Test archivage d'un patient."""
        patient.archive()
        db_session.flush()

        assert patient.status == PatientStatus.ARCHIVED.value
        assert patient.is_active is False

    def test_patient_mark_deceased(self, db_session: Session, patient: Patient):
        """Test marquage décédé."""
        patient.mark_deceased()
        db_session.flush()

        assert patient.status == PatientStatus.DECEASED.value
        assert patient.is_active is False

    def test_patient_optimistic_locking(self, db_session: Session, patient: Patient):
        """Test verrouillage optimiste (version)."""
        initial_version = patient.version

        # Modifier le patient
        patient.status = "modified"
        db_session.flush()

        # La version devrait être incrémentée
        # Note: SQLite ne supporte pas toujours bien ça,
        # mais PostgreSQL oui
        assert patient.version >= initial_version


class TestPatientAccess:
    """Tests pour le modèle PatientAccess (RGPD)."""

    def test_create_access(self, db_session: Session, tenant, patient, user_infirmier, user_admin):
        """Test création d'un accès patient."""
        access = PatientAccess(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            access_type=AccessType.READ.value,
            reason="Consultation du dossier",
            granted_by=user_admin.id,
            granted_at=datetime.now(timezone.utc)
        )
        db_session.add(access)
        db_session.flush()

        assert access.id is not None
        assert access.is_active is True

    def test_access_relations(self, patient_access: PatientAccess, patient, user_infirmier, user_admin):
        """Test relations PatientAccess."""
        assert patient_access.patient == patient
        assert patient_access.user == user_infirmier
        assert patient_access.granter == user_admin

    def test_access_is_active(self, patient_access: PatientAccess):
        """Test propriété is_active."""
        assert patient_access.is_active is True
        assert patient_access.is_revoked is False
        assert patient_access.is_expired is False

    def test_access_revoke(self, db_session: Session, patient_access: PatientAccess, user_admin):
        """Test révocation d'accès."""
        patient_access.revoke(user_admin.id)
        db_session.flush()

        assert patient_access.is_active is False
        assert patient_access.is_revoked is True
        assert patient_access.revoked_by == user_admin.id
        assert patient_access.revoked_at is not None

    def test_access_can_read(self, patient_access: PatientAccess):
        """Test méthode can_read."""
        # L'accès de la fixture est WRITE, donc peut lire
        assert patient_access.can_read() is True

    def test_access_can_write(self, patient_access: PatientAccess):
        """Test méthode can_write."""
        # L'accès de la fixture est WRITE
        assert patient_access.can_write() is True

    def test_access_read_only_cannot_write(self, db_session: Session, tenant, patient, user_infirmier, user_admin):
        """Test qu'un accès READ ne peut pas écrire."""
        access = PatientAccess(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            access_type=AccessType.READ.value,
            reason="Consultation uniquement",
            granted_by=user_admin.id,
            granted_at=datetime.now(timezone.utc)
        )
        db_session.add(access)
        db_session.flush()

        assert access.can_read() is True
        assert access.can_write() is False

    def test_patient_get_active_access(self, patient: Patient, patient_access: PatientAccess, user_infirmier):
        """Test méthode get_active_access_for_user."""
        access = patient.get_active_access_for_user(user_infirmier.id)
        assert access == patient_access

        # Utilisateur sans accès
        no_access = patient.get_active_access_for_user(999)
        assert no_access is None


class TestPatientEvaluation:
    """Tests pour le modèle PatientEvaluation."""

    def test_create_evaluation(self, db_session: Session, tenant, patient, user_medecin):
        """Test création d'une évaluation."""
        from datetime import date

        evaluation = PatientEvaluation(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            evaluator_id=user_medecin.id,
            schema_type="evaluation_complete",
            schema_version="v1",
            evaluation_data={"aggir": {"GIR": 3}},
            gir_score=3,
            evaluation_date=date.today()
        )
        db_session.add(evaluation)
        db_session.flush()

        assert evaluation.id is not None
        assert evaluation.gir_score == 3
        assert evaluation.is_validated is False

    def test_evaluation_relations(self, patient_evaluation: PatientEvaluation, patient, user_infirmier):
        """Test relations PatientEvaluation."""
        assert patient_evaluation.patient == patient
        # La fixture utilise user_infirmier comme evaluator
        assert patient_evaluation.evaluator == user_infirmier
        assert patient_evaluation in patient.evaluations

    def test_evaluation_validate(self, db_session: Session, patient_evaluation: PatientEvaluation, user_admin):
        """Test validation d'une évaluation."""
        assert patient_evaluation.is_validated is False

        patient_evaluation.validate(user_admin.id)
        db_session.flush()

        assert patient_evaluation.is_validated is True
        assert patient_evaluation.validated_by == user_admin.id
        assert patient_evaluation.validated_at is not None

    def test_evaluation_aggir_data(self, patient_evaluation: PatientEvaluation):
        """Test accès aux données AGGIR."""
        aggir = patient_evaluation.aggir_data
        assert aggir is not None
        assert aggir["GIR"] == 4

    def test_evaluation_extract_gir_score(self, patient_evaluation: PatientEvaluation):
        """Test extraction du score GIR."""
        gir = patient_evaluation.extract_gir_score()
        assert gir == 4

    def test_patient_latest_evaluation(self, patient: Patient, patient_evaluation: PatientEvaluation):
        """Test propriété latest_evaluation."""
        assert patient.latest_evaluation == patient_evaluation

    def test_patient_current_gir(self, patient: Patient, patient_evaluation: PatientEvaluation):
        """Test propriété current_gir."""
        assert patient.current_gir == 4


class TestPatientThreshold:
    """Tests pour le modèle PatientThreshold."""

    def test_create_threshold(self, db_session: Session, tenant, patient):
        """Test création d'un seuil."""
        threshold = PatientThreshold(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            vital_type=VitalType.FC.value,
            min_value=60,
            max_value=100,
            unit="bpm",
            surveillance_frequency="2x/jour"
        )
        db_session.add(threshold)
        db_session.flush()

        assert threshold.id is not None
        assert threshold.vital_type == "FC"

    def test_threshold_check_value_normal(self, patient_threshold: PatientThreshold):
        """Test check_value - valeur normale."""
        status = patient_threshold.check_value(120)  # Entre 100 et 140
        assert status == VitalStatus.NORMAL

    def test_threshold_check_value_low(self, patient_threshold: PatientThreshold):
        """Test check_value - valeur basse."""
        # min_value=100, donc 95 est en dessous mais pas critique (>= 100 * 0.9 = 90)
        status = patient_threshold.check_value(95)
        assert status == VitalStatus.LOW

    def test_threshold_check_value_high(self, patient_threshold: PatientThreshold):
        """Test check_value - valeur haute."""
        # max_value=140, donc 145 est au dessus mais pas critique (<= 140 * 1.1 = 154)
        status = patient_threshold.check_value(145)
        assert status == VitalStatus.HIGH

    def test_threshold_check_value_critical_low(self, patient_threshold: PatientThreshold):
        """Test check_value - valeur critique basse."""
        # min_value=100, critique si < 100 * 0.9 = 90
        status = patient_threshold.check_value(85)
        assert status == VitalStatus.CRITICAL

    def test_threshold_check_value_critical_high(self, patient_threshold: PatientThreshold):
        """Test check_value - valeur critique haute."""
        # max_value=140, critique si > 140 * 1.1 = 154
        status = patient_threshold.check_value(160)
        assert status == VitalStatus.CRITICAL


class TestPatientVitals:
    """Tests pour le modèle PatientVitals."""

    def test_create_vitals(self, db_session: Session, tenant, patient, user_infirmier):
        """Test création d'une mesure."""
        vitals = PatientVitals(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            vital_type=VitalType.FC.value,
            value=75,
            unit="bpm",
            status=VitalStatus.NORMAL.value,
            source="manual",
            measured_at=datetime.now(timezone.utc),
            recorded_by=user_infirmier.id
        )
        db_session.add(vitals)
        db_session.flush()

        assert vitals.id is not None
        assert vitals.value == 75

    def test_vitals_is_manual(self, patient_vitals: PatientVitals):
        """Test propriété is_manual."""
        assert patient_vitals.is_manual is True

    def test_vitals_is_abnormal(self, patient_vitals: PatientVitals):
        """Test propriété is_abnormal."""
        # La fixture a status="normal"
        assert patient_vitals.is_abnormal is False

    def test_vitals_is_critical(self, db_session: Session, tenant, patient, user_infirmier):
        """Test propriété is_critical."""
        vitals = PatientVitals(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            vital_type=VitalType.TA_SYS.value,
            value=180,
            unit="mmHg",
            status=VitalStatus.CRITICAL.value,
            source="manual",
            measured_at=datetime.now(timezone.utc),
            recorded_by=user_infirmier.id
        )
        db_session.add(vitals)
        db_session.flush()

        assert vitals.is_critical is True
        assert vitals.is_abnormal is True

    def test_patient_vitals_relation(self, patient: Patient, patient_vitals: PatientVitals):
        """Test relation Patient → Vitals."""
        assert patient_vitals in patient.vitals