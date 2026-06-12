/** * CareLink — SelectedServicesPanel * Chemin :
frontend/src/components/careplan/SelectedServicesPanel.vue * * Rôle : panier latéral des prestations
sélectionnées pour le plan d'aide. * Affiche chaque service draft avec quantité éditable, bouton
supprimer, * et footer récapitulatif (heures/semaine + budget estimé). */
<template>
  <div class="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
    <!-- Header -->
    <div class="rounded-t-xl bg-gradient-to-r from-teal-600 to-teal-700 px-4 py-3 text-white">
      <div class="flex items-center gap-2 text-sm font-bold">
        📋 Plan d'aide
        <span class="rounded-full bg-white/20 px-2 py-0.5 text-xs font-semibold"> BROUILLON </span>
      </div>
      <div class="mt-0.5 text-xs text-teal-100">
        {{ services.length }} prestation{{ services.length > 1 ? 's' : '' }}
      </div>
    </div>

    <!-- Services list -->
    <div class="flex-1 overflow-y-auto">
      <!-- Empty state -->
      <div
        v-if="services.length === 0"
        class="flex flex-col items-center justify-center px-4 py-12 text-center"
      >
        <div class="mb-2 text-3xl">🛒</div>
        <p class="text-sm font-medium text-slate-500">Aucune prestation</p>
        <p class="mt-1 text-xs text-slate-400">Sélectionnez des prestations dans le catalogue</p>
      </div>

      <!-- Service cards -->
      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="(service, index) in services"
          :key="index"
          class="group px-4 py-3 transition-colors hover:bg-slate-50"
        >
          <!-- Row 1: Name + remove -->
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="text-sm font-semibold text-slate-800 truncate">
                {{ service._display_service_name }}
              </div>
              <div
                class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-400"
              >
                <span class="font-mono text-teal-600">{{ service._display_service_code }}</span>
                <span v-if="service._display_entity_name">
                  · {{ service._display_entity_name }}
                </span>
              </div>
            </div>
            <button
              class="shrink-0 rounded p-1 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-500"
              title="Retirer"
              @click="$emit('remove', index)"
            >
              ✕
            </button>
          </div>

          <!-- Row 2: Editable fields -->
          <div class="mt-2 flex items-center gap-3">
            <!-- Quantity -->
            <div class="flex items-center gap-1.5">
              <label class="text-[0.625rem] font-semibold uppercase tracking-wide text-slate-400">
                Fréq/sem
              </label>
              <input
                :value="service.quantity_per_week"
                type="number"
                min="1"
                max="21"
                class="w-14 rounded border border-slate-200 px-2 py-1 text-center text-xs font-bold text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400/20"
                @change="onQuantityChange(index, $event)"
              />
            </div>

            <!-- Duration display -->
            <div class="text-xs text-slate-500">{{ service.duration_minutes }} min</div>

            <!-- Tarif display -->
            <div
              v-if="service._display_tarif !== null && service._display_tarif !== undefined"
              class="ml-auto text-xs font-bold text-slate-700"
            >
              {{ (service._display_tarif * service.quantity_per_week).toFixed(2) }} €/sem
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer: totals -->
    <div v-if="services.length > 0" class="border-t border-slate-200 px-4 py-3">
      <!-- Hours/week -->
      <div class="flex items-center justify-between text-xs">
        <span class="text-slate-500">Heures / semaine</span>
        <span class="font-bold text-slate-700"> {{ totalHoursWeek.toFixed(1) }}h </span>
      </div>

      <!-- Budget weekly -->
      <div class="mt-1 flex items-center justify-between text-xs">
        <span class="text-slate-500">Coût hebdo estimé</span>
        <span class="font-bold text-teal-600"> {{ budgetWeekly.toFixed(2) }} €/sem </span>
      </div>

      <!-- Budget bar (if budget allocated) -->
      <div v-if="budgetAllocated > 0" class="mt-2">
        <div class="flex items-center justify-between text-[0.625rem] text-slate-400">
          <span>Budget mensuel</span>
          <span> {{ budgetMonthly.toFixed(0) }} € / {{ budgetAllocated.toFixed(0) }} € </span>
        </div>
        <div class="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            :class="budgetBarClass"
            :style="{ width: `${Math.min(budgetPercent, 100)}%` }"
            class="h-full rounded-full transition-all"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  import type { CarePlanServiceDraft } from '@/types';

  const props = defineProps<{
    services: CarePlanServiceDraft[];
    totalHoursWeek: number;
    budgetWeekly: number;
    budgetAllocated: number;
  }>();

  const emit = defineEmits<{
    remove: [index: number];
    update: [index: number, data: Partial<CarePlanServiceDraft>];
  }>();

  /** Budget mensuel estimé (hebdo × 4.33) */
  const budgetMonthly = computed(() => props.budgetWeekly * 4.33);

  /** Pourcentage budget consommé */
  const budgetPercent = computed(() => {
    if (props.budgetAllocated <= 0) return 0;
    return (budgetMonthly.value / props.budgetAllocated) * 100;
  });

  /** Classe couleur de la barre budget */
  const budgetBarClass = computed(() => {
    if (budgetPercent.value >= 100) return 'bg-red-500';
    if (budgetPercent.value >= 80) return 'bg-amber-500';
    return 'bg-teal-500';
  });

  /** Handler changement quantité */
  function onQuantityChange(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = parseInt(target.value, 10);
    if (value >= 1 && value <= 21) {
      emit('update', index, { quantity_per_week: value });
    }
  }
</script>
