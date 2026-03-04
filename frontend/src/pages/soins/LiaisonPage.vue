<script setup lang="ts">
/**
 * Carnet de liaison
 * Fil d'actualité des transmissions entre professionnels
 */
import { ref } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

const searchQuery = ref('')
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Carnet de liaison</h1>
      <Button
        label="Nouvelle entrée"
        icon="pi pi-plus"
      />
    </div>

    <!-- Filtres -->
    <div class="flex gap-4">
      <span class="p-input-icon-left flex-1">
        <i class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          placeholder="Rechercher dans les transmissions..."
          class="w-full"
        />
      </span>
    </div>

    <!-- Liste des entrées -->
    <Card>
      <template #content>
        <div class="text-center py-12">
          <i class="pi pi-comments text-6xl text-neutral-300 mb-4"></i>
          <h3 class="text-lg font-medium text-neutral-900">
            Transmissions
          </h3>
          <p class="text-neutral-600 mt-2">
            Les entrées du carnet de liaison apparaîtront ici
          </p>
          <p class="text-sm text-neutral-400 mt-4">
            (Liste à implémenter)
          </p>
        </div>
      </template>
    </Card>
  </div>
</template>
