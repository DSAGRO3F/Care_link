<script setup lang="ts">
  /**
   * Layout principal de l'application
   * Sidebar de navigation + header + contenu principal
   */
  import { computed } from 'vue';
  import { useUiStore } from '@/stores';
  import AppHeader from '@/components/common/AppHeader.vue';
  import AppSidebar from '@/components/common/AppSidebar.vue';
  import AppBottomNav from '@/components/common/AppBottomNav.vue';

  const uiStore = useUiStore();

  // Classes dynamiques pour le contenu principal
  const mainClasses = computed(() => ({
    'lg:ml-64': uiStore.sidebarOpen,
    'lg:ml-20': !uiStore.sidebarOpen,
  }));
</script>

<template>
  <div class="min-h-screen bg-neutral-50">
    <!-- Sidebar Desktop -->
    <AppSidebar
      v-if="!uiStore.isMobile"
      :collapsed="!uiStore.sidebarOpen"
      @toggle="uiStore.toggleSidebar"
    />

    <!-- Contenu principal -->
    <div :class="mainClasses" class="flex flex-col min-h-screen transition-all duration-300">
      <!-- Header -->
      <AppHeader />

      <!-- Zone de contenu -->
      <main class="flex-1 p-4 lg:p-6 pb-20 lg:pb-6">
        <slot />
      </main>
    </div>

    <!-- Navigation mobile (bottom) -->
    <AppBottomNav v-if="uiStore.isMobile" />
  </div>
</template>
