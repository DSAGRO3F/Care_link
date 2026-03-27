<script setup lang="ts">
  /**
   * Navigation mobile (bottom tab bar)
   * 4 onglets principaux pour l'accès rapide
   */
  import { useRoute, useRouter } from 'vue-router';

  const route = useRoute();
  const router = useRouter();

  // Items de navigation mobile
  // ⚠️ DETTE TECHNIQUE (audit 25/02/2026)
  // Ces routes sont hardcodées pour l'espace soins. Quand le mobile admin
  // sera développé, ce composant devra recevoir ses items en prop ou détecter
  // l'espace courant via la route (soins vs admin) pour afficher les bons items.
  // AdminLayout contourne le problème avec sa propre sidebar intégrée,
  // mais utilise quand même AppBottomNav sur mobile → incohérence.
  const navItems = [
    { label: 'Journée', icon: 'pi-home', to: '/soins' },
    { label: 'Patients', icon: 'pi-users', to: '/soins/patients' },
    { label: 'Planning', icon: 'pi-calendar', to: '/soins/planning' },
    { label: 'Liaison', icon: 'pi-comments', to: '/soins/liaison' },
  ];

  // Vérifier si une route est active
  const isActive = (path: string) => {
    if (path === '/soins') {
      return route.path === '/soins' || route.path === '/soins/';
    }
    return route.path.startsWith(path);
  };

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
        :class="isActive(item.to) ? 'text-primary-600' : 'text-neutral-500'"
        class="flex flex-col items-center justify-center flex-1 h-full transition-colors"
        @click="navigate(item.to)"
      >
        <i :class="item.icon" class="pi text-xl mb-1"></i>
        <span class="text-xs font-medium">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>
