/**
 * Store Pinia — Module Catalogue Coordination (Phase 3B).
 *
 * Chemin : frontend/src/stores/coordination-catalog.store.ts
 *
 * Rôle : état global de la vue coordination consolidée.
 * Charge le catalogue consolidé cross-entités via un seul appel API,
 * expose des vues groupées (domaine → catégorie → prestations) avec
 * filtres texte + domaine.
 *
 * Lecture seule — pas de CRUD. Le CRUD reste dans entity-catalog.store.
 *
 * Convention Pinia : defineStore + computed pour état réactif.
 * Convention #67 : tri explicite sur les computed ordonnées.
 */

import { computed, ref } from 'vue';

import { defineStore } from 'pinia';

import { coordinationCatalogService } from '@/services';
import type {
  ConsolidatedCatalogResponse,
  ConsolidatedCatalogSummary,
  ConsolidatedEntitySummary,
  ConsolidatedPrestation,
  CoordinationCategoryGroup,
  CoordinationDomainGroup,
  ServiceDomain,
} from '@/types';
import {
  CATEGORY_ICONS,
  CATEGORY_LABELS,
  DOMAIN_CATEGORY_MAP,
  DOMAIN_COLORS,
  DOMAIN_LABELS,
  DOMAIN_ORDER,
} from '@/types';

export const useCoordinationCatalogStore = defineStore('coordination-catalog', () => {
  // =========================================================================
  // STATE
  // =========================================================================

  const data = ref<ConsolidatedCatalogResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Filtre domaine actif (null = tous) */
  const activeDomainFilter = ref<ServiceDomain | null>(null);

  /** Recherche textuelle */
  const searchQuery = ref('');

  // =========================================================================
  // COMPUTED — Prestations filtrées
  // =========================================================================

  /** Prestations filtrées par recherche textuelle + domaine */
  const filteredPrestations = computed<ConsolidatedPrestation[]>(() => {
    if (!data.value) return [];

    let result = [...data.value.prestations];

    // Filtre domaine
    if (activeDomainFilter.value) {
      result = result.filter((p) => p.domain === activeDomainFilter.value);
    }

    // Filtre recherche textuelle
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      result = result.filter(
        (p) =>
          p.code.toLowerCase().includes(q) ||
          p.name.toLowerCase().includes(q) ||
          p.category_label.toLowerCase().includes(q),
      );
    }

    // Tri déterministe : domain_order → category → template_id (convention #67)
    return result.sort((a, b) => {
      const domainDiff =
        DOMAIN_ORDER.indexOf(a.domain as ServiceDomain) -
        DOMAIN_ORDER.indexOf(b.domain as ServiceDomain);
      if (domainDiff !== 0) return domainDiff;
      if (a.category !== b.category) return a.category.localeCompare(b.category);
      return a.template_id - b.template_id;
    });
  });

  // =========================================================================
  // COMPUTED — Vue groupée pour l'accordéon
  // =========================================================================

  /** Vue groupée : domaine → catégorie → prestations consolidées */
  const domainGroups = computed<CoordinationDomainGroup[]>(() => {
    const domainsToShow = activeDomainFilter.value ? [activeDomainFilter.value] : DOMAIN_ORDER;

    return domainsToShow
      .map((domain) => {
        const domainPrestations = filteredPrestations.value.filter((p) => p.domain === domain);
        if (domainPrestations.length === 0 && activeDomainFilter.value === null) {
          return null;
        }

        const categoryList = DOMAIN_CATEGORY_MAP[domain];
        const categoryGroups: CoordinationCategoryGroup[] = categoryList
          .map((cat) => {
            const prestations = domainPrestations
              .filter((p) => p.category === cat)
              .sort((a, b) => a.template_id - b.template_id);

            return {
              category: cat,
              label: CATEGORY_LABELS[cat],
              icon: CATEGORY_ICONS[cat],
              prestations,
              prestationCount: prestations.length,
              totalOffers: prestations.reduce((sum, p) => sum + p.offer_count, 0),
            };
          })
          .filter((g) => g.prestationCount > 0);

        return {
          domain,
          label: DOMAIN_LABELS[domain],
          colors: DOMAIN_COLORS[domain],
          categories: categoryGroups,
          prestationCount: domainPrestations.length,
          totalOffers: domainPrestations.reduce((sum, p) => sum + p.offer_count, 0),
        };
      })
      .filter((g): g is CoordinationDomainGroup => g !== null);
  });

  // =========================================================================
  // COMPUTED — Délégations summary
  // =========================================================================

  /** Summary global (compteurs + liste entités) */
  const summary = computed<ConsolidatedCatalogSummary | null>(() => data.value?.summary ?? null);

  /** Entités participantes (nestées dans summary) */
  const entities = computed<ConsolidatedEntitySummary[]>(() => data.value?.summary.entities ?? []);

  /** Compteurs individuels */
  const totalNational = computed(() => data.value?.summary.total_national ?? 0);
  const totalActivePrestations = computed(() => data.value?.summary.total_active_prestations ?? 0);
  const entitiesCount = computed(() => data.value?.summary.entities_count ?? 0);

  /** Compteurs par domaine (pour les chips filtres) */
  const domainCounts = computed(() => {
    if (!data.value) return {};
    const counts: Record<string, number> = {};
    for (const d of DOMAIN_ORDER) {
      counts[d] = data.value.prestations.filter((p) => p.domain === d).length;
    }
    return counts;
  });

  // =========================================================================
  // ACTIONS
  // =========================================================================

  /** Charge le catalogue consolidé cross-entités */
  async function loadConsolidated(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      data.value = await coordinationCatalogService.getConsolidated();
    } catch (err: unknown) {
      if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = 'Erreur lors du chargement du catalogue consolidé';
      }
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Filtre par domaine */
  function setDomainFilter(domain: ServiceDomain | null): void {
    activeDomainFilter.value = domain;
  }

  /** Recherche textuelle */
  function setSearchQuery(query: string): void {
    searchQuery.value = query;
  }

  /** Reset filtres */
  function resetFilters(): void {
    activeDomainFilter.value = null;
    searchQuery.value = '';
  }

  // =========================================================================
  // EXPOSE
  // =========================================================================

  return {
    // State
    data,
    loading,
    error,
    activeDomainFilter,
    searchQuery,

    // Computed — Prestations
    filteredPrestations,
    domainGroups,

    // Computed — Summary & entités
    summary,
    entities,
    totalNational,
    totalActivePrestations,
    entitiesCount,
    domainCounts,

    // Actions
    loadConsolidated,
    setDomainFilter,
    setSearchQuery,
    resetFilters,
  };
});
