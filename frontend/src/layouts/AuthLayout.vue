<script setup lang="ts">
/**
 * Layout pour les pages d'authentification
 * Design centré, sans navigation
 */
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
    <!-- Carte centrée -->
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-600 text-white mb-4">
          <i class="pi pi-heart text-3xl"></i>
        </div>
        <h1 class="text-2xl font-bold text-neutral-900">CareLink</h1>
        <p class="text-neutral-600 mt-1">Coordination des soins à domicile</p>
      </div>

      <!-- Contenu (formulaire login, etc.) -->
      <div class="bg-white rounded-xl shadow-card p-6 lg:p-8">
        <slot />
      </div>

      <!-- Footer -->
      <p class="text-center text-sm text-neutral-500 mt-6">
        © {{ new Date().getFullYear() }} CareLink - Tous droits réservés
      </p>
    </div>
  </div>
</template>
