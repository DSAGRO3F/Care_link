<script setup lang="ts">
  /**
   * CatalogCategoryCard — Carte accordéon pour une catégorie.
   *
   * Header cliquable : emoji, nom catégorie, méta (plage durées, professions),
   * badges compteurs, chevron animé.
   * Body : liste de CatalogServiceRow OU CatalogEntityServiceRow selon le mode.
   *
   * Mode 'platform' : ServiceTemplateSummary[] — CRUD super-admin.
   * Mode 'admin'    : MergedEntityService[] — toggle activation + personnalisation.
   *
   * 🔄 v5.28 — Phase 3A : ajout mode admin avec CatalogEntityServiceRow.
   */

  import { computed, ref } from 'vue';

  import { ChevronDown } from 'lucide-vue-next';

  import CatalogEntityServiceRow from './CatalogEntityServiceRow.vue';
  import CatalogServiceRow from './CatalogServiceRow.vue';
  import type {
    CategoryGroup,
    EntityCategoryGroup,
    MergedEntityService,
    ServiceDomain,
    ServiceTemplateSummary,
  } from '@/types';
  import { DOMAIN_COLORS } from '@/types';

  const props = defineProps<{
    group: CategoryGroup | EntityCategoryGroup;
    domain: ServiceDomain;
    mode?: 'platform' | 'admin';
  }>();

  const emit = defineEmits<{
    /** Platform mode events */
    edit: [service: ServiceTemplateSummary];
    deactivate: [service: ServiceTemplateSummary];
    reactivate: [service: ServiceTemplateSummary];
    /** Admin mode events */
    toggle: [merged: MergedEntityService];
    save: [
      merged: MergedEntityService,
      fields: { price_euros: number | null; custom_duration_minutes: number | null },
    ];
  }>();

  const expanded = ref(false);
  const isAdmin = computed(() => props.mode === 'admin');
  const colors = computed(() => DOMAIN_COLORS[props.domain]);

  /** Plage de durées (ex: "10–45 min") */
  const durationRange = computed(() => {
    const durations = isAdmin.value
      ? (props.group.services as MergedEntityService[]).map(
          (m) => m.template.default_duration_minutes,
        )
      : (props.group.services as ServiceTemplateSummary[]).map((s) => s.default_duration_minutes);

    if (durations.length === 0) return '';
    const min = Math.min(...durations);
    const max = Math.max(...durations);
    return min === max ? `${min} min` : `${min}–${max} min`;
  });

  /** Label compteur selon le mode */
  const counterLabel = computed(() => {
    if (isAdmin.value) {
      const g = props.group as EntityCategoryGroup;
      return `${g.activatedCount}/${g.totalCount} activé${g.activatedCount > 1 ? 's' : ''}`;
    }
    return `${props.group.totalCount} service${props.group.totalCount > 1 ? 's' : ''}`;
  });

  /** Badge actifs (platform) ou masqué (admin — intégré dans counterLabel) */
  const showActivesBadge = computed(() => !isAdmin.value);

  /** Hauteur max estimée pour l'animation accordéon */
  const maxBodyHeight = computed(() => {
    const serviceCount = props.group.services.length;
    const rowHeight = isAdmin.value ? 160 : 120;
    return `${serviceCount * rowHeight + 40}px`;
  });

  function toggleExpanded(): void {
    expanded.value = !expanded.value;
  }
</script>

<template>
  <div
    :class="expanded ? 'shadow-md border-teal-200' : 'border-slate-200 hover:border-slate-300'"
    class="bg-white border rounded-xl mb-2.5 overflow-hidden transition-all"
  >
    <!-- Header (cliquable) -->
    <div
      :class="expanded ? 'bg-teal-50 border-b border-teal-100' : 'hover:bg-slate-50'"
      class="flex items-center gap-3 px-4 py-3 cursor-pointer select-none transition-colors"
      @click="toggleExpanded"
    >
      <!-- Emoji catégorie -->
      <div
        :class="colors.icon"
        class="w-9 h-9 rounded-lg flex items-center justify-center text-base shrink-0"
      >
        {{ group.icon }}
      </div>

      <!-- Info catégorie -->
      <div class="flex-1 min-w-0">
        <div class="text-[0.9375rem] font-bold text-slate-800">
          {{ group.label }}
        </div>
        <div class="flex gap-3 items-center text-xs text-slate-400 mt-0.5">
          <span v-if="durationRange" class="flex items-center gap-1">
            {{ durationRange }}
          </span>
        </div>
      </div>

      <!-- Badges compteurs -->
      <div class="flex gap-1.5 items-center">
        <span
          :class="isAdmin ? 'bg-teal-50 text-teal-700' : 'bg-slate-100 text-slate-600'"
          class="px-2 py-0.5 rounded-full text-[0.6875rem] font-semibold"
        >
          {{ counterLabel }}
        </span>
        <span
          v-if="showActivesBadge"
          class="px-2 py-0.5 rounded-full text-[0.6875rem] font-semibold bg-emerald-50 text-emerald-600"
        >
          {{ (group as CategoryGroup).activeCount }} actif{{
            (group as CategoryGroup).activeCount > 1 ? 's' : ''
          }}
        </span>
      </div>

      <!-- Chevron -->
      <ChevronDown
        :size="16"
        :stroke-width="2"
        :class="expanded ? 'rotate-180 text-teal-600' : 'text-slate-400'"
        class="shrink-0 transition-transform duration-250"
      />
    </div>

    <!-- Body (accordéon) -->
    <div
      :style="{ maxHeight: expanded ? maxBodyHeight : '0px' }"
      class="overflow-hidden transition-all duration-350 ease-in-out"
    >
      <div class="p-3.5 bg-slate-50 space-y-2.5">
        <!-- Admin mode : CatalogEntityServiceRow -->
        <template v-if="isAdmin">
          <CatalogEntityServiceRow
            v-for="merged in group.services as MergedEntityService[]"
            :key="merged.template.id"
            :merged="merged"
            @toggle="emit('toggle', $event)"
            @save="(m, fields) => emit('save', m, fields)"
          />
        </template>

        <!-- Platform mode : CatalogServiceRow -->
        <template v-else>
          <CatalogServiceRow
            v-for="service in group.services as ServiceTemplateSummary[]"
            :key="service.id"
            :service="service"
            :mode="mode"
            @edit="emit('edit', $event)"
            @deactivate="emit('deactivate', $event)"
            @reactivate="emit('reactivate', $event)"
          />
        </template>

        <!-- Message si vide après filtrage -->
        <div v-if="group.services.length === 0" class="text-center py-6 text-sm text-slate-400">
          Aucun service dans cette catégorie
        </div>
      </div>
    </div>
  </div>
</template>
