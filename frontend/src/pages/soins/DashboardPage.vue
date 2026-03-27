<script setup lang="ts">
  /**
   * Dashboard "Ma journée"
   * Vue d'ensemble : interventions du jour, alertes, statistiques rapides
   */
  import { ref, onMounted, computed } from 'vue';
  import { useRouter } from 'vue-router';
  import { useAuthStore } from '@/stores';
  import { planningService } from '@/services';
  import type { DailyPlanning } from '@/types';
  import Card from 'primevue/card';
  import Button from 'primevue/button';
  import Tag from 'primevue/tag';
  import Skeleton from 'primevue/skeleton';

  const router = useRouter();
  const authStore = useAuthStore();

  // État
  const planning = ref<DailyPlanning | null>(null);
  const isLoading = ref(true);
  const error = ref<string | null>(null);

  // Date du jour formatée
  const todayFormatted = computed(() => {
    return new Date().toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    });
  });

  // Statistiques rapides
  const stats = computed(() => {
    if (!planning.value) return null;

    const interventions = planning.value.interventions;
    const completed = interventions.filter((i) => i.is_completed).length;
    const pending = interventions.filter((i) => i.is_pending).length;

    return {
      total: interventions.length,
      completed,
      pending,
      totalMinutes: planning.value.total_scheduled_minutes,
      totalHours: Math.round((planning.value.total_scheduled_minutes / 60) * 10) / 10,
    };
  });

  // Prochaines interventions (non terminées)
  const upcomingInterventions = computed(() => {
    if (!planning.value) return [];
    return planning.value.interventions
      .filter((i) => !i.is_completed && !i.is_cancelled)
      .slice(0, 5);
  });

  // Charger le planning du jour
  onMounted(async () => {
    try {
      planning.value = await planningService.getMyDay();
    } catch (err) {
      error.value = 'Impossible de charger le planning';
      console.error(err);
    } finally {
      isLoading.value = false;
    }
  });

  // Navigation vers le patient
  const goToPatient = (patientId: number) => {
    router.push(`/soins/patients/${patientId}`);
  };

  // Couleur du tag selon le statut
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'success';
      case 'IN_PROGRESS':
        return 'info';
      case 'CANCELLED':
        return 'danger';
      case 'MISSED':
        return 'warning';
      default:
        return 'secondary';
    }
  };
</script>

<template>
  <div class="space-y-6">
    <!-- Header avec date et salutation -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">
          Bonjour, {{ authStore.user?.first_name }} 👋
        </h1>
        <p class="text-neutral-600 capitalize">{{ todayFormatted }}</p>
      </div>

      <Button
        label="Voir tout le planning"
        icon="pi pi-calendar"
        outlined
        @click="router.push('/soins/planning')"
      />
    </div>

    <!-- Statistiques rapides -->
    <div v-if="isLoading" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Skeleton v-for="i in 4" :key="i" height="80px" class="rounded-lg" />
    </div>

    <div v-else-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="card text-center">
        <div class="text-3xl font-bold text-primary-600">{{ stats.total }}</div>
        <div class="text-sm text-neutral-600">Interventions</div>
      </div>

      <div class="card text-center">
        <div class="text-3xl font-bold text-secondary-600">{{ stats.completed }}</div>
        <div class="text-sm text-neutral-600">Terminées</div>
      </div>

      <div class="card text-center">
        <div class="text-3xl font-bold text-warning-600">{{ stats.pending }}</div>
        <div class="text-sm text-neutral-600">En attente</div>
      </div>

      <div class="card text-center">
        <div class="text-3xl font-bold text-neutral-700">{{ stats.totalHours }}h</div>
        <div class="text-sm text-neutral-600">Temps total</div>
      </div>
    </div>

    <!-- Prochaines interventions -->
    <Card>
      <template #title>
        <div class="flex items-center justify-between">
          <span>Prochaines interventions</span>
          <Tag
            v-if="upcomingInterventions.length"
            :value="`${upcomingInterventions.length} restantes`"
          />
        </div>
      </template>

      <template #content>
        <!-- Loading -->
        <div v-if="isLoading" class="space-y-3">
          <Skeleton v-for="i in 3" :key="i" height="60px" class="rounded-lg" />
        </div>

        <!-- Liste des interventions -->
        <div v-else-if="upcomingInterventions.length" class="space-y-3">
          <div
            v-for="intervention in upcomingInterventions"
            :key="intervention.id"
            class="flex items-center gap-4 p-3 rounded-lg hover:bg-neutral-50 cursor-pointer transition-colors"
            @click="goToPatient(intervention.patient_id)"
          >
            <!-- Heure -->
            <div class="text-center min-w-[60px]">
              <div class="text-lg font-semibold text-neutral-900">
                {{ intervention.time_slot_display.split('-')[0] }}
              </div>
              <div class="text-xs text-neutral-500">
                {{ intervention.scheduled_duration_minutes }} min
              </div>
            </div>

            <!-- Infos -->
            <div class="flex-1 min-w-0">
              <div class="font-medium text-neutral-900 truncate">
                {{ intervention.service_name || 'Intervention' }}
              </div>
              <div class="text-sm text-neutral-600">Patient #{{ intervention.patient_id }}</div>
            </div>

            <!-- Statut -->
            <Tag :value="intervention.status" :severity="getStatusSeverity(intervention.status)" />

            <!-- Chevron -->
            <i class="pi pi-chevron-right text-neutral-400"></i>
          </div>
        </div>

        <!-- Vide -->
        <div v-else class="empty-state py-8">
          <i class="pi pi-check-circle empty-state-icon text-secondary-300"></i>
          <p class="empty-state-title">Toutes les interventions sont terminées !</p>
          <p class="empty-state-description">Profitez de votre journée 🎉</p>
        </div>
      </template>
    </Card>

    <!-- Actions rapides -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Button
        label="Mes patients"
        icon="pi pi-users"
        class="p-button-outlined"
        @click="router.push('/soins/patients')"
      />
      <Button
        label="Carnet de liaison"
        icon="pi pi-comments"
        class="p-button-outlined"
        @click="router.push('/soins/liaison')"
      />
      <Button
        label="Nouvelle entrée"
        icon="pi pi-plus"
        class="p-button-outlined"
        @click="router.push('/soins/liaison?new=1')"
      />
      <Button label="Scanner QR" icon="pi pi-qrcode" class="p-button-outlined" disabled />
    </div>
  </div>
</template>
