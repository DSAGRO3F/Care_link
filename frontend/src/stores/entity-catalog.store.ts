/**
 * Store Pinia — Module Catalogue Admin Tenant (Phase 3A).
 *
 * Responsabilité :
 * - Charger le catalogue national (service_templates) + les services entité
 * - Merger les deux sources en MergedEntityService[] pour l'UI
 * - Vue groupée domaine → catégorie → services fusionnés (accordéon)
 * - CRUD : activer, personnaliser, désactiver un service pour l'entité
 *
 * Convention #67 : tri explicite sur les computed ordonnées.
 * Convention Pinia facade : defineStore + computed pour état réactif.
 * Convention #72 : size ≤ 100 (géré dans le service).
 */

import { computed, ref } from 'vue';

import { defineStore } from 'pinia';

import { entityCatalogService } from '@/services';
import type {
  EntityCategoryGroup,
  EntityDomainGroup,
  EntityServiceCreate,
  EntityServiceResponse,
  EntityServiceUpdate,
  MergedEntityService,
  ServiceDomain,
  ServiceTemplateSummary,
} from '@/types';
import {
  CATEGORY_ICONS,
  CATEGORY_LABELS,
  DOMAIN_CATEGORY_MAP,
  DOMAIN_COLORS,
  DOMAIN_LABELS,
  DOMAIN_ORDER,
} from '@/types';

export const useEntityCatalogStore = defineStore('entityCatalog', () => {
  // =========================================================================
  // STATE
  // =========================================================================

  /** ID de l'entité actuellement sélectionnée */
  const entityId = ref<number | null>(null);

  /** Catalogue national complet (tous les templates actifs) */
  const nationalTemplates = ref<ServiceTemplateSummary[]>([]);

  /** Services activés/personnalisés par l'entité */
  const entityServices = ref<EntityServiceResponse[]>([]);

  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);

  /** Filtre domaine actif (null = tous) */
  const activeDomainFilter = ref<ServiceDomain | null>(null);

  /** Recherche textuelle */
  const searchQuery = ref('');

  /** Afficher uniquement les services activés */
  const showActivatedOnly = ref(false);

  // =========================================================================
  // COMPUTED — Merge national ↔ entity
  // =========================================================================

  /**
   * Index entity_services par service_template_id pour lookup O(1).
   * Un template peut n'avoir qu'un seul entity_service par entité.
   */
  const entityServiceIndex = computed(() => {
    const index = new Map<number, EntityServiceResponse>();
    for (const es of entityServices.value) {
      index.set(es.service_template_id, es);
    }
    return index;
  });

  /**
   * Fusion complète : chaque template national est enrichi avec
   * les données de l'entité (si activé) ou null (si non activé).
   */
  const mergedServices = computed<MergedEntityService[]>(() => {
    return nationalTemplates.value.map((template) => {
      const es = entityServiceIndex.value.get(template.id) ?? null;
      const isActivated = es !== null && es.is_active;

      return {
        template,
        entityService: es,
        isActivated,
        effectiveDuration: es?.custom_duration_minutes ?? template.default_duration_minutes,
        effectivePrice: es?.price_euros ?? null,
        effectiveFrequency: es?.max_capacity_week ?? null,
        hasCustomization:
          es !== null &&
          (es.has_custom_duration || es.has_custom_price || es.max_capacity_week !== null),
      };
    });
  });

  /** Services fusionnés filtrés par recherche + domaine + statut */
  const filteredMergedServices = computed(() => {
    let result = [...mergedServices.value];

    // Filtre domaine
    if (activeDomainFilter.value) {
      result = result.filter((m) => m.template.domain === activeDomainFilter.value);
    }

    // Filtre activés uniquement
    if (showActivatedOnly.value) {
      result = result.filter((m) => m.isActivated);
    }

    // Filtre recherche textuelle
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      result = result.filter(
        (m) =>
          m.template.code.toLowerCase().includes(q) ||
          m.template.name.toLowerCase().includes(q) ||
          m.template.category_label.toLowerCase().includes(q),
      );
    }

    // Tri déterministe : domain_order → category → id
    return result.sort((a, b) => {
      const domainDiff =
        DOMAIN_ORDER.indexOf(a.template.domain) - DOMAIN_ORDER.indexOf(b.template.domain);
      if (domainDiff !== 0) return domainDiff;
      if (a.template.category !== b.template.category) {
        return a.template.category.localeCompare(b.template.category);
      }
      return a.template.id - b.template.id;
    });
  });

  /** Vue groupée : domaine → catégorie → services fusionnés (pour l'accordéon) */
  const domainGroups = computed<EntityDomainGroup[]>(() => {
    const domainsToShow = activeDomainFilter.value ? [activeDomainFilter.value] : DOMAIN_ORDER;

    return domainsToShow
      .map((domain) => {
        const domainServices = filteredMergedServices.value.filter(
          (m) => m.template.domain === domain,
        );
        if (domainServices.length === 0 && activeDomainFilter.value === null) return null;

        const categoryList = DOMAIN_CATEGORY_MAP[domain];
        const categoryGroups: EntityCategoryGroup[] = categoryList
          .map((cat) => {
            const services = domainServices
              .filter((m) => m.template.category === cat)
              .sort((a, b) => a.template.id - b.template.id);

            return {
              category: cat,
              label: CATEGORY_LABELS[cat],
              icon: CATEGORY_ICONS[cat],
              services,
              activatedCount: services.filter((s) => s.isActivated).length,
              totalCount: services.length,
            };
          })
          .filter((g) => g.totalCount > 0);

        return {
          domain,
          label: DOMAIN_LABELS[domain],
          colors: DOMAIN_COLORS[domain],
          categories: categoryGroups,
          activatedCount: domainServices.filter((s) => s.isActivated).length,
          totalCount: domainServices.length,
        };
      })
      .filter((g): g is EntityDomainGroup => g !== null);
  });

  // =========================================================================
  // COMPUTED — Compteurs
  // =========================================================================

  /** Nombre de services activés par l'entité */
  const activatedCount = computed(() => mergedServices.value.filter((m) => m.isActivated).length);

  /** Nombre total de services dans le référentiel national */
  const nationalCount = computed(() => nationalTemplates.value.length);

  /** Compteurs par domaine (pour les chips filtres — basé sur le national) */
  const domainCounts = computed(() => {
    const counts: Record<string, number> = {};
    for (const d of DOMAIN_ORDER) {
      counts[d] = nationalTemplates.value.filter((t) => t.domain === d).length;
    }
    return counts;
  });

  /** Compteurs activés par domaine */
  const activatedDomainCounts = computed(() => {
    const counts: Record<string, number> = {};
    for (const d of DOMAIN_ORDER) {
      counts[d] = mergedServices.value.filter(
        (m) => m.template.domain === d && m.isActivated,
      ).length;
    }
    return counts;
  });

  // =========================================================================
  // ACTIONS — Chargement
  // =========================================================================

  /**
   * Charge le catalogue pour une entité donnée.
   * Deux appels en parallèle : catalogue national + services entité.
   */
  async function loadCatalog(targetEntityId: number): Promise<void> {
    entityId.value = targetEntityId;
    loading.value = true;
    error.value = null;

    try {
      const [templates, services] = await Promise.all([
        entityCatalogService.getAllNationalTemplates(),
        entityCatalogService.getEntityServices(targetEntityId),
      ]);

      nationalTemplates.value = templates;
      entityServices.value = services;
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

  /** Recharge uniquement les services entité (après un CRUD) */
  async function refreshEntityServices(): Promise<void> {
    if (!entityId.value) return;
    try {
      entityServices.value = await entityCatalogService.getEntityServices(entityId.value);
    } catch (err: unknown) {
      if (err instanceof Error) {
        error.value = err.message;
      }
    }
  }

  // =========================================================================
  // ACTIONS — CRUD entity services
  // =========================================================================

  /**
   * Active un service du catalogue national pour l'entité courante.
   * Crée un entity_service avec les valeurs par défaut.
   */
  async function activateService(
    templateId: number,
    customization?: Partial<EntityServiceCreate>,
  ): Promise<EntityServiceResponse> {
    if (!entityId.value) throw new Error('Aucune entité sélectionnée');
    saving.value = true;

    try {
      const payload: EntityServiceCreate = {
        service_template_id: templateId,
        is_active: true,
        ...customization,
      };
      const created = await entityCatalogService.activateService(entityId.value, payload);
      await refreshEntityServices();
      return created;
    } finally {
      saving.value = false;
    }
  }

  /**
   * Désactive un service pour l'entité courante.
   */
  async function deactivateService(entityServiceId: number): Promise<void> {
    if (!entityId.value) throw new Error('Aucune entité sélectionnée');
    saving.value = true;

    try {
      await entityCatalogService.deactivateService(entityId.value, entityServiceId);
      await refreshEntityServices();
    } finally {
      saving.value = false;
    }
  }

  /**
   * Met à jour la personnalisation d'un service entité.
   * Utilisé pour tarif, durée, fréquence, notes.
   */
  async function updateCustomization(
    entityServiceId: number,
    payload: EntityServiceUpdate,
  ): Promise<EntityServiceResponse> {
    if (!entityId.value) throw new Error('Aucune entité sélectionnée');
    saving.value = true;

    try {
      const updated = await entityCatalogService.updateService(
        entityId.value,
        entityServiceId,
        payload,
      );
      await refreshEntityServices();
      return updated;
    } finally {
      saving.value = false;
    }
  }

  /**
   * Toggle activation/désactivation d'un service.
   * Si pas encore activé → crée l'entity_service.
   * Si activé → désactive (DELETE).
   */
  async function toggleService(merged: MergedEntityService): Promise<void> {
    if (merged.isActivated && merged.entityService) {
      await deactivateService(merged.entityService.id);
    } else {
      await activateService(merged.template.id);
    }
  }

  // =========================================================================
  // ACTIONS — Filtres
  // =========================================================================

  function setDomainFilter(domain: ServiceDomain | null): void {
    activeDomainFilter.value = domain;
  }

  function setSearchQuery(query: string): void {
    searchQuery.value = query;
  }

  function resetFilters(): void {
    activeDomainFilter.value = null;
    searchQuery.value = '';
    showActivatedOnly.value = false;
  }

  // =========================================================================
  // EXPOSE
  // =========================================================================

  return {
    // State
    entityId,
    nationalTemplates,
    entityServices,
    loading,
    saving,
    error,
    activeDomainFilter,
    searchQuery,
    showActivatedOnly,

    // Computed — merge
    mergedServices,
    filteredMergedServices,
    domainGroups,

    // Computed — compteurs
    activatedCount,
    nationalCount,
    domainCounts,
    activatedDomainCounts,

    // Actions — chargement
    loadCatalog,
    refreshEntityServices,

    // Actions — CRUD
    activateService,
    deactivateService,
    updateCustomization,
    toggleService,

    // Actions — filtres
    setDomainFilter,
    setSearchQuery,
    resetFilters,
  };
});
