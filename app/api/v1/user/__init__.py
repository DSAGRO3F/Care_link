# app/api/v1/user/__init__.py
"""
Module User API.
"""

from app.api.v1.user.routes import router

# Exporter les dépendances de sécurité
from app.api.v1.user.tenant_users_security import (
    get_current_tenant_id,
    get_optional_tenant_id,
    get_active_tenant_id,
    TenantContext,
    verify_write_permission,
    CurrentTenantId,
    ActiveTenantId,
    OptionalTenantId,
    TenantCtx,
)

__all__ = [
    "router",
    # Sécurité tenant
    "get_current_tenant_id",
    "get_optional_tenant_id",
    "get_active_tenant_id",
    "TenantContext",
    "verify_write_permission",
    "CurrentTenantId",
    "ActiveTenantId",
    "OptionalTenantId",
    "TenantCtx",
]