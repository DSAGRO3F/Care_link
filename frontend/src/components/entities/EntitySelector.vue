<script setup lang="ts">
  /**
   * EntitySelector.vue — Sélecteur d'entité réutilisable
   *
   * Affiche la liste des entités du tenant avec indentation hiérarchique
   * et permet d'en sélectionner une via v-model.
   *
   * Usage :
   *   <EntitySelector
   *     v-model="selectedEntityId"
   *     @select="onEntitySelected"
   *   />
   *
   * Le composant charge les entités automatiquement au mount, ou accepte
   * une liste pré-chargée via la prop `entities`.
   *
   * Destination : src/components/entities/EntitySelector.vue
   */
  import { ref, computed, onMounted } from 'vue';
  import { entityService } from '@/services';
  import type { EntityResponse } from '@/types';

  // ─── Props ───────────────────────────────────────────────────────────────────

  interface Props {
    /** ID de l'entité sélectionnée (v-model) */
    modelValue: number | null;
    /** Liste d'entités pré-chargée (optionnel — sinon charge automatiquement) */
    entities?: EntityResponse[];
    /** Placeholder quand rien n'est sélectionné */
    placeholder?: string;
    /** Désactiver la sélection */
    disabled?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    entities: undefined,
    placeholder: 'Sélectionner une entité…',
    disabled: false,
  });

  const emit = defineEmits<{
    (e: 'update:modelValue', value: number | null): void;
    (e: 'select', entity: EntityResponse | null): void;
  }>();

  // ─── State ───────────────────────────────────────────────────────────────────

  const internalEntities = ref<EntityResponse[]>([]);
  const isLoading = ref(false);

  const allEntities = computed(() => props.entities ?? internalEntities.value);

  /** Entité actuellement sélectionnée */
  const selectedEntity = computed(
    () => allEntities.value.find((e) => e.id === props.modelValue) ?? null,
  );

  // ─── Hiérarchie ──────────────────────────────────────────────────────────────

  interface TreeItem {
    entity: EntityResponse;
    depth: number;
  }

  /** Construit une liste plate ordonnée par hiérarchie avec profondeur */
  const treeItems = computed<TreeItem[]>(() => {
    const items: TreeItem[] = [];
    const entities = allEntities.value;

    // Trouver les racines (parent_id null)
    const roots = entities.filter((e) => !e.parent_id);
    const childrenMap = new Map<number, EntityResponse[]>();

    for (const e of entities) {
      if (e.parent_id) {
        const siblings = childrenMap.get(e.parent_id) ?? [];
        siblings.push(e);
        childrenMap.set(e.parent_id, siblings);
      }
    }

    function walk(entity: EntityResponse, depth: number) {
      items.push({ entity, depth });
      const children = childrenMap.get(entity.id) ?? [];
      for (const child of children) {
        walk(child, depth + 1);
      }
    }

    for (const root of roots) {
      walk(root, 0);
    }

    // Ajouter les orphelins (entités dont le parent n'est pas dans la liste)
    const addedIds = new Set(items.map((i) => i.entity.id));
    for (const e of entities) {
      if (!addedIds.has(e.id)) {
        items.push({ entity: e, depth: 0 });
      }
    }

    return items;
  });

  // ─── Chargement ──────────────────────────────────────────────────────────────

  async function fetchEntities() {
    if (props.entities) return; // Liste fournie en prop
    isLoading.value = true;
    try {
      internalEntities.value = await entityService.list();
    } catch (err) {
      console.error('[EntitySelector] Erreur chargement:', err);
    } finally {
      isLoading.value = false;
    }
  }

  // ─── Sélection ───────────────────────────────────────────────────────────────

  function select(entity: EntityResponse) {
    if (props.disabled) return;
    emit('update:modelValue', entity.id);
    emit('select', entity);
  }

  function clear() {
    emit('update:modelValue', null);
    emit('select', null);
  }

  // ─── Lifecycle ───────────────────────────────────────────────────────────────

  onMounted(() => {
    fetchEntities();
  });
</script>

<template>
  <div class="entity-selector">
    <!-- État : entité sélectionnée -->
    <div
      v-if="selectedEntity"
      class="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl px-4 py-3"
    >
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center">
          <i class="pi pi-building text-blue-600"></i>
        </div>
        <div>
          <p class="font-medium text-slate-800 text-sm">{{ selectedEntity.name }}</p>
          <p class="text-xs text-slate-500">
            {{ selectedEntity.entity_type }}
            <span v-if="selectedEntity.city"> · {{ selectedEntity.city }}</span>
          </p>
        </div>
      </div>
      <button
        v-if="!disabled"
        class="text-sm text-slate-400 hover:text-slate-700 transition-colors"
        @click="clear"
      >
        <i class="pi pi-times"></i>
      </button>
    </div>

    <!-- État : chargement -->
    <div v-else-if="isLoading" class="flex items-center justify-center py-8">
      <i class="pi pi-spin pi-spinner text-blue-500 text-xl"></i>
    </div>

    <!-- État : liste vide -->
    <div v-else-if="allEntities.length === 0" class="text-center py-8">
      <p class="text-slate-400 text-sm">Aucune entité disponible</p>
    </div>

    <!-- État : liste de sélection -->
    <div v-else class="space-y-1 max-h-72 overflow-y-auto rounded-xl border border-slate-200 p-2">
      <button
        v-for="{ entity, depth } in treeItems"
        :key="entity.id"
        :class="[
          modelValue === entity.id
            ? 'bg-blue-50 border border-blue-300'
            : 'hover:bg-slate-50 border border-transparent',
          disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        ]"
        :style="{ paddingLeft: `${12 + depth * 20}px` }"
        :disabled="disabled"
        class="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg transition-all text-left"
        @click="select(entity)"
      >
        <!-- Icône indentation -->
        <i v-if="depth > 0" class="pi pi-minus text-slate-300 text-xs"></i>

        <div class="w-7 h-7 rounded bg-slate-100 flex items-center justify-center shrink-0">
          <i class="pi pi-building text-slate-400 text-xs"></i>
        </div>

        <div class="flex-1 min-w-0">
          <p :class="depth === 0 ? 'font-medium' : ''" class="text-sm text-slate-700 truncate">
            {{ entity.name }}
          </p>
          <p class="text-xs text-slate-400">{{ entity.entity_type }}</p>
        </div>

        <i v-if="modelValue === entity.id" class="pi pi-check-circle text-blue-500 shrink-0"></i>
      </button>
    </div>
  </div>
</template>
