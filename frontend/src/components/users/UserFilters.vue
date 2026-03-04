<script setup lang="ts">
/**
 * UserFilters.vue — Barre de filtres pour listes d'utilisateurs
 *
 * Composant réutilisable qui émet les changements de filtres vers le parent.
 * Ne gère pas d'état global — c'est le parent (UsersPage) ou le store qui pilote.
 *
 * Filtres disponibles :
 *   - Recherche textuelle (nom, email, RPPS)
 *   - Entité de rattachement (dropdown)
 *   - Rôle (dropdown)
 *   - Statut actif/inactif (dropdown)
 *
 * Usage :
 *   <UserFilters
 *     v-model:search="searchQuery"
 *     v-model:entityId="selectedEntityId"
 *     v-model:role="selectedRole"
 *     v-model:status="selectedStatus"
 *     :entity-options="entityOptions"
 *     :role-options="roleOptions"
 *     :has-active-filters="adminStore.hasActiveFilters"
 *     @reset="resetAllFilters"
 *   />
 *
 * Destination : src/components/users/UserFilters.vue
 */
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Select from 'primevue/select'
import Button from 'primevue/button'

// ─── Props ───────────────────────────────────────────────────────────────────

interface SelectOption {
  value: string | number | boolean | null
  label: string
}

interface Props {
  /** Valeur du champ recherche */
  search: string
  /** ID de l'entité sélectionnée */
  entityId: number | null
  /** Rôle sélectionné */
  role: string | null
  /** Statut actif/inactif sélectionné */
  status: boolean | null
  /** Options pour le dropdown entités */
  entityOptions?: SelectOption[]
  /** Options pour le dropdown rôles */
  roleOptions?: SelectOption[]
  /** Afficher le bouton reset */
  hasActiveFilters?: boolean
}

withDefaults(defineProps<Props>(), {
  entityOptions: () => [{ value: null, label: 'Toutes les entités' }],
  roleOptions: () => [{ value: null, label: 'Tous les rôles' }],
  hasActiveFilters: false,
})

// ─── Emits ───────────────────────────────────────────────────────────────────

const emit = defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'update:entityId', value: number | null): void
  (e: 'update:role', value: string | null): void
  (e: 'update:status', value: boolean | null): void
  (e: 'reset'): void
}>()

// ─── Options statiques ──────────────────────────────────────────────────────

const statusOptions: SelectOption[] = [
  { value: null, label: 'Tous les statuts' },
  { value: true, label: 'Actifs' },
  { value: false, label: 'Inactifs' },
]
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <div class="flex flex-col md:flex-row gap-3">
      <!-- Recherche -->
      <div class="flex-1">
      <IconField class="flex-1">
          <InputIcon class="pi pi-search" />
          <InputText
            :modelValue="search"
            @update:modelValue="emit('update:search', ($event as string) ?? '')"
            placeholder="Rechercher par nom, email ou RPPS..."
            class="w-full"
          />
        </IconField>
      </div>

      <!-- Filtre entité -->
      <Select
        :modelValue="entityId"
        @update:modelValue="emit('update:entityId', $event as number | null)"
        :options="entityOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Entité"
        class="w-full md:w-52"
      />

      <!-- Filtre rôle -->
      <Select
        :modelValue="role"
        @update:modelValue="emit('update:role', $event as string | null)"
        :options="roleOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Rôle"
        class="w-full md:w-48"
      />

      <!-- Filtre statut -->
      <Select
        :modelValue="status"
        @update:modelValue="emit('update:status', $event as boolean | null)"
        :options="statusOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Statut"
        class="w-full md:w-40"
      />

      <!-- Reset filtres -->
      <Button
        v-if="hasActiveFilters"
        icon="pi pi-filter-slash"
        severity="secondary"
        variant="outlined"
        @click="emit('reset')"
        v-tooltip="'Réinitialiser les filtres'"
      />
    </div>
  </div>
</template>