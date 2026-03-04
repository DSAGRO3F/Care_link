<script setup lang="ts">
/**
 * PatientCreatePage.vue — Wizard création patient
 *
 * Formulaire en 3 étapes (même pattern que UserCreatePage.vue) :
 *   1. Identité : nom, prénom, date naissance, NIR, INS, sexe
 *   2. Coordonnées : adresse, téléphone, email
 *   3. Rattachement : entité + médecin traitant
 *
 * 🆕 01/03/2026 — Améliorations UX :
 *   - Toast de confirmation soigné après création
 *   - Fix superposition calendrier (z-index)
 *
 * Route : /admin/patients/new
 * Layout : AdminLayout
 *
 * Destination : src/pages/admin/patients/PatientCreatePage.vue
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'

// PrimeVue Components
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import Message from 'primevue/message'

// Components
import EntitySelector from '@/components/entities/EntitySelector.vue'

// Store
import { useAdminStore } from '@/stores/admin.store'
import type { PatientCreate } from '@/types/patient'

const router = useRouter()
const adminStore = useAdminStore()
const toast = useToast()

// =============================================================================
// STATE
// =============================================================================

const currentStep = ref(1)
const totalSteps = 3

/** Données du formulaire — on utilise un type local aligné sur PatientCreate
 *  mais avec `null` au lieu de `undefined` pour les valeurs vides (PrimeVue). */
const form = ref({
  first_name: '',
  last_name: '',
  birth_date: '',
  nir: '',
  ins: '',
  address: '',
  phone: '',
  email: '',
  entity_id: 0,
  medecin_traitant_id: null as number | null,
})

/** Date de naissance comme objet Date pour Calendar */
const birthDateValue = ref<Date | null>(null)

/** Erreurs de validation par champ */
const validationErrors = ref<Record<string, string>>({})

// =============================================================================
// COMPUTED
// =============================================================================

const isFirstStep = computed(() => currentStep.value === 1)
const isLastStep = computed(() => currentStep.value === totalSteps)
const isSaving = computed(() => adminStore.isSavingPatient)

const stepLabels = [
  { number: 1, label: 'Identité', icon: 'pi pi-id-card' },
  { number: 2, label: 'Coordonnées', icon: 'pi pi-map-marker' },
  { number: 3, label: 'Rattachement', icon: 'pi pi-sitemap' },
]

const canProceed = computed(() => {
  if (currentStep.value === 1) {
    return !!form.value.last_name && !!form.value.first_name
  }
  if (currentStep.value === 2) {
    return true // Les coordonnées sont facultatives
  }
  if (currentStep.value === 3) {
    return form.value.entity_id > 0
  }
  return false
})

// =============================================================================
// METHODS
// =============================================================================

function nextStep() {
  if (currentStep.value < totalSteps) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

/** Synchronise la date Calendar → form.birth_date (ISO string) */
function onBirthDateChange(date: Date | Date[] | (Date | null)[] | null | undefined) {
  const d = Array.isArray(date) ? date[0] : date
  birthDateValue.value = d ?? null
  if (d) {
    form.value.birth_date = d.toISOString().split('T')[0]
  } else {
    form.value.birth_date = ''
  }
}

/** Sélection d'entité depuis EntitySelector */
function onEntitySelect(entityId: number | null) {
  form.value.entity_id = entityId ?? 0
}

/** Validation et soumission */
async function submit() {
  validationErrors.value = {}

  // Validation minimale
  if (!form.value.last_name) {
    validationErrors.value.last_name = 'Le nom est obligatoire'
  }
  if (!form.value.first_name) {
    validationErrors.value.first_name = 'Le prénom est obligatoire'
  }
  if (!form.value.entity_id || form.value.entity_id === 0) {
    validationErrors.value.entity_id = 'L\'entité de rattachement est obligatoire'
  }

  if (Object.keys(validationErrors.value).length > 0) {
    return
  }

  // Nettoyage : supprimer les champs vides
  const payload: PatientCreate = {
    ...form.value,
    nir: form.value.nir || undefined,
    ins: form.value.ins || undefined,
    address: form.value.address || undefined,
    phone: form.value.phone || undefined,
    email: form.value.email || undefined,
    birth_date: form.value.birth_date || undefined,
    medecin_traitant_id: form.value.medecin_traitant_id || undefined,
  }

  const result = await adminStore.createPatient(payload)

  if (result) {
    // Toast de confirmation
    const patientName = `${result.last_name ?? form.value.last_name} ${result.first_name ?? form.value.first_name}`
    toast.add({
      severity: 'success',
      summary: 'Patient créé',
      detail: `Le dossier de ${patientName} a été créé avec succès.`,
      life: 4000,
    })

    router.push({ name: 'admin-patient-detail', params: { id: result.id } })
  } else {
    toast.add({
      severity: 'error',
      summary: 'Erreur de création',
      detail: adminStore.patientError || 'Impossible de créer le patient. Vérifiez les données saisies.',
      life: 6000,
    })
  }
}

function cancel() {
  router.push({ name: 'admin-patients' })
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">

    <!-- ─── HEADER ─── -->
    <div class="flex items-center gap-4">
      <Button
        icon="pi pi-arrow-left"
        severity="secondary"
        variant="text"
        rounded
        @click="cancel"
      />
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Nouveau patient</h1>
        <p class="text-slate-500 mt-1">Étape {{ currentStep }} sur {{ totalSteps }}</p>
      </div>
    </div>

    <!-- ─── STEPPER ─── -->
    <div class="flex items-center justify-center gap-2">
      <template v-for="step in stepLabels" :key="step.number">
        <div
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="step.number === currentStep
            ? 'bg-blue-600 text-white'
            : step.number < currentStep
              ? 'bg-blue-50 text-blue-600'
              : 'bg-slate-100 text-slate-400'"
        >
          <i :class="step.icon" />
          <span class="hidden sm:inline">{{ step.label }}</span>
        </div>
        <i
          v-if="step.number < totalSteps"
          class="pi pi-chevron-right text-slate-300 text-xs"
        />
      </template>
    </div>

    <!-- ─── ERREUR GLOBALE ─── -->
    <Message v-if="adminStore.patientError" severity="error" :closable="false">
      {{ adminStore.patientError }}
    </Message>

    <!-- ─── ÉTAPE 1 : IDENTITÉ ─── -->
    <Card v-if="currentStep === 1">
      <template #title>
        <div class="flex items-center gap-2 text-lg">
          <i class="pi pi-id-card text-blue-600" />
          Identité du patient
        </div>
      </template>
      <template #content>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Nom -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">
              Nom de famille <span class="text-red-500">*</span>
            </label>
            <InputText
              v-model="form.last_name"
              placeholder="DUPONT"
              :class="{ 'p-invalid': validationErrors.last_name }"
            />
            <small v-if="validationErrors.last_name" class="text-red-500">
              {{ validationErrors.last_name }}
            </small>
          </div>

          <!-- Prénom -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">
              Prénom <span class="text-red-500">*</span>
            </label>
            <InputText
              v-model="form.first_name"
              placeholder="Jean"
              :class="{ 'p-invalid': validationErrors.first_name }"
            />
            <small v-if="validationErrors.first_name" class="text-red-500">
              {{ validationErrors.first_name }}
            </small>
          </div>

          <!-- Date de naissance -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">Date de naissance</label>
            <DatePicker
              :modelValue="birthDateValue"
              @update:modelValue="onBirthDateChange"
              dateFormat="dd/mm/yy"
              placeholder="JJ/MM/AAAA"
              showIcon
              :maxDate="new Date()"
              appendTo="body"
            />
          </div>

          <!-- Espace vide pour alignement grille -->
          <div></div>

          <Divider class="col-span-full" />

          <!-- NIR -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">N° Sécurité Sociale (NIR)</label>
            <InputText
              v-model="form.nir"
              placeholder="1 85 01 75 108 042 36"
              maxlength="15"
            />
            <small class="text-slate-400">15 chiffres — sera chiffré en base</small>
          </div>

          <!-- INS -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">Identifiant National de Santé (INS)</label>
            <InputText
              v-model="form.ins"
              placeholder="Identifiant INS"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- ─── ÉTAPE 2 : COORDONNÉES ─── -->
    <Card v-if="currentStep === 2">
      <template #title>
        <div class="flex items-center gap-2 text-lg">
          <i class="pi pi-map-marker text-blue-600" />
          Coordonnées
        </div>
      </template>
      <template #content>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Adresse -->
          <div class="flex flex-col gap-1 col-span-full">
            <label class="text-sm font-medium text-slate-700">Adresse</label>
            <InputText
              v-model="form.address"
              placeholder="12 avenue Caffin, 94100 La Varenne Saint-Hilaire"
            />
          </div>

          <!-- Téléphone -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">Téléphone</label>
            <InputText
              v-model="form.phone"
              placeholder="06 12 34 56 78"
            />
          </div>

          <!-- Email -->
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700">Email</label>
            <InputText
              v-model="form.email"
              type="email"
              placeholder="patient@email.com"
            />
          </div>
        </div>

        <div class="mt-4 p-3 bg-slate-50 rounded-lg">
          <p class="text-sm text-slate-500">
            <i class="pi pi-lock mr-1" />
            Toutes les données personnelles sont chiffrées (AES-256-GCM) conformément aux exigences RGPD/HDS.
          </p>
        </div>
      </template>
    </Card>

    <!-- ─── ÉTAPE 3 : RATTACHEMENT ─── -->
    <Card v-if="currentStep === 3">
      <template #title>
        <div class="flex items-center gap-2 text-lg">
          <i class="pi pi-sitemap text-blue-600" />
          Rattachement organisationnel
        </div>
      </template>
      <template #content>
        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium text-slate-700 mb-2 block">
              Entité de rattachement <span class="text-red-500">*</span>
            </label>
            <p class="text-sm text-slate-400 mb-3">
              Sélectionnez l'entité à laquelle ce patient sera rattaché.
            </p>
            <div class="border border-slate-200 rounded-lg p-3">
              <EntitySelector
                :modelValue="form.entity_id || null"
                @update:modelValue="onEntitySelect"
              />
            </div>
            <small v-if="validationErrors.entity_id" class="text-red-500 mt-1 block">
              {{ validationErrors.entity_id }}
            </small>
          </div>

          <!-- TODO: Sélecteur médecin traitant (dropdown users avec filtre profession = médecin) -->
          <div>
            <label class="text-sm font-medium text-slate-700 mb-2 block">
              Médecin traitant
            </label>
            <p class="text-sm text-slate-400">
              Sera disponible après intégration du filtre professions sur l'API users.
            </p>
          </div>
        </div>
      </template>
    </Card>

    <!-- ─── NAVIGATION ─── -->
    <div class="flex items-center justify-between pt-2">
      <Button
        v-if="!isFirstStep"
        label="Précédent"
        icon="pi pi-arrow-left"
        severity="secondary"
        variant="outlined"
        @click="prevStep"
      />
      <div v-else></div>

      <div class="flex gap-2">
        <Button
          label="Annuler"
          severity="secondary"
          variant="text"
          @click="cancel"
        />
        <Button
          v-if="!isLastStep"
          label="Suivant"
          icon="pi pi-arrow-right"
          iconPos="right"
          :disabled="!canProceed"
          @click="nextStep"
        />
        <Button
          v-else
          label="Créer le patient"
          icon="pi pi-check"
          :loading="isSaving"
          :disabled="!canProceed"
          @click="submit"
        />
      </div>
    </div>
  </div>
</template>