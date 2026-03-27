<script setup lang="ts">
  /**
   * RoleChips.vue — Badges de rôles utilisateur
   *
   * Affiche les rôles d'un professionnel sous forme de chips colorés.
   * Supporte un mode éditable (ajout/suppression) pour les formulaires.
   *
   * Usage lecture seule :
   *   <RoleChips :roles="user.roles" />
   *
   * Usage éditable :
   *   <RoleChips :roles="user.roles" editable @remove="onRemoveRole" />
   *
   * Destination : src/components/users/RoleChips.vue
   */
  import { computed } from 'vue';
  import Tag from 'primevue/tag';
  import type { RoleResponse } from '@/types';

  // ─── Props ───────────────────────────────────────────────────────────────────

  interface Props {
    /** Liste des rôles à afficher */
    roles: RoleResponse[];
    /** Nombre maximum de rôles affichés avant "+N" */
    max?: number;
    /** Rendre les chips supprimables */
    editable?: boolean;
    /** Taille des chips */
    size?: 'small' | 'normal';
  }

  const props = withDefaults(defineProps<Props>(), {
    max: 5,
    editable: false,
    size: 'normal',
  });

  const emit = defineEmits<{
    (e: 'remove', role: RoleResponse): void;
  }>();

  // ─── Computed ────────────────────────────────────────────────────────────────

  const visibleRoles = computed(() => props.roles.slice(0, props.max));
  const hiddenCount = computed(() => Math.max(0, props.roles.length - props.max));

  /**
   * Couleur selon le type de rôle :
   *   - Rôles système (IDE, AS, IDEC...) → blue
   *   - Rôles admin → amber
   *   - Rôles personnalisés → slate
   */
  function getRoleSeverity(role: RoleResponse): string {
    if (role.name.toLowerCase().includes('admin')) return 'warn';
    if (role.is_system_role) return 'info';
    return 'secondary';
  }
</script>

<template>
  <div class="flex flex-wrap gap-1.5">
    <!-- Aucun rôle -->
    <span v-if="roles.length === 0" class="text-sm text-slate-400 italic"> Aucun rôle </span>

    <!-- Rôles visibles -->
    <Tag
      v-for="role in visibleRoles"
      :key="role.id"
      :value="role.name"
      :severity="getRoleSeverity(role)"
      :class="size === 'small' ? 'text-xs' : ''"
    >
      <template v-if="editable" #default>
        <span class="flex items-center gap-1">
          {{ role.name }}
          <i
            class="pi pi-times text-xs cursor-pointer opacity-60 hover:opacity-100"
            @click.stop="emit('remove', role)"
          />
        </span>
      </template>
    </Tag>

    <!-- Overflow "+N" -->
    <Tag
      v-if="hiddenCount > 0"
      v-tooltip="`${hiddenCount} rôle(s) supplémentaire(s)`"
      :value="`+${hiddenCount}`"
      :class="size === 'small' ? 'text-xs' : ''"
      severity="secondary"
    />
  </div>
</template>
