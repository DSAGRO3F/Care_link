<script setup lang="ts">
/**
 * Page de connexion
 * - Bouton Pro Santé Connect (principal)
 * - Formulaire email/mot de passe (secondaire)
 */
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores'
import { authService } from '@/services'
import { getDefaultRoute } from '@/utils/routing'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// État du formulaire
const email = ref('')
const password = ref('')
const tenantCode = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

// Config PSC
const pscConfigured = ref(false)

// Vérifier si PSC est configuré au chargement
onMounted(async () => {
  try {
    const status = await authService.getStatus()
    pscConfigured.value = status.psc_configured
  } catch {
    console.warn('Impossible de vérifier la configuration PSC')
  }
})

// Connexion via Pro Santé Connect
const loginWithPSC = async () => {
  try {
    const redirectAfter = route.query.redirect as string | undefined
    await authStore.loginWithPSC(redirectAfter)
  } catch (err) {
    error.value = 'Impossible de se connecter à Pro Santé Connect'
  }
}

// Connexion email/mot de passe
const loginWithCredentials = async () => {
  if (!tenantCode.value || !email.value || !password.value) {
    error.value = 'Veuillez remplir tous les champs'
    return
  }

  isLoading.value = true
  error.value = null

  try {
    await authStore.loginWithCredentials(tenantCode.value, email.value, password.value)

    // Rediriger vers la page demandée ou le dashboard
    const redirect = route.query.redirect as string || getDefaultRoute(authStore.user)
    router.push(redirect)
  } catch (err) {
    error.value = 'Identifiants incorrects'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="text-center">
      <h2 class="text-xl font-semibold text-neutral-900">Connexion</h2>
      <p class="text-neutral-600 mt-1">Accédez à votre espace CareLink</p>
    </div>

    <!-- Message d'erreur -->
    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- Bouton Pro Santé Connect -->
    <div v-if="pscConfigured" class="space-y-4">
      <Button
        label="Se connecter avec Pro Santé Connect"
        icon="pi pi-shield"
        class="w-full"
        severity="info"
        size="large"
        @click="loginWithPSC"
      />

      <div class="relative">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-neutral-200"></div>
        </div>
        <div class="relative flex justify-center text-sm">
          <span class="px-4 bg-white text-neutral-500">ou</span>
        </div>
      </div>
    </div>

    <!-- Formulaire email/mot de passe -->
    <form @submit.prevent="loginWithCredentials" class="space-y-4">
      <!-- 🆕 Code structure -->
      <div class="input-group">
        <label for="tenantCode" class="input-label">Code structure</label>
        <InputText
          id="tenantCode"
          v-model="tenantCode"
          placeholder="Ex: SSIAD-NORD"
          class="w-full"
          :disabled="isLoading"
        />
        <small class="text-neutral-400 text-xs mt-1 block">
          Communiqué par votre administrateur CareLink
        </small>
      </div>

      <div class="input-group">
        <label for="email" class="input-label">Email</label>
        <InputText
          id="email"
          v-model="email"
          type="email"
          placeholder="votre@email.fr"
          class="w-full"
          :disabled="isLoading"
        />
      </div>

      <div class="input-group">
        <label for="password" class="input-label">Mot de passe</label>
        <Password
          id="password"
          v-model="password"
          placeholder="••••••••"
          class="w-full"
          :feedback="false"
          toggleMask
          :disabled="isLoading"
          inputClass="w-full"
        />
      </div>

      <Button
        type="submit"
        label="Se connecter"
        icon="pi pi-sign-in"
        class="w-full"
        :loading="isLoading"
      />
    </form>

    <!-- Lien mot de passe oublié -->
    <p class="text-center text-sm text-neutral-600">
      <a href="#" class="text-primary-600 hover:underline">
        Mot de passe oublié ?
      </a>
    </p>
  </div>
</template>