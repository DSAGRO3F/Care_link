"""
Services métier pour le module Coordination.

Contient la logique CRUD pour :
- CoordinationEntryService
- ScheduledInterventionService

Version multi-tenant : toutes les requêtes filtrent par tenant_id.
"""
from typing import Optional, List, Tuple
from datetime import datetime, timezone, date

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload

from app.models.coordination.coordination_entry import CoordinationEntry
from app.models.coordination.scheduled_intervention import ScheduledIntervention
from app.models.patient.patient import Patient
from app.models.user.user import User
from app.models.careplan.care_plan_service import CarePlanService
from app.models.enums import InterventionStatus

from app.api.v1.coordination.schemas import (
    CoordinationEntryCreate, CoordinationEntryUpdate, CoordinationEntryFilters,
    ScheduledInterventionCreate, ScheduledInterventionUpdate, ScheduledInterventionFilters,
    InterventionStart, InterventionComplete, InterventionCancel, InterventionReschedule,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class CoordinationEntryNotFoundError(Exception):
    """Entrée de coordination non trouvée."""
    pass


class ScheduledInterventionNotFoundError(Exception):
    """Intervention planifiée non trouvée."""
    pass


class PatientNotFoundError(Exception):
    """Patient non trouvé."""
    pass


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""
    pass


class CarePlanServiceNotFoundError(Exception):
    """Service de plan non trouvé."""
    pass


class InterventionStatusError(Exception):
    """Erreur de statut d'intervention."""
    pass


class EntryAlreadyDeletedError(Exception):
    """Entrée déjà supprimée."""
    pass


# =============================================================================
# COORDINATION ENTRY SERVICE
# =============================================================================

class CoordinationEntryService:
    """
    Service pour la gestion du carnet de coordination.

    Version multi-tenant : toutes les requêtes filtrent par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec la session DB et le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant pour le filtrage multi-tenant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant_id."""
        return select(CoordinationEntry).where(CoordinationEntry.tenant_id == self.tenant_id)

    def _verify_patient_belongs_to_tenant(self, patient_id: int) -> Patient:
        """
        Vérifie qu'un patient appartient au tenant.

        Args:
            patient_id: ID du patient à vérifier

        Returns:
            Patient: Le patient si il appartient au tenant

        Raises:
            PatientNotFoundError: Si le patient n'existe pas ou n'appartient pas au tenant
        """
        patient_query = select(Patient).where(
            Patient.id == patient_id,
            Patient.tenant_id == self.tenant_id
        )
        patient = self.db.execute(patient_query).scalar_one_or_none()
        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            filters: Optional[CoordinationEntryFilters] = None,
    ) -> Tuple[List[CoordinationEntry], int]:
        """Liste les entrées de coordination avec pagination et filtres."""
        query = self._base_query()

        # Par défaut, exclure les supprimées
        if not filters or not filters.include_deleted:
            query = query.where(CoordinationEntry.deleted_at.is_(None))

        if filters:
            if filters.patient_id:
                query = query.where(CoordinationEntry.patient_id == filters.patient_id)

            if filters.user_id:
                query = query.where(CoordinationEntry.user_id == filters.user_id)

            if filters.category:
                query = query.where(CoordinationEntry.category == filters.category.upper())

            if filters.date_from:
                query = query.where(CoordinationEntry.performed_at >= filters.date_from)

            if filters.date_to:
                query = query.where(CoordinationEntry.performed_at <= filters.date_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri par date d'intervention décroissante
        query = query.order_by(CoordinationEntry.performed_at.desc())

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, entry_id: int) -> CoordinationEntry:
        """Récupère une entrée par son ID."""
        query = self._base_query().where(CoordinationEntry.id == entry_id)
        entry = self.db.execute(query).scalar_one_or_none()
        if not entry:
            raise CoordinationEntryNotFoundError(f"Entrée {entry_id} non trouvée")
        return entry

    def get_for_patient(
            self,
            patient_id: int,
            limit: int = 50,
            include_deleted: bool = False,
    ) -> List[CoordinationEntry]:
        """Récupère les entrées d'un patient."""
        # Vérifier que le patient appartient au tenant
        self._verify_patient_belongs_to_tenant(patient_id)

        query = self._base_query().where(
            CoordinationEntry.patient_id == patient_id
        )

        if not include_deleted:
            query = query.where(CoordinationEntry.deleted_at.is_(None))

        query = query.order_by(CoordinationEntry.performed_at.desc()).limit(limit)
        return list(self.db.execute(query).scalars().all())

    def create(
            self,
            data: CoordinationEntryCreate,
            user_id: int,
    ) -> CoordinationEntry:
        """Crée une nouvelle entrée de coordination."""
        # Vérifier que le patient existe et appartient au tenant
        self._verify_patient_belongs_to_tenant(data.patient_id)

        entry = CoordinationEntry(
            tenant_id=self.tenant_id,
            patient_id=data.patient_id,
            user_id=user_id,
            category=data.category,
            intervention_type=data.intervention_type,
            description=data.description,
            observations=data.observations,
            next_actions=data.next_actions,
            performed_at=data.performed_at,
            duration_minutes=data.duration_minutes,
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def update(
            self,
            entry_id: int,
            data: CoordinationEntryUpdate,
    ) -> CoordinationEntry:
        """Met à jour une entrée de coordination."""
        entry = self.get_by_id(entry_id)

        if entry.is_deleted:
            raise EntryAlreadyDeletedError("Impossible de modifier une entrée supprimée")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entry, field, value)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry_id: int) -> None:
        """Supprime une entrée (soft delete)."""
        entry = self.get_by_id(entry_id)

        if entry.is_deleted:
            raise EntryAlreadyDeletedError("Entrée déjà supprimée")

        entry.soft_delete()
        self.db.commit()

    def restore(self, entry_id: int) -> CoordinationEntry:
        """Restaure une entrée supprimée."""
        entry = self.get_by_id(entry_id)

        if not entry.is_deleted:
            raise EntryAlreadyDeletedError("L'entrée n'est pas supprimée")

        entry.restore()
        self.db.commit()
        self.db.refresh(entry)
        return entry


# =============================================================================
# SCHEDULED INTERVENTION SERVICE
# =============================================================================

class ScheduledInterventionService:
    """
    Service pour la gestion des interventions planifiées.

    Version multi-tenant : toutes les requêtes filtrent par tenant_id.
    """

    def __init__(self, db: Session, tenant_id: int):
        """
        Initialise le service avec la session DB et le tenant_id.

        Args:
            db: Session SQLAlchemy
            tenant_id: ID du tenant pour le filtrage multi-tenant
        """
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        """Retourne une requête de base filtrée par tenant_id."""
        return select(ScheduledIntervention).where(ScheduledIntervention.tenant_id == self.tenant_id)

    def _verify_patient_belongs_to_tenant(self, patient_id: int) -> Patient:
        """Vérifie qu'un patient appartient au tenant."""
        patient_query = select(Patient).where(
            Patient.id == patient_id,
            Patient.tenant_id == self.tenant_id
        )
        patient = self.db.execute(patient_query).scalar_one_or_none()
        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        return patient

    def _verify_user_belongs_to_tenant(self, user_id: int) -> User:
        """Vérifie qu'un utilisateur appartient au tenant."""
        user_query = select(User).where(
            User.id == user_id,
            User.tenant_id == self.tenant_id
        )
        user = self.db.execute(user_query).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"Utilisateur {user_id} non trouvé")
        return user

    def _verify_care_plan_service_belongs_to_tenant(self, service_id: int) -> CarePlanService:
        """Vérifie qu'un service de plan appartient au tenant."""
        service_query = select(CarePlanService).where(
            CarePlanService.id == service_id,
            CarePlanService.tenant_id == self.tenant_id
        )
        service = self.db.execute(service_query).scalar_one_or_none()
        if not service:
            raise CarePlanServiceNotFoundError(f"Service de plan {service_id} non trouvé")
        return service

    def get_all(
            self,
            filters: Optional[ScheduledInterventionFilters] = None,
    ) -> List[ScheduledIntervention]:
        """Liste les interventions planifiées avec filtres."""
        query = self._base_query().options(
            selectinload(ScheduledIntervention.care_plan_service)
        )

        if filters:
            if filters.patient_id:
                query = query.where(ScheduledIntervention.patient_id == filters.patient_id)

            if filters.user_id:
                query = query.where(ScheduledIntervention.user_id == filters.user_id)

            if filters.care_plan_service_id:
                query = query.where(ScheduledIntervention.care_plan_service_id == filters.care_plan_service_id)

            if filters.date_from:
                query = query.where(ScheduledIntervention.scheduled_date >= filters.date_from)

            if filters.date_to:
                query = query.where(ScheduledIntervention.scheduled_date <= filters.date_to)

            if filters.status:
                query = query.where(ScheduledIntervention.status == InterventionStatus(filters.status.upper()))

        query = query.order_by(
            ScheduledIntervention.scheduled_date,
            ScheduledIntervention.scheduled_start_time,
        )

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, intervention_id: int) -> ScheduledIntervention:
        """Récupère une intervention par son ID."""
        query = self._base_query().where(
            ScheduledIntervention.id == intervention_id
        ).options(
            selectinload(ScheduledIntervention.care_plan_service)
        )
        intervention = self.db.execute(query).scalar_one_or_none()
        if not intervention:
            raise ScheduledInterventionNotFoundError(f"Intervention {intervention_id} non trouvée")
        return intervention

    def get_daily_planning(
            self,
            user_id: int,
            planning_date: date,
    ) -> List[ScheduledIntervention]:
        """Récupère le planning journalier d'un professionnel."""
        # Vérifier que l'utilisateur appartient au tenant
        self._verify_user_belongs_to_tenant(user_id)

        query = self._base_query().where(
            and_(
                ScheduledIntervention.user_id == user_id,
                ScheduledIntervention.scheduled_date == planning_date,
                ScheduledIntervention.status.not_in([
                    InterventionStatus.CANCELLED,
                    InterventionStatus.RESCHEDULED,
                ])
            )
        ).options(
            selectinload(ScheduledIntervention.care_plan_service)
        ).order_by(ScheduledIntervention.scheduled_start_time)

        return list(self.db.execute(query).scalars().all())

    def create(
            self,
            data: ScheduledInterventionCreate,
    ) -> ScheduledIntervention:
        """Crée une nouvelle intervention planifiée."""
        # Vérifier que le service du plan existe et appartient au tenant
        self._verify_care_plan_service_belongs_to_tenant(data.care_plan_service_id)

        # Vérifier que le patient existe et appartient au tenant
        self._verify_patient_belongs_to_tenant(data.patient_id)

        # Vérifier l'utilisateur si fourni
        if data.user_id:
            self._verify_user_belongs_to_tenant(data.user_id)

        intervention = ScheduledIntervention(
            tenant_id=self.tenant_id,
            care_plan_service_id=data.care_plan_service_id,
            patient_id=data.patient_id,
            user_id=data.user_id,
            scheduled_date=data.scheduled_date,
            scheduled_start_time=data.scheduled_start_time,
            scheduled_end_time=data.scheduled_end_time,
            status=InterventionStatus.SCHEDULED,
        )

        self.db.add(intervention)
        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def update(
            self,
            intervention_id: int,
            data: ScheduledInterventionUpdate,
    ) -> ScheduledIntervention:
        """Met à jour une intervention planifiée."""
        intervention = self.get_by_id(intervention_id)

        if intervention.is_terminal:
            raise InterventionStatusError(
                "Une intervention terminée ne peut pas être modifiée"
            )

        # Vérifier l'utilisateur si modifié
        if data.user_id is not None:
            if data.user_id != 0:  # 0 = désaffectation
                self._verify_user_belongs_to_tenant(data.user_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(intervention, field, value)

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def delete(self, intervention_id: int) -> None:
        """Supprime une intervention (seulement si pas encore démarrée)."""
        intervention = self.get_by_id(intervention_id)

        if not intervention.is_pending:
            raise InterventionStatusError(
                "Seule une intervention en attente peut être supprimée"
            )

        self.db.delete(intervention)
        self.db.commit()

    # === Actions de workflow ===

    def confirm(self, intervention_id: int) -> ScheduledIntervention:
        """Confirme une intervention."""
        intervention = self.get_by_id(intervention_id)

        try:
            intervention.confirm()
        except ValueError as e:
            raise InterventionStatusError(str(e))

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def start(
            self,
            intervention_id: int,
            data: Optional[InterventionStart] = None,
    ) -> ScheduledIntervention:
        """Démarre une intervention."""
        intervention = self.get_by_id(intervention_id)

        actual_start = data.actual_start_time if data else None

        try:
            intervention.start(actual_start)
        except ValueError as e:
            raise InterventionStatusError(str(e))

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def complete(
            self,
            intervention_id: int,
            data: Optional[InterventionComplete] = None,
    ) -> ScheduledIntervention:
        """Termine une intervention."""
        intervention = self.get_by_id(intervention_id)

        actual_end = data.actual_end_time if data else None
        notes = data.notes if data else None

        try:
            intervention.complete(actual_end, notes)
        except ValueError as e:
            raise InterventionStatusError(str(e))

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def cancel(
            self,
            intervention_id: int,
            data: InterventionCancel,
    ) -> ScheduledIntervention:
        """Annule une intervention."""
        intervention = self.get_by_id(intervention_id)

        try:
            intervention.cancel(data.reason)
        except ValueError as e:
            raise InterventionStatusError(str(e))

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def mark_missed(
            self,
            intervention_id: int,
            reason: Optional[str] = None,
    ) -> ScheduledIntervention:
        """Marque une intervention comme manquée."""
        intervention = self.get_by_id(intervention_id)

        try:
            intervention.mark_missed(reason)
        except ValueError as e:
            raise InterventionStatusError(str(e))

        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def reschedule(
            self,
            intervention_id: int,
            data: InterventionReschedule,
    ) -> ScheduledIntervention:
        """Reprogramme une intervention."""
        intervention = self.get_by_id(intervention_id)

        if intervention.is_terminal:
            raise InterventionStatusError(
                "Une intervention terminée ne peut pas être reprogrammée"
            )

        # Créer la nouvelle intervention avec le tenant_id
        new_intervention = ScheduledIntervention(
            tenant_id=self.tenant_id,
            care_plan_service_id=intervention.care_plan_service_id,
            patient_id=intervention.patient_id,
            user_id=intervention.user_id,
            scheduled_date=data.new_date,
            scheduled_start_time=data.new_start_time,
            scheduled_end_time=data.new_end_time,
            status=InterventionStatus.SCHEDULED,
            rescheduled_from_id=intervention.id,
        )

        self.db.add(new_intervention)
        self.db.flush()

        # Marquer l'ancienne comme reprogrammée
        intervention.status = InterventionStatus.RESCHEDULED
        intervention.rescheduled_to_id = new_intervention.id
        if data.reason:
            intervention.cancellation_reason = data.reason

        self.db.commit()
        self.db.refresh(new_intervention)
        return new_intervention