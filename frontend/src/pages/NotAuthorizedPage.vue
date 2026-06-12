<script setup lang="ts">
/**
 * NotAuthorizedPage — Page 403 affichée quand un utilisateur tente
 * d'accéder à une route dont les `requiredPermissions` ne sont pas
 * satisfaites par ses permissions effectives.
 *
 * B48 Palier 4 / 4c — branchée par le guard `beforeEach` de
 * `router/index.ts` qui redirige vers `{ name: 'not-authorized' }`
 * en cas d'échec de `hasAnyPermission(...)`.
 *
 * Pas de `requiredPermissions` sur sa propre route (sinon boucle infinie).
 *
 * Destination : src/pages/NotAuthorizedPage.vue
 */
import { useRouter } from 'vue-router';
import Button from 'primevue/button';
import { useAuthStore } from '@/stores';
import { getDefaultRouteName } from '@/utils/routing';

const router = useRouter();
const authStore = useAuthStore();

function goHome() {
  const targetName = getDefaultRouteName(authStore.user);
  router.push({ name: targetName });
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[60vh] p-8">
    <div class="text-center max-w-md">
      <div class="text-6xl text-orange-500 mb-6">
        <i class="pi pi-lock" />
      </div>
      <h1 class="text-3xl font-semibold mb-2 text-slate-800">
        Accès refusé
      </h1>
      <p class="text-lg text-slate-600 mb-2">
        Vous n'avez pas les permissions nécessaires pour accéder à cette page.
      </p>
      <p class="text-sm text-slate-500 mb-8">
        Si vous pensez qu'il s'agit d'une erreur, contactez l'administrateur
        de votre structure.
      </p>
      <Button
        label="Retour à mon accueil"
        icon="pi pi-home"
        @click="goHome"
      />
    </div>
  </div>
</template>