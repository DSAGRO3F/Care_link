<script setup lang="ts">
  /**
   * CatalogDomainSection — Section domaine SERAFIN-PH.
   *
   * Affiche le header du domaine (icône colorée, titre, compteur)
   * puis la liste de CatalogCategoryCard.
   *
   * Mode 'platform' : DomainGroup — CRUD super-admin.
   * Mode 'admin'    : EntityDomainGroup — toggle activation + personnalisation.
   *
   * Icônes domaines : Activity (Soins), Users (Autonomie), Heart (Social).
   *
   * 🔄 v5.28 — Phase 3A : ajout mode admin avec EntityDomainGroup.
   */

  import { computed } from 'vue';

  import { Activity, Heart, Users } from 'lucide-vue-next';

  import CatalogCategoryCard from './CatalogCategoryCard.vue';
  import type {
    DomainGroup,
    EntityDomainGroup,
    MergedEntityService,
    ServiceTemplateSummary,
  } from '@/types';

  const props = defineProps<{
    group: DomainGroup | EntityDomainGroup;
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

  const isAdmin = computed(() => props.mode === 'admin');

  /** Icône Lucide par domaine */
  const domainIcons = {
    SOINS_SANTE: Activity,
    AUTONOMIE: Users,
    PARTICIPATION_SOCIALE: Heart,
  } as const;

  /** Compteur affiché : "X/Y activés" (admin) ou "X services" (platform) */
  const counterText = computed(() => {
    if (isAdmin.value) {
      const g = props.group as EntityDomainGroup;
      return `${g.activatedCount}/${g.totalCount} activé${g.activatedCount > 1 ? 's' : ''}`;
    }
    return `${props.group.totalCount} service${props.group.totalCount > 1 ? 's' : ''}`;
  });
</script>

<template>
  <div class="mb-6">
    <!-- Domain header -->
    <div class="flex items-center gap-3 py-2.5 mb-3 border-b-2 border-slate-100">
      <div
        :class="group.colors.icon"
        class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
      >
        <component :is="domainIcons[group.domain]" :size="16" :stroke-width="2.5" />
      </div>
      <span class="text-base font-bold text-slate-800">
        {{ group.label }}
      </span>
      <span class="text-xs text-slate-400 font-medium">
        {{ counterText }}
      </span>
    </div>

    <!-- Category cards -->
    <CatalogCategoryCard
      v-for="catGroup in group.categories"
      :key="catGroup.category"
      :group="catGroup"
      :domain="group.domain"
      :mode="mode"
      @edit="emit('edit', $event)"
      @deactivate="emit('deactivate', $event)"
      @reactivate="emit('reactivate', $event)"
      @toggle="emit('toggle', $event)"
      @save="(m, fields) => emit('save', m, fields)"
    />

    <!-- Message si aucune catégorie -->
    <div v-if="group.categories.length === 0" class="text-center py-8 text-sm text-slate-400">
      Aucun service dans ce domaine
    </div>
  </div>
</template>
