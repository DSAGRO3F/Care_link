# app/api/v1/platform/__init__.py
"""
Module Platform API - Administration CareLink.
"""

from app.api.v1.platform.routes import router

# Exporter les dépendances de sécurité SuperAdmin
from app.api.v1.platform.super_admin_security import (
    get_current_super_admin,
    get_optional_super_admin,
    require_role,
    require_super_admin_permission,
    SuperAdminPermissions,
)

__all__ = [
    "router",
    # Sécurité SuperAdmin
    "get_current_super_admin",
    "get_optional_super_admin",
    "require_role",
    "require_super_admin_permission",
    "SuperAdminPermissions",
]