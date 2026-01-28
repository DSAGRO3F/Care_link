"""
Services métier pour le module CarePlan.

Contient la logique CRUD pour :
- CarePlanCRUDService (le service métier)
- CarePlanServiceCRUDService (services du plan)

Version multi-tenant : toutes les requêtes filtrent par tenant_id.
"""
from typing import Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.api.v1.careplan.schemas import (
    CarePlanCreate, CarePlanUpdate, CarePlanFilters,
    CarePlanServiceCreate, CarePlanServiceUpdate, ServiceAssignment,
)
from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService
from app.models.catalog.service_template import ServiceTemplate
from app.models.enums import CarePlanStatus
from app.models.organization.entity import Entity
from app.models.patient.patient import Patient
from app.models.user.user import User


# =============================================================================
# EXCEPTIONS
# =============================================================================

class CarePlanNotFoundError(Exception):
    """Plan d'aide non trouvé."""
    pass


class CarePlanServiceNotFoundError(Exception):
    """Service de plan non trouvé."""
    pass


class PatientNotFoundError(Exception):
    """Patient non trouvé."""
    pass


class EntityNotFoundError(Exception):
    """Entité non trouvée."""
    pass


class ServiceTemplateNotFoundError(Exception):
    """Service template non trouvé."""
    pass


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""
    pass


class CarePlanNotEditableError(Exception):
    """Le plan n'est pas modifiable."""
    pass


class CarePlanStatusError(Exception):
    """Erreur de statut du plan."""
    pass


class AssignmentStatusError(Exception):
    """Erreur de statut d'affectation."""
    pass


class DuplicateReferenceError(Exception):
    """Numéro de référence déjà existant."""
    pass


# =============================================================================
# CARE PLAN SERVICE (le service métier)
# =============================================================================

class CarePlanCRUDService:
    """
    Service pour la gestion des plans d'aide.

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
        return select(CarePlan).where(CarePlan.tenant_id == self.tenant_id)

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            filters: Optional[CarePlanFilters] = None,
    ) -> Tuple[List[CarePlan], int]:
        """Liste les plans d'aide avec pagination et filtres."""
        query = self._base_query().options(
            selectinload(CarePlan.services)
        )

        if filters:
            if filters.patient_id:
                query = query.where(CarePlan.patient_id == filters.patient_id)

            if filters.entity_id:
                query = query.where(CarePlan.entity_id == filters.entity_id)

            if filters.status:
                query = query.where(CarePlan.status == CarePlanStatus(filters.status.upper()))

            if filters.start_date_from:
                query = query.where(CarePlan.start_date >= filters.start_date_from)

            if filters.start_date_to:
                query = query.where(CarePlan.start_date <= filters.start_date_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(CarePlan, sort_by, CarePlan.created_at)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().unique().all()

        # Filtrer par is_fully_assigned si demandé (après chargement)
        if filters and filters.is_fully_assigned is not None:
            items = [p for p in items if p.is_fully_assigned == filters.is_fully_assigned]
            total = len(items)

        return list(items), total

    def get_by_id(self, plan_id: int) -> CarePlan:
        """Récupère un plan d'aide par son ID."""
        query = self._base_query().where(CarePlan.id == plan_id).options(
            selectinload(CarePlan.services).selectinload(CarePlanService.service_template)
        )
        plan = self.db.execute(query).scalar_one_or_none()
        if not plan:
            raise CarePlanNotFoundError(f"Plan d'aide {plan_id} non trouvé")
        return plan

    def get_by_patient(self, patient_id: int) -> List[CarePlan]:
        """Récupère tous les plans d'un patient."""
        query = self._base_query().where(
            CarePlan.patient_id == patient_id
        ).options(
            selectinload(CarePlan.services)
        ).order_by(CarePlan.created_at.desc())

        return list(self.db.execute(query).scalars().unique().all())

    def create(
            self,
            data: CarePlanCreate,
            created_by: int,
    ) -> CarePlan:
        """Crée un nouveau plan d'aide."""
        # Vérifier que le patient existe et appartient au tenant
        patient_query = select(Patient).where(
            Patient.id == data.patient_id,
            Patient.tenant_id == self.tenant_id
        )
        patient = self.db.execute(patient_query).scalar_one_or_none()
        if not patient:
            raise PatientNotFoundError(f"Patient {data.patient_id} non trouvé")

        # Vérifier que l'entité existe et appartient au tenant
        entity_query = select(Entity).where(
            Entity.id == data.entity_id,
            Entity.tenant_id == self.tenant_id
        )
        entity = self.db.execute(entity_query).scalar_one_or_none()
        if not entity:
            raise EntityNotFoundError(f"Entité {data.entity_id} non trouvée")

        # Vérifier unicité du numéro de référence dans le tenant
        if data.reference_number:
            existing = self.db.execute(
                self._base_query().where(CarePlan.reference_number == data.reference_number)
            ).scalar_one_or_none()
            if existing:
                raise DuplicateReferenceError(
                    f"Le numéro de référence '{data.reference_number}' existe déjà"
                )

        # Créer le plan avec le tenant_id
        plan = CarePlan(
            tenant_id=self.tenant_id,
            patient_id=data.patient_id,
            entity_id=data.entity_id,
            source_evaluation_id=data.source_evaluation_id,
            title=data.title,
            reference_number=data.reference_number,
            start_date=data.start_date,
            end_date=data.end_date,
            total_hours_week=data.total_hours_week,
            gir_at_creation=data.gir_at_creation,
            notes=data.notes,
            status=CarePlanStatus.DRAFT,
            created_by=created_by,
        )

        self.db.add(plan)
        self.db.flush()

        # Ajouter les services initiaux si fournis
        if data.services:
            for service_data in data.services:
                # ServiceTemplate est global (pas de tenant_id)
                template = self.db.get(ServiceTemplate, service_data.service_template_id)
                if not template:
                    raise ServiceTemplateNotFoundError(
                        f"Service template {service_data.service_template_id} non trouvé"
                    )

                service = CarePlanService(
                    tenant_id=self.tenant_id,
                    care_plan_id=plan.id,
                    service_template_id=service_data.service_template_id,
                    quantity_per_week=service_data.quantity_per_week,
                    frequency_type=service_data.frequency_type,
                    frequency_days=service_data.frequency_days,
                    preferred_time_start=service_data.preferred_time_start,
                    preferred_time_end=service_data.preferred_time_end,
                    duration_minutes=service_data.duration_minutes,
                    priority=service_data.priority,
                    special_instructions=service_data.special_instructions,
                )
                self.db.add(service)

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update(self, plan_id: int, data: CarePlanUpdate) -> CarePlan:
        """Met à jour un plan d'aide."""
        plan = self.get_by_id(plan_id)

        if not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        update_data = data.model_dump(exclude_unset=True)

        # Vérifier unicité du numéro de référence si modifié (dans le tenant)
        if "reference_number" in update_data and update_data["reference_number"]:
            existing = self.db.execute(
                self._base_query().where(
                    CarePlan.reference_number == update_data["reference_number"],
                    CarePlan.id != plan_id,
                )
            ).scalar_one_or_none()
            if existing:
                raise DuplicateReferenceError(
                    f"Le numéro de référence '{update_data['reference_number']}' existe déjà"
                )

        for field, value in update_data.items():
            setattr(plan, field, value)

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def delete(self, plan_id: int) -> None:
        """Supprime un plan d'aide (seulement si en brouillon)."""
        plan = self.get_by_id(plan_id)

        if plan.status != CarePlanStatus.DRAFT:
            raise CarePlanStatusError(
                "Seul un plan en brouillon peut être supprimé"
            )

        self.db.delete(plan)
        self.db.commit()

    # === Actions de workflow ===

    def submit_for_validation(self, plan_id: int) -> CarePlan:
        """Soumet le plan pour validation."""
        plan = self.get_by_id(plan_id)

        try:
            plan.submit_for_validation()
        except ValueError as e:
            raise CarePlanStatusError(str(e))

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def validate(self, plan_id: int, validated_by: int) -> CarePlan:
        """Valide le plan d'aide."""
        plan = self.get_by_id(plan_id)

        # Vérifier que l'utilisateur existe et appartient au tenant
        user_query = select(User).where(
            User.id == validated_by,
            User.tenant_id == self.tenant_id
        )
        user = self.db.execute(user_query).scalar_one_or_none()

        if not user:
            raise UserNotFoundError(f"Utilisateur {validated_by} non trouvé")

        if plan.status not in (CarePlanStatus.DRAFT, CarePlanStatus.PENDING_VALIDATION):
            raise CarePlanStatusError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être validé"
            )

        plan.validate(user)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def suspend(self, plan_id: int, reason: Optional[str] = None) -> CarePlan:
        """Suspend le plan d'aide."""
        plan = self.get_by_id(plan_id)

        if plan.status != CarePlanStatus.ACTIVE:
            raise CarePlanStatusError("Seul un plan actif peut être suspendu")

        plan.suspend(reason)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def reactivate(self, plan_id: int) -> CarePlan:
        """Réactive un plan suspendu."""
        plan = self.get_by_id(plan_id)

        try:
            plan.reactivate()
        except ValueError as e:
            raise CarePlanStatusError(str(e))

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def complete(self, plan_id: int) -> CarePlan:
        """Marque le plan comme terminé."""
        plan = self.get_by_id(plan_id)
        plan.complete()
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def cancel(self, plan_id: int, reason: Optional[str] = None) -> CarePlan:
        """Annule le plan d'aide."""
        plan = self.get_by_id(plan_id)
        plan.cancel(reason)
        self.db.commit()
        self.db.refresh(plan)
        return plan


# =============================================================================
# CARE PLAN SERVICE SERVICE (services du plan)
# =============================================================================

class CarePlanServiceCRUDService:
    """
    Service pour la gestion des services de plan d'aide.

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
        return select(CarePlanService).where(CarePlanService.tenant_id == self.tenant_id)

    def get_all_for_plan(self, plan_id: int) -> List[CarePlanService]:
        """Liste les services d'un plan."""
        query = self._base_query().where(
            CarePlanService.care_plan_id == plan_id
        ).options(
            selectinload(CarePlanService.service_template)
        ).order_by(CarePlanService.id)

        return list(self.db.execute(query).scalars().all())

    def get_by_id(self, service_id: int) -> CarePlanService:
        """Récupère un service par son ID."""
        query = self._base_query().where(
            CarePlanService.id == service_id
        ).options(
            selectinload(CarePlanService.service_template)
        )
        service = self.db.execute(query).scalar_one_or_none()
        if not service:
            raise CarePlanServiceNotFoundError(f"Service {service_id} non trouvé")
        return service

    def create(
            self,
            plan_id: int,
            data: CarePlanServiceCreate,
    ) -> CarePlanService:
        """Ajoute un service à un plan."""
        # Vérifier que le plan existe, appartient au tenant et est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == plan_id,
            CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if not plan:
            raise CarePlanNotFoundError(f"Plan {plan_id} non trouvé")

        if not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        # ServiceTemplate est global (pas de tenant_id)
        template = self.db.get(ServiceTemplate, data.service_template_id)
        if not template:
            raise ServiceTemplateNotFoundError(
                f"Service template {data.service_template_id} non trouvé"
            )

        service = CarePlanService(
            tenant_id=self.tenant_id,
            care_plan_id=plan_id,
            service_template_id=data.service_template_id,
            quantity_per_week=data.quantity_per_week,
            frequency_type=data.frequency_type,
            frequency_days=data.frequency_days,
            preferred_time_start=data.preferred_time_start,
            preferred_time_end=data.preferred_time_end,
            duration_minutes=data.duration_minutes,
            priority=data.priority,
            special_instructions=data.special_instructions,
        )

        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def update(
            self,
            service_id: int,
            data: CarePlanServiceUpdate,
    ) -> CarePlanService:
        """Met à jour un service de plan."""
        service = self.get_by_id(service_id)

        # Vérifier que le plan est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == service.care_plan_id,
            CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if plan and not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(service, field, value)

        self.db.commit()
        self.db.refresh(service)
        return service

    def delete(self, service_id: int) -> None:
        """Supprime un service de plan."""
        service = self.get_by_id(service_id)

        # Vérifier que le plan est éditable
        plan_query = select(CarePlan).where(
            CarePlan.id == service.care_plan_id,
            CarePlan.tenant_id == self.tenant_id
        )
        plan = self.db.execute(plan_query).scalar_one_or_none()
        if plan and not plan.is_editable:
            raise CarePlanNotEditableError(
                f"Le plan en statut '{plan.status.value}' ne peut pas être modifié"
            )

        self.db.delete(service)
        self.db.commit()

    # === Affectation ===

    def assign(
            self,
            service_id: int,
            data: ServiceAssignment,
            assigned_by: int,
    ) -> CarePlanService:
        """Affecte un service à un professionnel."""
        service = self.get_by_id(service_id)

        # Vérifier que l'utilisateur à affecter appartient au tenant
        user_query = select(User).where(
            User.id == data.user_id,
            User.tenant_id == self.tenant_id
        )
        user = self.db.execute(user_query).scalar_one_or_none()
        if not user:
            raise UserNotFoundError(f"Utilisateur {data.user_id} non trouvé")

        # Vérifier que l'assigneur appartient au tenant
        assigner_query = select(User).where(
            User.id == assigned_by,
            User.tenant_id == self.tenant_id
        )
        assigner = self.db.execute(assigner_query).scalar_one_or_none()
        if not assigner:
            raise UserNotFoundError(f"Utilisateur {assigned_by} non trouvé")

        if data.mode == "assign":
            service.assign_to(user, assigner)
        else:
            service.propose_to(user, assigner)

        self.db.commit()
        self.db.refresh(service)
        return service

    def unassign(self, service_id: int) -> CarePlanService:
        """Retire l'affectation d'un service."""
        service = self.get_by_id(service_id)
        service.unassign()
        self.db.commit()
        self.db.refresh(service)
        return service

    def confirm_assignment(self, service_id: int) -> CarePlanService:
        """Confirme l'affectation (acceptée par le professionnel)."""
        service = self.get_by_id(service_id)

        try:
            service.confirm_assignment()
        except ValueError as e:
            raise AssignmentStatusError(str(e))

        self.db.commit()
        self.db.refresh(service)
        return service

    def reject_assignment(self, service_id: int) -> CarePlanService:
        """Rejette l'affectation (refusée par le professionnel)."""
        service = self.get_by_id(service_id)

        try:
            service.reject_assignment()
        except ValueError as e:
            raise AssignmentStatusError(str(e))

        self.db.commit()
        self.db.refresh(service)
        return service