"""
Service de provisioning d'un admin client depuis le contexte Platform.

Permet au SuperAdmin de créer le premier administrateur d'un tenant,
résolvant le problème du "bootstrapping" : les endpoints /users nécessitent
un JWT tenant, mais le SuperAdmin opère dans le circuit Platform.

Ce service est le chaînon manquant entre la création du tenant et
l'autonomie de l'admin client.

Changement v4.8 : Harmonisation encryption
- encrypt_for_db() retourne maintenant des clés {field}_encrypted (convention BaseEncryptor)
- Création User avec email_encrypted/rpps_encrypted
- Déchiffrement via decrypt_model() au lieu de decrypt_field()

🔄 S5 fix : Role.name == "ADMIN" (et non "ADMIN_FULL")
- Depuis S3, le rôle s'appelle ADMIN, la permission s'appelle ADMIN_FULL
- Corrige le bug où l'admin client n'avait aucun rôle assigné
"""
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.security.hashing import hash_password
from app.models.organization.entity import Entity
from app.models.platform.platform_audit_log import PlatformAuditLog
from app.models.platform.super_admin import SuperAdmin
from app.models.tenants.tenant import Tenant
from app.models.enums import TenantStatus
from app.models.user.user import User
from app.models.user.role import Role
from app.models.user.user_associations import UserRole, UserEntity

from app.services.encryption import user_encryptor

from app.api.v1.platform.schemas import TenantAdminUserCreate, TenantAdminUserResponse


# =============================================================================
# EXCEPTIONS
# =============================================================================

class TenantNotActiveError(Exception):
    """Le tenant n'est pas actif."""
    pass


class AdminEmailExistsError(Exception):
    """Un utilisateur avec cet email existe déjà dans ce tenant."""
    pass


class NoRootEntityError(Exception):
    """Aucune entité racine trouvée pour ce tenant."""
    pass


class EntityNotInTenantError(Exception):
    """L'entité spécifiée n'appartient pas à ce tenant."""
    pass


class AdminRoleNotFoundError(Exception):
    """Le rôle ADMIN n'a pas été trouvé en base."""
    pass


# =============================================================================
# SERVICE
# =============================================================================

class TenantAdminService:
    """Service pour la gestion des admin clients depuis l'espace Platform."""

    def __init__(self, db: Session):
        self.db = db

    def create_admin_user(
            self,
            tenant_id: int,
            data: TenantAdminUserCreate,
            created_by: SuperAdmin,
    ) -> TenantAdminUserResponse:
        """
        Crée un utilisateur admin dans un tenant.

        Étapes :
        1. Vérifier que le tenant existe et est ACTIVE
        2. Vérifier unicité email (blind index)
        3. Résoudre l'entité de rattachement (racine si non fourni)
        4. Créer le user (chiffrement email, hash password)
        5. Rattacher à l'entité
        6. Assigner le rôle ADMIN (permission ADMIN_FULL)
        7. Logger dans platform_audit_logs
        """
        from app.api.v1.platform.services import TenantNotFoundError

        # 1. Vérifier le tenant
        tenant = self.db.get(Tenant, tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} non trouvé")
        if tenant.status != TenantStatus.ACTIVE:
            raise TenantNotActiveError(
                f"Le tenant est {tenant.status.value}, il doit être ACTIVE"
            )

        # 2. Vérifier unicité email dans le tenant (via blind index)
        # v4.8 : encrypt_for_db retourne maintenant {field}_encrypted
        encrypted_data = user_encryptor.encrypt_for_db(
            {"email": data.email},
            tenant_id
        )

        existing = self.db.execute(
            select(User).where(
                and_(
                    User.email_blind == encrypted_data["email_blind"],
                    User.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            raise AdminEmailExistsError(
                f"Un utilisateur avec cet email existe déjà dans ce tenant"
            )

        # 3. Résoudre l'entité de rattachement
        if data.entity_id:
            entity = self.db.execute(
                select(Entity).where(
                    and_(
                        Entity.id == data.entity_id,
                        Entity.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if not entity:
                raise EntityNotInTenantError(
                    f"Entité {data.entity_id} non trouvée dans ce tenant"
                )
        else:
            # Rattacher à l'entité racine (parent_id IS NULL)
            entity = self.db.execute(
                select(Entity).where(
                    and_(
                        Entity.tenant_id == tenant_id,
                        Entity.parent_entity_id.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not entity:
                raise NoRootEntityError(
                    "Aucune entité racine trouvée. "
                    "Créez la structure organisationnelle avant d'ajouter un administrateur."
                )

        # 4. Créer le user
        # v4.8 : Utiliser les noms de colonnes _encrypted
        user = User(
            tenant_id=tenant_id,
            first_name=data.first_name,
            last_name=data.last_name,
            # Champs chiffrés (convention _encrypted)
            email_encrypted=encrypted_data["email_encrypted"],
            email_blind=encrypted_data["email_blind"],
            rpps_encrypted=None,
            rpps_blind=None,
            # Auth
            password_hash=hash_password(data.password),
            # Flags
            is_admin=True,
            is_active=True,
            must_change_password=True,
            # Pas de profession pour un admin pur
            profession_id=None,
        )
        self.db.add(user)
        self.db.flush()  # Pour obtenir user.id

        # 5. Rattacher à l'entité
        user_entity = UserEntity(
            user_id=user.id,
            entity_id=entity.id,
            tenant_id=tenant_id,
            is_primary=True,
            start_date=data.start_date_value,
        )
        self.db.add(user_entity)

        # ──────────────────────────────────────────────────────────────────
        # 6. Assigner le rôle ADMIN
        #
        # 🔄 S5 fix : Depuis S3, le rôle s'appelle "ADMIN" (pas "ADMIN_FULL").
        #   - "ADMIN" est le nom du rôle dans la table roles
        #   - "ADMIN_FULL" est le nom de la permission portée par ce rôle
        #
        # Si le rôle n'est pas trouvé, on lève AdminRoleNotFoundError
        # au lieu de continuer silencieusement sans rôle assigné.
        # ──────────────────────────────────────────────────────────────────
        admin_role = self.db.execute(
            select(Role).where(
                and_(
                    Role.name == "ADMIN",           # 🔄 S5 fix (était "ADMIN_FULL")
                    Role.is_system_role == True,
                )
            )
        ).scalar_one_or_none()

        if not admin_role:
            raise AdminRoleNotFoundError(
                "Le rôle système ADMIN n'a pas été trouvé en base. "
                "Vérifiez que init_db / seed a été exécuté correctement."
            )

        user_role = UserRole(
            user_id=user.id,
            role_id=admin_role.id,
            tenant_id=tenant_id,
            # assigned_by reste None : le SuperAdmin n'est pas un User
        )
        self.db.add(user_role)

        # 7. Audit log
        self._log_action(
            action="tenant_admin.create",
            resource_type="User",
            resource_id=str(user.id),
            super_admin_id=created_by.id,
            tenant_id=tenant_id,
            details={
                "user_name": f"{data.first_name} {data.last_name}",
                "user_email": data.email,
                "entity_id": entity.id,
                "entity_name": entity.name,
            }
        )

        self.db.commit()
        self.db.refresh(user)

        return TenantAdminUserResponse(
            id=user.id,
            tenant_id=tenant_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=data.email,  # Retourner en clair (on vient de le chiffrer)
            phone=data.phone,
            is_admin=True,
            is_active=True,
            entity_id=entity.id,
            entity_name=entity.name,
            role="ADMIN",                           # 🔄 S5 fix (était "ADMIN_FULL")
            must_change_password=True,
            created_at=user.created_at,
        )

    def list_admin_users(self, tenant_id: int) -> List[TenantAdminUserResponse]:
        """
        Liste les administrateurs d'un tenant.

        Retourne les users ayant is_admin=True dans ce tenant.
        """
        from app.api.v1.platform.services import TenantNotFoundError

        # Vérifier que le tenant existe
        tenant = self.db.get(Tenant, tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} non trouvé")

        # Récupérer les admins du tenant
        admins = self.db.execute(
            select(User).where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_admin == True,
                    User.is_active == True,
                )
            )
        ).scalars().all()

        results = []
        for admin in admins:
            # v4.8 : Déchiffrer via decrypt_model au lieu de decrypt_field
            email_clear = None
            try:
                decrypted = user_encryptor.decrypt_model(admin)
                email_clear = decrypted.get("email")
            except Exception:
                # Fallback : valeur brute (chiffrée)
                email_clear = admin.email_encrypted

            # Trouver l'entité principale
            entity_id = None
            entity_name = None
            if admin.primary_entity:
                entity_id = admin.primary_entity.id
                entity_name = admin.primary_entity.name

            # ──────────────────────────────────────────────────────────
            # 🔄 S5 fix : Le rôle s'appelle "ADMIN" (pas "ADMIN_FULL")
            # ──────────────────────────────────────────────────────────
            role_name = "ADMIN" if "ADMIN" in admin.role_names else (
                admin.role_names[0] if admin.role_names else "AUCUN_ROLE"
            )

            results.append(TenantAdminUserResponse(
                id=admin.id,
                tenant_id=tenant_id,
                first_name=admin.first_name,
                last_name=admin.last_name,
                email=email_clear,
                phone=None,
                is_admin=admin.is_admin,
                is_active=admin.is_active,
                entity_id=entity_id,
                entity_name=entity_name,
                role=role_name,
                must_change_password=admin.must_change_password,
                created_at=admin.created_at,
            ))

        return results

    def _log_action(
            self,
            action: str,
            resource_type: str,
            resource_id: str,
            super_admin_id: Optional[int],
            tenant_id: Optional[int] = None,
            details: Optional[dict] = None,
    ):
        """Crée une entrée dans le log d'audit."""
        log = PlatformAuditLog(
            super_admin_id=super_admin_id,
            action=action,
            target_table=resource_type,
            target_id=int(resource_id) if resource_id and resource_id.isdigit() else None,
            target_tenant_id=tenant_id,
            details=details or {},
        )
        self.db.add(log)