<script setup lang="ts">
/**
 * Liste des patients
 * Affiche les patients en cards avec recherche et filtres
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { patientService } from '@/services'
import type { PatientSummary } from '@/types'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'

const router = useRouter()

// État
const patients = ref<PatientSummary[]>([])
const total = ref(0)
const isLoading = ref(true)
const searchQuery = ref('')

// Charger les patients
const loadPatients = async () => {
  isLoading.value = true
  try {
    const response = await patientService.getAll({
      page: 1,
      size: 20,
      search: searchQuery.value || undefined,
    })
    patients.value = response.items
    total.value = response.total
  } catch (error) {
    console.error('Erreur chargement patients:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(loadPatients)

// Recherche avec debounce
let searchTimeout: ReturnType<typeof setTimeout>
const onSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(loadPatients, 300)
}

// Navigation vers le dossier patient
const goToPatient = (id: number) => {
  router.push(`/soins/patients/${id}`)
}

// Couleur du badge GIR
const getGirClass = (gir: number | undefined) => {
  if (!gir) return 'badge-neutral'
  if (gir <= 2) return 'gir-1'
  if (gir <= 4) return 'gir-3'
  return 'gir-5'
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">Mes patients</h1>
      <div class="flex gap-2">
        <span class="p-input-icon-left">
          <i class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Rechercher..."
            class="w-64"
            @input="onSearch"
          />
        </span>
      </div>
    </div>

    <!-- Compteur -->
    <p class="text-neutral-600">
      {{ total }} patient{{ total > 1 ? 's' : '' }} trouvé{{ total > 1 ? 's' : '' }}
    </p>

    <!-- Liste en cards -->
    <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Skeleton v-for="i in 6" :key="i" height="120px" class="rounded-lg" />
    </div>

    <div v-else-if="patients.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="patient in patients"
        :key="patient.id"
        class="card-hover cursor-pointer"
        @click="goToPatient(patient.id)"
      >
        <div class="flex items-start gap-4">
          <!-- Avatar -->
          <div class="w-12 h-12 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-semibold">
            {{ (patient.first_name?.[0] || '') + (patient.last_name?.[0] || '') }}
          </div>
          
          <!-- Infos -->
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-neutral-900">
              {{ patient.first_name }} {{ patient.last_name }}
            </div>
            <div class="text-sm text-neutral-600">
              {{ patient.birth_date ? new Date(patient.birth_date).toLocaleDateString('fr-FR') : 'Date inconnue' }}
            </div>
          </div>
          
          <!-- Badge GIR -->
          <div
            v-if="patient.current_gir"
            class="gir-badge"
            :class="getGirClass(patient.current_gir)"
          >
            {{ patient.current_gir }}
          </div>
        </div>
        
        <!-- Statut -->
        <div class="mt-3 flex items-center justify-between">
          <Tag
            :value="patient.status"
            :severity="patient.status === 'ACTIVE' ? 'success' : 'secondary'"
          />
          <i class="pi pi-chevron-right text-neutral-400"></i>
        </div>
      </div>
    </div>

    <!-- Vide -->
    <div v-else class="empty-state">
      <i class="pi pi-users empty-state-icon"></i>
      <p class="empty-state-title">Aucun patient trouvé</p>
      <p class="empty-state-description">
        Modifiez votre recherche ou contactez votre coordinateur
      </p>
    </div>
  </div>
</template>
