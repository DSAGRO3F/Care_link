-- =============================================================================
-- SCRIPT DE VÉRIFICATION RLS - CareLink
-- =============================================================================
-- Ce script vérifie que Row-Level Security est correctement configuré.
-- À exécuter après la migration.
-- =============================================================================

\echo '=============================================='
\echo 'VÉRIFICATION RLS - CareLink'
\echo '=============================================='
\echo ''

-- -----------------------------------------------------------------------------
-- 1. Vérifier que les fonctions existent
-- -----------------------------------------------------------------------------
\echo '1. Vérification des fonctions RLS...'

SELECT 
    proname AS function_name,
    CASE WHEN proname IS NOT NULL THEN '✅ OK' ELSE '❌ MANQUANT' END AS status
FROM pg_proc 
WHERE proname IN ('get_current_tenant_id', 'is_super_admin', 'check_tenant_access', 'check_tenant_access_with_assignments');

\echo ''

-- -----------------------------------------------------------------------------
-- 2. Vérifier que RLS est activé sur les tables
-- -----------------------------------------------------------------------------
\echo '2. Vérification de l''activation RLS sur les tables...'

SELECT 
    tablename,
    CASE WHEN rowsecurity THEN '✅ Activé' ELSE '❌ Désactivé' END AS rls_status,
    CASE WHEN forcerowsecurity THEN '✅ Forcé' ELSE '⚠️ Non forcé' END AS force_status
FROM pg_tables t
LEFT JOIN pg_class c ON c.relname = t.tablename
WHERE schemaname = 'public'
AND tablename IN (
    'entities', 'users', 'patients', 
    'patient_access', 'patient_evaluations', 'patient_thresholds',
    'patient_vitals', 'patient_devices', 'patient_documents',
    'coordination_entries', 'user_roles', 'user_entities',
    'user_availabilities', 'care_plans', 'care_plan_services',
    'scheduled_interventions', 'entity_services'
)
ORDER BY tablename;

\echo ''

-- -----------------------------------------------------------------------------
-- 3. Compter les policies par table
-- -----------------------------------------------------------------------------
\echo '3. Nombre de policies par table...'

SELECT 
    tablename,
    COUNT(*) AS policy_count,
    CASE 
        WHEN COUNT(*) >= 4 THEN '✅ Complet (4 policies)'
        WHEN COUNT(*) > 0 THEN '⚠️ Partiel'
        ELSE '❌ Aucune policy'
    END AS status
FROM pg_policies 
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

\echo ''

-- -----------------------------------------------------------------------------
-- 4. Détail des policies
-- -----------------------------------------------------------------------------
\echo '4. Détail des policies RLS...'

SELECT 
    tablename,
    policyname,
    cmd AS action,
    CASE WHEN permissive = 'PERMISSIVE' THEN 'Permissive' ELSE 'Restrictive' END AS type
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, cmd;

\echo ''

-- -----------------------------------------------------------------------------
-- 5. Test des fonctions
-- -----------------------------------------------------------------------------
\echo '5. Test des fonctions RLS...'

-- Test sans contexte
\echo 'Test sans contexte (doit retourner NULL):'
SELECT get_current_tenant_id() AS tenant_id;

-- Définir un contexte
SET app.current_tenant_id = '42';
SET app.is_super_admin = 'false';

\echo 'Test avec contexte tenant_id=42:'
SELECT get_current_tenant_id() AS tenant_id;
SELECT is_super_admin() AS is_admin;
SELECT check_tenant_access(42) AS access_to_42;
SELECT check_tenant_access(99) AS access_to_99;

-- Reset
RESET app.current_tenant_id;
RESET app.is_super_admin;

\echo ''

-- -----------------------------------------------------------------------------
-- 6. Vérifier le rôle applicatif
-- -----------------------------------------------------------------------------
\echo '6. Vérification du rôle applicatif...'

SELECT 
    rolname,
    CASE WHEN rolname IS NOT NULL THEN '✅ Existe' ELSE '❌ Manquant' END AS status,
    rolcanlogin AS can_login
FROM pg_roles 
WHERE rolname = 'carelink_app';

\echo ''

-- -----------------------------------------------------------------------------
-- 7. Résumé
-- -----------------------------------------------------------------------------
\echo '=============================================='
\echo 'RÉSUMÉ'
\echo '=============================================='

WITH stats AS (
    SELECT 
        (SELECT COUNT(*) FROM pg_proc WHERE proname IN ('get_current_tenant_id', 'is_super_admin', 'check_tenant_access')) AS functions_count,
        (SELECT COUNT(*) FROM pg_tables t JOIN pg_class c ON c.relname = t.tablename WHERE t.schemaname = 'public' AND c.relrowsecurity = true) AS tables_with_rls,
        (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public') AS policies_count
)
SELECT 
    functions_count || '/3 fonctions créées' AS fonctions,
    tables_with_rls || ' tables avec RLS activé' AS tables,
    policies_count || ' policies créées' AS policies
FROM stats;

\echo ''
\echo 'Pour tester manuellement:'
\echo '  SET app.current_tenant_id = ''1'';'
\echo '  SET app.is_super_admin = ''false'';'
\echo '  SELECT * FROM patients; -- Doit montrer uniquement les patients du tenant 1'
\echo ''
