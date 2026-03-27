<script setup lang="ts">
  /**
   * EntityTreeView — Arborescence interactive des entités
   *
   * v6 — Ajout des props tenantCode, childCount, totalUsers
   *       pour la grille d'infos du card racine (EntityTreeNode)
   *
   * Reconstruit l'arbre hiérarchique depuis une liste plate d'EntityResponse,
   * gère l'état expand/collapse, et délègue le rendu à EntityTreeNode.
   *
   * Destination : src/components/entities/EntityTreeView.vue
   */
  import { computed, ref, watch } from 'vue';
  import { ROOT_ENTITY_TYPES, type EntityResponse } from '@/types';

  import EntityTreeNode, { type TreeNode } from './EntityTreeNode.vue';

  // =============================================================================
  // PROPS & EMITS
  // =============================================================================

  interface Props {
    entities: EntityResponse[];
    dark?: boolean;
    readonly?: boolean;
    selectedId?: number | null;
    /** Code structure du tenant (affiché dans la grille racine) */
    tenantCode?: string;
    /** Nombre total d'entités rattachées (hors racine) */
    childCount?: number;
    /** Nombre total de professionnels */
    totalUsers?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    dark: false,
    readonly: false,
    selectedId: null,
    tenantCode: '',
    childCount: 0,
    totalUsers: 0,
  });

  const emit = defineEmits<{
    select: [entity: EntityResponse];
    create: [parentId: number | null];
    edit: [entity: EntityResponse];
    delete: [entity: EntityResponse];
  }>();

  // =============================================================================
  // TREE CONSTRUCTION — Liste plate → arbre hiérarchique
  // =============================================================================

  const tree = computed<TreeNode[]>(() => {
    const map = new Map<number, TreeNode>();
    const roots: TreeNode[] = [];

    // 1ère passe : créer les nœuds
    for (const e of props.entities) {
      map.set(e.id, { ...e, _children: [] });
    }

    // 2ème passe : rattacher enfants à parents
    for (const e of props.entities) {
      const node = map.get(e.id)!;
      if (e.parent_id && map.has(e.parent_id)) {
        map.get(e.parent_id)!._children.push(node);
      } else {
        roots.push(node);
      }
    }

    return roots;
  });

  // =============================================================================
  // EXPAND / COLLAPSE
  // =============================================================================

  const expandedIds = ref<Set<number>>(new Set());

  function initExpanded() {
    for (const e of props.entities) {
      if (ROOT_ENTITY_TYPES.includes(e.entity_type)) {
        expandedIds.value.add(e.id);
      }
    }
  }

  watch(
    () => props.entities,
    () => initExpanded(),
    { immediate: true },
  );

  function toggleExpand(id: number) {
    if (expandedIds.value.has(id)) {
      expandedIds.value.delete(id);
    } else {
      expandedIds.value.add(id);
    }
  }

  function expandAll() {
    for (const e of props.entities) expandedIds.value.add(e.id);
  }

  function collapseAll() {
    expandedIds.value.clear();
  }

  defineExpose({ expandAll, collapseAll });
</script>

<template>
  <div class="entity-tree-view">
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-3 px-1">
      <div class="flex items-center gap-2">
        <button
          :class="
            dark
              ? 'text-slate-400 hover:text-white hover:bg-slate-700'
              : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100'
          "
          class="text-xs px-2.5 py-1 rounded-md transition-colors"
          @click="expandAll"
        >
          <i class="pi pi-angle-double-down text-[10px] mr-1"></i>Tout ouvrir
        </button>
        <button
          :class="
            dark
              ? 'text-slate-400 hover:text-white hover:bg-slate-700'
              : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-100'
          "
          class="text-xs px-2.5 py-1 rounded-md transition-colors"
          @click="collapseAll"
        >
          <i class="pi pi-angle-double-up text-[10px] mr-1"></i>Tout fermer
        </button>
      </div>

      <span :class="dark ? 'text-slate-500' : 'text-zinc-400'" class="text-xs">
        {{ entities.length }} entité{{ entities.length !== 1 ? 's' : '' }}
      </span>
    </div>

    <!-- Nœuds de l'arbre -->
    <div class="space-y-0.5">
      <EntityTreeNode
        v-for="root in tree"
        :key="root.id"
        :node="root"
        :depth="0"
        :dark="dark"
        :readonly="readonly"
        :selected-id="selectedId"
        :expanded-ids="expandedIds"
        :tenant-code="tenantCode"
        :child-count="childCount"
        :total-users="totalUsers"
        @select="(e) => emit('select', e)"
        @create="(pid) => emit('create', pid)"
        @edit="(e) => emit('edit', e)"
        @delete="(e) => emit('delete', e)"
        @toggle="toggleExpand"
      />
    </div>

    <!-- État vide -->
    <div
      v-if="tree.length === 0"
      :class="dark ? 'border-slate-700 text-slate-500' : 'border-zinc-200 text-zinc-400'"
      class="text-center py-12 rounded-xl border-2 border-dashed"
    >
      <i class="pi pi-sitemap text-3xl mb-3 block opacity-40"></i>
      <p class="text-sm font-medium">Aucune entité</p>
      <p class="text-xs mt-1 opacity-70">Créez la première entité de cette structure</p>
    </div>
  </div>
</template>
