-- =============================================================================
-- 🆕 B40-J3 — FIL D'ÉCHANGE DU PORTAIL DE VALIDATION (Phase 4 bis)
-- =============================================================================
-- Table validation_exchanges : RLS standard par tenant_id (4 policies),
-- jumelle stricte de validation_requests (patron tenant standard).
--
-- Décision d'architecture (D32) : la RLS ne porte QUE l'isolation tenant.
-- Le besoin-d'en-connaître intra-tenant (visibility INTERNAL_ONLY / SHARED_EXTERNAL)
-- est porté au service/serializer, JAMAIS en RLS.
--
-- Total après ce bloc : +1 table, +4 policies → 22 tables protégées, 89 policies.
--
-- Hors Alembic (décision projet : les policies RLS vivent dans ce script SQL).
-- À concaténer dans rls_policies.sql ; exécutable aussi en standalone — idempotent
-- grâce aux DROP POLICY IF EXISTS.
-- =============================================================================

BEGIN;

-- --- ENABLE + FORCE RLS ---
ALTER TABLE public.validation_exchanges ENABLE ROW LEVEL SECURITY;
ALTER TABLE ONLY public.validation_exchanges FORCE ROW LEVEL SECURITY;

-- --- validation_exchanges : RLS standard par tenant_id ---

DROP POLICY IF EXISTS tenant_isolation_select_validation_exchanges ON public.validation_exchanges;
CREATE POLICY tenant_isolation_select_validation_exchanges ON public.validation_exchanges FOR SELECT USING (public.check_tenant_access(tenant_id));

DROP POLICY IF EXISTS tenant_isolation_insert_validation_exchanges ON public.validation_exchanges;
CREATE POLICY tenant_isolation_insert_validation_exchanges ON public.validation_exchanges FOR INSERT WITH CHECK ((public.is_super_admin() OR (tenant_id = public.get_current_tenant_id())));

DROP POLICY IF EXISTS tenant_isolation_update_validation_exchanges ON public.validation_exchanges;
CREATE POLICY tenant_isolation_update_validation_exchanges ON public.validation_exchanges FOR UPDATE USING (public.check_tenant_access(tenant_id));

DROP POLICY IF EXISTS tenant_isolation_delete_validation_exchanges ON public.validation_exchanges;
CREATE POLICY tenant_isolation_delete_validation_exchanges ON public.validation_exchanges FOR DELETE USING (public.check_tenant_access(tenant_id));

COMMIT;