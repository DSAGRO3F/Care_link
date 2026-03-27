<script setup lang="ts">
  /**
   * RoleCard.vue — Carte d'un rôle fonctionnel (Zone 1 de RolesPage)
   *
   * Affiche : icône pastille, nom, description, badge Système,
   * compteur permissions, compteur utilisateurs.
   *
   * Le rôle ADMIN a un traitement visuel distinct (accent amber)
   * pour signaler le court-circuit ADMIN_FULL.
   */
  import { computed } from 'vue';
  import type { RoleResponse } from '@/types';
  import { ROLE_DISPLAY_CONFIG } from '@/types';

  const props = defineProps<{
    role: RoleResponse;
    selected: boolean;
    userCount: number;
  }>();

  const emit = defineEmits<{
    select: [role: RoleResponse];
  }>();

  // ─── Config d'affichage du rôle ─────────────────────────────────────────────

  const config = computed(
    () =>
      ROLE_DISPLAY_CONFIG[props.role.name] ?? {
        icon: 'pi pi-circle',
        color: 'slate',
        description: props.role.description ?? '',
      },
  );

  const isAdmin = computed(() => props.role.name === 'ADMIN');

  // ─── Compteur permissions lisible ───────────────────────────────────────────

  const permissionLabel = computed(() => {
    if (isAdmin.value) return 'Accès complet';
    const n = props.role.permissions.length;
    return `${n} permission${n > 1 ? 's' : ''}`;
  });

  const userLabel = computed(() => {
    const n = props.userCount;
    if (n === 0) return 'Aucun professionnel';
    return `${n} professionnel${n > 1 ? 's' : ''}`;
  });

  // ─── Classes Tailwind dynamiques (pastille & sélection) ─────────────────────
  // Toutes les classes sont écrites en clair pour que Tailwind JIT les détecte.

  const pastilleClasses = computed(() => {
    const map: Record<string, string> = {
      amber: 'bg-amber-100 text-amber-600',
      teal: 'bg-teal-50 text-teal-600',
      blue: 'bg-blue-50 text-blue-600',
      violet: 'bg-violet-50 text-violet-600',
      slate: 'bg-slate-100 text-slate-600',
    };
    return map[config.value.color] ?? 'bg-slate-100 text-slate-600';
  });

  const cardClasses = computed(() => {
    if (props.selected && isAdmin.value) {
      return 'border-amber-400 bg-amber-50/30 ring-1 ring-amber-200';
    }
    if (props.selected) {
      return 'border-teal-400 bg-teal-50/30 ring-1 ring-teal-200';
    }
    return 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm';
  });
</script>

<template>
  <button
    :class="cardClasses"
    class="relative flex flex-col gap-4 p-5 text-left rounded-2xl border transition-all duration-200 cursor-pointer w-full"
    @click="emit('select', role)"
  >
    <!-- Ligne supérieure : pastille + badges -->
    <div class="flex items-start justify-between">
      <!-- Pastille icône -->
      <div :class="pastilleClasses" class="flex items-center justify-center w-11 h-11 rounded-xl">
        <i :class="config.icon" class="text-lg" />
      </div>

      <!-- Badges -->
      <div class="flex items-center gap-2">
        <span
          v-if="role.is_system_role"
          class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500"
        >
          <i class="pi pi-lock text-[10px]" />
          Système
        </span>
        <span
          v-if="isAdmin"
          class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700"
        >
          ADMIN_FULL
        </span>
      </div>
    </div>

    <!-- Nom du rôle -->
    <div>
      <h3 class="text-base font-semibold text-slate-800">
        {{ role.name }}
      </h3>
      <p class="mt-0.5 text-sm text-slate-400 leading-snug">
        {{ config.description || role.description }}
      </p>
    </div>

    <!-- Compteurs -->
    <div class="flex items-center gap-4 pt-1 border-t border-slate-100">
      <span class="inline-flex items-center gap-1.5 text-xs text-slate-500">
        <i class="pi pi-key text-[11px]" />
        {{ permissionLabel }}
      </span>
      <span class="inline-flex items-center gap-1.5 text-xs text-slate-500">
        <i class="pi pi-users text-[11px]" />
        {{ userLabel }}
      </span>
    </div>

    <!-- Indicateur de sélection -->
    <div
      v-if="selected"
      :class="isAdmin ? 'bg-amber-400' : 'bg-teal-500'"
      class="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-3 h-3 rounded-full"
    />
  </button>
</template>
