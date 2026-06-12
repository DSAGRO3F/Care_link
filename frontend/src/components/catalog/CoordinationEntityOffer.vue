/** * CareLink — CoordinationEntityOffer * Chemin :
frontend/src/components/catalog/CoordinationEntityOffer.vue * * Rôle : ligne d'offre d'une entité
pour une prestation donnée. * Affiche le nom de l'entité (dot coloré par type), tarif, durée, *
badge « meilleur tarif » si applicable, et bouton Sélectionner (Phase 4). */
<template>
  <div
    class="flex items-center gap-4 border-b border-slate-100 px-5 py-3 transition-colors last:border-b-0 hover:bg-slate-50"
  >
    <!-- Entity name with type dot -->
    <div class="flex min-w-[180px] items-center gap-2 text-sm font-semibold text-slate-700">
      <span :class="dotClass" class="inline-block h-2 w-2 shrink-0 rounded-full" />
      {{ offer.entity_name }}
    </div>

    <!-- Fields: tarif + durée -->
    <div class="flex flex-1 items-center gap-6">
      <!-- Tarif -->
      <div class="flex min-w-[80px] flex-col items-center">
        <span class="text-[0.5625rem] font-semibold uppercase tracking-wide text-slate-400">
          Tarif
        </span>
        <span v-if="offer.custom_tarif != null" class="text-sm font-bold text-slate-800">
          {{ offer.custom_tarif.toFixed(2) }} €
        </span>
        <span v-else class="text-sm italic text-slate-400">Non défini</span>
      </div>

      <!-- Durée -->
      <div class="flex min-w-[80px] flex-col items-center">
        <span class="text-[0.5625rem] font-semibold uppercase tracking-wide text-slate-400">
          Durée
        </span>
        <span v-if="offer.custom_duree != null" class="text-sm font-bold text-slate-800">
          {{ offer.custom_duree }} min
        </span>
        <span v-else class="text-sm italic text-slate-400">Par défaut</span>
      </div>

      <!-- Best tarif badge -->
      <span
        v-if="isBestTarif"
        class="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-xs font-semibold text-teal-700"
      >
        ✓ Meilleur tarif
      </span>
    </div>

    <!-- Select button (prépare Phase 4) -->
    <button
      class="shrink-0 rounded-md border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-600 transition-colors hover:border-teal-300 hover:bg-teal-100"
      @click="$emit('select', offer)"
    >
      Sélectionner →
    </button>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  import type { ConsolidatedEntityOffer } from '@/types';

  const props = defineProps<{
    offer: ConsolidatedEntityOffer;
    isBestTarif: boolean;
  }>();

  defineEmits<{
    select: [offer: ConsolidatedEntityOffer];
  }>();

  /** Couleur du dot selon le type d'entité */
  const ENTITY_TYPE_COLORS: Record<string, string> = {
    SSIAD: 'bg-blue-500',
    SAAD: 'bg-amber-500',
    EHPAD: 'bg-violet-500',
    SPASAD: 'bg-teal-500',
  };

  const dotClass = computed(() => {
    return ENTITY_TYPE_COLORS[props.offer.entity_type] ?? 'bg-slate-400';
  });
</script>
