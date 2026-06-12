<script setup lang="ts">
  /**
   * AppSidebar.vue — Sidebar de navigation (desktop) — shell unique
   *
   * 🔄 B48 Palier 3 (19/05/2026) — Shell unifié :
   *   - Sidebar unique des espaces /soins ET /admin (layout admin dédié retiré)
   *   - Gating des sections Gestion/Configuration migré isAdmin → hasPermission('ADMIN_FULL')
   *   - isActive : exact-match sur les chemins racines (/admin, /soins) pour éviter
   *     le double-surlignage de l'item racine sur les sous-routes
   *
   * 🔄 v5.29 — Design unifié prototype C : fond slate-50, accent teal, sections en
   *   cards (en-tête pastille + titre teal), 3 sections Soins/Gestion/Configuration.
   *
   * Destination : src/components/common/AppSidebar.vue
   */
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useAuthStore } from '@/stores';
  import { isRootActive } from '@/utils/navigation';

  defineProps<{
    collapsed: boolean;
  }>();

  const emit = defineEmits<{
    toggle: [];
  }>();

  const route = useRoute();
  const router = useRouter();
  const authStore = useAuthStore();

  // ─── Navigation par sections (cards) ───────────────────────────────────────

  interface NavChild {
    label: string;
    icon: string;
    to: string;
  }

  interface NavSection {
    label: string;
    sectionIcon: string;
    visible: boolean;
    children: NavChild[];
  }

  const menuSections = computed<NavSection[]>(() => {
    const sections: NavSection[] = [
      // Section Soins — visible par tous
      {
        label: 'Soins',
        sectionIcon: 'pi-heart',
        visible: true,
        children: [
          { label: 'Ma journée', icon: 'pi-home', to: '/soins' },
          { label: 'Mes patients', icon: 'pi-users', to: '/soins/patients' },
          { label: 'Mes brouillons', icon: 'pi-pencil', to: '/soins/care-plans/drafts' },
          ...(authStore.hasPermission('VALIDATION_VIEW')
            ? [{ label: 'Validation', icon: 'pi-check-square', to: '/soins/validation' }]
            : []),
          { label: 'Planning', icon: 'pi-calendar', to: '/soins/planning' },
          { label: 'Liaison', icon: 'pi-comments', to: '/soins/liaison' },
        ],
      },
      // Section Gestion — visible si permission ADMIN_FULL
      {
        label: 'Gestion',
        sectionIcon: 'pi-th-large',
        visible: authStore.hasPermission('ADMIN_FULL'),
        children: [
          { label: 'Tableau de bord', icon: 'pi-chart-bar', to: '/admin' },
          { label: 'Professionnels', icon: 'pi-id-card', to: '/admin/users' },
          { label: 'Patients', icon: 'pi-heart', to: '/admin/patients' },
          { label: 'Structure', icon: 'pi-sitemap', to: '/admin/entities' },
          { label: 'Catalogue', icon: 'pi-book', to: '/admin/catalog' },
          { label: 'Catalogue consolidé', icon: 'pi-share-alt', to: '/admin/coordination-catalog' },
          { label: "Plans d'aide", icon: 'pi-file-edit', to: '/admin/care-plans' },
        ],
      },
      // Section Configuration — visible si permission ADMIN_FULL
      {
        label: 'Configuration',
        sectionIcon: 'pi-cog',
        visible: authStore.hasPermission('ADMIN_FULL'),
        children: [{ label: 'Rôles', icon: 'pi-shield', to: '/admin/roles' }],
      },
    ];

    return sections.filter((s) => s.visible);
  });

  // Vérifier si une route est active (cf. convention #128)
  const isActive = (path: string) => isRootActive(route.path, path);

  // Navigation
  const navigate = (path: string) => {
    router.push(path);
  };
</script>

<template>
  <aside
    :class="collapsed ? 'w-20' : 'w-64'"
    class="fixed top-0 left-0 z-30 h-screen bg-slate-50 border-r border-slate-200 transition-all duration-300"
  >
    <!-- ─── Header ─── -->
    <div class="flex items-center h-16 px-3.5 bg-white border-b border-slate-200">
      <div class="flex items-center gap-3">
        <div
          class="w-9 h-9 rounded-lg text-white font-bold text-xs flex items-center justify-center flex-shrink-0"
          style="background: linear-gradient(135deg, #14b8a6, #0d9488)"
        >
          CL
        </div>
        <div v-if="!collapsed" class="flex flex-col">
          <span class="text-sm font-bold text-slate-800">CareLink</span>
          <span class="text-[11px] text-teal-600 font-medium">Coordination des soins</span>
        </div>
      </div>

      <!-- Bouton toggle -->
      <button
        class="ml-auto p-2 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
        @click="emit('toggle')"
      >
        <i :class="collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"></i>
      </button>
    </div>

    <!-- ─── Navigation (section cards) ─── -->
    <nav class="p-2.5 overflow-y-auto h-[calc(100vh-4rem)] scrollbar-thin space-y-2">
      <div
        v-for="section in menuSections"
        :key="section.label"
        class="bg-white rounded-[10px] border border-slate-200 overflow-hidden"
      >
        <!-- En-tête section (card header avec pastille) -->
        <div
          v-if="!collapsed"
          class="flex items-center gap-2.5 px-3.5 py-2 border-b border-slate-100"
          style="background: linear-gradient(to right, #f0fdfa, #ffffff)"
        >
          <div
            class="w-[26px] h-[26px] flex items-center justify-center bg-teal-100 rounded-md flex-shrink-0"
          >
            <i :class="['pi', section.sectionIcon, 'text-xs text-teal-600']"></i>
          </div>
          <span class="text-[11.5px] font-bold uppercase tracking-wide text-teal-700">
            {{ section.label }}
          </span>
        </div>
        <!-- Mode collapsed : barre teal discrète -->
        <div v-else class="h-0.5 bg-teal-100" />

        <!-- Items -->
        <div class="p-1.5">
          <button
            v-for="item in section.children"
            :key="item.to"
            :class="
              isActive(item.to)
                ? 'bg-teal-50 text-teal-700 font-semibold'
                : 'text-slate-500 hover:bg-teal-50 hover:text-teal-700'
            "
            :title="collapsed ? item.label : undefined"
            class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors"
            @click="navigate(item.to)"
          >
            <i
              :class="[
                'pi',
                item.icon,
                'text-[15px]',
                isActive(item.to) ? 'text-teal-500' : 'text-slate-400',
              ]"
            ></i>
            <span v-if="!collapsed" class="font-medium">{{ item.label }}</span>
          </button>
        </div>
      </div>
    </nav>
  </aside>
</template>