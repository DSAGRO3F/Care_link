"""
Module Platform — Opérations SuperAdmin sur le parc CareLink.

Ce module expose les endpoints qui manipulent le parc de tenants dans
son ensemble ou des ressources transversales : création/listing de
tenants, gestion des entités, audit global, statistiques, gestion
des SuperAdmins.

Tous les endpoints sont protégés par require_super_admin_permission.

Règle de placement : un router va ici si son URL ne nécessite PAS un
{tenant_id} dans le path. Sinon, voir le module tenants/.

Voir backend_spec — section "Architecture : Frontière platform/ vs tenants/"
pour la règle complète.
"""

from app.api.v1.platform.routes import router

# Exporter les dépendances de sécurité SuperAdmin
from app.api.v1.platform.super_admin_security import (
    SuperAdminPermissions,
    get_current_super_admin,
    get_optional_super_admin,
    require_role,
    require_super_admin_permission,
)


__all__ = [
    "SuperAdminPermissions",
    # Sécurité SuperAdmin
    "get_current_super_admin",
    "get_optional_super_admin",
    "require_role",
    "require_super_admin_permission",
    "router",
]
