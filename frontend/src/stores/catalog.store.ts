/**
 * Store Pinia — Module Catalogue.
 *
 * État global :
 * - templates[] : liste plate de tous les service templates
 * - domainGroups[] : vue groupée domaine → catégorie → services (computed)
 * - filters : recherche textuelle + filtre domaine
 * - CRUD : create, update, deactivate avec refresh automatique
 *
 * Convention #67 : tri explicite sur les computed ordonnées.
 * Convention Pinia facade : defineStore + computed pour état réactif.
 */

import { computed, ref } from 'vue';

import { defineStore } from 'pinia';

import { catalogService } from '@/services';
import type {
  CategoryGroup,
  CategoryWithCounts,
  DomainGroup,
  DomainWithCounts,
  ServiceDomain,
  ServiceTemplateCreate,
  ServiceTemplateResponse,
  ServiceTemplateSummary,
  ServiceTemplateUpdate,
} from '@/types';
import {
  CATEGORY_ICONS,
  CATEGORY_LABELS,
  DOMAIN_CATEGORY_MAP,
  DOMAIN_COLORS,
  DOMAIN_LABELS,
  DOMAIN_ORDER,
} from '@/types';

export const useCatalogStore = defineStore('catalog', () => {
  // =========================================================================
  // STATE
  // =========================================================================

  const templates = ref<ServiceTemplateSummary[]>([]);
  const domains = ref<DomainWithCounts[]>([]);
  const categories = ref<CategoryWithCounts[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Filtre domaine actif (null = tous) */
  const activeDomainFilter = ref<ServiceDomain | null>(null);

  /** Recherche textuelle */
  const searchQuery = ref('');

  /** Afficher les inactifs */
  const showInactive = ref(true);

  // =========================================================================
  // COMPUTED — Vue groupée pour l'accordéon
  // =========================================================================

  /** Templates filtrés par recherche + domaine + statut */
  const filteredTemplates = computed(() => {
    let result = [...templates.value];

    // Filtre domaine
    if (activeDomainFilter.value) {
      result = result.filter((t) => t.domain === activeDomainFilter.value);
    }

    // Filtre statut
    if (!showInactive.value) {
      result = result.filter((t) => t.is_active);
    }

    // Filtre recherche textuelle
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      result = result.filter(
        (t) =>
          t.code.toLowerCase().includes(q) ||
          t.name.toLowerCase().includes(q) ||
          t.category_label.toLowerCase().includes(q),
      );
    }

    // Tri déterministe : domain_order → category → display_order implicite (id)
    return result.sort((a, b) => {
      const domainDiff = DOMAIN_ORDER.indexOf(a.domain) - DOMAIN_ORDER.indexOf(b.domain);
      if (domainDiff !== 0) return domainDiff;
      if (a.category !== b.category) return a.category.localeCompare(b.category);
      return a.id - b.id;
    });
  });

  /** Vue groupée : domaine → catégorie → services */
  const domainGroups = computed<DomainGroup[]>(() => {
    const domainsToShow = activeDomainFilter.value ? [activeDomainFilter.value] : DOMAIN_ORDER;

    return domainsToShow
      .map((domain) => {
        const domainTemplates = filteredTemplates.value.filter((t) => t.domain === domain);
        if (domainTemplates.length === 0 && activeDomainFilter.value === null) return null;

        const categoryList = DOMAIN_CATEGORY_MAP[domain];
        const categoryGroups: CategoryGroup[] = categoryList
          .map((cat) => {
            const services = domainTemplates
              .filter((t) => t.category === cat)
              .sort((a, b) => a.id - b.id);

            return {
              category: cat,
              label: CATEGORY_LABELS[cat],
              icon: CATEGORY_ICONS[cat],
              services,
              activeCount: services.filter((s) => s.is_active).length,
              totalCount: services.length,
            };
          })
          .filter((g) => g.totalCount > 0);

        return {
          domain,
          label: DOMAIN_LABELS[domain],
          colors: DOMAIN_COLORS[domain],
          categories: categoryGroups,
          activeCount: domainTemplates.filter((t) => t.is_active).length,
          totalCount: domainTemplates.length,
        };
      })
      .filter((g): g is DomainGroup => g !== null);
  });

  /** Compteurs globaux */
  const totalActive = computed(() => templates.value.filter((t) => t.is_active).length);
  const totalInactive = computed(() => templates.value.filter((t) => !t.is_active).length);
  const totalCount = computed(() => templates.value.length);

  /** Compteurs par domaine (pour les chips filtres) */
  const domainCounts = computed(() => {
    const counts: Record<string, number> = {};
    for (const d of DOMAIN_ORDER) {
      counts[d] = templates.value.filter((t) => t.domain === d).length;
    }
    return counts;
  });

  // =========================================================================
  // ACTIONS
  // =========================================================================

  /** Charge tous les service templates + domaines + catégories */
  async function fetchAll(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      // Charger tous les templates (size=100, max autorisé par PaginationParams)
      const [templateData, domainData, categoryData] = await Promise.all([
        catalogService.getAll(1, 100),
        catalogService.getDomains(),
        catalogService.getCategories(),
      ]);

      templates.value = templateData.items;
      domains.value = domainData;
      categories.value = categoryData;
    } catch (err: unknown) {
      if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = 'Erreur lors du chargement du catalogue';
      }
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Crée un service template et rafraîchit la liste */
  async function createTemplate(payload: ServiceTemplateCreate): Promise<ServiceTemplateResponse> {
    const created = await catalogService.create(payload);
    await fetchAll();
    return created;
  }

  /** Met à jour un service template et rafraîchit la liste */
  async function updateTemplate(
    id: number,
    payload: ServiceTemplateUpdate,
  ): Promise<ServiceTemplateResponse> {
    const updated = await catalogService.update(id, payload);
    await fetchAll();
    return updated;
  }

  /** Désactive un service template et rafraîchit la liste */
  async function deactivateTemplate(id: number): Promise<void> {
    await catalogService.deactivate(id);
    await fetchAll();
  }

  /** Réactive un service template (PATCH status: active) */
  async function reactivateTemplate(id: number): Promise<void> {
    await catalogService.update(id, { status: 'active' });
    await fetchAll();
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
    showInactive.value = true;
  }

  /** Trouve un template par son ID dans le cache local */
  function getTemplateById(id: number): ServiceTemplateSummary | undefined {
    return templates.value.find((t) => t.id === id);
  }

  // =========================================================================
  // EXPOSE
  // =========================================================================

  return {
    // State
    templates,
    domains,
    categories,
    loading,
    error,
    activeDomainFilter,
    searchQuery,
    showInactive,

    // Computed
    filteredTemplates,
    domainGroups,
    totalActive,
    totalInactive,
    totalCount,
    domainCounts,

    // Actions
    fetchAll,
    createTemplate,
    updateTemplate,
    deactivateTemplate,
    reactivateTemplate,
    setDomainFilter,
    setSearchQuery,
    resetFilters,
    getTemplateById,
  };
});
