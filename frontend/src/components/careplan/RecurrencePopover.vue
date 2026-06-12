/** * CareLink — RecurrencePopover * Chemin : frontend/src/components/careplan/RecurrencePopover.vue
* * Rôle : popover de récurrence pour la semaine type (F3). * Permet de placer une prestation sur
plusieurs jours à la même heure. * S'ouvre au drop ou au double-clic sur une prestation dans la
palette. * Émet @apply avec les jours sélectionnés, l'heure et la durée. */
<template>
  <!-- Backdrop (clic = ferme) -->
  <Teleport to="body">
    <Transition name="popover-fade">
      <div v-if="visible" class="fixed inset-0 z-[90]" @click="$emit('close')" />
    </Transition>

    <!-- Popover card -->
    <Transition name="popover-scale">
      <div
        v-if="visible"
        :style="{ top: `${posY}px`, left: `${posX}px` }"
        class="fixed z-[100] w-[300px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        @click.stop
      >
        <!-- Header -->
        <div class="flex items-center gap-2 border-b border-slate-100 px-4 py-2.5">
          <span :class="['inline-block h-2 w-2 rounded-full', domainDotClass]" aria-hidden="true" />
          <span class="flex-1 truncate text-[0.8125rem] font-bold text-slate-700">
            {{ draft._display_service_name }}
          </span>
          <span class="text-[0.6875rem] text-slate-400"> {{ draft.duration_minutes }} min </span>
        </div>

        <!-- Body -->
        <div class="px-4 py-3">
          <!-- Day buttons -->
          <p class="mb-1.5 text-[0.625rem] font-bold uppercase tracking-wide text-slate-400">
            Jours de récurrence
          </p>
          <div class="mb-3 flex gap-1">
            <button
              v-for="(abbr, idx) in WEEK_DAY_ABBR"
              :key="idx"
              :class="[
                'flex h-8 w-8 items-center justify-center rounded-full border-[1.5px] text-[0.6875rem] font-bold transition-all',
                selectedDays.has(idx)
                  ? 'border-teal-500 bg-teal-500 text-white'
                  : 'border-slate-300 bg-white text-slate-500 hover:border-teal-300 hover:text-teal-600',
              ]"
              type="button"
              @click="toggleDay(idx)"
            >
              {{ abbr }}
            </button>
          </div>

          <!-- Time & Duration -->
          <p class="mb-1.5 text-[0.625rem] font-bold uppercase tracking-wide text-slate-400">
            Horaire
          </p>
          <div class="mb-1 grid grid-cols-[auto_1fr_auto_auto_auto] items-center gap-x-2 gap-y-1.5">
            <span class="text-[0.6875rem] text-slate-500">Début</span>
            <input
              v-model="startTime"
              type="time"
              class="rounded-md border border-slate-300 px-2 py-1 text-center text-[0.8125rem] font-semibold text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-100"
            />
            <span class="text-[0.6875rem] text-slate-500">Durée</span>
            <input
              v-model.number="duration"
              type="number"
              min="5"
              max="240"
              step="5"
              class="w-14 rounded-md border border-slate-300 px-2 py-1 text-center text-[0.8125rem] font-semibold text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-100"
            />
            <span class="text-[0.6875rem] text-slate-400">min</span>
          </div>
        </div>

        <!-- Footer -->
        <div
          class="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-4 py-2.5"
        >
          <!-- Preview -->
          <div class="text-[0.6875rem] text-slate-500">
            <template v-if="selectedDays.size > 0">
              <strong class="font-bold text-teal-600">{{ selectedDays.size }}×</strong>
              {{ previewDayNames }}
              · {{ startTime }}–{{ previewEndTime }}
            </template>
            <span v-else class="text-slate-400"> Sélectionnez au moins un jour </span>
          </div>

          <!-- Actions -->
          <div class="flex gap-1.5">
            <button
              type="button"
              class="rounded-md border border-slate-300 bg-white px-3 py-1 text-[0.6875rem] font-semibold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
              @click="$emit('close')"
            >
              Annuler
            </button>
            <button
              :disabled="selectedDays.size === 0"
              :class="[
                'rounded-md border px-3 py-1 text-[0.6875rem] font-semibold transition-colors',
                selectedDays.size > 0
                  ? 'border-teal-500 bg-teal-500 text-white hover:bg-teal-600'
                  : 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400',
              ]"
              type="button"
              @click="onApply"
            >
              Appliquer
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  import type { CarePlanServiceDraft } from '@/types';
  import { WEEK_DAY_ABBR, WEEK_DAY_SHORT } from '@/types';

  // =========================================================================
  // PROPS & EMITS
  // =========================================================================

  const props = defineProps<{
    visible: boolean;
    draft: CarePlanServiceDraft;
    /** Index dans draftServices[] */
    draftIndex: number;
    /** Clé de la période cible (matin, midi, etc.) */
    period: string;
    /** Heure de début pré-calculée (auto-stacked) */
    initialStartTime: string;
    /** Jour de drop initial (0-6) — pré-coché */
    initialDay: number | null;
    /** Position X du popover */
    posX: number;
    /** Position Y du popover */
    posY: number;
  }>();

  const emit = defineEmits<{
    close: [];
    apply: [
      draftIndex: number,
      days: number[],
      period: string,
      startTime: string,
      duration: number,
    ];
  }>();

  // =========================================================================
  // LOCAL STATE
  // =========================================================================

  const selectedDays = ref<Set<number>>(new Set());
  const startTime = ref('08:00');
  const duration = ref(30);

  // =========================================================================
  // WATCH — reset state when popover opens with new data
  // =========================================================================

  watch(
    () => props.visible,
    (isVisible) => {
      if (isVisible) {
        // Pre-fill from props
        startTime.value = props.initialStartTime;
        duration.value = props.draft.duration_minutes;

        // Pre-select day: if dropped on a specific day, select that one
        // Otherwise, select weekdays (Mon-Fri)
        if (props.initialDay !== null) {
          selectedDays.value = new Set([props.initialDay]);
        } else {
          selectedDays.value = new Set([0, 1, 2, 3, 4]);
        }
      }
    },
  );

  // =========================================================================
  // DAY TOGGLE
  // =========================================================================

  function toggleDay(dayIdx: number): void {
    const next = new Set(selectedDays.value);
    if (next.has(dayIdx)) {
      next.delete(dayIdx);
    } else {
      next.add(dayIdx);
    }
    selectedDays.value = next;
  }

  // =========================================================================
  // DOMAIN DOT
  // =========================================================================

  const DOMAIN_DOT_MAP: Record<string, string> = {
    SANTE: 'bg-blue-500',
    AUTONOMIE: 'bg-violet-500',
    PARTICIPATION_SOCIALE: 'bg-orange-500',
  };

  const domainDotClass = computed(
    () => DOMAIN_DOT_MAP[props.draft._display_domain ?? 'SANTE'] ?? 'bg-slate-400',
  );

  // =========================================================================
  // PREVIEW
  // =========================================================================

  const previewDayNames = computed(() => {
    const sorted = [...selectedDays.value].sort();
    return sorted.map((d) => WEEK_DAY_SHORT[d]).join(', ');
  });

  const previewEndTime = computed(() => {
    const [h, m] = startTime.value.split(':').map(Number);
    const totalMin = h * 60 + (m || 0) + duration.value;
    const endH = Math.floor(totalMin / 60) % 24;
    const endM = totalMin % 60;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  });

  // =========================================================================
  // APPLY
  // =========================================================================

  function onApply(): void {
    if (selectedDays.value.size === 0) return;
    emit(
      'apply',
      props.draftIndex,
      [...selectedDays.value].sort(),
      props.period,
      startTime.value,
      duration.value,
    );
  }
</script>

<style scoped>
  .popover-fade-enter-active,
  .popover-fade-leave-active {
    transition: opacity 150ms ease;
  }
  .popover-fade-enter-from,
  .popover-fade-leave-to {
    opacity: 0;
  }

  .popover-scale-enter-active {
    transition: all 150ms ease;
  }
  .popover-scale-leave-active {
    transition: all 100ms ease;
  }
  .popover-scale-enter-from {
    opacity: 0;
    transform: scale(0.95) translateY(4px);
  }
  .popover-scale-leave-to {
    opacity: 0;
    transform: scale(0.97) translateY(2px);
  }
</style>
