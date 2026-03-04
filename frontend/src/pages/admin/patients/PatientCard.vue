<script setup lang="ts">
/**
 * PatientCard.vue — Vignette patient pour les listes
 *
 * Affiche un résumé patient : avatar initiales, nom, date de naissance,
 * statut, score GIR. Émet un click pour la navigation vers le détail.
 *
 * Pattern calqué sur UserCard.vue avec adaptations métier :
 *   - Statut patient (ACTIVE/INACTIVE/ARCHIVED/DECEASED) au lieu de is_active
 *   - Score GIR affiché en badge coloré (1-2 = rouge, 3-4 = orange, 5-6 = vert)
 *   - Date de naissance formatée en âge
 *
 * Destination : src/components/patients/PatientCard.vue
 */
import Tag from 'primevue/tag'
import type { PatientSummary } from '@/types/patient'

const props = defineProps<{
  patient: PatientSummary
}>()

defineEmits<{
  click: [patient: PatientSummary]
}>()

// =============================================================================
// HELPERS
// =============================================================================

/** Initiales pour l'avatar */
function getInitials(): string {
  const first = props.patient.first_name?.[0] ?? ''
  const last = props.patient.last_name?.[0] ?? ''
  return `${first}${last}`.toUpperCase() || '?'
}

/** Calcule l'âge à partir de la date de naissance */
function getAge(): string {
  if (!props.patient.birth_date) return '—'
  const birth = new Date(props.patient.birth_date)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--
  }
  return `${age} ans`
}

/** Formate la date de naissance en format français */
function formatBirthDate(): string {
  if (!props.patient.birth_date) return 'Date inconnue'
  const date = new Date(props.patient.birth_date)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Nom complet du patient */
function getFullName(): string {
  const parts = [props.patient.last_name, props.patient.first_name].filter(Boolean)
  return parts.join(' ') || 'Patient sans nom'
}

/** Label et severity du statut */
function getStatusConfig(): { label: string; severity: string } {
  switch (props.patient.status) {
    case 'ACTIVE':
      return { label: 'Actif', severity: 'success' }
    case 'INACTIVE':
      return { label: 'Inactif', severity: 'warn' }
    case 'ARCHIVED':
      return { label: 'Archivé', severity: 'secondary' }
    case 'DECEASED':
      return { label: 'Décédé', severity: 'danger' }
    default:
      return { label: props.patient.status, severity: 'info' }
  }
}

/** Couleur du badge GIR selon le niveau de dépendance */
function getGirConfig(): { label: string; class: string } | null {
  const gir = props.patient.current_gir
  if (!gir) return null

  if (gir <= 2) {
    return { label: `GIR ${gir}`, class: 'bg-red-100 text-red-700' }
  } else if (gir <= 4) {
    return { label: `GIR ${gir}`, class: 'bg-amber-100 text-amber-700' }
  } else {
    return { label: `GIR ${gir}`, class: 'bg-emerald-100 text-emerald-700' }
  }
}

/** Classes CSS de l'avatar selon le statut */
function getAvatarClasses(): string {
  if (props.patient.status === 'ACTIVE') {
    return 'bg-blue-50 text-blue-600'
  }
  return 'bg-slate-100 text-slate-400'
}
</script>

<template>
  <div
    class="flex items-center gap-3 cursor-pointer"
    @click="$emit('click', patient)"
  >
    <!-- Avatar initiales -->
    <div
      class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold shrink-0"
      :class="getAvatarClasses()"
    >
      {{ getInitials() }}
    </div>

    <!-- Infos principales -->
    <div class="flex-1 min-w-0">
      <p class="font-medium text-slate-800 truncate">{{ getFullName() }}</p>
      <p class="text-sm text-slate-400">
        {{ formatBirthDate() }} · {{ getAge() }}
      </p>
    </div>

    <!-- Badges GIR + Statut -->
    <div class="flex items-center gap-2 shrink-0">
      <span
        v-if="getGirConfig()"
        class="text-xs font-semibold px-2 py-0.5 rounded-full"
        :class="getGirConfig()!.class"
      >
        {{ getGirConfig()!.label }}
      </span>
      <Tag
        :value="getStatusConfig().label"
        :severity="getStatusConfig().severity as any"
      />
    </div>
  </div>
</template>