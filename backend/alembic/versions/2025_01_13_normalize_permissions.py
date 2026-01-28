"""normalize_permissions_tables

Revision ID: normalize_permissions
Revises: ea35c5fec585
Create Date: 2025-01-13

Cette migration normalise la gestion des permissions :
- Crée la table `permissions` pour stocker les permissions individuelles
- Crée la table `role_permissions` pour associer rôles et permissions
- Supprime la colonne JSON `permissions` de la table `roles`

Avantages :
- Contraintes d'intégrité (FK) au lieu de JSON non validé
- Requêtes SQL efficaces sur les permissions
- Traçabilité (qui a accordé quelle permission, quand)
- Permissions custom par tenant
"""

from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'normalize_permissions'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# =============================================================================
# DONNÉES INITIALES
# =============================================================================

INITIAL_PERMISSIONS = [
    # ADMIN
    {"code": "ADMIN_FULL", "name": "Accès administrateur complet", 
     "description": "Donne accès à toutes les fonctionnalités sans restriction",
     "category": "ADMIN", "is_system": True, "display_order": 1},
    
    # PATIENT
    {"code": "PATIENT_VIEW", "name": "Voir les patients",
     "description": "Permet de consulter les dossiers patients",
     "category": "PATIENT", "is_system": True, "display_order": 10},
    {"code": "PATIENT_CREATE", "name": "Créer un patient",
     "description": "Permet de créer un nouveau dossier patient",
     "category": "PATIENT", "is_system": True, "display_order": 11},
    {"code": "PATIENT_EDIT", "name": "Modifier un patient",
     "description": "Permet de modifier les informations d'un patient",
     "category": "PATIENT", "is_system": True, "display_order": 12},
    {"code": "PATIENT_DELETE", "name": "Supprimer un patient",
     "description": "Permet de supprimer ou archiver un dossier patient",
     "category": "PATIENT", "is_system": True, "display_order": 13},
    
    # EVALUATION
    {"code": "EVALUATION_VIEW", "name": "Voir les évaluations",
     "description": "Permet de consulter les évaluations AGGIR",
     "category": "EVALUATION", "is_system": True, "display_order": 20},
    {"code": "EVALUATION_CREATE", "name": "Créer une évaluation",
     "description": "Permet de créer une nouvelle évaluation",
     "category": "EVALUATION", "is_system": True, "display_order": 21},
    {"code": "EVALUATION_EDIT", "name": "Modifier une évaluation",
     "description": "Permet de modifier une évaluation existante",
     "category": "EVALUATION", "is_system": True, "display_order": 22},
    {"code": "EVALUATION_VALIDATE", "name": "Valider une évaluation",
     "description": "Permet de valider officiellement une évaluation",
     "category": "EVALUATION", "is_system": True, "display_order": 23},
    
    # VITALS
    {"code": "VITALS_VIEW", "name": "Voir les constantes",
     "description": "Permet de consulter les constantes vitales",
     "category": "VITALS", "is_system": True, "display_order": 30},
    {"code": "VITALS_CREATE", "name": "Saisir des constantes",
     "description": "Permet de saisir de nouvelles mesures",
     "category": "VITALS", "is_system": True, "display_order": 31},
    
    # USER
    {"code": "USER_VIEW", "name": "Voir les utilisateurs",
     "description": "Permet de consulter la liste des professionnels",
     "category": "USER", "is_system": True, "display_order": 40},
    {"code": "USER_CREATE", "name": "Créer un utilisateur",
     "description": "Permet de créer un nouveau compte utilisateur",
     "category": "USER", "is_system": True, "display_order": 41},
    {"code": "USER_EDIT", "name": "Modifier un utilisateur",
     "description": "Permet de modifier les informations d'un utilisateur",
     "category": "USER", "is_system": True, "display_order": 42},
    {"code": "USER_DELETE", "name": "Supprimer un utilisateur",
     "description": "Permet de désactiver ou supprimer un compte",
     "category": "USER", "is_system": True, "display_order": 43},
    
    # COORDINATION
    {"code": "COORDINATION_VIEW", "name": "Voir la coordination",
     "description": "Permet de consulter le carnet de coordination",
     "category": "COORDINATION", "is_system": True, "display_order": 50},
    {"code": "COORDINATION_CREATE", "name": "Créer une entrée",
     "description": "Permet d'ajouter une entrée au carnet",
     "category": "COORDINATION", "is_system": True, "display_order": 51},
    {"code": "COORDINATION_EDIT", "name": "Modifier une entrée",
     "description": "Permet de modifier une entrée de coordination",
     "category": "COORDINATION", "is_system": True, "display_order": 52},
    
    # CAREPLAN
    {"code": "CAREPLAN_VIEW", "name": "Voir les plans d'aide",
     "description": "Permet de consulter les plans d'aide",
     "category": "CAREPLAN", "is_system": True, "display_order": 60},
    {"code": "CAREPLAN_CREATE", "name": "Créer un plan d'aide",
     "description": "Permet de créer un nouveau plan d'aide",
     "category": "CAREPLAN", "is_system": True, "display_order": 61},
    {"code": "CAREPLAN_EDIT", "name": "Modifier un plan d'aide",
     "description": "Permet de modifier un plan d'aide existant",
     "category": "CAREPLAN", "is_system": True, "display_order": 62},
    {"code": "CAREPLAN_VALIDATE", "name": "Valider un plan d'aide",
     "description": "Permet de valider officiellement un plan d'aide",
     "category": "CAREPLAN", "is_system": True, "display_order": 63},
    
    # ACCESS
    {"code": "ACCESS_GRANT", "name": "Accorder un accès",
     "description": "Permet d'accorder l'accès à un dossier patient",
     "category": "ACCESS", "is_system": True, "display_order": 70},
    {"code": "ACCESS_REVOKE", "name": "Révoquer un accès",
     "description": "Permet de révoquer l'accès à un dossier patient",
     "category": "ACCESS", "is_system": True, "display_order": 71},
    
    # ROLE
    {"code": "ROLE_VIEW", "name": "Voir les rôles",
     "description": "Permet de consulter les rôles et leurs permissions",
     "category": "ROLE", "is_system": True, "display_order": 80},
    {"code": "ROLE_CREATE", "name": "Créer un rôle",
     "description": "Permet de créer un nouveau rôle personnalisé",
     "category": "ROLE", "is_system": True, "display_order": 81},
    {"code": "ROLE_EDIT", "name": "Modifier un rôle",
     "description": "Permet de modifier un rôle et ses permissions",
     "category": "ROLE", "is_system": True, "display_order": 82},
    {"code": "ROLE_DELETE", "name": "Supprimer un rôle",
     "description": "Permet de supprimer un rôle personnalisé",
     "category": "ROLE", "is_system": True, "display_order": 83},
    {"code": "ROLE_ASSIGN", "name": "Attribuer un rôle",
     "description": "Permet d'attribuer un rôle à un utilisateur",
     "category": "ROLE", "is_system": True, "display_order": 84},
]

INITIAL_ROLE_PERMISSIONS = {
    "ADMIN": ["ADMIN_FULL"],
    "COORDINATEUR": [
        "PATIENT_VIEW", "PATIENT_CREATE", "PATIENT_EDIT",
        "EVALUATION_VIEW", "EVALUATION_CREATE",
        "COORDINATION_VIEW", "COORDINATION_CREATE", "COORDINATION_EDIT",
        "CAREPLAN_VIEW", "CAREPLAN_CREATE", "CAREPLAN_EDIT",
        "USER_VIEW",
        "ACCESS_GRANT", "ACCESS_REVOKE",
        "ROLE_VIEW", "ROLE_ASSIGN"
    ],
    "MEDECIN_TRAITANT": [
        "PATIENT_VIEW", "PATIENT_EDIT",
        "EVALUATION_VIEW", "EVALUATION_CREATE", "EVALUATION_VALIDATE",
        "VITALS_VIEW", "VITALS_CREATE",
        "COORDINATION_VIEW", "COORDINATION_CREATE",
        "CAREPLAN_VIEW", "CAREPLAN_VALIDATE"
    ],
    "MEDECIN_SPECIALISTE": [
        "PATIENT_VIEW",
        "EVALUATION_VIEW",
        "VITALS_VIEW",
        "COORDINATION_VIEW"
    ],
    "INFIRMIERE": [
        "PATIENT_VIEW", "PATIENT_EDIT",
        "EVALUATION_VIEW", "EVALUATION_CREATE",
        "VITALS_VIEW", "VITALS_CREATE",
        "COORDINATION_VIEW", "COORDINATION_CREATE", "COORDINATION_EDIT",
        "CAREPLAN_VIEW"
    ],
    "AIDE_SOIGNANTE": [
        "PATIENT_VIEW",
        "EVALUATION_VIEW",
        "VITALS_VIEW", "VITALS_CREATE",
        "COORDINATION_VIEW", "COORDINATION_CREATE"
    ],
    "KINESITHERAPEUTE": [
        "PATIENT_VIEW",
        "EVALUATION_VIEW",
        "VITALS_VIEW",
        "COORDINATION_VIEW", "COORDINATION_CREATE"
    ],
    "AUXILIAIRE_VIE": [
        "PATIENT_VIEW",
        "COORDINATION_VIEW", "COORDINATION_CREATE"
    ],
    "ASSISTANT_SOCIAL": [
        "PATIENT_VIEW",
        "EVALUATION_VIEW",
        "COORDINATION_VIEW", "COORDINATION_CREATE"
    ],
    "INTERVENANT": [
        "PATIENT_VIEW",
        "VITALS_VIEW",
        "COORDINATION_VIEW"
    ]
}


# =============================================================================
# HELPERS
# =============================================================================

def table_exists(table_name: str) -> bool:
    """Vérifie si une table existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()


def column_exists(table_name: str, column_name: str) -> bool:
    """Vérifie si une colonne existe dans une table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def constraint_exists(constraint_name: str) -> bool:
    """Vérifie si une contrainte existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM pg_constraint WHERE conname = '{constraint_name}'
        )
    """))
    return result.scalar()


# =============================================================================
# UPGRADE
# =============================================================================

def upgrade() -> None:
    """Upgrade schema - Normaliser les permissions."""
    
    # =========================================================================
    # 1. CRÉER LA TABLE permissions
    # =========================================================================
    
    if not table_exists('permissions'):
        op.create_table(
            'permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), 
                      sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                      nullable=True, index=True),
            sa.Column('code', sa.String(50), nullable=False, index=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('category', sa.String(30), nullable=False, index=True),
            sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
            sa.Column('display_order', sa.Integer(), nullable=False, default=100),
            sa.Column('created_at', sa.DateTime(), nullable=False, 
                      default=datetime.now(timezone.utc)),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('code', 'tenant_id', name='uq_permission_code_tenant'),
            comment='Table des permissions granulaires du système'
        )
        
        # Insérer les permissions système
        conn = op.get_bind()
        now = datetime.now(timezone.utc)
        
        for perm in INITIAL_PERMISSIONS:
            conn.execute(sa.text("""
                INSERT INTO permissions (code, name, description, category, is_system, display_order, created_at)
                VALUES (:code, :name, :description, :category, :is_system, :display_order, :created_at)
            """), {
                "code": perm["code"],
                "name": perm["name"],
                "description": perm["description"],
                "category": perm["category"],
                "is_system": perm["is_system"],
                "display_order": perm["display_order"],
                "created_at": now
            })
    
    # =========================================================================
    # 2. CRÉER LA TABLE role_permissions
    # =========================================================================
    
    if not table_exists('role_permissions'):
        op.create_table(
            'role_permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('role_id', sa.Integer(),
                      sa.ForeignKey('roles.id', ondelete='CASCADE'),
                      nullable=False, index=True),
            sa.Column('permission_id', sa.Integer(),
                      sa.ForeignKey('permissions.id', ondelete='CASCADE'),
                      nullable=False, index=True),
            sa.Column('tenant_id', sa.Integer(),
                      sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                      nullable=True, index=True),
            sa.Column('granted_at', sa.DateTime(), nullable=False,
                      default=datetime.now(timezone.utc)),
            sa.Column('granted_by_id', sa.Integer(),
                      sa.ForeignKey('users.id', ondelete='SET NULL'),
                      nullable=True),
            sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
            comment='Table de jonction Role ↔ Permission (many-to-many)'
        )
        
        # Récupérer les IDs des rôles et permissions pour créer les associations
        conn = op.get_bind()
        now = datetime.now(timezone.utc)
        
        # Récupérer tous les rôles système existants
        roles_result = conn.execute(sa.text("""
            SELECT id, name FROM roles WHERE is_system_role = true
        """))
        roles = {row[1]: row[0] for row in roles_result}
        
        # Récupérer toutes les permissions système
        perms_result = conn.execute(sa.text("""
            SELECT id, code FROM permissions WHERE is_system = true
        """))
        permissions = {row[1]: row[0] for row in perms_result}
        
        # Créer les associations
        for role_name, perm_codes in INITIAL_ROLE_PERMISSIONS.items():
            if role_name in roles:
                role_id = roles[role_name]
                for perm_code in perm_codes:
                    if perm_code in permissions:
                        perm_id = permissions[perm_code]
                        conn.execute(sa.text("""
                            INSERT INTO role_permissions (role_id, permission_id, granted_at)
                            VALUES (:role_id, :permission_id, :granted_at)
                        """), {
                            "role_id": role_id,
                            "permission_id": perm_id,
                            "granted_at": now
                        })
    
    # =========================================================================
    # 3. SUPPRIMER LA COLONNE JSON permissions DE roles
    # =========================================================================
    
    if column_exists('roles', 'permissions'):
        op.drop_column('roles', 'permissions')


# =============================================================================
# DOWNGRADE
# =============================================================================

def downgrade() -> None:
    """Downgrade schema - Restaurer la colonne JSON permissions."""
    
    # =========================================================================
    # 1. RESTAURER LA COLONNE JSON permissions SUR roles
    # =========================================================================
    
    if not column_exists('roles', 'permissions'):
        op.add_column('roles', 
            sa.Column('permissions', sa.JSON(), nullable=True, default=list)
        )
        
        # Reconstruire les permissions JSON depuis role_permissions
        conn = op.get_bind()
        
        # Pour chaque rôle, récupérer ses permissions et les stocker en JSON
        roles_result = conn.execute(sa.text("SELECT id FROM roles"))
        for (role_id,) in roles_result:
            perms_result = conn.execute(sa.text("""
                SELECT p.code 
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = :role_id
            """), {"role_id": role_id})
            
            perm_codes = [row[0] for row in perms_result]
            
            # Mettre à jour avec le JSON
            import json
            conn.execute(sa.text("""
                UPDATE roles SET permissions = :perms WHERE id = :role_id
            """), {"perms": json.dumps(perm_codes), "role_id": role_id})
    
    # =========================================================================
    # 2. SUPPRIMER LA TABLE role_permissions
    # =========================================================================
    
    if table_exists('role_permissions'):
        op.drop_table('role_permissions')
    
    # =========================================================================
    # 3. SUPPRIMER LA TABLE permissions
    # =========================================================================
    
    if table_exists('permissions'):
        op.drop_table('permissions')
