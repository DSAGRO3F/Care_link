/** * CareLink — WeeklyDayCard * Chemin : frontend/src/components/careplan/WeeklyDayCard.vue * *
Rôle : carte-jour de la grille hebdomadaire (F3). * Affiche 5 zones de période (Matin → Nuit),
chacune est un drop target. * Regroupe visuellement les items concurrents (même startTime) : * - « ∥
parallèle » (ambre) si prestations différentes * - « ⚠ doublon » (rouge) si même prestation (erreur
probable) */
<template>
  <div
    :class="[
      'flex flex-col rounded-xl border bg-white transition-all',
      isDragOver ? 'border-teal-400 shadow-md shadow-teal-100' : 'border-slate-200',
    ]"
  >
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-slate-100 px-2.5 py-2">
      <span class="text-[0.8125rem] font-bold text-slate-700">
        {{ dayName }}
      </span>
      <span
        :class="[
          'rounded-full px-2 py-0.5 text-[0.625rem] font-semibold',
          totalMinutes > 0 ? 'bg-teal-50 text-teal-600' : 'bg-slate-100 text-slate-400',
        ]"
      >
        {{ totalMinutes > 0 ? formattedTotal : '—' }}
      </span>
    </div>

    <!-- Period zones -->
    <div class="flex flex-1 flex-col p-1.5">
      <div v-for="period in PERIODS" :key="period.key" class="mb-1 flex flex-1 flex-col">
        <!-- Period label -->
        <div class="flex items-center justify-between px-1.5 py-0.5">
          <span class="text-[0.5625rem] font-bold uppercase tracking-wide text-slate-400">
            {{ period.label }}
          </span>
          <span class="text-[0.5rem] text-slate-300">
            {{ period.range }}
          </span>
        </div>

        <!-- Drop zone -->
        <div
          :data-period="period.key"
          :class="[
            'min-h-[52px] flex-1 rounded-md border-[1.5px] p-1 transition-all',
            periodHasItems(period.key)
              ? 'border-solid border-slate-200 bg-slate-50'
              : 'border-dashed border-slate-200',
            activePeriod === period.key ? 'border-teal-400 bg-teal-50' : '',
          ]"
          @dragover.prevent="onDragOver(period.key)"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop($event, period.key)"
        >
          <!-- Render grouped items -->
          <template v-for="group in getGroupsForPeriod(period.key)" :key="group.key">
            <!-- Concurrent group (2+ items at same time) -->
            <div
              v-if="group.items.length > 1"
              :class="[
                'mb-0.5 rounded-lg border-[1.5px] p-1 relative',
                group.hasDoublon ? 'border-red-400 bg-red-50' : 'border-amber-400 bg-amber-50',
              ]"
            >
              <span
                :class="[
                  'absolute -top-2 left-1.5 px-1 text-[0.5rem] font-bold uppercase tracking-wide',
                  group.hasDoublon ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600',
                ]"
              >
                {{ group.hasDoublon ? '⚠ doublon' : '∥ parallèle' }}
                · {{ group.items[0].placement.startTime }}
              </span>
              <div class="flex flex-col gap-0.5 pt-1">
                <WeeklyScheduleItem
                  v-for="item in group.items"
                  :key="item.placement.id"
                  :placement="item.placement"
                  :draft="item.draft"
                  :is-doublon="item.isDoublon"
                  @remove="$emit('removePlacement', $event)"
                  @update-time="(id, time) => $emit('updatePlacementTime', id, time)"
                />
              </div>
            </div>

            <!-- Single item (no grouping needed) -->
            <WeeklyScheduleItem
              v-else
              :placement="group.items[0].placement"
              :draft="group.items[0].draft"
              :is-doublon="false"
              @remove="$emit('removePlacement', $event)"
              @update-time="(id, time) => $emit('updatePlacementTime', id, time)"
            />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  import WeeklyScheduleItem from './WeeklyScheduleItem.vue';
  import type { CarePlanServiceDraft, WeeklyPlacement } from '@/types';
  import { PERIODS } from '@/types';

  // =========================================================================
  // PROPS & EMITS
  // =========================================================================

  const props = defineProps<{
    /** Index du jour (0=Lundi … 6=Dimanche) */
    day: number;
    /** Nom affiché ("Lundi", etc.) */
    dayName: string;
    /** Placements de CE jour uniquement (filtrés par le parent) */
    placements: WeeklyPlacement[];
    /** Tableau complet des drafts (pour lookup par draftIndex) */
    drafts: CarePlanServiceDraft[];
  }>();

  const emit = defineEmits<{
    drop: [draftIndex: number, periodKey: string];
    removePlacement: [placementId: number];
    updatePlacementTime: [placementId: number, newTime: string];
  }>();

  // =========================================================================
  // DRAG STATE
  // =========================================================================

  const isDragOver = ref(false);
  const activePeriod = ref<string | null>(null);

  function onDragOver(periodKey: string): void {
    isDragOver.value = true;
    activePeriod.value = periodKey;
  }

  function onDragLeave(): void {
    isDragOver.value = false;
    activePeriod.value = null;
  }

  function onDrop(event: DragEvent, periodKey: string): void {
    isDragOver.value = false;
    activePeriod.value = null;

    const draftIndexStr = event.dataTransfer?.getData('application/x-draft-index');
    if (draftIndexStr === undefined || draftIndexStr === '') return;

    const draftIndex = parseInt(draftIndexStr, 10);
    if (Number.isNaN(draftIndex)) return;

    emit('drop', draftIndex, periodKey);
  }

  // =========================================================================
  // COMPUTED — totals
  // =========================================================================

  const totalMinutes = computed(() => props.placements.reduce((sum, p) => sum + p.duration, 0));

  const formattedTotal = computed(() => {
    const h = Math.floor(totalMinutes.value / 60);
    const m = totalMinutes.value % 60;
    return `${h}h${String(m).padStart(2, '0')}`;
  });

  // =========================================================================
  // HELPERS
  // =========================================================================

  function periodHasItems(periodKey: string): boolean {
    return props.placements.some((p) => p.period === periodKey);
  }

  /** Parse 'HH:MM' → minutes */
  function parseTimeToMin(time: string): number {
    const [h, m] = time.split(':').map(Number);
    return h * 60 + (m || 0);
  }

  // =========================================================================
  // GROUPING — concurrent items detection
  // =========================================================================

  interface GroupedItem {
    placement: WeeklyPlacement;
    draft: CarePlanServiceDraft;
    isDoublon: boolean;
  }

  interface ItemGroup {
    key: string;
    items: GroupedItem[];
    hasDoublon: boolean;
  }

  /**
   * Regroupe les items d'une période par startTime.
   * Les items à la même heure sont regroupés visuellement.
   * Un "doublon" = même draftIndex dans le même groupe (même prestation, même heure).
   */
  function getGroupsForPeriod(periodKey: string): ItemGroup[] {
    const periodItems = props.placements
      .filter((p) => p.period === periodKey)
      .sort((a, b) => parseTimeToMin(a.startTime) - parseTimeToMin(b.startTime));

    // Group by startTime
    const timeMap = new Map<string, WeeklyPlacement[]>();
    periodItems.forEach((p) => {
      if (!timeMap.has(p.startTime)) timeMap.set(p.startTime, []);
      timeMap.get(p.startTime)!.push(p);
    });

    const groups: ItemGroup[] = [];

    timeMap.forEach((placements, startTime) => {
      // Detect doublons within this time group
      const draftIndexCounts = new Map<number, number>();
      placements.forEach((p) => {
        draftIndexCounts.set(p.draftIndex, (draftIndexCounts.get(p.draftIndex) ?? 0) + 1);
      });

      const hasDoublon = [...draftIndexCounts.values()].some((count) => count > 1);

      const items: GroupedItem[] = placements.map((placement) => ({
        placement,
        draft: props.drafts[placement.draftIndex],
        isDoublon: hasDoublon && (draftIndexCounts.get(placement.draftIndex) ?? 0) > 1,
      }));

      groups.push({
        key: `${periodKey}-${startTime}`,
        items,
        hasDoublon,
      });
    });

    return groups;
  }
</script>
