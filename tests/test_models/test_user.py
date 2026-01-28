"""
Tests unitaires pour le modèle User et ses associations.
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserRole, UserEntity, Role, Entity, Country
from app.models.enums import EntityType, RoleName, ContractType


class TestUser:
    """Tests pour le modèle User."""

    def test_create_user(self, db_session: Session, tenant, profession_medecin):
        """Test création d'un utilisateur."""
        user = User(
            tenant_id=tenant.id,  # MULTI-TENANT: Ajouté
            email="nouveau@test.fr",
            first_name="Pierre",
            last_name="Durand",
            rpps="11111111111",
            profession_id=profession_medecin.id,
            is_admin=False,
            is_active=True
        )
        db_session.add(user)
        db_session.flush()

        assert user.id is not None
        assert user.email == "nouveau@test.fr"
        assert user.first_name == "Pierre"
        assert user.last_name == "Durand"
        assert user.tenant_id == tenant.id  # Vérifier tenant
        assert user.created_at is not None

    def test_user_tenant_relation(self, user_admin, tenant):
        """Test relation User → Tenant."""
        assert user_admin.tenant == tenant
        assert user_admin in tenant.users

    def test_user_email_unique(self, db_session: Session, user_admin: User, tenant):
        """Test que l'email est unique."""
        duplicate = User(
            tenant_id=tenant.id,  # MULTI-TENANT: Ajouté
            email="admin@test.fr",  # Même email que la fixture
            first_name="Autre",
            last_name="Admin"
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_user_rpps_unique(self, db_session: Session, user_admin: User, tenant):
        """Test que le RPPS est unique."""
        duplicate = User(
            tenant_id=tenant.id,  # MULTI-TENANT: Ajouté
            email="autre@test.fr",
            first_name="Autre",
            last_name="User",
            rpps="00000000001"  # Même RPPS que la fixture
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_user_full_name(self, user_medecin: User):
        """Test propriété full_name."""
        assert user_medecin.full_name == "Jean Dupont"

    def test_user_display_name_medecin(self, user_medecin: User):
        """Test display_name pour un médecin."""
        assert user_medecin.display_name == "Dr. Dupont"

    def test_user_display_name_non_medecin(self, user_infirmier: User):
        """Test display_name pour un non-médecin."""
        assert user_infirmier.display_name == "Marie Martin"

    def test_user_str(self, user_medecin: User):
        """Test représentation string."""
        assert str(user_medecin) == "Jean Dupont"


class TestUserRoles:
    """Tests pour les relations User ↔ Role."""

    def test_user_roles_property(self, user_medecin: User, role_medecin: Role):
        """Test propriété roles."""
        assert len(user_medecin.roles) == 1
        assert role_medecin in user_medecin.roles

    def test_user_role_names(self, user_medecin: User):
        """Test propriété role_names."""
        assert RoleName.MEDECIN_TRAITANT.value in user_medecin.role_names

    def test_user_has_role(self, user_medecin: User):
        """Test méthode has_role."""
        assert user_medecin.has_role(RoleName.MEDECIN_TRAITANT.value) is True
        assert user_medecin.has_role(RoleName.ADMIN.value) is False

    def test_user_all_permissions(self, user_medecin: User):
        """Test propriété all_permissions."""
        permissions = user_medecin.all_permissions
        assert "PATIENT_VIEW" in permissions
        assert "EVALUATION_VIEW" in permissions

    def test_user_has_permission(self, user_medecin: User):
        """Test méthode has_permission."""
        assert user_medecin.has_permission("PATIENT_VIEW") is True
        assert user_medecin.has_permission("ADMIN_FULL") is False

    def test_admin_has_all_permissions(self, user_admin: User):
        """Test que l'admin a toutes les permissions."""
        # is_admin=True donne accès à tout
        assert user_admin.has_permission("PATIENT_VIEW") is True
        assert user_admin.has_permission("ANY_PERMISSION") is True

    def test_add_multiple_roles(self, db_session: Session, tenant, user_medecin: User, role_admin: Role):
        """Test ajout de plusieurs rôles."""
        # Ajouter un second rôle
        user_role = UserRole(
            user_id=user_medecin.id,
            role_id=role_admin.id,
            tenant_id=tenant.id  # MULTI-TENANT v4.3
        )
        db_session.add(user_role)
        db_session.flush()

        # Rafraîchir
        db_session.refresh(user_medecin)

        assert len(user_medecin.roles) == 2

    def test_user_role_assigned_by(self, db_session: Session, tenant, user_admin: User, user_medecin: User, role_infirmier: Role):
        """Test traçabilité de l'attribution du rôle."""
        user_role = UserRole(
            user_id=user_medecin.id,
            role_id=role_infirmier.id,
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            assigned_by=user_admin.id
        )
        db_session.add(user_role)
        db_session.flush()

        assert user_role.assigned_by == user_admin.id
        assert user_role.assigned_at is not None
        assert user_role.assigner == user_admin


class TestUserEntities:
    """Tests pour les relations User ↔ Entity."""

    def test_user_entities_property(self, user_medecin: User, entity: Entity):
        """Test propriété entities."""
        assert len(user_medecin.entities) == 1
        assert entity in user_medecin.entities

    def test_user_primary_entity(self, user_medecin: User, entity: Entity):
        """Test propriété primary_entity."""
        assert user_medecin.primary_entity == entity

    def test_user_belongs_to_entity(self, user_medecin: User, entity: Entity):
        """Test méthode belongs_to_entity."""
        assert user_medecin.belongs_to_entity(entity.id) is True
        assert user_medecin.belongs_to_entity(999) is False

    def test_add_multiple_entities(self, db_session: Session, tenant, user_medecin: User, country: Country):
        """Test utilisateur rattaché à plusieurs entités."""
        # Créer une seconde entité
        entity2 = Entity(
            tenant_id=tenant.id,  # MULTI-TENANT: Ajouté
            name="SSIAD Autre",
            entity_type=EntityType.SSIAD,  # Utiliser l'enum
            country_id=country.id,
            status="active"
        )
        db_session.add(entity2)
        db_session.flush()

        # Rattacher l'utilisateur (vacation)
        user_entity = UserEntity(
            user_id=user_medecin.id,
            entity_id=entity2.id,
            tenant_id=tenant.id,  # MULTI-TENANT v4.3
            is_primary=False,
            contract_type=ContractType.VACATION.value,
            start_date=date.today()
        )
        db_session.add(user_entity)
        db_session.flush()

        # Rafraîchir
        db_session.refresh(user_medecin)

        assert len(user_medecin.entities) == 2

    def test_user_entity_terminate(self, db_session: Session, user_medecin: User):
        """Test fin de rattachement à une entité."""
        # Récupérer l'association
        user_entity = user_medecin.entity_associations[0]
        assert user_entity.is_active is True

        # Terminer le rattachement
        user_entity.terminate()
        db_session.flush()

        assert user_entity.is_active is False
        assert user_entity.end_date == date.today()

        # L'entité ne doit plus apparaître dans entities (actives seulement)
        db_session.refresh(user_medecin)
        assert len(user_medecin.entities) == 0

    def test_user_entity_contract_types(self, db_session: Session, user_medecin: User):
        """Test les différents types de contrat."""
        user_entity = user_medecin.entity_associations[0]
        assert user_entity.contract_type == ContractType.LIBERAL.value