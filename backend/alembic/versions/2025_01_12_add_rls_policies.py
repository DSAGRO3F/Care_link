"""add_rls_policies

Revision ID: c3d4e5f6a7b8
Revises: d2d7f0966055
Create Date: 2025-01-12

Cette migration configure Row-Level Security (RLS) pour l'isolation multi-tenant :
1. Crée les fonctions PostgreSQL pour le contexte tenant
2. Active RLS sur les tables avec tenant_id
3. Crée les politiques d'isolation par tenant
4. Configure le bypass pour les super-admins

IMPORTANT: Cette migration nécessite PostgreSQL 9.5+
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision = 'd2d7f0966055'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# =============================================================================
# CONFIGURATION - Tables avec tenant_id direct
# =============================================================================

# Tables principales avec tenant_id direct
TABLES_WITH_TENANT_ID = [
    'entities',
    'users', 
    'patients',
    'patient_access',
    'patient_evaluations',
    'patient_thresholds',
    'patient_vitals',
    'patient_devices',
    'patient_documents',
    'coordination_entries',
    'user_roles',
    'user_entities',
    'user_availabilities',
    'care_plans',
    'care_plan_services',
    'scheduled_interventions',
    'entity_services',
]

# Tables de référence globales (pas de RLS)
GLOBAL_TABLES = [
    'countries',
    'professions', 
    'roles',
    'service_templates',
    'tenants',  # La table tenant elle-même
    'super_admins',
    'platform_audit_logs',
    'user_tenant_assignments',
]


# =============================================================================
# HELPERS
# =============================================================================

def table_exists(table_name: str) -> bool:
    """Vérifie si une table existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = '{table_name}'
    """))
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    """Vérifie si une colonne existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}' 
        AND column_name = '{column_name}'
    """))
    return result.fetchone() is not None


def function_exists(function_name: str) -> bool:
    """Vérifie si une fonction existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM pg_proc 
        WHERE proname = '{function_name}'
    """))
    return result.fetchone() is not None


def policy_exists(policy_name: str, table_name: str) -> bool:
    """Vérifie si une policy RLS existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM pg_policies 
        WHERE policyname = '{policy_name}' AND tablename = '{table_name}'
    """))
    return result.fetchone() is not None


# =============================================================================
# UPGRADE
# =============================================================================

def upgrade() -> None:
    """Configure Row-Level Security pour l'isolation multi-tenant."""
    
    # =========================================================================
    # 1. Créer la fonction pour récupérer le tenant_id courant
    # =========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_tenant_id()
        RETURNS INTEGER AS $$
        DECLARE
            tenant_id_str TEXT;
        BEGIN
            -- Récupère le tenant_id depuis la variable de session PostgreSQL
            -- Définie par l'application via: SET app.current_tenant_id = '123'
            tenant_id_str := current_setting('app.current_tenant_id', true);
            
            -- Retourne NULL si non défini ou vide
            IF tenant_id_str IS NULL OR tenant_id_str = '' THEN
                RETURN NULL;
            END IF;
            
            RETURN tenant_id_str::INTEGER;
        EXCEPTION
            WHEN OTHERS THEN
                -- En cas d'erreur de conversion, retourne NULL
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        COMMENT ON FUNCTION get_current_tenant_id() IS 
            'Récupère le tenant_id de la session courante pour RLS';
    """)
    
    # =========================================================================
    # 2. Créer la fonction pour vérifier si c'est un super-admin
    # =========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION is_super_admin()
        RETURNS BOOLEAN AS $$
        DECLARE
            is_admin_str TEXT;
        BEGIN
            -- Récupère le flag super-admin depuis la session
            is_admin_str := current_setting('app.is_super_admin', true);
            
            IF is_admin_str IS NULL OR is_admin_str = '' THEN
                RETURN FALSE;
            END IF;
            
            RETURN is_admin_str::BOOLEAN;
        EXCEPTION
            WHEN OTHERS THEN
                RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        COMMENT ON FUNCTION is_super_admin() IS 
            'Vérifie si la session courante est un super-admin (bypass RLS)';
    """)
    
    # =========================================================================
    # 3. Créer la fonction principale de vérification d'accès tenant
    # =========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION check_tenant_access(row_tenant_id INTEGER)
        RETURNS BOOLEAN AS $$
        DECLARE
            current_tenant INTEGER;
        BEGIN
            -- Super-admin bypass: accès à tout
            IF is_super_admin() THEN
                RETURN TRUE;
            END IF;
            
            -- Récupérer le tenant courant
            current_tenant := get_current_tenant_id();
            
            -- Si pas de tenant défini, refuser l'accès (sécurité par défaut)
            IF current_tenant IS NULL THEN
                RETURN FALSE;
            END IF;
            
            -- Vérifier que le tenant_id de la ligne correspond
            RETURN row_tenant_id = current_tenant;
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        COMMENT ON FUNCTION check_tenant_access(INTEGER) IS 
            'Vérifie si l''utilisateur a accès à une ligne selon son tenant_id';
    """)
    
    # =========================================================================
    # 4. Créer la fonction pour les accès cross-tenant (via assignments)
    # =========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION check_tenant_access_with_assignments(
            row_tenant_id INTEGER,
            check_user_id INTEGER DEFAULT NULL
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            current_tenant INTEGER;
            has_assignment BOOLEAN;
        BEGIN
            -- Super-admin bypass
            IF is_super_admin() THEN
                RETURN TRUE;
            END IF;
            
            current_tenant := get_current_tenant_id();
            
            IF current_tenant IS NULL THEN
                RETURN FALSE;
            END IF;
            
            -- Accès direct au tenant principal
            IF row_tenant_id = current_tenant THEN
                RETURN TRUE;
            END IF;
            
            -- Vérifier les assignments cross-tenant si un user_id est fourni
            IF check_user_id IS NOT NULL THEN
                SELECT EXISTS(
                    SELECT 1 FROM user_tenant_assignments
                    WHERE user_id = check_user_id
                    AND tenant_id = row_tenant_id
                    AND is_active = TRUE
                    AND (expires_at IS NULL OR expires_at > NOW())
                ) INTO has_assignment;
                
                RETURN has_assignment;
            END IF;
            
            RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        COMMENT ON FUNCTION check_tenant_access_with_assignments(INTEGER, INTEGER) IS 
            'Vérifie l''accès tenant avec support des assignments cross-tenant';
    """)
    
    # =========================================================================
    # 5. Activer RLS et créer les politiques pour chaque table
    # =========================================================================
    
    for table_name in TABLES_WITH_TENANT_ID:
        if not table_exists(table_name):
            print(f"  ⚠️  Table {table_name} n'existe pas, skip")
            continue
            
        if not column_exists(table_name, 'tenant_id'):
            print(f"  ⚠️  Table {table_name} n'a pas de tenant_id, skip")
            continue
        
        print(f"  ✅ Configuration RLS pour {table_name}")
        
        # -----------------------------------------------------------------
        # 5a. Activer RLS sur la table
        # -----------------------------------------------------------------
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
        
        # -----------------------------------------------------------------
        # 5b. Forcer RLS même pour le propriétaire de la table
        #     (important pour que l'app user soit aussi soumis au RLS)
        # -----------------------------------------------------------------
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;")
        
        # -----------------------------------------------------------------
        # 5c. Politique SELECT : lecture des données du tenant courant
        # -----------------------------------------------------------------
        policy_name = f"tenant_isolation_select_{table_name}"
        if not policy_exists(policy_name, table_name):
            op.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                FOR SELECT
                USING (check_tenant_access(tenant_id));
            """)
        
        # -----------------------------------------------------------------
        # 5d. Politique INSERT : insertion uniquement dans le tenant courant
        # -----------------------------------------------------------------
        policy_name = f"tenant_isolation_insert_{table_name}"
        if not policy_exists(policy_name, table_name):
            op.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                FOR INSERT
                WITH CHECK (
                    -- Super-admin peut insérer partout
                    is_super_admin() 
                    OR 
                    -- Sinon, le tenant_id doit correspondre au tenant courant
                    tenant_id = get_current_tenant_id()
                );
            """)
        
        # -----------------------------------------------------------------
        # 5e. Politique UPDATE : modification des données du tenant courant
        # -----------------------------------------------------------------
        policy_name = f"tenant_isolation_update_{table_name}"
        if not policy_exists(policy_name, table_name):
            op.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                FOR UPDATE
                USING (check_tenant_access(tenant_id))
                WITH CHECK (
                    -- Empêcher le changement de tenant_id (sauf super-admin)
                    is_super_admin()
                    OR
                    tenant_id = get_current_tenant_id()
                );
            """)
        
        # -----------------------------------------------------------------
        # 5f. Politique DELETE : suppression des données du tenant courant
        # -----------------------------------------------------------------
        policy_name = f"tenant_isolation_delete_{table_name}"
        if not policy_exists(policy_name, table_name):
            op.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                FOR DELETE
                USING (check_tenant_access(tenant_id));
            """)

# =========================================================================
# 6. Rôle applicatif
# =========================================================================
# Le rôle "carelink" (défini dans DATABASE_URL) est déjà configuré
# comme rôle non-superuser, donc RLS sera appliqué automatiquement.
#
# Pour un nouveau déploiement, voir docs/RLS_GUIDE.md pour créer
# un rôle applicatif dédié si nécessaire.


# =============================================================================
# DOWNGRADE
# =============================================================================

def downgrade() -> None:
    """Supprime la configuration RLS."""
    
    # =========================================================================
    # 1. Désactiver RLS et supprimer les politiques
    # =========================================================================
    
    for table_name in TABLES_WITH_TENANT_ID:
        if not table_exists(table_name):
            continue
        
        # Supprimer les politiques
        for action in ['select', 'insert', 'update', 'delete']:
            policy_name = f"tenant_isolation_{action}_{table_name}"
            if policy_exists(policy_name, table_name):
                op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")
        
        # Désactiver RLS
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")
    
    # =========================================================================
    # 2. Supprimer les fonctions
    # =========================================================================
    
    op.execute("DROP FUNCTION IF EXISTS check_tenant_access_with_assignments(INTEGER, INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS check_tenant_access(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS is_super_admin();")
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant_id();")
    
    # =========================================================================
    # 3. Supprimer le rôle applicatif (optionnel)
    # =========================================================================
    
    # Note: Ne pas supprimer le rôle automatiquement car il pourrait
    # être propriétaire d'objets
    # op.execute("DROP ROLE IF EXISTS carelink_app;")
