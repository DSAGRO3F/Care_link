<script setup lang="ts">
  /**
   * AppBottomNav.vue — Navigation mobile (bottom tab bar)
   *
   * 🔄 B48 Palier 3 (19/05/2026) — Espace-aware :
   *   - Deux jeux d'onglets (Soins / Admin) sélectionnés selon route.path (convention #125)
   *   - La barre reflète l'espace courant — plus de routes Soins hardcodées
   *   - Dette technique de l'audit 25/02/2026 soldée
   */
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { isRootActive } from '@/utils/navigation';

  const route = useRoute();
  const router = useRouter();

  interface NavItem {
    label: string;
    icon: string;
    to: string;
  }

  // Onglets de l'espace Soins
  const soinsNavItems: NavItem[] = [
    { label: 'Journée', icon: 'pi-home', to: '/soins' },
    { label: 'Patients', icon: 'pi-users', to: '/soins/patients' },
    { label: 'Planning', icon: 'pi-calendar', to: '/soins/planning' },
    { label: 'Liaison', icon: 'pi-comments', to: '/soins/liaison' },
  ];

  // Onglets de l'espace Admin
  const adminNavItems: NavItem[] = [
    { label: 'Tableau de bord', icon: 'pi-chart-bar', to: '/admin' },
    { label: 'Patients', icon: 'pi-heart', to: '/admin/patients' },
    { label: 'Professionnels', icon: 'pi-id-card', to: '/admin/users' },
    { label: "Plans d'aide", icon: 'pi-file-edit', to: '/admin/care-plans' },
  ];

  // Espace courant détecté via l'URL (convention #125 — jamais via isAdmin ni un rôle)
  const isAdminSpace = computed(() => route.path.startsWith('/admin'));

  // Items affichés selon l'espace courant
  const navItems = computed(() => (isAdminSpace.value ? adminNavItems : soinsNavItems));

  // Vérifier si une route est active (cf. convention #128 — cohérent AppSidebar)
  const isActive = (path: string) => isRootActive(route.path, path);

  // Navigation
  const navigate = (path: string) => {
    router.push(path);
  };
</script>

<template>
  <nav class="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-neutral-200 safe-bottom">
    <div class="flex items-center justify-around h-16">
      <button
        v-for="item in navItems"
        :key="item.to"
        :class="isActive(item.to) ? 'text-teal-600' : 'text-neutral-500'"
        class="flex flex-col items-center justify-center flex-1 h-full transition-colors"
        @click="navigate(item.to)"
      >
        <i :class="item.icon" class="pi text-xl mb-1"></i>
        <span class="text-xs font-medium">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>