/** * CareLink — WeeklyScheduleItem * Chemin :
frontend/src/components/careplan/WeeklyScheduleItem.vue * * Rôle : item unitaire placé dans une zone
de période de la semaine type (F3). * Affiche nom, créneau horaire (éditable inline), durée, barre
proportionnelle. * Signale visuellement les doublons (même prestation au même créneau). */
<template>
  <div
    :class="[
      'group relative flex items-center gap-1 overflow-hidden rounded-md border-l-[3px] px-2 py-1.5 transition-shadow hover:shadow-sm',
      domainClasses.bg,
      domainClasses.border,
      domainClasses.text,
      isDoublon ? 'ring-2 ring-red-400 animate-pulse-conflict' : '',
    ]"
    draggable="true"
    @dragstart="onDragStart"
  >
    <!-- Name -->
    <span class="flex-1 truncate text-[0.625rem] font-semibold">
      {{ draft._display_service_name }}
    </span>

    <!-- Duration label -->
    <span class="shrink-0 text-[0.5rem] font-semibold opacity-60"> {{ placement.duration }}′ </span>

    <!-- Time range (inline editable) -->
    <span
      v-if="!isEditingTime"
      :title="'Cliquer pour modifier l\'heure'"
      class="shrink-0 cursor-pointer rounded px-1 py-0.5 text-[0.5625rem] font-semibold transition-colors hover:bg-black/5"
      @click="startEditTime"
    >
      {{ placement.startTime }}–{{ endTime }}
    </span>

    <!-- Inline time input (shown when editing) -->
    <input
      v-else
      ref="timeInputRef"
      v-model="editingTimeValue"
      type="time"
      class="w-[52px] shrink-0 rounded border border-teal-400 bg-white px-1 py-0.5 text-center text-[0.5625rem] font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-teal-300"
      @blur="commitTimeEdit"
      @keydown.enter="commitTimeEdit"
      @keydown.escape="cancelTimeEdit"
    />

    <!-- Remove button -->
    <button
      :class="domainClasses.text"
      class="ml-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[0.625rem] opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-100 hover:text-red-500"
      title="Retirer"
      @click="$emit('remove', placement.id)"
    >
      ×
    </button>

    <!-- Duration bar (bottom, proportional) -->
    <div
      :class="[
        'absolute bottom-0 left-[3px] right-0 h-[2.5px] rounded-br opacity-40',
        domainClasses.bar,
      ]"
      :style="{ width: durBarWidth }"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref } from 'vue';

  import type { CarePlanServiceDraft, WeeklyPlacement } from '@/types';

  // =========================================================================
  // PROPS & EMITS
  // =========================================================================

  const props = defineProps<{
    placement: WeeklyPlacement;
    draft: CarePlanServiceDraft;
    isDoublon: boolean;
  }>();

  const emit = defineEmits<{
    remove: [placementId: number];
    updateTime: [placementId: number, newTime: string];
  }>();

  // =========================================================================
  // DOMAIN COLORS — Tailwind classes (convention #B14)
  // =========================================================================

  interface DomainStyle {
    bg: string;
    border: string;
    text: string;
    bar: string;
  }

  const DOMAIN_STYLES: Record<string, DomainStyle> = {
    SANTE: {
      bg: 'bg-blue-50',
      border: 'border-l-blue-500',
      text: 'text-blue-700',
      bar: 'bg-blue-500',
    },
    AUTONOMIE: {
      bg: 'bg-violet-50',
      border: 'border-l-violet-500',
      text: 'text-violet-700',
      bar: 'bg-violet-500',
    },
    PARTICIPATION_SOCIALE: {
      bg: 'bg-orange-50',
      border: 'border-l-orange-500',
      text: 'text-orange-700',
      bar: 'bg-orange-500',
    },
  };

  const FALLBACK_STYLE: DomainStyle = {
    bg: 'bg-slate-50',
    border: 'border-l-slate-400',
    text: 'text-slate-700',
    bar: 'bg-slate-400',
  };

  const domainClasses = computed<DomainStyle>(() => {
    const domain = props.draft._display_domain ?? 'SANTE';
    return DOMAIN_STYLES[domain] ?? FALLBACK_STYLE;
  });

  // =========================================================================
  // TIME DISPLAY
  // =========================================================================

  /** Heure de fin calculée depuis startTime + duration */
  const endTime = computed(() => {
    const [h, m] = props.placement.startTime.split(':').map(Number);
    const totalMin = h * 60 + (m || 0) + props.placement.duration;
    const endH = Math.floor(totalMin / 60) % 24;
    const endM = totalMin % 60;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  });

  // =========================================================================
  // DURATION BAR — proportional width (120 min = 100%)
  // =========================================================================

  const MAX_DUR_REF = 120;

  const durBarWidth = computed(() => {
    const pct = Math.min(100, (props.placement.duration / MAX_DUR_REF) * 100);
    return `${pct}%`;
  });

  // =========================================================================
  // INLINE TIME EDIT
  // =========================================================================

  const isEditingTime = ref(false);
  const editingTimeValue = ref('');
  const timeInputRef = ref<HTMLInputElement | null>(null);

  function startEditTime(): void {
    editingTimeValue.value = props.placement.startTime;
    isEditingTime.value = true;
    nextTick(() => {
      timeInputRef.value?.focus();
    });
  }

  function commitTimeEdit(): void {
    isEditingTime.value = false;
    if (editingTimeValue.value && editingTimeValue.value !== props.placement.startTime) {
      emit('updateTime', props.placement.id, editingTimeValue.value);
    }
  }

  function cancelTimeEdit(): void {
    isEditingTime.value = false;
  }

  // =========================================================================
  // DRAG (reorder / move between days)
  // =========================================================================

  function onDragStart(event: DragEvent): void {
    if (!event.dataTransfer) return;
    event.dataTransfer.setData('application/x-draft-index', String(props.placement.draftIndex));
    event.dataTransfer.setData('application/x-placement-id', String(props.placement.id));
    event.dataTransfer.effectAllowed = 'move';
  }
</script>

<style scoped>
  @keyframes pulse-conflict {
    0%,
    100% {
      --tw-ring-color: rgb(248 113 113);
    }
    50% {
      --tw-ring-color: rgb(248 113 113 / 0.3);
    }
  }
  .animate-pulse-conflict {
    animation: pulse-conflict 2s infinite;
  }
</style>
