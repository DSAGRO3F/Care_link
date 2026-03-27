<script setup lang="ts">
  /**
   * Layout pour les pages d'authentification
   * Design centré, sans navigation
   * 🆕 Option 1 teal unifié — logo intégré en header carte, liséré emerald vif
   */
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 auth-background">
    <div class="w-full max-w-md">
      <!-- Carte unique : header logo + corps (slot) -->
      <div class="bg-white rounded-2xl overflow-hidden auth-card">
        <!-- Header carte : logo + branding -->
        <div class="auth-card-header px-7 py-5 border-b border-slate-100 flex items-center gap-4">
          <div class="auth-logo-circle flex-shrink-0 flex items-center justify-center">
            <i class="pi pi-heart text-white text-lg"></i>
          </div>
          <div>
            <h1 class="text-lg font-bold text-slate-900 leading-tight tracking-tight">CareLink</h1>
            <p class="text-slate-500 text-xs mt-0.5">Coordination des soins à domicile</p>
          </div>
        </div>

        <!-- Corps : contenu injecté (LoginPage, etc.) -->
        <div class="p-6 lg:p-8">
          <slot />
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-teal-700/50 mt-5">
        © {{ new Date().getFullYear() }} CareLink — Tous droits réservés
      </p>
    </div>
  </div>
</template>

<style scoped>
  /* Fond dégradé teal/cyan unifié Option 1 */
  .auth-background {
    background: linear-gradient(160deg, #ccfbf1 0%, #99f6e4 20%, #a5f3fc 60%, #e0f2fe 100%);
  }

  /* Carte : liséré emerald vif + ombre teintée teal */
  .auth-card {
    border: 1px solid rgba(52, 211, 153, 0.5);
    box-shadow:
      0 20px 60px -12px rgba(13, 148, 136, 0.15),
      0 4px 16px -4px rgba(0, 0, 0, 0.08);
  }

  /* Header de la carte : fond teal très pâle */
  .auth-card-header {
    background: linear-gradient(135deg, #f0fdfa 0%, #f0f9ff 100%);
  }

  /* Logo : dégradé teal → cyan, coins arrondis */
  .auth-logo-circle {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, #0d9488, #0891b2);
    box-shadow: 0 4px 12px -2px rgba(13, 148, 136, 0.4);
  }
</style>
