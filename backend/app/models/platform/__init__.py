"""
Platform models - Administration de la plateforme CareLink.

Ce module contient les modèles liés à la gestion de la plateforme :
- SuperAdmin : Administrateurs CareLink (équipe technique/commerciale)
- PlatformAuditLog : Logs d'audit des actions super-admin

Note v4.3 : UserTenantAssignment a été déplacé vers app.models.user
car il s'agit d'une association utilisateur, cohérent avec UserRole, UserEntity.
"""
from app.models.platform.platform_audit_log import PlatformAuditLog, AuditAction
from app.models.platform.super_admin import SuperAdmin, SuperAdminRole

__all__ = [
    "SuperAdmin",
    "SuperAdminRole",
    "PlatformAuditLog",
    "AuditAction",
]