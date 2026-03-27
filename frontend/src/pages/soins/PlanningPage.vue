<script setup lang="ts">
  /**
   * Page Planning
   * Vue calendrier des interventions (jour, semaine)
   */
  import { ref } from 'vue';
  import Card from 'primevue/card';
  import Button from 'primevue/button';
  import Calendar from 'primevue/calendar';

  const selectedDate = ref(new Date());
  const viewMode = ref<'day' | 'week'>('day');
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Mon planning</h1>
      <div class="flex gap-2">
        <Button
          :label="viewMode === 'day' ? 'Jour' : 'Semaine'"
          icon="pi pi-calendar"
          outlined
          @click="viewMode = viewMode === 'day' ? 'week' : 'day'"
        />
        <Calendar v-model="selectedDate" dateFormat="dd/mm/yy" showIcon />
      </div>
    </div>

    <!-- Contenu planning -->
    <Card>
      <template #content>
        <div class="text-center py-12">
          <i class="pi pi-calendar text-6xl text-neutral-300 mb-4"></i>
          <h3 class="text-lg font-medium text-neutral-900">
            Vue {{ viewMode === 'day' ? 'journalière' : 'hebdomadaire' }}
          </h3>
          <p class="text-neutral-600 mt-2">
            {{
              selectedDate.toLocaleDateString('fr-FR', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })
            }}
          </p>
          <p class="text-sm text-neutral-400 mt-4">(Composant calendrier à implémenter)</p>
        </div>
      </template>
    </Card>
  </div>
</template>
