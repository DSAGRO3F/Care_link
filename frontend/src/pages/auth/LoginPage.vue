<script setup lang="ts">
  /**
   * Page de connexion
   * - Bouton Pro Santé Connect (principal)
   * - Formulaire email/mot de passe (secondaire)
   * 🆕 Option 1 teal unifié — bouton PSC teal gradient, bouton login teal
   */
  import { ref, onMounted } from 'vue';
  import { useRouter, useRoute } from 'vue-router';
  import { useAuthStore } from '@/stores';
  import { authService } from '@/services';
  import { getDefaultRoute } from '@/utils/routing';
  import Button from 'primevue/button';
  import InputText from 'primevue/inputtext';
  import Password from 'primevue/password';
  import Message from 'primevue/message';

  const router = useRouter();
  const route = useRoute();
  const authStore = useAuthStore();

  // État du formulaire
  const email = ref('');
  const password = ref('');
  const tenantCode = ref('');
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Config PSC
  const pscConfigured = ref(false);

  // Vérifier si PSC est configuré au chargement
  onMounted(async () => {
    try {
      const status = await authService.getStatus();
      pscConfigured.value = status.psc_configured;
    } catch {
      console.warn('Impossible de vérifier la configuration PSC');
    }
  });

  // Connexion via Pro Santé Connect
  const loginWithPSC = async () => {
    try {
      const redirectAfter = route.query.redirect as string | undefined;
      await authStore.loginWithPSC(redirectAfter);
    } catch (_err) {
      error.value = 'Impossible de se connecter à Pro Santé Connect';
    }
  };

  // Connexion email/mot de passe
  const loginWithCredentials = async () => {
    if (!tenantCode.value || !email.value || !password.value) {
      error.value = 'Veuillez remplir tous les champs';
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      await authStore.loginWithCredentials(tenantCode.value, email.value, password.value);

      // Rediriger vers la page demandée ou le dashboard
      const redirect = (route.query.redirect as string) || getDefaultRoute(authStore.user);
      router.push(redirect);
    } catch (_err) {
      error.value = 'Identifiants incorrects';
    } finally {
      isLoading.value = false;
    }
  };
</script>

<template>
  <div class="space-y-5">
    <!-- Titre section -->
    <div class="text-center">
      <h2 class="text-lg font-semibold text-slate-800">Connexion</h2>
      <p class="text-slate-400 text-sm mt-0.5">Accédez à votre espace CareLink</p>
    </div>

    <!-- Message d'erreur -->
    <Message v-if="error" :closable="false" severity="error">
      {{ error }}
    </Message>

    <!-- Bouton Pro Santé Connect -->
    <div v-if="pscConfigured" class="space-y-4">
      <button class="btn-psc w-full" @click="loginWithPSC">
        <i class="pi pi-shield text-sm"></i>
        Se connecter avec Pro Santé Connect
      </button>

      <div class="relative">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-slate-200"></div>
        </div>
        <div class="relative flex justify-center text-sm">
          <span class="px-4 bg-white text-slate-400 text-xs">ou</span>
        </div>
      </div>
    </div>

    <!-- Formulaire email/mot de passe -->
    <form class="space-y-4" @submit.prevent="loginWithCredentials">
      <div class="input-group">
        <label for="tenantCode" class="input-label">Code structure</label>
        <InputText
          id="tenantCode"
          v-model="tenantCode"
          :disabled="isLoading"
          placeholder="Ex: SSIAD-NORD"
          class="w-full"
        />
        <small class="text-slate-400 text-xs mt-1 block">
          Communiqué par votre administrateur CareLink
        </small>
      </div>

      <div class="input-group">
        <label for="email" class="input-label">Email</label>
        <InputText
          id="email"
          v-model="email"
          :disabled="isLoading"
          type="email"
          placeholder="votre@email.fr"
          class="w-full"
        />
      </div>

      <div class="input-group">
        <label for="password" class="input-label">Mot de passe</label>
        <Password
          id="password"
          v-model="password"
          :feedback="false"
          :disabled="isLoading"
          placeholder="••••••••"
          class="w-full"
          inputClass="w-full"
          toggleMask
        />
      </div>

      <Button
        :loading="isLoading"
        type="submit"
        label="Se connecter"
        icon="pi pi-sign-in"
        class="w-full"
      />
    </form>

    <!-- Lien mot de passe oublié -->
    <p class="text-center text-sm">
      <a href="#" class="text-teal-600 hover:text-teal-700 hover:underline transition-colors">
        Mot de passe oublié ?
      </a>
    </p>
  </div>
</template>

<style scoped>
  /* Bouton Pro Santé Connect — dégradé teal → cyan unifié */
  .btn-psc {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 11px 16px;
    border-radius: 8px;
    border: none;
    background: linear-gradient(135deg, #0d9488 0%, #0891b2 100%);
    color: white;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    letter-spacing: 0.01em;
    box-shadow: 0 3px 10px -2px rgba(13, 148, 136, 0.45);
    transition:
      opacity 0.2s,
      box-shadow 0.2s;
  }

  .btn-psc:hover {
    opacity: 0.92;
    box-shadow: 0 5px 14px -3px rgba(13, 148, 136, 0.5);
  }

  .btn-psc:active {
    opacity: 0.85;
  }
</style>