<script setup lang="ts">
  /**
   * CatalogToolbar — Barre de recherche + filtres domaine + stats.
   *
   * Mode 'platform' : stats actifs/inactifs du référentiel national.
   * Mode 'admin'    : stats activés/disponibles pour l'entité.
   *
   * Chips filtre : Tous + 3 domaines avec compteurs.
   *
   * 🔄 v5.28 — Phase 3A : ajout mode admin avec compteurs activés.
   */

  import { computed } from 'vue';

  import { Search } from 'lucide-vue-next';

  import type { CatalogViewMode, ServiceDomain } from '@/types';
  import { DOMAIN_LABELS, DOMAIN_ORDER } from '@/types';

  const props = defineProps<{
    searchQuery: string;
    activeDomain: ServiceDomain | null;
    domainCounts: Record<string, number>;
    totalCount: number;
    totalActive: number;
    totalInactive: number;
    mode?: CatalogViewMode;
  }>();

  const emit = defineEmits<{
    'update:searchQuery': [value: string];
    'update:activeDomain': [value: ServiceDomain | null];
  }>();

  const isAdmin = computed(() => props.mode === 'admin');

  /** Placeholder de recherche adapté au mode */
  const searchPlaceholder = computed(() =>
    isAdmin.value
      ? 'Rechercher une prestation (nom, code, mot-clé)...'
      : 'Rechercher un service (nom, code, mot-clé)...',
  );
</script>

<template>
  <div class="flex items-center gap-3 mb-6 flex-wrap">
    <!-- Search box -->
    <div class="flex-1 min-w-[240px] max-w-[400px] relative">
      <Search
        :size="16"
        :stroke-width="2"
        class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        :value="searchQuery"
        :placeholder="searchPlaceholder"
        type="text"
        class="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-xl text-sm bg-white text-slate-700 focus:outline-none focus:border-teal-400 focus:ring-3 focus:ring-teal-400/10 placeholder:text-slate-400 transition"
        @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- Domain chips -->
    <button
      :class="
        activeDomain === null
          ? 'bg-teal-50 border-teal-300 text-teal-700 font-semibold'
          : 'bg-white border-slate-200 text-slate-600 hover:border-teal-300 hover:text-teal-600'
      "
      class="px-3.5 py-1.5 rounded-full text-[0.8125rem] font-medium border cursor-pointer transition-all"
      @click="emit('update:activeDomain', null)"
    >
      Tous
      <span
        :class="activeDomain === null ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-500'"
        class="inline-flex items-center justify-center min-w-[1.25rem] h-5 rounded-full text-[0.6875rem] font-bold ml-1.5 px-1"
      >
        {{ totalCount }}
      </span>
    </button>

    <button
      v-for="domain in DOMAIN_ORDER"
      :key="domain"
      :class="
        activeDomain === domain
          ? 'bg-teal-50 border-teal-300 text-teal-700 font-semibold'
          : 'bg-white border-slate-200 text-slate-600 hover:border-teal-300 hover:text-teal-600'
      "
      class="px-3.5 py-1.5 rounded-full text-[0.8125rem] font-medium border cursor-pointer transition-all"
      @click="emit('update:activeDomain', domain)"
    >
      {{ DOMAIN_LABELS[domain] }}
      <span
        :class="
          activeDomain === domain ? 'bg-teal-100 text-teal-700' : 'bg-slate-100 text-slate-500'
        "
        class="inline-flex items-center justify-center min-w-[1.25rem] h-5 rounded-full text-[0.6875rem] font-bold ml-1.5 px-1"
      >
        {{ domainCounts[domain] || 0 }}
      </span>
    </button>

    <!-- Stats badges -->
    <div class="flex gap-2 ml-auto items-center">
      <!-- Admin mode : activés / disponibles -->
      <template v-if="isAdmin">
        <div
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-teal-50 text-teal-700"
        >
          <span class="w-2 h-2 rounded-full bg-teal-500" />
          {{ totalActive }} activé{{ totalActive > 1 ? 's' : '' }}
        </div>
        <div
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600"
        >
          <span class="w-2 h-2 rounded-full bg-slate-300" />
          {{ totalCount }} disponibles
        </div>
      </template>

      <!-- Platform mode : actifs / inactifs -->
      <template v-else>
        <div
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600"
        >
          <span class="w-2 h-2 rounded-full bg-emerald-500" />
          {{ totalActive }} actifs
        </div>
        <div
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600"
        >
          <span class="w-2 h-2 rounded-full bg-slate-300" />
          {{ totalInactive }} inactifs
        </div>
      </template>
    </div>
  </div>
</template>
