<script setup lang="ts">
/**
 * CareLink - PatientDetailPage
 * Chemin : frontend/src/pages/soins/PatientDetailPage.vue
 *
 * Dossier patient détaillé — Espace Soins
 * Design Option A : Bannière enrichie + Onglets horizontaux + Widgets constantes
 *
 * Phase 5 : EvaluationDetailDialog intégré
 * Phase 6 : Refonte visuelle (bannière, onglet Synthèse, widgets vitaux)
 *
 * Migration PrimeVue 4 (04/03/2026) :
 * - TabView/TabPanel → Tabs/TabList/Tab/TabPanels/TabPanel (API v4)
 * - activeTab : ref(0) numérique → ref('synthese') string (valeur = clé onglet)
 * - Icônes onglets : pseudo-éléments CSS ::before PrimeIcons → Lucide en slot natif
 * - Button : class="p-button-sm" → size="small", p-button-outlined → variant="outlined"
 * - Suppression de ~80 lignes de CSS workaround :deep(.p-tabview-*)
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { patientService } from '@/services'
import type {
  PatientResponse,
  PatientEvaluationResponse,
  PatientVitalsResponse,
} from '@/types'

// PrimeVue 4 — API Tabs native
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

// Lucide — icônes onglets (convention module évaluation + Soins)
import {
  LayoutDashboard,
  ClipboardCheck,
  Activity,
  MessageSquare,
  FileText,
  CheckSquare,
  MapPin,
  Building2,
  Phone,
  User,
} from 'lucide-vue-next'

// Phase 5 — Modal d'évaluation
import EvaluationDetailDialog from '@/components/evaluation/EvaluationDetailDialog.vue'

const route = useRoute()
const router = useRouter()

const props = defineProps<{
  id: string
}>()

// ============================================================
// ÉTAT
// ============================================================

const patient = ref<PatientResponse | null>(null)
const isLoading = ref(true)

// v4 : activeTab est maintenant la valeur string de l'onglet actif,
// pas un index numérique. C'est l'API native Tabs PrimeVue 4.
const activeTab = ref('synthese')

// État évaluations
const evaluations = ref<PatientEvaluationResponse[]>([])
const evaluationsLoading = ref(false)
const evaluationsLoaded = ref(false)

// État constantes vitales (synthèse)
const latestVitals = ref<Record<string, PatientVitalsResponse | null>>({
  TA_SYS: null,
  FC: null,
  TEMP: null,
  SPO2: null,
})
const vitalsLoading = ref(false)
const vitalsLoaded = ref(false)

// Phase 5 — Modal évaluation
const showEvaluationModal = ref(false)
const selectedEvaluation = ref<PatientEvaluationResponse | null>(null)
const evaluationDetailLoading = ref(false)

// Valeurs valides pour les onglets (utilisées pour la validation de l'URL)
const VALID_TABS = ['synthese', 'evaluations', 'constantes', 'liaison', 'documents']

// ============================================================
// COMPUTED
// ============================================================

/** Âge calculé depuis la date de naissance */
const age = computed(() => {
  if (!patient.value?.birth_date) return null
  const birth = new Date(patient.value.birth_date)
  const now = new Date()
  return Math.floor((now.getTime() - birth.getTime()) / (365.25 * 24 * 60 * 60 * 1000))
})

/** Initiales du patient */
const initials = computed(() => {
  if (!patient.value) return ''
  return (patient.value.first_name?.[0] || '') + (patient.value.last_name?.[0] || '')
})

/** Classe CSS du badge GIR (bannière) */
const girBadgeClass = computed(() => {
  const gir = patient.value?.current_gir
  if (!gir) return ''
  if (gir <= 2) return 'patient-gir-badge--severe'
  if (gir <= 4) return 'patient-gir-badge--moderate'
  return 'patient-gir-badge--light'
})

/** Label du statut patient en français */
const statusLabel = computed(() => {
  switch (patient.value?.status) {
    case 'ACTIVE': return 'Actif'
    case 'INACTIVE': return 'Inactif'
    case 'ARCHIVED': return 'Archivé'
    case 'DECEASED': return 'Décédé'
    default: return patient.value?.status || ''
  }
})

/** Dernière évaluation disponible */
const latestEvaluation = computed(() => {
  if (!patient.value?.evaluations?.length) return null
  return patient.value.evaluations
    .slice()
    .sort((a, b) => new Date(b.evaluation_date).getTime() - new Date(a.evaluation_date).getTime())[0]
})

// ============================================================
// WIDGETS CONSTANTES — Configuration & helpers
// ============================================================

interface VitalWidgetConfig {
  key: string
  label: string
  unit: string
  icon: string
}

const vitalWidgets: VitalWidgetConfig[] = [
  { key: 'TA_SYS', label: 'Tension', unit: 'mmHg', icon: 'pi pi-heart' },
  { key: 'FC', label: 'Fréq. cardiaque', unit: 'bpm', icon: 'pi pi-bolt' },
  { key: 'TEMP', label: 'Température', unit: '°C', icon: 'pi pi-sun' },
  { key: 'SPO2', label: 'Saturation O2', unit: '%', icon: 'pi pi-wave-pulse' },
]

/** Classe de couleur du widget selon l'état de la mesure */
function getVitalStatusClass(vital: PatientVitalsResponse | null): string {
  if (!vital) return 'vital-widget--empty'
  if (vital.is_critical) return 'vital-widget--critical'
  if (vital.is_abnormal) return 'vital-widget--warning'
  return 'vital-widget--ok'
}

/** Valeur formatée de la constante */
function formatVitalValue(vital: PatientVitalsResponse | null): string {
  if (!vital) return '\u2014'
  return String(vital.value)
}

/** Date relative de la mesure */
function formatVitalDate(vital: PatientVitalsResponse | null): string {
  if (!vital?.measured_at) return ''
  const measured = new Date(vital.measured_at)
  const now = new Date()
  const diffMs = now.getTime() - measured.getTime()
  const diffH = Math.floor(diffMs / (1000 * 60 * 60))
  const diffD = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffH < 1) return "À l'instant"
  if (diffH < 24) return 'Il y a ' + diffH + 'h'
  if (diffD === 1) return 'Hier'
  if (diffD < 7) return 'Il y a ' + diffD + 'j'
  return measured.toLocaleDateString('fr-FR')
}

// ============================================================
// CHARGEMENT DES DONNÉES
// ============================================================

/** Initialiser l'onglet depuis le paramètre URL ?tab= */
const initTab = () => {
  const tabParam = route.query.tab as string
  if (tabParam && VALID_TABS.includes(tabParam)) {
    activeTab.value = tabParam
  }
}

/** Charger les dernières constantes vitales */
const loadLatestVitals = async () => {
  if (vitalsLoaded.value || vitalsLoading.value) return

  vitalsLoading.value = true
  const patientId = Number(props.id)
  const vitalTypes = ['TA_SYS', 'FC', 'TEMP', 'SPO2']

  try {
    const results = await Promise.allSettled(
      vitalTypes.map((type) => patientService.getLatestVital(patientId, type))
    )

    results.forEach((result, index) => {
      latestVitals.value[vitalTypes[index]] =
        result.status === 'fulfilled' ? result.value : null
    })
    vitalsLoaded.value = true
  } catch (error) {
    if (import.meta.env.DEV) console.warn('[PatientDetail] Erreur chargement vitals:', error)
  } finally {
    vitalsLoading.value = false
  }
}

/** Charger les évaluations du patient */
const loadEvaluations = async () => {
  if (evaluationsLoaded.value || evaluationsLoading.value) return

  evaluationsLoading.value = true
  try {
    const response = await patientService.getEvaluations(Number(props.id))
    evaluations.value = response.items || []
    evaluationsLoaded.value = true
  } catch (error) {
    if (import.meta.env.DEV) console.error('[PatientDetail] Erreur chargement évaluations:', error)
  } finally {
    evaluationsLoading.value = false
  }
}

// Phase 5 — Ouvrir le modal d'évaluation
const openEvaluationDetail = async (evaluation: PatientEvaluationResponse) => {
  if (evaluation.evaluation_data && Object.keys(evaluation.evaluation_data).length > 0) {
    selectedEvaluation.value = evaluation
    showEvaluationModal.value = true
    return
  }

  evaluationDetailLoading.value = true
  try {
    const fullEvaluation = await patientService.getEvaluation(
      Number(props.id),
      evaluation.id
    )
    selectedEvaluation.value = fullEvaluation
    showEvaluationModal.value = true
  } catch (error) {
    if (import.meta.env.DEV) console.error('[PatientDetail] Erreur chargement détail évaluation:', error)
  } finally {
    evaluationDetailLoading.value = false
  }
}

const closeEvaluationModal = () => {
  showEvaluationModal.value = false
  setTimeout(() => {
    selectedEvaluation.value = null
  }, 300)
}

// ============================================================
// LIFECYCLE
// ============================================================

onMounted(async () => {
  initTab()
  try {
    patient.value = await patientService.getById(Number(props.id))

    // Charger les données de l'onglet actif au montage
    if (activeTab.value === 'synthese') await loadLatestVitals()
    if (activeTab.value === 'evaluations') await loadEvaluations()
  } catch (error) {
    if (import.meta.env.DEV) console.error('[PatientDetail] Erreur chargement patient:', error)
    router.push('/soins/patients')
  } finally {
    isLoading.value = false
  }
})

// Sync URL + chargement lazy par onglet
// v4 : newTab est directement la string ('synthese', 'evaluations', etc.)
watch(activeTab, async (newTab) => {
  router.replace({ query: { ...route.query, tab: newTab } })

  if (newTab === 'synthese') await loadLatestVitals()
  if (newTab === 'evaluations') await loadEvaluations()
})

// ============================================================
// HELPERS D'AFFICHAGE
// ============================================================

const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('fr-FR')
}

const getStatusSeverity = (status: string): string => {
  switch (status) {
    case 'VALIDATED': return 'success'
    case 'SUBMITTED':
    case 'IN_PROGRESS': return 'info'
    case 'DRAFT': return 'warn'
    default: return 'secondary'
  }
}

const getStatusLabel = (status: string): string => {
  switch (status) {
    case 'VALIDATED': return 'Validée'
    case 'SUBMITTED': return 'Soumise'
    case 'IN_PROGRESS': return 'En cours'
    case 'DRAFT': return 'Brouillon'
    case 'PENDING_MEDICAL': return 'Attente médecin'
    case 'PENDING_DEPARTMENT': return 'Attente CD'
    case 'ARCHIVED': return 'Archivée'
    default: return status
  }
}

function callPhone(phone: string) {
  window.location.href = 'tel:' + phone
}
</script>

<template>
  <div class="patient-detail">

    <!-- ================================================================ -->
    <!-- BANNIÈRE PATIENT — Skeleton                                      -->
    <!-- ================================================================ -->
    <div v-if="isLoading" class="patient-banner">
      <div class="patient-banner__top">
        <Skeleton shape="circle" size="4rem" />
        <div class="flex-1 space-y-2">
          <Skeleton width="220px" height="1.5rem" />
          <Skeleton width="180px" height="1rem" />
        </div>
      </div>
    </div>

    <!-- ================================================================ -->
    <!-- BANNIÈRE PATIENT — Contenu                                       -->
    <!-- ================================================================ -->
    <div v-else-if="patient" class="patient-banner">

      <!-- Ligne principale : Avatar + Identité + Badges + Actions -->
      <div class="patient-banner__top">

        <!-- Avatar -->
        <div class="patient-avatar">
          <span class="patient-avatar__initials">{{ initials }}</span>
          <span
            class="patient-avatar__status"
            :class="{ 'patient-avatar__status--active': patient.status === 'ACTIVE' }"
          />
        </div>

        <!-- Identité + chips info -->
        <div class="patient-banner__identity">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="patient-banner__name">
              {{ patient.first_name }} {{ patient.last_name }}
            </h1>

            <!-- Badge GIR -->
            <span
              v-if="patient.current_gir"
              class="patient-gir-badge"
              :class="girBadgeClass"
            >
              GIR {{ patient.current_gir }}
            </span>

            <!-- Badge statut -->
            <Tag
              :value="statusLabel"
              :severity="patient.status === 'ACTIVE' ? 'success' : 'secondary'"
              class="text-xs"
            />
          </div>

          <!-- Chips info -->
          <div class="patient-banner__chips">
            <span v-if="age" class="patient-chip">
              <User :size="13" class="patient-chip__icon" />
              {{ age }} ans
              <template v-if="patient.birth_date">
                &middot; né(e) le {{ formatDate(patient.birth_date) }}
              </template>
            </span>
            <span
              v-if="patient.phone"
              class="patient-chip patient-chip--clickable"
              @click="callPhone(patient.phone!)"
            >
              <Phone :size="13" class="patient-chip__icon" />
              {{ patient.phone }}
            </span>
            <span v-if="patient.address" class="patient-chip" :title="patient.address">
              <MapPin :size="13" class="patient-chip__icon" />
              <span class="patient-chip__truncate">{{ patient.address }}</span>
            </span>
          </div>
        </div>

        <!-- Actions rapides -->
        <!-- v4 : size="small" et variant="outlined" remplacent les classes CSS -->
        <div class="patient-banner__actions">
          <Button
            label="Nouvelle évaluation"
            icon="pi pi-plus"
            size="small"
          />
          <Button
            label="Constantes"
            icon="pi pi-chart-line"
            size="small"
            variant="outlined"
            @click="activeTab = 'constantes'"
          />
        </div>
      </div>

      <!-- Barre de métadonnées -->
      <div class="patient-banner__meta">
        <div class="patient-meta-tag">
          <span class="patient-meta-tag__label">Structure</span>
          <span class="patient-meta-tag__value">{{ patient.entity_name || '\u2014' }}</span>
        </div>
        <div class="patient-meta-tag">
          <span class="patient-meta-tag__label">Dernière évaluation</span>
          <span class="patient-meta-tag__value">
            {{ latestEvaluation ? formatDate(latestEvaluation.evaluation_date) : '\u2014' }}
          </span>
        </div>
        <div class="patient-meta-tag">
          <span class="patient-meta-tag__label">GIR actuel</span>
          <span class="patient-meta-tag__value">
            {{ patient.current_gir ? 'GIR ' + patient.current_gir : '\u2014' }}
          </span>
        </div>
      </div>
    </div>

    <!-- ================================================================ -->
    <!-- ONGLETS — API PrimeVue 4 native                                  -->
    <!-- v-model:value sur string (plus d'index numérique)                -->
    <!-- Icônes Lucide dans le slot par défaut de <Tab>                   -->
    <!-- ================================================================ -->
    <Tabs v-model:value="activeTab" class="patient-tabs">

      <TabList>
        <Tab value="synthese">
          <LayoutDashboard :size="14" :stroke-width="1.8" class="tab-icon" />
          Synthèse
        </Tab>
        <Tab value="evaluations">
          <ClipboardCheck :size="14" :stroke-width="1.8" class="tab-icon" />
          Évaluations
        </Tab>
        <Tab value="constantes">
          <Activity :size="14" :stroke-width="1.8" class="tab-icon" />
          Constantes
        </Tab>
        <Tab value="liaison">
          <MessageSquare :size="14" :stroke-width="1.8" class="tab-icon" />
          Liaison
        </Tab>
        <Tab value="documents">
          <FileText :size="14" :stroke-width="1.8" class="tab-icon" />
          Documents
        </Tab>
      </TabList>

      <TabPanels>

        <!-- ── Synthèse ──────────────────────────────────────────────── -->
        <TabPanel value="synthese">
          <div class="tab-content">

            <!-- Widgets constantes vitales -->
            <section class="mb-6">
              <h3 class="tab-section-title">Dernières constantes</h3>

              <!-- Loading -->
              <div v-if="vitalsLoading" class="vital-grid">
                <div v-for="n in 4" :key="n" class="vital-widget vital-widget--empty">
                  <Skeleton width="60%" height="1rem" class="mb-2" />
                  <Skeleton width="40%" height="2rem" />
                </div>
              </div>

              <!-- Widgets -->
              <div v-else class="vital-grid">
                <div
                  v-for="config in vitalWidgets"
                  :key="config.key"
                  class="vital-widget"
                  :class="getVitalStatusClass(latestVitals[config.key])"
                >
                  <div class="vital-widget__header">
                    <i :class="config.icon" class="vital-widget__icon" />
                    <span class="vital-widget__label">{{ config.label }}</span>
                  </div>
                  <div class="vital-widget__body">
                    <span class="vital-widget__value">
                      {{ formatVitalValue(latestVitals[config.key]) }}
                    </span>
                    <span class="vital-widget__unit">{{ config.unit }}</span>
                  </div>
                  <span class="vital-widget__date">
                    {{ formatVitalDate(latestVitals[config.key]) }}
                  </span>
                </div>
              </div>
            </section>

            <!-- Résumé patient -->
            <section>
              <h3 class="tab-section-title">Informations clés</h3>
              <div class="synthese-info-grid">
                <div class="synthese-info-card">
                  <CheckSquare :size="16" class="synthese-info-card__icon" />
                  <div>
                    <p class="synthese-info-card__label">Dernière évaluation</p>
                    <p class="synthese-info-card__value">
                      <template v-if="latestEvaluation">
                        {{ formatDate(latestEvaluation.evaluation_date) }}
                        &mdash; GIR {{ latestEvaluation.gir_score || '?' }}
                        <Tag
                          :value="getStatusLabel(latestEvaluation.status)"
                          :severity="getStatusSeverity(latestEvaluation.status)"
                          class="ml-2 text-xs"
                        />
                      </template>
                      <span v-else class="text-slate-400">Aucune évaluation</span>
                    </p>
                  </div>
                </div>

                <div class="synthese-info-card">
                  <MapPin :size="16" class="synthese-info-card__icon" />
                  <div>
                    <p class="synthese-info-card__label">Adresse</p>
                    <p class="synthese-info-card__value">
                      {{ patient?.address || '\u2014' }}
                    </p>
                  </div>
                </div>

                <div class="synthese-info-card">
                  <Building2 :size="16" class="synthese-info-card__icon" />
                  <div>
                    <p class="synthese-info-card__label">Structure</p>
                    <p class="synthese-info-card__value">
                      {{ patient?.entity_name || '\u2014' }}
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </TabPanel>

        <!-- ── Évaluations ───────────────────────────────────────────── -->
        <TabPanel value="evaluations">
          <div class="tab-content">
            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">Évaluations AGGIR</h3>
              <Button label="Nouvelle évaluation" icon="pi pi-plus" size="small" />
            </div>

            <!-- Loading -->
            <div v-if="evaluationsLoading" class="space-y-3">
              <Skeleton height="3rem" />
              <Skeleton height="3rem" />
              <Skeleton height="3rem" />
            </div>

            <!-- Table évaluations -->
            <DataTable
              v-else-if="evaluations.length > 0"
              :value="evaluations"
              stripedRows
              class="p-datatable-sm"
            >
              <Column field="evaluation_date" header="Date" sortable>
                <template #body="{ data }">
                  {{ formatDate(data.evaluation_date) }}
                </template>
              </Column>

              <Column field="gir_score" header="GIR" sortable>
                <template #body="{ data }">
                  <span
                    v-if="data.gir_score"
                    class="patient-gir-badge"
                    :class="{
                      'patient-gir-badge--severe': data.gir_score <= 2,
                      'patient-gir-badge--moderate': data.gir_score > 2 && data.gir_score <= 4,
                      'patient-gir-badge--light': data.gir_score > 4,
                    }"
                  >
                    GIR {{ data.gir_score }}
                  </span>
                  <span v-else class="text-slate-400">-</span>
                </template>
              </Column>

              <Column field="status" header="Statut" sortable>
                <template #body="{ data }">
                  <Tag
                    :value="getStatusLabel(data.status)"
                    :severity="getStatusSeverity(data.status)"
                  />
                </template>
              </Column>

              <Column field="completion_percent" header="Complétion">
                <template #body="{ data }">
                  <div class="flex items-center gap-2">
                    <div class="w-20 bg-slate-200 rounded-full h-2">
                      <div
                        class="bg-teal-500 h-2 rounded-full transition-all"
                        :style="{ width: (data.completion_percent || 0) + '%' }"
                      />
                    </div>
                    <span class="text-sm text-slate-600">
                      {{ data.completion_percent || 0 }}%
                    </span>
                  </div>
                </template>
              </Column>

              <Column field="validated_at" header="Validation">
                <template #body="{ data }">
                  <span v-if="data.validated_at" class="text-emerald-600 font-medium">
                    {{ formatDate(data.validated_at) }}
                  </span>
                  <span v-else class="text-slate-400">En attente</span>
                </template>
              </Column>

              <Column header="Actions" style="width: 100px">
                <template #body="{ data }">
                  <Button
                    icon="pi pi-eye"
                    size="small"
                    variant="text"
                    rounded
                    title="Voir l'évaluation"
                    :loading="evaluationDetailLoading && selectedEvaluation?.id === data.id"
                    @click="openEvaluationDetail(data)"
                  />
                  <Button
                    v-if="data.status === 'DRAFT'"
                    icon="pi pi-pencil"
                    size="small"
                    variant="text"
                    rounded
                    title="Modifier"
                  />
                </template>
              </Column>
            </DataTable>

            <!-- Aucune évaluation -->
            <div v-else class="empty-state">
              <ClipboardCheck :size="48" class="empty-state-icon" />
              <p class="empty-state-title">Aucune évaluation</p>
              <p class="empty-state-description">
                Cliquez sur Nouvelle évaluation pour commencer le suivi AGGIR.
              </p>
            </div>
          </div>
        </TabPanel>

        <!-- ── Constantes ─────────────────────────────────────────────── -->
        <TabPanel value="constantes">
          <div class="tab-content">
            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">Historique des constantes</h3>
              <Button label="Ajouter une mesure" icon="pi pi-plus" size="small" />
            </div>
            <p class="text-slate-500 text-sm">
              Historique des constantes vitales avec graphiques et alertes.
            </p>
            <p class="mt-2 text-xs text-slate-400">(Contenu à implémenter)</p>
          </div>
        </TabPanel>

        <!-- ── Liaison ────────────────────────────────────────────────── -->
        <TabPanel value="liaison">
          <div class="tab-content">
            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">Carnet de liaison</h3>
              <Button label="Nouvelle entrée" icon="pi pi-plus" size="small" />
            </div>
            <p class="text-slate-500 text-sm">
              Carnet de liaison filtré sur ce patient.
            </p>
            <p class="mt-2 text-xs text-slate-400">(Contenu à implémenter)</p>
          </div>
        </TabPanel>

        <!-- ── Documents ──────────────────────────────────────────────── -->
        <TabPanel value="documents">
          <div class="tab-content">
            <h3 class="tab-section-title">Documents générés</h3>
            <p class="text-slate-500 text-sm">
              Documents PPA, PPCS, recommandations.
            </p>
            <p class="mt-2 text-xs text-slate-400">(Contenu à implémenter)</p>
          </div>
        </TabPanel>

      </TabPanels>
    </Tabs>

    <!-- Phase 5 — Modal détail évaluation -->
    <EvaluationDetailDialog
      v-model:visible="showEvaluationModal"
      :evaluation="selectedEvaluation"
      :patient-name="patient ? patient.first_name + ' ' + patient.last_name : ''"
      @close="closeEvaluationModal"
    />
  </div>
</template>

<style scoped>
/* =================================================================
   PATIENT DETAIL — Styles scoped
   Palette Soins : slate-* / teal-500/600 (FRONTEND_CONVENTIONS PATCH 1)

   Migration PrimeVue 4 (04/03/2026) :
   Suppression de ~80 lignes de CSS workaround :deep(.p-tabview-*).
   Les onglets sont maintenant stylés via :
   - definePreset teal dans main.ts (couleur active automatique)
   - .tab-icon pour l'alignement des icônes Lucide dans les onglets
   ================================================================= */

.patient-detail {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* -- Bannière --------------------------------------------------------- */

.patient-banner {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.patient-banner__top {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
}

@media (max-width: 640px) {
  .patient-banner__top {
    flex-direction: column;
    align-items: stretch;
  }
}

/* Avatar avec pastille statut */
.patient-avatar {
  position: relative;
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.patient-avatar__initials {
  font-size: 1.375rem;
  font-weight: 700;
  color: #475569;
  line-height: 1;
}

.patient-avatar__status {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: #94a3b8;
  border: 2.5px solid white;
}

.patient-avatar__status--active {
  background: #10b981;
}

/* Identité */
.patient-banner__identity {
  flex: 1;
  min-width: 0;
}

.patient-banner__name {
  font-size: 1.375rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.patient-banner__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
  margin-top: 0.5rem;
}

.patient-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: #475569;
  line-height: 1;
}

.patient-chip__icon {
  color: #94a3b8;
  flex-shrink: 0;
}

.patient-chip--clickable {
  cursor: pointer;
  border-radius: 0.375rem;
  padding: 0.125rem 0.25rem;
  margin: -0.125rem -0.25rem;
  transition: background-color 0.15s ease;
}

.patient-chip--clickable:hover {
  background: #f1f5f9;
  color: #0d9488;
}

.patient-chip--clickable:hover .patient-chip__icon {
  color: #0d9488;
}

.patient-chip__truncate {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Actions rapides */
.patient-banner__actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .patient-banner__actions {
    justify-content: stretch;
  }
  .patient-banner__actions :deep(.p-button) {
    flex: 1;
  }
}

/* Badge GIR */
.patient-gir-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-weight: 700;
  font-size: 0.75rem;
  letter-spacing: 0.025em;
}

.patient-gir-badge--severe   { background: #fee2e2; color: #dc2626; }
.patient-gir-badge--moderate { background: #fef3c7; color: #d97706; }
.patient-gir-badge--light    { background: #dcfce7; color: #16a34a; }

/* Barre de métadonnées */
.patient-banner__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding: 0.75rem 1.5rem;
  border-top: 1px solid #f1f5f9;
  background: #f8fafc;
}

.patient-meta-tag {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.patient-meta-tag__label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  color: #94a3b8;
}

.patient-meta-tag__value {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #334155;
}

/* -- Onglets — PrimeVue 4 + definePreset teal ----------------------- */
/*
 * Plus de :deep(.p-tabview-*) nécessaires.
 * definePreset teal dans main.ts gère automatiquement :
 *   - couleur de l'onglet actif (underline + texte teal)
 *   - hover states
 *   - focus rings
 * .tab-icon aligne les icônes Lucide dans le slot <Tab>.
 */

.patient-tabs {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.tab-icon {
  flex-shrink: 0;
  margin-right: 0.375rem;
}

:deep(.patient-tabs .p-tabpanels) {
  padding: 0;
}

.tab-content {
  padding: 1.25rem 1.5rem;
}

.tab-section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 1rem;
}

/* -- Widgets constantes vitales --------------------------------------- */

.vital-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

@media (min-width: 768px) {
  .vital-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.vital-widget {
  border-radius: 0.75rem;
  padding: 1rem;
  border: 1px solid transparent;
  transition: box-shadow 0.15s ease;
}

.vital-widget:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.vital-widget__header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.5rem;
}

.vital-widget__icon {
  font-size: 0.875rem;
}

.vital-widget__label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.vital-widget__body {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.vital-widget__value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.vital-widget__unit {
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.7;
}

.vital-widget__date {
  display: block;
  font-size: 0.6875rem;
  margin-top: 0.375rem;
  opacity: 0.6;
}

/* Variantes couleur */
.vital-widget--ok      { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
.vital-widget--warning { background: #fff7ed; border-color: #fed7aa; color: #9a3412; }
.vital-widget--critical { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
.vital-widget--empty   { background: #f8fafc; border-color: #e2e8f0; color: #94a3b8; }

.vital-widget--ok .vital-widget__icon      { color: #16a34a; }
.vital-widget--warning .vital-widget__icon { color: #ea580c; }
.vital-widget--critical .vital-widget__icon { color: #dc2626; }

/* -- Synthèse — Cartes info ------------------------------------------- */

.synthese-info-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.synthese-info-card {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 0.625rem;
}

.synthese-info-card__icon {
  color: #0d9488;
  margin-top: 0.125rem;
  flex-shrink: 0;
}

.synthese-info-card__label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #94a3b8;
  margin-bottom: 0.125rem;
}

.synthese-info-card__value {
  font-size: 0.875rem;
  color: #334155;
  line-height: 1.5;
}
</style>