<script setup lang="ts">
  /**
   * Page de callback Pro Santé Connect
   * Traite le code d'autorisation retourné par PSC
   */
  import { onMounted, ref } from 'vue';
  import { useRouter, useRoute } from 'vue-router';
  import { useAuthStore } from '@/stores';
  import ProgressSpinner from 'primevue/progressspinner';
  import Message from 'primevue/message';
  import Button from 'primevue/button';

  const router = useRouter();
  const route = useRoute();
  const authStore = useAuthStore();

  const error = ref<string | null>(null);

  onMounted(async () => {
    const code = route.query.code as string;
    const state = route.query.state as string;
    const errorParam = route.query.error as string;

    // Erreur retournée par PSC
    if (errorParam) {
      const errorDesc = route.query.error_description as string;
      error.value = errorDesc || errorParam;
      return;
    }

    // Paramètres manquants
    if (!code || !state) {
      error.value = "Paramètres d'authentification manquants";
      return;
    }

    try {
      // Échanger le code contre des tokens
      await authStore.handlePSCCallback(code, state);

      // Rediriger vers la page demandée ou le dashboard
      const redirectAfter = (route.query.redirect_after as string) || '/soins';
      router.push(redirectAfter);
    } catch (_err) {
      error.value = "Échec de l'authentification. Veuillez réessayer.";
    }
  });

  const goToLogin = () => {
    router.push('/login');
  };
</script>

<template>
  <div class="text-center space-y-6">
    <!-- Chargement -->
    <div v-if="!error" class="space-y-4">
      <ProgressSpinner style="width: 50px; height: 50px" strokeWidth="4" />
      <p class="text-neutral-600">Connexion en cours...</p>
      <p class="text-sm text-neutral-500">Vérification de votre identité Pro Santé Connect</p>
    </div>

    <!-- Erreur -->
    <div v-else class="space-y-4">
      <div class="w-16 h-16 mx-auto rounded-full bg-danger-100 flex items-center justify-center">
        <i class="pi pi-times text-3xl text-danger-600"></i>
      </div>

      <h2 class="text-xl font-semibold text-neutral-900">Échec de la connexion</h2>

      <Message :closable="false" severity="error">
        {{ error }}
      </Message>

      <Button label="Retour à la connexion" icon="pi pi-arrow-left" @click="goToLogin" />
    </div>
  </div>
</template>