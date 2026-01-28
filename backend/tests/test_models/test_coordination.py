"""
Tests unitaires pour les modèles PatientDocument et CoordinationEntry.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models import (
    PatientDocument,
    CoordinationEntry,
    Patient,
    User,
    PatientEvaluation,
    DocumentType,
    DocumentFormat,
    CoordinationCategory,
)


# ============================================================================
# TESTS PatientDocument
# ============================================================================

class TestPatientDocument:
    """Tests pour le modèle PatientDocument."""

    def test_create_document(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test création d'un document."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPA.value,
            title="PPA - Monsieur Dupont",
            description="Plan personnalisé d'accompagnement",
            file_path="/documents/patients/1/ppa_2024_12.pdf",
            file_format=DocumentFormat.PDF.value,
            file_size_bytes=125000,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.id is not None
        assert doc.document_type == "PPA"
        assert doc.title == "PPA - Monsieur Dupont"
        # file_format peut être en minuscules selon l'implémentation
        assert doc.file_format.upper() == "PDF"
        assert doc.file_size_bytes == 125000

    def test_document_patient_relation(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test relation document → patient."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPCS.value,
            title="PPCS - Coordination",
            file_path="/documents/patients/1/ppcs_2024_12.docx",
            file_format=DocumentFormat.DOCX.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.patient is not None
        assert doc.patient.id == patient.id

    def test_document_generator_relation(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test relation document → générateur (user)."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.RECOMMENDATION.value,
            title="Recommandations post-chute",
            file_path="/documents/patients/1/reco_chute.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
            generation_prompt="Patient a fait une chute, quelles recommandations ?",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.generator is not None
        assert doc.generator.id == user_medecin.id

    def test_document_with_source_evaluation(
        self, db_session: Session, tenant, patient: Patient, user_medecin: User, patient_evaluation: PatientEvaluation
    ):
        """Test document lié à une évaluation source."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPA.value,
            title="PPA basé sur évaluation",
            file_path="/documents/patients/1/ppa_eval.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
            source_evaluation_id=patient_evaluation.id,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.source_evaluation is not None
        assert doc.source_evaluation.id == patient_evaluation.id

    def test_document_with_generation_context(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test document avec contexte de génération JSON."""
        context = {
            "patient_name": "Dupont Jean",
            "gir_score": 4,
            "pathologies": ["diabète", "hypertension"],
        }
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.RECOMMENDATION.value,
            title="Recommandations personnalisées",
            file_path="/documents/patients/1/reco.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
            generation_context=context,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        assert doc.generation_context is not None
        assert doc.generation_context["gir_score"] == 4
        assert "diabète" in doc.generation_context["pathologies"]

    def test_document_is_ppa(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test propriété is_ppa."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPA.value,
            title="PPA Test",
            file_path="/documents/test.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.is_ppa is True
        assert doc.is_ppcs is False
        assert doc.is_recommendation is False

    def test_document_is_ppcs(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test propriété is_ppcs."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPCS.value,
            title="PPCS Test",
            file_path="/documents/test.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.is_ppa is False
        assert doc.is_ppcs is True
        assert doc.is_recommendation is False

    def test_document_is_recommendation(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test propriété is_recommendation."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.RECOMMENDATION.value,
            title="Recommandation Test",
            file_path="/documents/test.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.is_ppa is False
        assert doc.is_ppcs is False
        assert doc.is_recommendation is True

    def test_document_file_extension(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test propriété file_extension."""
        doc_pdf = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPA.value,
            title="Doc PDF",
            file_path="/documents/test.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        doc_docx = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPCS.value,
            title="Doc DOCX",
            file_path="/documents/test.docx",
            file_format=DocumentFormat.DOCX.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add_all([doc_pdf, doc_docx])
        db_session.commit()

        assert doc_pdf.file_extension == ".pdf"
        assert doc_docx.file_extension == ".docx"

    def test_document_str(self, db_session: Session, tenant, patient: Patient, user_medecin: User):
        """Test représentation string du document."""
        doc = PatientDocument(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            document_type=DocumentType.PPA.value,
            title="PPA - Test String",
            file_path="/documents/test.pdf",
            file_format=DocumentFormat.PDF.value,
            generated_by=user_medecin.id,
            generated_at=datetime.now(timezone.utc),
        )
        db_session.add(doc)
        db_session.commit()

        str_repr = str(doc)
        assert "PPA" in str_repr
        assert "PPA - Test String" in str_repr


# ============================================================================
# TESTS CoordinationEntry
# ============================================================================

class TestCoordinationEntry:
    """Tests pour le modèle CoordinationEntry (carnet de coordination)."""

    def test_create_entry(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test création d'une entrée de coordination."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.SOINS.value,
            intervention_type="Pansement",
            description="Réfection du pansement au pied droit",
            performed_at=datetime.now(timezone.utc),
            duration_minutes=20,
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.id is not None
        assert entry.category == "SOINS"
        assert entry.intervention_type == "Pansement"
        assert entry.duration_minutes == 20

    def test_entry_patient_relation(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test relation entrée → patient."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.HYGIENE.value,
            intervention_type="Toilette",
            description="Toilette complète au lit",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.patient is not None
        assert entry.patient.id == patient.id

    def test_entry_user_relation(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test relation entrée → utilisateur."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.ALIMENTATION.value,  # CORRIGÉ: était REPAS
            intervention_type="Aide au repas",
            description="Aide au déjeuner, bon appétit",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.user is not None
        assert entry.user.id == user_infirmier.id

    def test_entry_with_observations(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test entrée avec observations."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.OBSERVATION.value,  # CORRIGÉ: était AUTRE
            intervention_type="Surveillance",
            description="Visite de contrôle",
            observations="Patient fatigué, légère pâleur",
            next_actions="Surveiller tension demain",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        assert entry.observations == "Patient fatigué, légère pâleur"
        assert entry.next_actions == "Surveiller tension demain"

    def test_entry_is_active(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test propriété is_active (non supprimé)."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.SOINS.value,
            intervention_type="Injection",
            description="Injection insuline",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.is_active is True
        assert entry.is_deleted is False

    def test_entry_soft_delete(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test suppression logique (soft delete)."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.SOINS.value,
            intervention_type="Pansement",
            description="Entrée à supprimer",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()

        # Soft delete
        entry.soft_delete()
        db_session.commit()
        db_session.refresh(entry)

        assert entry.is_active is False
        assert entry.is_deleted is True
        assert entry.deleted_at is not None

    def test_entry_restore(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test restauration d'une entrée supprimée."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.SOINS.value,
            intervention_type="Pansement",
            description="Entrée à restaurer",
            performed_at=datetime.now(timezone.utc),
        )
        db_session.add(entry)
        db_session.commit()

        # Soft delete puis restore
        entry.soft_delete()
        db_session.commit()
        assert entry.is_deleted is True

        entry.restore()
        db_session.commit()
        db_session.refresh(entry)

        assert entry.is_active is True
        assert entry.is_deleted is False
        assert entry.deleted_at is None

    def test_entry_is_recent_true(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test propriété is_recent (moins de 24h)."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.HYGIENE.value,
            intervention_type="Toilette",
            description="Toilette récente",
            performed_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.is_recent is True

    def test_entry_is_recent_false(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test propriété is_recent (plus de 24h)."""
        entry = CoordinationEntry(
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            patient_id=patient.id,
            user_id=user_infirmier.id,
            category=CoordinationCategory.HYGIENE.value,
            intervention_type="Toilette",
            description="Toilette ancienne",
            performed_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        db_session.add(entry)
        db_session.commit()

        assert entry.is_recent is False

    def test_entry_all_categories(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test toutes les catégories d'intervention."""
        categories = [
            (CoordinationCategory.SOINS, "Injection"),
            (CoordinationCategory.HYGIENE, "Toilette"),
            (CoordinationCategory.ALIMENTATION, "Aide au repas"),  # CORRIGÉ: était REPAS
            (CoordinationCategory.MOBILITE, "Transfert lit-fauteuil"),
            (CoordinationCategory.MEDICAL, "Visite médecin"),
            (CoordinationCategory.SOCIAL, "Visite famille"),
            (CoordinationCategory.ADMINISTRATIF, "Appel mutuelle"),
            (CoordinationCategory.OBSERVATION, "Surveillance"),  # CORRIGÉ: était AUTRE
        ]

        for cat, intervention in categories:
            entry = CoordinationEntry(
                tenant_id=tenant.id,  # MULTI-TENANT v4.3
                patient_id=patient.id,
                user_id=user_infirmier.id,
                category=cat.value,
                intervention_type=intervention,
                description=f"Test {cat.value}",
                performed_at=datetime.now(timezone.utc),
            )
            db_session.add(entry)

        db_session.commit()

        # Vérifier qu'on a bien 8 entrées
        entries = db_session.query(CoordinationEntry).filter_by(patient_id=patient.id).all()
        assert len(entries) == 8

    def test_patient_coordination_entries_relation(self, db_session: Session, tenant, patient: Patient, user_infirmier: User):
        """Test relation patient → coordination_entries."""
        # Créer plusieurs entrées
        for i in range(3):
            entry = CoordinationEntry(
                tenant_id=tenant.id,  # MULTI-TENANT v4.3
                patient_id=patient.id,
                user_id=user_infirmier.id,
                category=CoordinationCategory.SOINS.value,
                intervention_type=f"Soin {i+1}",
                description=f"Description {i+1}",
                performed_at=datetime.now(timezone.utc) - timedelta(hours=i),
            )
            db_session.add(entry)

        db_session.commit()
        db_session.refresh(patient)

        assert len(patient.coordination_entries) == 3