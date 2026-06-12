/** * CareLink — CoordinationBanner * Chemin :
frontend/src/components/catalog/CoordinationBanner.vue * * Rôle : bandeau gradient teal-700/800
affichant les compteurs globaux * du catalogue consolidé (entités, prestations actives, référentiel
national). * Utilisé en haut de CoordinationCatalogPage. */
<template>
  <div
    class="flex items-center justify-between gap-4 rounded-xl bg-gradient-to-br from-teal-700 to-teal-800 px-6 py-5 text-white"
  >
    <!-- Left: icon + title + subtitle -->
    <div class="flex items-center gap-4">
      <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-teal-500/15">
        <component :is="UsersIcon" class="h-5 w-5 text-teal-300" />
      </div>
      <div>
        <h2 class="text-lg font-bold leading-tight text-white">Catalogue Consolidé</h2>
        <p class="mt-0.5 text-sm text-teal-200">
          {{ summary.entities_count }} entité{{ summary.entities_count > 1 ? 's' : '' }} rattachée{{
            summary.entities_count > 1 ? 's' : ''
          }}
          · Coordination des soins
        </p>
      </div>
    </div>

    <!-- Right: stat blocks -->
    <div class="flex gap-8">
      <div class="text-center">
        <div class="text-2xl font-extrabold leading-tight">
          {{ summary.entities_count }}
        </div>
        <div class="text-xs font-semibold uppercase tracking-wide text-teal-300">Entités</div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-extrabold leading-tight">
          {{ summary.total_active_prestations }}
        </div>
        <div class="text-xs font-semibold uppercase tracking-wide text-teal-300">
          Prestations actives
        </div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-extrabold leading-tight">
          {{ summary.total_national }}
        </div>
        <div class="text-xs font-semibold uppercase tracking-wide text-teal-300">
          Référentiel national
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Users as UsersIcon } from 'lucide-vue-next';

  import type { ConsolidatedCatalogSummary } from '@/types';

  defineProps<{
    summary: ConsolidatedCatalogSummary;
  }>();
</script>
