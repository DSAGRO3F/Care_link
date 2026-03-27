# app/api/v1/user/__init__.py
"""
Module User API.
"""

from app.api.v1.user.routes import router

# Exporter les dépendances de sécurité
from app.api.v1.user.tenant_users_security import (
    CurrentTenantId,
    OptionalTenantId,
    TenantContext,
    TenantCtx,
    get_current_tenant_id,
    get_optional_tenant_id,
    verify_write_permission,
)


__all__ = [
    "CurrentTenantId",
    "OptionalTenantId",
    "TenantContext",
    "TenantCtx",
    # Sécurité tenant
    "get_current_tenant_id",
    "get_optional_tenant_id",
    "router",
    "verify_write_permission",
]
