<script setup lang="ts">
/**
 * Page de connexion SuperAdmin — Espace Platform
 * Route: /platform/login
 *
 * Thème : clair élégant — fond gris clair, card blanche, accent violet
 *
 * Destination : src/pages/platform/LoginPage.vue
 */
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePlatformStore } from '@/stores'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const router = useRouter()
const route = useRoute()
const platformStore = usePlatformStore()

// =============================================================================
// STATE
// =============================================================================

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

// =============================================================================
// COMPUTED
// =============================================================================

const isFormValid = computed(() => {
  return email.value.includes('@') && password.value.length >= 6
})

// =============================================================================
// METHODS
// =============================================================================

async function handleLogin() {
  if (!isFormValid.value || isLoading.value) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    await platformStore.loginSuperAdmin(email.value, password.value)

    const redirectUrl = route.query.redirect as string || '/platform'
    router.push(redirectUrl)

  } catch (error: any) {
    if (import.meta.env.DEV) {
      console.error('[Platform Login] Error:', error)
    }

    if (error.response?.status === 401) {
      errorMessage.value = 'Email ou mot de passe incorrect'
    } else if (error.response?.status === 403) {
      errorMessage.value = 'Compte désactivé ou verrouillé'
    } else {
      errorMessage.value = error.response?.data?.detail || 'Erreur de connexion'
    }
  } finally {
    isLoading.value = false
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && isFormValid.value) {
    handleLogin()
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4 relative">
    <!-- Gradient décoratif subtil -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-96 h-96 bg-violet-200/40 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-96 h-96 bg-purple-200/30 rounded-full blur-3xl"></div>
    </div>

    <!-- Login Card -->
    <div class="relative w-full max-w-md">
      <!-- Logo et titre -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 text-white mb-4 shadow-lg shadow-violet-500/20">
          <i class="pi pi-bolt text-3xl"></i>
        </div>
        <h1 class="text-2xl font-bold text-zinc-800">CareLink Platform</h1>
        <p class="text-zinc-500 mt-2">Administration de la plateforme</p>
      </div>

      <!-- Formulaire -->
      <div class="bg-white rounded-2xl border border-zinc-200 p-8 shadow-lg shadow-zinc-200/50">
        <h2 class="text-xl font-semibold text-zinc-800 mb-6">Connexion SuperAdmin</h2>

        <!-- Message d'erreur -->
        <Message
          v-if="errorMessage"
          severity="error"
          :closable="false"
          class="mb-6"
        >
          {{ errorMessage }}
        </Message>

        <form @submit.prevent="handleLogin" @keydown="handleKeydown">
          <!-- Email -->
          <div class="mb-5">
            <label class="block text-sm font-medium text-zinc-600 mb-2">
              Email
            </label>
            <span class="p-input-icon-left w-full">
              <i class="pi pi-envelope" />
              <InputText
                v-model="email"
                type="email"
                placeholder="admin@carelink.fr"
                class="w-full"
                :disabled="isLoading"
                autocomplete="email"
              />
            </span>
          </div>

          <!-- Mot de passe -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-zinc-600 mb-2">
              Mot de passe
            </label>
            <Password
              v-model="password"
              placeholder="••••••••"
              class="w-full"
              :feedback="false"
              :toggleMask="true"
              :disabled="isLoading"
              inputClass="w-full"
              autocomplete="current-password"
            />
          </div>

          <!-- Bouton connexion -->
          <Button
            type="submit"
            label="Se connecter"
            icon="pi pi-sign-in"
            class="w-full login-btn"
            :loading="isLoading"
            :disabled="!isFormValid"
          />
        </form>

        <!-- Séparateur -->
        <div class="relative my-6">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-zinc-200"></div>
          </div>
          <div class="relative flex justify-center text-sm">
            <span class="px-3 bg-white text-zinc-400">Accès restreint</span>
          </div>
        </div>

        <!-- Info -->
        <p class="text-center text-sm text-zinc-500">
          Cette interface est réservée à l'équipe CareLink.
          <br />
          <router-link to="/login" class="text-violet-600 hover:text-violet-700 font-medium">
            Connexion utilisateur standard →
          </router-link>
        </p>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-zinc-400 mt-6">
        CareLink Platform &copy; {{ new Date().getFullYear() }}
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Bouton gradient violet — seul override nécessaire */
:deep(.login-btn.p-button) {
  @apply bg-gradient-to-r from-violet-600 to-purple-600 border-0;

  &:hover:not(:disabled) {
    @apply from-violet-500 to-purple-500;
  }

  &:focus {
    @apply ring-2 ring-violet-500/30 ring-offset-2;
  }
}

:deep(.p-password) {
  @apply w-full;
}
</style>