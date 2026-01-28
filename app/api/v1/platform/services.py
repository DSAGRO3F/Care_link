"""
Services métier pour le module Platform.

Gestion au niveau plateforme (SuperAdmin) :
- TenantService : CRUD des tenants
- SuperAdminService : CRUD des super admins
- PlatformAuditLogService : Consultation des logs
- UserTenantAssignmentService : Gestion des accès cross-tenant
- PlatformStatsService : Statistiques globales
"""
import uuid
from typing import Optional, List, Tuple
from datetime import datetime, timezone, date, timedelta

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, selectinload

from app.models.tenants.tenant import Tenant, TenantStatus, TenantType
from app.models.platform.super_admin import SuperAdmin, SuperAdminRole
from app.models.platform.platform_audit_log import PlatformAuditLog
from app.models.user.user_tenant_assignment import UserTenantAssignment
from app.models.user.user import User
from app.models.patient.patient import Patient
from app.models.organization.entity import Entity

from app.core.hashing import hash_password, verify_password

from app.api.v1.platform.schemas import (
    TenantCreate, TenantUpdate, TenantFilters, SuperAdminCreate, SuperAdminUpdate, SuperAdminPasswordChange,
    AuditLogFilters,
    UserTenantAssignmentCreate, UserTenantAssignmentUpdate, UserTenantAssignmentFilters,
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class TenantNotFoundError(Exception):
    """Tenant non trouvé."""
    pass


class TenantCodeExistsError(Exception):
    """Code de tenant déjà utilisé."""
    pass


class SuperAdminNotFoundError(Exception):
    """SuperAdmin non trouvé."""
    pass


class SuperAdminEmailExistsError(Exception):
    """Email de SuperAdmin déjà utilisé."""
    pass


class InvalidPasswordError(Exception):
    """Mot de passe invalide."""
    pass


class UserTenantAssignmentNotFoundError(Exception):
    """Affectation cross-tenant non trouvée."""
    pass


class UserNotFoundError(Exception):
    """Utilisateur non trouvé."""
    pass


class DuplicateAssignmentError(Exception):
    """Affectation déjà existante."""
    pass


class InvalidAssignmentError(Exception):
    """Affectation invalide."""
    pass


# =============================================================================
# TENANT SERVICE
# =============================================================================

class TenantService:
    """Service pour la gestion des tenants."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            filters: Optional[TenantFilters] = None,
    ) -> Tuple[List[Tenant], int]:
        """Liste les tenants avec pagination et filtres."""
        query = select(Tenant)

        if filters:
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.where(
                    or_(
                        Tenant.name.ilike(search_term),
                        Tenant.code.ilike(search_term),
                        Tenant.legal_name.ilike(search_term),
                    )
                )

            if filters.status:
                query = query.where(Tenant.status == TenantStatus(filters.status.value))

            if filters.tenant_type:
                query = query.where(Tenant.tenant_type == TenantType(filters.tenant_type.value))

            if filters.city:
                query = query.where(Tenant.city.ilike(f"%{filters.city}%"))

            if filters.country_id:
                query = query.where(Tenant.country_id == filters.country_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        order_column = getattr(Tenant, sort_by, Tenant.created_at)
        if sort_order.lower() == "desc":
            order_column = order_column.desc()
        query = query.order_by(order_column)

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, tenant_id: int) -> Tenant:
        """Récupère un tenant par son ID."""
        tenant = self.db.get(Tenant, tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} non trouvé")
        return tenant

    def get_by_code(self, code: str) -> Optional[Tenant]:
        """Récupère un tenant par son code."""
        query = select(Tenant).where(Tenant.code == code.upper())
        return self.db.execute(query).scalar_one_or_none()

    def create(
            self,
            data: TenantCreate,
            created_by_id: Optional[int] = None,
    ) -> Tenant:
        """Crée un nouveau tenant."""
        # Vérifier unicité du code
        existing = self.get_by_code(data.code)
        if existing:
            raise TenantCodeExistsError(f"Le code '{data.code}' est déjà utilisé")

        # Générer une clé de chiffrement unique pour ce tenant
        encryption_key_id = f"tenant-key-{uuid.uuid4().hex[:16]}"

        # Créer le tenant
        tenant = Tenant(
            code=data.code.upper(),
            name=data.name,
            legal_name=data.legal_name,
            siret=data.siret,
            tenant_type=TenantType(data.tenant_type.value),
            status=TenantStatus.ACTIVE,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            billing_email=data.billing_email,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            postal_code=data.postal_code,
            city=data.city,
            country_id=data.country_id,
            encryption_key_id=encryption_key_id,
            timezone=data.timezone,
            locale=data.locale,
            max_patients=data.max_patients,
            max_users=data.max_users,
            max_storage_gb=data.max_storage_gb,
            settings=data.settings or {},
        )

        self.db.add(tenant)
        self.db.flush()

        # Logger l'action
        self._log_action(
            action="tenant.create",
            resource_type="Tenant",
            resource_id=str(tenant.id),
            super_admin_id=created_by_id,
            tenant_id=tenant.id,
            details={
                "tenant_code": tenant.code,
                "tenant_name": tenant.name,
                "tenant_type": tenant.tenant_type.value,
            }
        )

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update(
            self,
            tenant_id: int,
            data: TenantUpdate,
            updated_by_id: Optional[int] = None
    ) -> Tenant:
        """Met à jour un tenant."""
        tenant = self.get_by_id(tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        changes = {}

        for field, value in update_data.items():
            if hasattr(tenant, field):
                old_value = getattr(tenant, field)

                # Conversion des enums API vers enums modèle
                if field == "status" and value:
                    value = TenantStatus(value.value if hasattr(value, 'value') else value)
                elif field == "tenant_type" and value:
                    value = TenantType(value.value if hasattr(value, 'value') else value)

                if old_value != value:
                    changes[field] = {"old": str(old_value), "new": str(value)}
                    setattr(tenant, field, value)

        if changes:
            self._log_action(
                action="tenant.update",
                resource_type="Tenant",
                resource_id=str(tenant_id),
                super_admin_id=updated_by_id,
                tenant_id=tenant_id,
                details={"changes": changes}
            )

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def delete(self, tenant_id: int, deleted_by_id: Optional[int] = None) -> bool:
        """
        Supprime un tenant (soft delete via status TERMINATED).

        Attention : Cette action est irréversible et doit être confirmée.
        """
        tenant = self.get_by_id(tenant_id)

        tenant.status = TenantStatus.TERMINATED
        tenant.terminated_at = datetime.now(timezone.utc)

        self._log_action(
            action="tenant.delete",
            resource_type="Tenant",
            resource_id=str(tenant_id),
            super_admin_id=deleted_by_id,
            tenant_id=tenant_id,
            details={
                "tenant_code": tenant.code,
                "tenant_name": tenant.name,
            }
        )

        self.db.commit()
        return True

    def suspend(self, tenant_id: int, reason: str, suspended_by_id: Optional[int] = None) -> Tenant:
        """Suspend un tenant."""
        tenant = self.get_by_id(tenant_id)

        if tenant.status == TenantStatus.TERMINATED:
            raise InvalidAssignmentError("Impossible de suspendre un tenant terminé")

        tenant.status = TenantStatus.SUSPENDED

        self._log_action(
            action="tenant.suspend",
            resource_type="Tenant",
            resource_id=str(tenant_id),
            super_admin_id=suspended_by_id,
            tenant_id=tenant_id,
            details={"reason": reason}
        )

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def reactivate(self, tenant_id: int, reactivated_by_id: Optional[int] = None) -> Tenant:
        """Réactive un tenant suspendu."""
        tenant = self.get_by_id(tenant_id)

        if tenant.status == TenantStatus.TERMINATED:
            raise InvalidAssignmentError("Impossible de réactiver un tenant terminé")

        tenant.status = TenantStatus.ACTIVE
        tenant.activated_at = datetime.now(timezone.utc)

        self._log_action(
            action="tenant.reactivate",
            resource_type="Tenant",
            resource_id=str(tenant_id),
            super_admin_id=reactivated_by_id,
            tenant_id=tenant_id,
            details={}
        )

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_stats(self, tenant_id: int) -> dict:
        """Récupère les statistiques d'un tenant."""
        tenant = self.get_by_id(tenant_id)

        # Compter les entités
        entities_count = self.db.execute(
            select(func.count(Entity.id)).where(Entity.tenant_id == tenant_id)
        ).scalar() or 0

        # Compter les utilisateurs
        users_count = self.db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant_id)
        ).scalar() or 0

        # Compter les patients
        patients_count = self.db.execute(
            select(func.count(Patient.id)).where(Patient.tenant_id == tenant_id)
        ).scalar() or 0

        # Calculer les pourcentages d'utilisation
        users_usage_percent = None
        if tenant.max_users:
            users_usage_percent = (users_count / tenant.max_users) * 100

        patients_usage_percent = None
        if tenant.max_patients:
            patients_usage_percent = (patients_count / tenant.max_patients) * 100

        return {
            "tenant_id": tenant.id,
            "tenant_code": tenant.code,
            "tenant_name": tenant.name,
            "entities_count": entities_count,
            "users_count": users_count,
            "patients_count": patients_count,
            "users_limit": tenant.max_users,
            "patients_limit": tenant.max_patients,
            "users_usage_percent": users_usage_percent,
            "patients_usage_percent": patients_usage_percent,
        }

    def _log_action(
            self,
            action: str,
            resource_type: str,
            resource_id: str,
            super_admin_id: Optional[int],
            tenant_id: Optional[int] = None,
            details: Optional[dict] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
    ):
        """Crée une entrée dans le log d'audit."""
        log = PlatformAuditLog(
            super_admin_id=super_admin_id,
            action=action,
            target_tenant_id=tenant_id,
            target_table=resource_type,
            target_id=int(resource_id) if resource_id and resource_id.isdigit() else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)


# =============================================================================
# SUPER ADMIN SERVICE
# =============================================================================

class SuperAdminService:
    """Service pour la gestion des super admins."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            include_inactive: bool = False,
    ) -> Tuple[List[SuperAdmin], int]:
        """Liste les super admins avec pagination."""
        query = select(SuperAdmin)

        if not include_inactive:
            query = query.where(SuperAdmin.is_active == True)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Pagination
        query = query.order_by(SuperAdmin.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, admin_id: int) -> SuperAdmin:
        """Récupère un super admin par son ID."""
        admin = self.db.get(SuperAdmin, admin_id)
        if not admin:
            raise SuperAdminNotFoundError(f"SuperAdmin {admin_id} non trouvé")
        return admin

    def get_by_email(self, email: str) -> Optional[SuperAdmin]:
        """Récupère un super admin par son email."""
        query = select(SuperAdmin).where(SuperAdmin.email == email.lower())
        return self.db.execute(query).scalar_one_or_none()

    def create(
            self,
            data: SuperAdminCreate,
            created_by_id: Optional[int] = None,
    ) -> SuperAdmin:
        """Crée un nouveau super admin."""
        # Vérifier unicité de l'email
        existing = self.get_by_email(data.email)
        if existing:
            raise SuperAdminEmailExistsError(f"L'email '{data.email}' est déjà utilisé")

        admin = SuperAdmin(
            email=data.email.lower(),
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=hash_password(data.password),
            role=SuperAdminRole(data.role.value),
            is_active=data.is_active,
        )

        self.db.add(admin)
        self.db.flush()

        # Logger
        self._log_action(
            action="super_admin.create",
            resource_type="SuperAdmin",
            resource_id=str(admin.id),
            super_admin_id=created_by_id,
            details={"email": admin.email, "role": admin.role.value}
        )

        self.db.commit()
        self.db.refresh(admin)
        return admin

    def update(
            self,
            admin_id: int,
            data: SuperAdminUpdate,
            updated_by_id: Optional[int] = None,
    ) -> SuperAdmin:
        """Met à jour un super admin."""
        admin = self.get_by_id(admin_id)

        update_data = data.model_dump(exclude_unset=True)
        changes = {}

        # Vérifier unicité de l'email si modifié
        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].lower()
            if new_email != admin.email:
                existing = self.get_by_email(new_email)
                if existing:
                    raise SuperAdminEmailExistsError(f"L'email '{new_email}' est déjà utilisé")
                update_data["email"] = new_email

        # Convertir le rôle API vers le rôle modèle si présent
        if "role" in update_data and update_data["role"] is not None:
            update_data["role"] = SuperAdminRole(update_data["role"].value)

        for field, value in update_data.items():
            if hasattr(admin, field):
                old_value = getattr(admin, field)
                if old_value != value:
                    # Pour les enums, afficher la valeur
                    old_display = old_value.value if hasattr(old_value, 'value') else str(old_value)
                    new_display = value.value if hasattr(value, 'value') else str(value)
                    changes[field] = {"old": old_display, "new": new_display}
                    setattr(admin, field, value)

        if changes:
            self._log_action(
                action="super_admin.update",
                resource_type="SuperAdmin",
                resource_id=str(admin_id),
                super_admin_id=updated_by_id,
                details={"changes": changes}
            )

        self.db.commit()
        self.db.refresh(admin)
        return admin

    def delete(self, admin_id: int, deleted_by_id: Optional[int] = None) -> bool:
        """Désactive un super admin (soft delete)."""
        admin = self.get_by_id(admin_id)

        # Empêcher l'auto-suppression
        if admin_id == deleted_by_id:
            raise InvalidAssignmentError("Impossible de supprimer son propre compte")

        admin.is_active = False

        self._log_action(
            action="super_admin.delete",
            resource_type="SuperAdmin",
            resource_id=str(admin_id),
            super_admin_id=deleted_by_id,
            details={"email": admin.email}
        )

        self.db.commit()
        return True

    def change_password(
            self,
            admin_id: int,
            data: SuperAdminPasswordChange,
    ) -> bool:
        """Change le mot de passe d'un super admin."""
        admin = self.get_by_id(admin_id)

        if not verify_password(data.current_password, admin.password_hash):
            raise InvalidPasswordError("Mot de passe actuel incorrect")

        admin.password_hash = hash_password(data.new_password)

        self._log_action(
            action="super_admin.password_change",
            resource_type="SuperAdmin",
            resource_id=str(admin_id),
            super_admin_id=admin_id,
            details={}
        )

        self.db.commit()
        return True

    def authenticate(self, email: str, password: str) -> Optional[SuperAdmin]:
        """
        Authentifie un super admin.

        Gère le verrouillage après tentatives échouées.
        """
        admin = self.get_by_email(email)
        if not admin:
            return None

        if not admin.is_active:
            return None

        # Vérifier si le compte est verrouillé
        if admin.is_locked:
            return None

        if not verify_password(password, admin.password_hash):
            # Enregistrer l'échec
            admin.record_login_failure()
            self.db.commit()
            return None

        # Succès : enregistrer et réinitialiser les compteurs
        admin.record_login_success()
        self.db.commit()

        return admin

    def _log_action(
            self,
            action: str,
            resource_type: str,
            resource_id: str,
            super_admin_id: Optional[int],
            details: Optional[dict] = None,
    ):
        """Crée une entrée dans le log d'audit."""
        log = PlatformAuditLog(
            super_admin_id=super_admin_id,
            action=action,
            target_table=resource_type,
            target_id=int(resource_id) if resource_id and resource_id.isdigit() else None,
            details=details or {},
        )
        self.db.add(log)


# =============================================================================
# PLATFORM AUDIT LOG SERVICE
# =============================================================================

class PlatformAuditLogService:
    """Service pour la consultation des logs d'audit."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(
            self,
            page: int = 1,
            size: int = 50,
            filters: Optional[AuditLogFilters] = None,
    ) -> Tuple[List[PlatformAuditLog], int]:
        """Liste les logs d'audit avec pagination et filtres."""
        query = select(PlatformAuditLog).options(
            selectinload(PlatformAuditLog.super_admin),
            selectinload(PlatformAuditLog.tenant),
        )

        if filters:
            if filters.super_admin_id:
                query = query.where(PlatformAuditLog.super_admin_id == filters.super_admin_id)

            if filters.action:
                query = query.where(PlatformAuditLog.action == filters.action)

            if filters.resource_type:
                query = query.where(PlatformAuditLog.resource_type == filters.resource_type)

            if filters.tenant_id:
                query = query.where(PlatformAuditLog.tenant_id == filters.tenant_id)

            if filters.date_from:
                query = query.where(PlatformAuditLog.created_at >= filters.date_from)

            if filters.date_to:
                query = query.where(PlatformAuditLog.created_at <= filters.date_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri par date décroissante
        query = query.order_by(PlatformAuditLog.created_at.desc())

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, log_id: int) -> PlatformAuditLog:
        """Récupère un log d'audit par son ID."""
        query = select(PlatformAuditLog).options(
            selectinload(PlatformAuditLog.super_admin),
            selectinload(PlatformAuditLog.tenant),
        ).where(PlatformAuditLog.id == log_id)

        log = self.db.execute(query).scalar_one_or_none()
        if not log:
            raise ValueError(f"Log {log_id} non trouvé")
        return log


# =============================================================================
# USER TENANT ASSIGNMENT SERVICE
# =============================================================================

class UserTenantAssignmentService:
    """Service pour la gestion des affectations cross-tenant."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(
            self,
            page: int = 1,
            size: int = 20,
            filters: Optional[UserTenantAssignmentFilters] = None,
    ) -> Tuple[List[UserTenantAssignment], int]:
        """Liste les affectations avec pagination et filtres."""
        query = select(UserTenantAssignment).options(
            selectinload(UserTenantAssignment.user),
            selectinload(UserTenantAssignment.tenant),
        )

        if filters:
            if filters.user_id:
                query = query.where(UserTenantAssignment.user_id == filters.user_id)

            if filters.tenant_id:
                query = query.where(UserTenantAssignment.tenant_id == filters.tenant_id)

            if filters.assignment_type:
                query = query.where(UserTenantAssignment.assignment_type == filters.assignment_type.value)

            if filters.is_active is not None:
                query = query.where(UserTenantAssignment.is_active == filters.is_active)

            if not filters.include_expired:
                today = date.today()
                query = query.where(
                    or_(
                        UserTenantAssignment.end_date.is_(None),
                        UserTenantAssignment.end_date >= today
                    )
                )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Tri
        query = query.order_by(UserTenantAssignment.created_at.desc())

        # Pagination
        query = query.offset((page - 1) * size).limit(size)

        items = self.db.execute(query).scalars().all()
        return list(items), total

    def get_by_id(self, assignment_id: int) -> UserTenantAssignment:
        """Récupère une affectation par son ID."""
        query = select(UserTenantAssignment).options(
            selectinload(UserTenantAssignment.user),
            selectinload(UserTenantAssignment.tenant),
        ).where(UserTenantAssignment.id == assignment_id)

        assignment = self.db.execute(query).scalar_one_or_none()
        if not assignment:
            raise UserTenantAssignmentNotFoundError(f"Affectation {assignment_id} non trouvée")
        return assignment

    def create(
            self,
            data: UserTenantAssignmentCreate,
            created_by_id: Optional[int] = None,
    ) -> UserTenantAssignment:
        """Crée une nouvelle affectation cross-tenant."""
        # Vérifier que l'utilisateur existe
        user = self.db.get(User, data.user_id)
        if not user:
            raise UserNotFoundError(f"Utilisateur {data.user_id} non trouvé")

        # Vérifier que le tenant de destination existe
        tenant = self.db.get(Tenant, data.tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {data.tenant_id} non trouvé")

        # Vérifier que l'utilisateur n'est pas déjà rattaché à ce tenant principalement
        if user.tenant_id == data.tenant_id:
            raise InvalidAssignmentError(
                f"L'utilisateur {data.user_id} est déjà rattaché principalement au tenant {data.tenant_id}"
            )

        # Vérifier qu'une affectation similaire n'existe pas déjà
        existing = self.db.execute(
            select(UserTenantAssignment).where(
                and_(
                    UserTenantAssignment.user_id == data.user_id,
                    UserTenantAssignment.tenant_id == data.tenant_id,
                    UserTenantAssignment.is_active == True,
                    or_(
                        UserTenantAssignment.end_date.is_(None),
                        UserTenantAssignment.end_date >= date.today()
                    )
                )
            )
        ).scalar_one_or_none()

        if existing:
            raise DuplicateAssignmentError(
                f"L'utilisateur {data.user_id} a déjà une affectation active vers le tenant {data.tenant_id}"
            )

        assignment = UserTenantAssignment(
            user_id=data.user_id,
            tenant_id=data.tenant_id,
            assignment_type=data.assignment_type.value,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            permissions=data.permissions,
            is_active=True,
            granted_by_super_admin_id=created_by_id,
        )

        self.db.add(assignment)
        self.db.flush()

        # Logger
        self._log_action(
            action="assignment.create",
            resource_type="UserTenantAssignment",
            resource_id=str(assignment.id),
            super_admin_id=created_by_id,
            target_tenant_id=data.tenant_id,
            details={
                "user_id": data.user_id,
                "tenant_id": data.tenant_id,
                "assignment_type": data.assignment_type.value,
            }
        )

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def update(
            self,
            assignment_id: int,
            data: UserTenantAssignmentUpdate,
            updated_by_id: Optional[int] = None,
    ) -> UserTenantAssignment:
        """Met à jour une affectation."""
        assignment = self.get_by_id(assignment_id)

        update_data = data.model_dump(exclude_unset=True)
        changes = {}

        for field, value in update_data.items():
            if hasattr(assignment, field):
                old_value = getattr(assignment, field)

                # Conversion enum
                if field == "assignment_type" and value:
                    value = value.value if hasattr(value, 'value') else value

                if old_value != value:
                    changes[field] = {"old": str(old_value), "new": str(value)}
                    setattr(assignment, field, value)

        if changes:
            self._log_action(
                action="assignment.update",
                resource_type="UserTenantAssignment",
                resource_id=str(assignment_id),
                super_admin_id=updated_by_id,
                target_tenant_id=assignment.tenant_id,
                details={"changes": changes}
            )

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def delete(self, assignment_id: int, deleted_by_id: Optional[int] = None) -> bool:
        """Désactive une affectation (soft delete)."""
        assignment = self.get_by_id(assignment_id)

        assignment.is_active = False
        assignment.end_date = date.today()

        self._log_action(
            action="assignment.delete",
            resource_type="UserTenantAssignment",
            resource_id=str(assignment_id),
            super_admin_id=deleted_by_id,
            target_tenant_id=assignment.tenant_id,
            details={"user_id": assignment.user_id}
        )

        self.db.commit()
        return True

    def _log_action(
            self,
            action: str,
            resource_type: str,
            resource_id: str,
            super_admin_id: Optional[int],
            target_tenant_id: Optional[int] = None,
            details: Optional[dict] = None,
    ):
        """Crée une entrée dans le log d'audit."""
        log = PlatformAuditLog(
            super_admin_id=super_admin_id,
            action=action,
            target_table=resource_type,
            target_id=int(resource_id) if resource_id and resource_id.isdigit() else None,
            target_tenant_id=target_tenant_id,
            details=details or {},
        )
        self.db.add(log)


# =============================================================================
# PLATFORM STATS SERVICE
# =============================================================================

class PlatformStatsService:
    """Service pour les statistiques globales de la plateforme."""

    def __init__(self, db: Session):
        self.db = db

    def get_platform_stats(self) -> dict:
        """Récupère les statistiques globales de la plateforme."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Tenants par statut
        tenant_stats = self.db.execute(
            select(Tenant.status, func.count(Tenant.id))
            .group_by(Tenant.status)
        ).all()

        tenant_counts = {status.value: count for status, count in tenant_stats}
        total_tenants = sum(tenant_counts.values())

        # Compteurs globaux
        total_users = self.db.execute(select(func.count(User.id))).scalar() or 0
        total_patients = self.db.execute(select(func.count(Patient.id))).scalar() or 0
        total_entities = self.db.execute(select(func.count(Entity.id))).scalar() or 0

        # Affectations actives
        active_assignments = self.db.execute(
            select(func.count(UserTenantAssignment.id)).where(
                and_(
                    UserTenantAssignment.is_active == True,
                    or_(
                        UserTenantAssignment.end_date.is_(None),
                        UserTenantAssignment.end_date >= date.today()
                    )
                )
            )
        ).scalar() or 0

        # Tenants créés les 30 derniers jours
        tenants_last_30 = self.db.execute(
            select(func.count(Tenant.id)).where(Tenant.created_at >= thirty_days_ago)
        ).scalar() or 0

        # Users créés les 30 derniers jours
        users_last_30 = self.db.execute(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        ).scalar() or 0

        # Super admins
        total_super_admins = self.db.execute(select(func.count(SuperAdmin.id))).scalar() or 0
        active_super_admins = self.db.execute(
            select(func.count(SuperAdmin.id)).where(SuperAdmin.is_active == True)
        ).scalar() or 0

        return {
            "total_tenants": total_tenants,
            "active_tenants": tenant_counts.get("ACTIVE", 0),
            "suspended_tenants": tenant_counts.get("SUSPENDED", 0),
            "terminated_tenants": tenant_counts.get("TERMINATED", 0),
            "total_users": total_users,
            "total_patients": total_patients,
            "total_entities": total_entities,
            "active_assignments": active_assignments,
            "tenants_created_last_30_days": tenants_last_30,
            "users_created_last_30_days": users_last_30,
            "total_super_admins": total_super_admins,
            "active_super_admins": active_super_admins,
        }