<script setup lang="ts">
  /**
   * CatalogEntityServiceRow — Ligne service en mode Admin Tenant.
   *
   * Affiche un toggle activation + info template national + champs inline
   * de personnalisation (tarif, durée, fréquence) avec bouton enregistrer.
   *
   * Différences avec CatalogServiceRow (mode platform) :
   * - Pas de CRUD sur le template (lecture seule)
   * - Toggle activation/désactivation entity_service
   * - Champs inline éditables quand activé
   * - Bouton "Enregistrer" quand un champ est modifié
   *
   * 🆕 v5.28 — Phase 3A.
   */

  import { computed, ref, watch } from 'vue';

  import { Clock, FileText, Save, ShieldCheck, Stethoscope } from 'lucide-vue-next';
  import type { MergedEntityService } from '@/types';

  const props = defineProps<{
    merged: MergedEntityService;
  }>();

  const emit = defineEmits<{
    toggle: [merged: MergedEntityService];
    save: [
      merged: MergedEntityService,
      fields: { price_euros: number | null; custom_duration_minutes: number | null },
    ];
  }>();

  // =========================================================================
  // LOCAL STATE — Champs éditables (initialisés depuis les props)
  // =========================================================================

  const localPrice = ref<string>('');
  const localDuration = ref<string>('');

  /** Synchronise les champs locaux quand les données changent */
  function syncLocalFields(): void {
    localPrice.value =
      props.merged.effectivePrice !== null ? String(props.merged.effectivePrice) : '';
    localDuration.value =
      props.merged.entityService?.custom_duration_minutes !== null &&
      props.merged.entityService?.custom_duration_minutes !== undefined
        ? String(props.merged.entityService.custom_duration_minutes)
        : '';
  }

  // Sync au mount et quand l'entityService change
  watch(
    () => props.merged.entityService,
    () => syncLocalFields(),
    { immediate: true },
  );

  // =========================================================================
  // COMPUTED
  // =========================================================================

  /** Durée affichée : personnalisée ou défaut national */
  const displayDuration = computed(
    () =>
      props.merged.entityService?.custom_duration_minutes ??
      props.merged.template.default_duration_minutes,
  );

  /** Détecte si un champ a été modifié par rapport aux valeurs enregistrées */
  const hasUnsavedChanges = computed(() => {
    if (!props.merged.isActivated) return false;

    const currentPrice = localPrice.value.trim() === '' ? null : parseFloat(localPrice.value);
    const currentDuration =
      localDuration.value.trim() === '' ? null : parseInt(localDuration.value);

    const savedPrice = props.merged.effectivePrice;
    const savedDuration = props.merged.entityService?.custom_duration_minutes ?? null;

    return currentPrice !== savedPrice || currentDuration !== savedDuration;
  });

  // =========================================================================
  // ACTIONS
  // =========================================================================

  function onToggle(): void {
    emit('toggle', props.merged);
  }

  function onSave(): void {
    if (!hasUnsavedChanges.value) return;

    emit('save', props.merged, {
      price_euros: localPrice.value.trim() === '' ? null : parseFloat(localPrice.value),
      custom_duration_minutes:
        localDuration.value.trim() === '' ? null : parseInt(localDuration.value),
    });
  }
</script>

<template>
  <div
    :class="
      merged.isActivated
        ? 'border-slate-200 hover:border-teal-200 hover:shadow-md'
        : 'border-dashed border-slate-200 opacity-55 hover:opacity-75 bg-slate-50'
    "
    class="flex items-start gap-3 p-3.5 rounded-xl transition-all bg-white border shadow-sm"
  >
    <!-- Toggle activation -->
    <div class="flex items-start pt-0.5 shrink-0">
      <label class="relative inline-block w-10 h-[1.375rem] cursor-pointer">
        <input
          :checked="merged.isActivated"
          type="checkbox"
          class="sr-only peer"
          @change="onToggle"
        />
        <span
          class="absolute inset-0 rounded-full bg-slate-200 transition-colors peer-checked:bg-teal-500"
        />
        <span
          class="absolute top-[3px] left-[3px] w-4 h-4 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-[1.125rem]"
        />
      </label>
    </div>

    <!-- Contenu principal -->
    <div class="flex-1 min-w-0">
      <!-- Code + Nom -->
      <div class="flex items-center gap-2 mb-0.5">
        <span
          class="font-mono text-[0.6875rem] font-semibold text-teal-600 bg-teal-50 px-1.5 py-0.5 rounded tracking-wide"
        >
          {{ merged.template.code }}
        </span>
        <span class="text-sm font-bold text-slate-800 truncate">
          {{ merged.template.name }}
        </span>
      </div>

      <!-- Tags -->
      <div class="flex flex-wrap gap-1 mt-1.5">
        <!-- Durée -->
        <span
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-slate-100 text-slate-600"
        >
          <Clock :size="10" :stroke-width="2.5" />
          {{ displayDuration }} min
        </span>

        <!-- Ordonnance -->
        <span
          v-if="merged.template.requires_prescription"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-amber-50 text-amber-600"
        >
          <FileText :size="10" :stroke-width="2.5" />
          Ordonnance
        </span>

        <!-- Acte médical -->
        <span
          v-if="merged.template.is_medical_act"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-rose-50 text-rose-600"
        >
          <Stethoscope :size="10" :stroke-width="2.5" />
          Acte médical
        </span>

        <!-- APA -->
        <span
          v-if="merged.template.apa_eligible"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[0.6875rem] font-medium bg-emerald-50 text-emerald-600"
        >
          <ShieldCheck :size="10" :stroke-width="2.5" />
          APA
        </span>
      </div>

      <!-- Champs personnalisation inline (seulement quand activé) -->
      <div
        v-if="merged.isActivated"
        class="flex items-end gap-2 mt-2.5 pt-2.5 border-t border-dashed border-slate-200"
      >
        <!-- Tarif -->
        <div class="flex flex-col gap-0.5">
          <label class="text-[0.625rem] font-semibold uppercase tracking-wide text-slate-400">
            Tarif (€)
          </label>
          <input
            v-model="localPrice"
            type="text"
            inputmode="decimal"
            placeholder="—"
            class="w-[6.5rem] px-2 py-1.5 border border-slate-200 rounded-lg text-[0.8125rem] text-slate-700 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/10 transition placeholder:text-slate-400 placeholder:italic"
          />
        </div>

        <!-- Durée -->
        <div class="flex flex-col gap-0.5">
          <label class="text-[0.625rem] font-semibold uppercase tracking-wide text-slate-400">
            Durée (min)
          </label>
          <input
            v-model="localDuration"
            :placeholder="String(merged.template.default_duration_minutes)"
            type="text"
            inputmode="numeric"
            class="w-[6.5rem] px-2 py-1.5 border border-slate-200 rounded-lg text-[0.8125rem] text-slate-700 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/10 transition placeholder:text-slate-400 placeholder:italic"
          />
        </div>

        <!-- Bouton enregistrer -->
        <button
          :disabled="!hasUnsavedChanges"
          :class="
            hasUnsavedChanges
              ? 'bg-teal-50 text-teal-600 border-teal-200 hover:bg-teal-100 hover:border-teal-300'
              : 'bg-slate-50 text-slate-300 border-slate-100 cursor-not-allowed'
          "
          class="px-2.5 py-1.5 rounded-lg text-[0.6875rem] font-semibold border transition-all flex items-center gap-1"
          @click="onSave"
        >
          <Save :size="12" :stroke-width="2.5" />
          Enregistrer
        </button>
      </div>
    </div>
  </div>
</template>
