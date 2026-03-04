<script setup lang="ts">
/**
 * UserCard.vue — Vignette d'un professionnel de santé
 *
 * Composant réutilisable affichant les informations essentielles d'un user :
 *   - Avatar (initiales colorées)
 *   - Nom complet + email
 *   - RPPS si disponible
 *   - Statut actif/inactif
 *   - Rôles sous forme de chips (si fournis via UserResponse)
 *
 * Utilisé dans :
 *   - UsersPage.vue (potentiel mode grille mobile)
 *   - UserDetailPage.vue (carte identité en header)
 *   - Partout où on veut afficher un résumé user
 *
 * Destination : src/components/users/UserCard.vue
 */
import { computed } from 'vue'
import Tag from 'primevue/tag'
import type { UserSummary, RoleResponse } from '@/types/user'

// ─── Props ───────────────────────────────────────────────────────────────────

interface Props {
  /** Données user (UserSummary ou UserResponse) */
  user: UserSummary
  /** Rôles à afficher (optionnel — présents dans UserResponse, pas dans UserSummary) */
  roles?: RoleResponse[]
  /** Afficher l'email sous le nom */
  showEmail?: boolean
  /** Afficher le RPPS */
  showRpps?: boolean
  /** Rendre la carte cliquable */
  clickable?: boolean
  /** Taille compacte (pour listes denses) */
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  roles: () => [],
  showEmail: true,
  showRpps: true,
  clickable: true,
  compact: false,
})

const emit = defineEmits<{
  (e: 'click', user: UserSummary): void
}>()

// ─── Computed ────────────────────────────────────────────────────────────────

const initials = computed(() => {
  const first = props.user.first_name?.[0] ?? ''
  const last = props.user.last_name?.[0] ?? ''
  return `${first}${last}`.toUpperCase() || '?'
})

const fullName = computed(() => {
  return `${props.user.last_name} ${props.user.first_name}`.trim() || 'Sans nom'
})

const avatarClasses = computed(() => {
  const base = 'rounded-full flex items-center justify-center font-semibold'
  const size = props.compact ? 'w-9 h-9 text-xs' : 'w-11 h-11 text-sm'
  const color = props.user.is_active
    ? 'bg-blue-50 text-blue-600'
    : 'bg-slate-100 text-slate-400'
  return `${base} ${size} ${color}`
})

const cardClasses = computed(() => {
  const base = 'flex items-center gap-3 bg-white border border-slate-200 rounded-xl shadow-sm transition-all'
  const padding = props.compact ? 'px-3 py-2.5' : 'px-4 py-3.5'
  const hover = props.clickable ? 'hover:border-blue-300 hover:shadow-md cursor-pointer' : ''
  return `${base} ${padding} ${hover}`
})

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleClick() {
  if (props.clickable) {
    emit('click', props.user)
  }
}
</script>

<template>
  <div :class="cardClasses" @click="handleClick">
    <!-- Avatar -->
    <div :class="avatarClasses">
      {{ initials }}
    </div>

    <!-- Infos -->
    <div class="flex-1 min-w-0">
      <!-- Nom -->
      <p
        class="font-medium text-slate-800 truncate"
        :class="compact ? 'text-sm' : ''"
      >
        {{ fullName }}
      </p>

      <!-- Email -->
      <p
        v-if="showEmail"
        class="text-slate-400 truncate"
        :class="compact ? 'text-xs' : 'text-sm'"
      >
        {{ user.email }}
      </p>

      <!-- RPPS -->
      <p
        v-if="showRpps && user.rpps"
        class="text-slate-400 font-mono"
        :class="compact ? 'text-xs' : 'text-xs mt-0.5'"
      >
        RPPS {{ user.rpps }}
      </p>
    </div>

    <!-- Badges à droite -->
    <div class="flex flex-col items-end gap-1.5 shrink-0">
      <!-- Statut -->
      <Tag
        :value="user.is_active ? 'Actif' : 'Inactif'"
        :severity="user.is_active ? 'success' : 'danger'"
        class="text-xs"
      />

      <!-- Rôles (max 2 affichés) -->
      <div v-if="roles.length > 0" class="flex gap-1">
        <Tag
          v-for="role in roles.slice(0, 2)"
          :key="role.id"
          :value="role.name"
          severity="info"
          class="text-xs"
        />
        <Tag
          v-if="roles.length > 2"
          :value="`+${roles.length - 2}`"
          severity="secondary"
          class="text-xs"
        />
      </div>
    </div>
  </div>
</template>