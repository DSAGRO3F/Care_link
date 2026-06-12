/**
 * Store Pinia — Entities (entités accessibles à l'utilisateur dans son tenant)
 *
 * Chemin : frontend/src/stores/entity.store.ts
 *
 * Rôle : état global des entités (SSIAD, SAAD, EHPAD, GCSMS, GTSMS…) du tenant
 * courant. Chargé une fois au besoin, mis en cache via le flag `loaded`,
 * réutilisable pour tous les écrans qui doivent proposer une sélection
 * d'entité (création plan d'aide en Phase 4, vues inter-entités en F6/F7,
 * futur outil de remplacement en Phase 6+).
 *
 * Le backend filtre automatiquement par `tenant_id` via `get_current_tenant_id`,
 * donc aucun paramètre tenant n'est nécessaire côté front.
 *
 * Décision architecturale : Piste A (vrai store Pinia dédié) — validée en
 * session 3 étape 2 du 08/04/2026. Justification : cohérence avec le pattern
 * `entity-catalog.store.ts` existant, réutilisabilité transverse, coût mémoire
 * négligeable (6 entités en moyenne par tenant).
 *
 * Convention Pinia : defineStore + setup function + computed pour état réactif.
 * Convention #67 : tri explicite sur les computed ordonnées.
 */

import { computed, ref } from 'vue';

import { defineStore } from 'pinia';

import { entityService } from '@/services';
import type { EntityResponse, EntityType } from '@/types';
import { EntityTypeLabels } from '@/types';

/** Option structurée pour alimenter un `<Select>` PrimeVue. */
export interface EntityOption {
  value: number;
  label: string;
  typeLabel: string;
  entityType: EntityType;
  entity: EntityResponse;
}

export const useEntityStore = defineStore('entity', () => {
  // =========================================================================
  // STATE
  // =========================================================================

  /** Entités accessibles à l'utilisateur courant (dans son tenant) */
  const entities = ref<EntityResponse[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Flag de cache : true si le chargement a abouti au moins une fois */
  const loaded = ref(false);

  // =========================================================================
  // COMPUTED
  // =========================================================================

  /** Map id → EntityResponse pour lookup O(1) (utile édition, détail) */
  const entityById = computed(() => {
    const index = new Map<number, EntityResponse>();
    for (const entity of entities.value) {
      index.set(entity.id, entity);
    }
    return index;
  });

  /**
   * Entités actives uniquement — exclut les entités archivées qui ne doivent
   * pas apparaître dans un Select de création (sémantiquement on ne rattache
   * pas un nouveau plan d'aide à une entité désactivée).
   */
  const activeEntities = computed(() => entities.value.filter((e) => e.is_active !== false));

  /**
   * Options triées pour un `<Select>` PrimeVue.
   * Tri : nom A→Z insensible à la casse et aux accents (convention #67).
   * Label primaire = nom de l'entité, labelType affiché en secondaire.
   */
  const entityOptions = computed<EntityOption[]>(() => {
    return activeEntities.value
      .map((entity) => ({
        value: entity.id,
        label: entity.name,
        typeLabel: EntityTypeLabels[entity.entity_type as EntityType] ?? entity.entity_type,
        entityType: entity.entity_type as EntityType,
        entity,
      }))
      .sort((a, b) => a.label.localeCompare(b.label, 'fr', { sensitivity: 'base' }));
  });

  // =========================================================================
  // ACTIONS
  // =========================================================================

  /**
   * Charge la liste des entités du tenant courant.
   * Idempotent grâce au flag `loaded` : si déjà chargé, no-op sauf si
   * `force=true` (utile après un CRUD d'entité pour rafraîchir le cache).
   */
  async function load(force = false): Promise<void> {
    if (loaded.value && !force) return;

    loading.value = true;
    error.value = null;

    try {
      entities.value = await entityService.list();
      loaded.value = true;
    } catch (err: unknown) {
      if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = 'Erreur lors du chargement des entités';
      }
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Réinitialise le store (utile au logout / changement de tenant) */
  function reset(): void {
    entities.value = [];
    loading.value = false;
    error.value = null;
    loaded.value = false;
  }

  // =========================================================================
  // EXPOSE
  // =========================================================================

  return {
    // State
    entities,
    loading,
    error,
    loaded,

    // Computed
    entityById,
    activeEntities,
    entityOptions,

    // Actions
    load,
    reset,
  };
});
