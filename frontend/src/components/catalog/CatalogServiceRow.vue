<script setup lang="ts">
  /**
   * CatalogServiceRow — Card individuelle d'un service dans l'accordéon.
   *
   * Affiche : indicateur actif/inactif, code mono, nom, description,
   * tags (durée, profession, ordonnance, APA, acte médical),
   * boutons d'action au hover (modifier, désactiver/réactiver).
   *
   * Mode : 'platform' (CRUD super-admin) | 'admin' (lecture seule, Phase 3).
   */

  import { computed } from 'vue';

  import {
    Ban,
    Clock,
    Pencil,
    RefreshCw,
    ShieldCheck,
    Stethoscope,
    FileText,
  } from 'lucide-vue-next';
  import type { ServiceTemplateSummary } from '@/types';

  const props = defineProps<{
    service: ServiceTemplateSummary;
    mode?: 'platform' | 'admin';
  }>();

  const emit = defineEmits<{
    edit: [service: ServiceTemplateSummary];
    deactivate: [service: ServiceTemplateSummary];
    reactivate: [service: ServiceTemplateSummary];
  }>();

  const isPlatform = computed(() => props.mode !== 'admin');
</script>

<template>
  <div
    :class="
      service.is_active
        ? 'border-slate-200 hover:border-teal-200 hover:shadow-md hover:-translate-y-px'
        : 'border-dashed border-slate-200 opacity-55 hover:opacity-75 bg-slate-50'
    "
    class="flex items-start gap-3 p-3.5 rounded-xl transition-all bg-white border shadow-sm group"
  >
    <!-- Indicateur actif/inactif -->
    <div
      :class="service.is_active ? 'bg-emerald-500' : 'bg-slate-300'"
      class="w-1 min-h-[2.5rem] self-stretch rounded-full shrink-0"
    />

    <!-- Contenu principal -->
    <div class="flex-1 min-w-0">
      <!-- Code + Nom -->
      <div class="flex items-center gap-2 mb-0.5">
        <span
          class="font-mono text-[0.6875rem] font-semibold text-teal-600 bg-teal-50 px-1.5 py-0.5 rounded tracking-wide"
        >
          {{ service.code }}
        </span>
        <span class="text-sm font-bold text-slate-800 truncate">
          {{ service.name }}
        </span>
      </div>

      <!-- Tags -->
      <div class="flex flex-wrap gap-1 mt-1.5">
        <!-- Durée -->
        <span
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-slate-100 text-slate-600"
        >
          <Clock :size="10" :stroke-width="2.5" />
          {{ service.default_duration_minutes }} min
        </span>

        <!-- Ordonnance -->
        <span
          v-if="service.requires_prescription"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-amber-50 text-amber-600"
        >
          <FileText :size="10" :stroke-width="2.5" />
          Ordonnance
        </span>

        <!-- Acte médical -->
        <span
          v-if="service.is_medical_act"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-rose-50 text-rose-600"
        >
          <Stethoscope :size="10" :stroke-width="2.5" />
          Acte médical
        </span>

        <!-- APA -->
        <span
          v-if="service.apa_eligible"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-emerald-50 text-emerald-600"
        >
          <ShieldCheck :size="10" :stroke-width="2.5" />
          APA
        </span>
      </div>
    </div>

    <!-- Actions (hover only, platform mode) -->
    <div
      v-if="isPlatform"
      class="flex gap-0.5 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
    >
      <button
        class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all"
        title="Modifier"
        @click.stop="emit('edit', service)"
      >
        <Pencil :size="14" :stroke-width="2" />
      </button>
      <button
        v-if="service.is_active"
        class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-red-50 hover:text-red-500 transition-all"
        title="Désactiver"
        @click.stop="emit('deactivate', service)"
      >
        <Ban :size="14" :stroke-width="2" />
      </button>
      <button
        v-else
        class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:bg-emerald-50 hover:text-emerald-600 transition-all"
        title="Réactiver"
        @click.stop="emit('reactivate', service)"
      >
        <RefreshCw :size="14" :stroke-width="2" />
      </button>
    </div>
  </div>
</template>
