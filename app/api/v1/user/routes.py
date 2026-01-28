"""
Routes FastAPI pour le module User.

Endpoints pour :
- /professions : Gestion des professions (données partagées - pas de tenant)
- /roles : Gestion des rôles (filtrés par tenant)
- /users : Gestion des utilisateurs (filtrés par tenant)
- /users/{id}/roles : Gestion des rôles d'un utilisateur
- /users/{id}/entities : Gestion des rattachements
- /users/{id}/availabilities : Gestion des disponibilités

MULTI-TENANT: Les endpoints User et Role injectent automatiquement le tenant_id
depuis l'utilisateur authentifié.
"""
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session_rls import get_db
from app.core.user_auth import get_current_user, require_role

from app.models.user.user import User

from app.api.v1.user.schemas import (
    # Profession
    ProfessionCreate, ProfessionUpdate, ProfessionResponse, ProfessionList,
    # Role
    RoleCreate, RoleUpdate, RoleResponse, RoleList,
    # User
    UserCreate, UserUpdate, UserResponse, UserList, UserSummary,
    UserWithEntities, UserFilters,
    # UserEntity
    UserEntityCreate, UserEntityUpdate, UserEntityResponse,
    # UserRole
    UserRoleCreate, UserRoleResponse,
    # UserAvailability
    UserAvailabilityCreate, UserAvailabilityUpdate,
    UserAvailabilityResponse, UserAvailabilityList,
)

from app.api.v1.user.services import (
    ProfessionService, RoleService, UserService, UserAvailabilityService,
    # Exceptions
    UserNotFoundError, RoleNotFoundError, ProfessionNotFoundError,
    AvailabilityNotFoundError, EntityNotFoundError,
    DuplicateEmailError, DuplicateRPPSError,
    DuplicateProfessionNameError, DuplicateProfessionCodeError,
    DuplicateRoleNameError, SystemRoleModificationError,
    UserAlreadyHasRoleError, UserEntityAlreadyExistsError,
)

from app.api.v1.dependencies import PaginationParams
from app.api.v1.user.tenant_users_security import get_current_tenant_id

# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter(tags=["Users"])
professions_router = APIRouter(prefix="/professions", tags=["Professions"])
roles_router = APIRouter(prefix="/roles", tags=["Roles"])
users_router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# PROFESSION ENDPOINTS (DONNÉES PARTAGÉES - PAS DE TENANT)
# =============================================================================

@professions_router.get("", response_model=ProfessionList)
def list_professions(
        pagination: PaginationParams = Depends(),
        category: Optional[str] = Query(None, description="Filtrer par catégorie"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Liste toutes les professions.

    NOTE: Les professions sont des données de référence partagées entre tous les tenants.
    """
    items, total = ProfessionService.get_all(
        db, page=pagination.page, size=pagination.size, category=category
    )
    pages = (total + pagination.size - 1) // pagination.size
    return ProfessionList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@professions_router.get("/{profession_id}", response_model=ProfessionResponse)
def get_profession(
        profession_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Récupère une profession par son ID."""
    try:
        return ProfessionService.get_by_id(db, profession_id)
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@professions_router.post("", response_model=ProfessionResponse, status_code=status.HTTP_201_CREATED)
def create_profession(
        data: ProfessionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Crée une nouvelle profession (admin uniquement)."""
    try:
        return ProfessionService.create(db, data)
    except DuplicateProfessionNameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateProfessionCodeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@professions_router.patch("/{profession_id}", response_model=ProfessionResponse)
def update_profession(
        profession_id: int,
        data: ProfessionUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Met à jour une profession (admin uniquement)."""
    try:
        return ProfessionService.update(db, profession_id, data)
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (DuplicateProfessionNameError, DuplicateProfessionCodeError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@professions_router.delete("/{profession_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profession(
        profession_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Supprime une profession (admin uniquement)."""
    try:
        ProfessionService.delete(db, profession_id)
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# ROLE ENDPOINTS (MULTI-TENANT)
# =============================================================================

@roles_router.get("", response_model=RoleList)
def list_roles(
        pagination: PaginationParams = Depends(),
        is_system_role: Optional[bool] = Query(None, description="Filtrer par rôle système"),
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """
    Liste tous les rôles.

    **MULTI-TENANT**: Retourne les rôles du tenant + les rôles système partagés.
    """
    service = RoleService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page, size=pagination.size, is_system_role=is_system_role
    )
    pages = (total + pagination.size - 1) // pagination.size
    return RoleList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@roles_router.get("/{role_id}", response_model=RoleResponse)
def get_role(
        role_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Récupère un rôle par son ID."""
    try:
        service = RoleService(db, tenant_id)
        return service.get_by_id(role_id)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@roles_router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
        data: RoleCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Crée un nouveau rôle (admin uniquement).

    **MULTI-TENANT**: Le tenant_id est automatiquement injecté.
    """
    try:
        service = RoleService(db, tenant_id)
        return service.create(data)
    except DuplicateRoleNameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@roles_router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
        role_id: int,
        data: RoleUpdate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Met à jour un rôle (admin uniquement)."""
    try:
        service = RoleService(db, tenant_id)
        return service.update(role_id, data)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateRoleNameError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except SystemRoleModificationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@roles_router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
        role_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Supprime un rôle (admin uniquement)."""
    try:
        service = RoleService(db, tenant_id)
        service.delete(role_id)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SystemRoleModificationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# =============================================================================
# USER ENDPOINTS (MULTI-TENANT)
# =============================================================================

@users_router.get("", response_model=UserList)
def list_users(
        pagination: PaginationParams = Depends(),
        profession_id: Optional[int] = Query(None),
        role_name: Optional[str] = Query(None),
        entity_id: Optional[int] = Query(None),
        is_active: Optional[bool] = Query(None),
        is_admin: Optional[bool] = Query(None),
        search: Optional[str] = Query(None, description="Recherche sur nom, prénom, email, RPPS"),
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """
    Liste les utilisateurs avec filtres.

    **MULTI-TENANT**: Filtre automatiquement par le tenant de l'utilisateur.
    """
    filters = UserFilters(
        profession_id=profession_id,
        role_name=role_name,
        entity_id=entity_id,
        is_active=is_active,
        is_admin=is_admin,
        search=search,
    )
    service = UserService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by or "last_name",
        sort_order=pagination.sort_order or "asc",
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size
    return UserList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@users_router.get("/me", response_model=UserWithEntities)
def get_current_user_profile(
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Récupère le profil de l'utilisateur connecté."""
    service = UserService(db, tenant_id)
    return service.get_by_id(current_user.id)


@users_router.get("/{user_id}", response_model=UserWithEntities)
def get_user(
        user_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Récupère un utilisateur par son ID."""
    try:
        service = UserService(db, tenant_id)
        return service.get_by_id(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
        data: UserCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Crée un nouvel utilisateur (admin uniquement).

    **MULTI-TENANT**: Le tenant_id est automatiquement injecté.
    """
    try:
        service = UserService(db, tenant_id)
        return service.create(data)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateRPPSError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.patch("/{user_id}", response_model=UserResponse)
def update_user(
        user_id: int,
        data: UserUpdate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Met à jour un utilisateur."""
    # Seul l'admin ou l'utilisateur lui-même peut modifier
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que votre propre profil"
        )

    # Seul l'admin peut modifier is_admin ou is_active
    if not current_user.is_admin:
        if data.is_admin is not None or data.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul un administrateur peut modifier ces champs"
            )

    try:
        service = UserService(db, tenant_id)
        return service.update(user_id, data)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateRPPSError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Désactive un utilisateur (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        service.delete(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# USER ROLES ENDPOINTS
# =============================================================================

@users_router.get("/{user_id}/roles", response_model=List[UserRoleResponse])
def get_user_roles(
        user_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Liste les rôles d'un utilisateur."""
    try:
        service = UserService(db, tenant_id)
        user = service.get_by_id(user_id)
        return user.role_associations
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.post("/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
def add_user_role(
        user_id: int,
        data: UserRoleCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Attribue un rôle à un utilisateur (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        return service.add_role(user_id, data.role_id, assigned_by=current_user.id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserAlreadyHasRoleError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@users_router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_role(
        user_id: int,
        role_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Retire un rôle à un utilisateur (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        service.remove_role(user_id, role_id)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# USER ENTITIES ENDPOINTS
# =============================================================================

@users_router.get("/{user_id}/entities", response_model=List[UserEntityResponse])
def get_user_entities(
        user_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Liste les entités rattachées à un utilisateur."""
    try:
        service = UserService(db, tenant_id)
        user = service.get_by_id(user_id)
        return user.entity_associations
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.post("/{user_id}/entities", response_model=UserEntityResponse, status_code=status.HTTP_201_CREATED)
def add_user_entity(
        user_id: int,
        data: UserEntityCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Rattache un utilisateur à une entité (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        return service.add_entity(user_id, data)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserEntityAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@users_router.patch("/{user_id}/entities/{entity_id}", response_model=UserEntityResponse)
def update_user_entity(
        user_id: int,
        entity_id: int,
        data: UserEntityUpdate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Met à jour le rattachement à une entité (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        return service.update_entity(user_id, entity_id, data)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.delete("/{user_id}/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_entity(
        user_id: int,
        entity_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """Détache un utilisateur d'une entité (admin uniquement)."""
    try:
        service = UserService(db, tenant_id)
        service.remove_entity(user_id, entity_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# USER AVAILABILITIES ENDPOINTS
# =============================================================================

@users_router.get("/{user_id}/availabilities", response_model=UserAvailabilityList)
def get_user_availabilities(
        user_id: int,
        entity_id: Optional[int] = Query(None, description="Filtrer par entité"),
        day_of_week: Optional[int] = Query(None, ge=1, le=7, description="Filtrer par jour"),
        is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Liste les disponibilités d'un utilisateur."""
    service = UserAvailabilityService(db, tenant_id)
    items = service.get_all_for_user(
        user_id, entity_id=entity_id, day_of_week=day_of_week, is_active=is_active
    )
    return UserAvailabilityList(items=items, total=len(items))


@users_router.post("/{user_id}/availabilities", response_model=UserAvailabilityResponse,
                   status_code=status.HTTP_201_CREATED)
def create_user_availability(
        user_id: int,
        data: UserAvailabilityCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Crée une disponibilité pour un utilisateur."""
    # L'utilisateur peut créer ses propres disponibilités ou l'admin peut le faire
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez gérer que vos propres disponibilités"
        )

    try:
        service = UserAvailabilityService(db, tenant_id)
        return service.create(user_id, data)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.get("/{user_id}/availabilities/{availability_id}", response_model=UserAvailabilityResponse)
def get_user_availability(
        user_id: int,
        availability_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Récupère une disponibilité par son ID."""
    try:
        service = UserAvailabilityService(db, tenant_id)
        availability = service.get_by_id(availability_id, user_id)
        return availability
    except AvailabilityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.patch("/{user_id}/availabilities/{availability_id}", response_model=UserAvailabilityResponse)
def update_user_availability(
        user_id: int,
        availability_id: int,
        data: UserAvailabilityUpdate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Met à jour une disponibilité."""
    # Vérifier les droits
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez gérer que vos propres disponibilités"
        )

    try:
        service = UserAvailabilityService(db, tenant_id)
        return service.update(availability_id, user_id, data)
    except AvailabilityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@users_router.delete("/{user_id}/availabilities/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_availability(
        user_id: int,
        availability_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """Supprime une disponibilité."""
    # Vérifier les droits
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez gérer que vos propres disponibilités"
        )

    try:
        service = UserAvailabilityService(db, tenant_id)
        service.delete(availability_id, user_id)
    except AvailabilityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(professions_router)
router.include_router(roles_router)
router.include_router(users_router)