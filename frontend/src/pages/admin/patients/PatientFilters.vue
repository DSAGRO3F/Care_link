<script setup lang="ts">
  /**
   * PatientFilters.vue — Barre de filtres pour la liste patients
   *
   * Filtres disponibles :
   *   - Recherche texte (nom, prénom, NIR)
   *   - Entité de rattachement (dropdown)
   *   - Statut patient (ACTIVE, INACTIVE, ARCHIVED, DECEASED)
   *   - Score GIR (plage 1-6)
   *
   * Émet des événements de changement vers la page parente qui pilote le store.
   *
   * Pattern calqué sur UserFilters.vue
   *
   * Destination : src/components/patients/PatientFilters.vue
   */
  import InputText from 'primevue/inputtext';
  import IconField from 'primevue/iconfield';
  import InputIcon from 'primevue/inputicon';
  import Select from 'primevue/select';
  import Button from 'primevue/button';
  import type { PatientStatus } from '@/types';

  // =============================================================================
  // PROPS & EMITS
  // =============================================================================

  const props = defineProps<{
    search: string;
    entityId: number | null;
    status: PatientStatus | null;
    girMin: number | null;
    girMax: number | null;
    entityOptions: Array<{ value: number | null; label: string }>;
    hasActiveFilters: boolean;
  }>();

  const emit = defineEmits<{
    'update:search': [value: string];
    'update:entityId': [value: number | null];
    'update:status': [value: PatientStatus | null];
    'update:girMin': [value: number | null];
    'update:girMax': [value: number | null];
    reset: [];
  }>();

  // =============================================================================
  // OPTIONS STATIQUES
  // =============================================================================

  const statusOptions = [
    { value: null, label: 'Tous les statuts' },
    { value: 'ACTIVE' as PatientStatus, label: 'Actifs' },
    { value: 'INACTIVE' as PatientStatus, label: 'Inactifs' },
    { value: 'ARCHIVED' as PatientStatus, label: 'Archivés' },
    { value: 'DECEASED' as PatientStatus, label: 'Décédés' },
  ];

  const girOptions = [
    { value: null, label: 'Tous les GIR' },
    { value: 1, label: 'GIR 1-2 (très dépendant)' },
    { value: 3, label: 'GIR 3-4 (dépendance partielle)' },
    { value: 5, label: 'GIR 5-6 (peu/pas dépendant)' },
  ];

  // =============================================================================
  // METHODS
  // =============================================================================

  /** Applique un filtre GIR par plage */
  function onGirFilterChange(value: number | null) {
    if (value === null) {
      emit('update:girMin', null);
      emit('update:girMax', null);
    } else if (value === 1) {
      emit('update:girMin', 1);
      emit('update:girMax', 2);
    } else if (value === 3) {
      emit('update:girMin', 3);
      emit('update:girMax', 4);
    } else if (value === 5) {
      emit('update:girMin', 5);
      emit('update:girMax', 6);
    }
  }

  /** Déduit la valeur du dropdown GIR depuis les filtres actuels */
  function getCurrentGirValue(): number | null {
    if (props.girMin === 1 && props.girMax === 2) return 1;
    if (props.girMin === 3 && props.girMax === 4) return 3;
    if (props.girMin === 5 && props.girMax === 6) return 5;
    return null;
  }
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <div class="flex flex-col md:flex-row gap-3">
      <!-- Recherche -->
      <IconField class="flex-1">
        <InputIcon class="pi pi-search" />
        <InputText
          :modelValue="search"
          placeholder="Rechercher par nom, prénom ou NIR..."
          class="w-full"
          @update:modelValue="(val: string | undefined) => emit('update:search', val ?? '')"
        />
      </IconField>

      <!-- Filtre entité -->
      <Select
        :modelValue="entityId"
        :options="entityOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Entité"
        class="w-full md:w-52"
        @update:modelValue="$emit('update:entityId', $event)"
      />

      <!-- Filtre statut -->
      <Select
        :modelValue="status"
        :options="statusOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Statut"
        class="w-full md:w-44"
        @update:modelValue="$emit('update:status', $event)"
      />

      <!-- Filtre GIR -->
      <Select
        :modelValue="getCurrentGirValue()"
        :options="girOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="GIR"
        class="w-full md:w-56"
        @update:modelValue="onGirFilterChange"
      />

      <!-- Reset filtres -->
      <Button
        v-if="hasActiveFilters"
        v-tooltip="'Réinitialiser les filtres'"
        icon="pi pi-filter-slash"
        severity="secondary"
        variant="outlined"
        @click="$emit('reset')"
      />
    </div>
  </div>
</template>