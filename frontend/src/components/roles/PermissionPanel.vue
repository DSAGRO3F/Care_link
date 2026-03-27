<script setup lang="ts">
  /**
   * PermissionPanel.vue — Panel inline des permissions d'un rôle (Zone 2 de RolesPage)
   *
   * Affiche les permissions groupées par catégorie (Patient, Évaluation, etc.)
   * avec des checkmarks en lecture seule.
   *
   * Cas spécial : le rôle ADMIN avec ADMIN_FULL affiche un message
   * de court-circuit au lieu de la liste détaillée.
   */
  import { computed } from 'vue';
  import type { RoleResponse } from '@/types';
  import {
    PERMISSION_CATEGORIES,
    PERMISSION_CATEGORY_ORDER,
    PERMISSION_LABELS,
    getPermissionCategory,
  } from '@/types';

  const props = defineProps<{
    role: RoleResponse;
  }>();

  // ─── Détection ADMIN_FULL ───────────────────────────────────────────────────

  const isAdminFull = computed(() => props.role.permissions.includes('ADMIN_FULL'));

  // ─── Groupement des permissions par catégorie ───────────────────────────────

  interface PermissionGroup {
    key: string;
    label: string;
    icon: string;
    color: string;
    permissions: { code: string; label: string }[];
  }

  const groupedPermissions = computed<PermissionGroup[]>(() => {
    if (isAdminFull.value) return [];

    // Grouper les permissions par catégorie
    const grouped = new Map<string, { code: string; label: string }[]>();

    for (const code of props.role.permissions) {
      const cat = getPermissionCategory(code);
      if (!grouped.has(cat)) grouped.set(cat, []);
      grouped.get(cat)!.push({
        code,
        label: PERMISSION_LABELS[code] ?? code,
      });
    }

    // Construire les groupes dans l'ordre défini
    return PERMISSION_CATEGORY_ORDER.filter((key) => grouped.has(key)).map((key) => {
      const cat = PERMISSION_CATEGORIES[key];
      return {
        key,
        label: cat?.label ?? key,
        icon: cat?.icon ?? 'pi pi-circle',
        color: cat?.color ?? 'slate',
        permissions: grouped.get(key)!,
      };
    });
  });

  // ─── Classes couleur par catégorie ──────────────────────────────────────────
  // Écrites en clair pour Tailwind JIT.

  function getCategoryColors(color: string) {
    const map: Record<string, { bg: string; text: string; check: string; iconBg: string }> = {
      teal: {
        bg: 'bg-teal-50/50',
        text: 'text-teal-700',
        check: 'text-teal-500',
        iconBg: 'bg-teal-100 text-teal-600',
      },
      blue: {
        bg: 'bg-blue-50/50',
        text: 'text-blue-700',
        check: 'text-blue-500',
        iconBg: 'bg-blue-100 text-blue-600',
      },
      red: {
        bg: 'bg-red-50/50',
        text: 'text-red-700',
        check: 'text-red-500',
        iconBg: 'bg-red-100 text-red-600',
      },
      violet: {
        bg: 'bg-violet-50/50',
        text: 'text-violet-700',
        check: 'text-violet-500',
        iconBg: 'bg-violet-100 text-violet-600',
      },
      amber: {
        bg: 'bg-amber-50/50',
        text: 'text-amber-700',
        check: 'text-amber-500',
        iconBg: 'bg-amber-100 text-amber-600',
      },
      slate: {
        bg: 'bg-slate-50',
        text: 'text-slate-700',
        check: 'text-slate-500',
        iconBg: 'bg-slate-100 text-slate-600',
      },
      zinc: {
        bg: 'bg-zinc-50',
        text: 'text-zinc-700',
        check: 'text-zinc-500',
        iconBg: 'bg-zinc-100 text-zinc-600',
      },
    };
    return map[color] ?? map.slate;
  }
</script>

<template>
  <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden">
    <!-- En-tête du panel -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
      <div class="flex items-center gap-3">
        <h2 class="text-base font-semibold text-slate-800">Permissions du rôle</h2>
        <span class="text-sm font-medium text-teal-600">
          {{ role.name }}
        </span>
      </div>
      <span v-if="!isAdminFull" class="text-xs text-slate-400">
        {{ role.permissions.length }} permission{{ role.permissions.length > 1 ? 's' : '' }}
      </span>
    </div>

    <!-- Cas ADMIN_FULL : message court-circuit -->
    <div v-if="isAdminFull" class="px-6 py-8">
      <div class="flex items-start gap-4 p-5 rounded-xl bg-amber-50/60 border border-amber-200">
        <div class="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-100 shrink-0">
          <i class="pi pi-shield text-amber-600 text-lg" />
        </div>
        <div>
          <p class="font-semibold text-amber-800 mb-1">Accès complet — ADMIN_FULL</p>
          <p class="text-sm text-amber-700 leading-relaxed">
            Ce rôle court-circuite toutes les vérifications de permission. Un utilisateur avec le
            rôle <strong>ADMIN</strong> dispose d'un accès total à l'ensemble des fonctionnalités du
            tenant, indépendamment des permissions individuelles.
          </p>
        </div>
      </div>
    </div>

    <!-- Cas normal : permissions groupées par catégorie -->
    <div v-else class="px-6 py-5 space-y-5">
      <div v-for="group in groupedPermissions" :key="group.key">
        <!-- En-tête catégorie -->
        <div class="flex items-center gap-3 mb-3">
          <div
            :class="getCategoryColors(group.color).iconBg"
            class="flex items-center justify-center w-8 h-8 rounded-lg"
          >
            <i :class="group.icon" class="text-sm" />
          </div>
          <span class="text-sm font-semibold text-slate-700">
            {{ group.label }}
          </span>
          <span class="text-xs text-slate-400">
            — {{ group.permissions.length }} permission{{ group.permissions.length > 1 ? 's' : '' }}
          </span>
        </div>

        <!-- Liste des permissions -->
        <div class="ml-11 space-y-1.5">
          <div
            v-for="perm in group.permissions"
            :key="perm.code"
            :class="getCategoryColors(group.color).bg"
            class="flex items-center gap-3 py-1.5 px-3 rounded-lg transition-colors"
          >
            <i :class="getCategoryColors(group.color).check" class="pi pi-check-circle text-sm" />
            <span class="text-sm text-slate-600 flex-1">
              {{ perm.label }}
            </span>
            <code class="text-[11px] text-slate-400 font-mono hidden sm:inline">
              {{ perm.code }}
            </code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
