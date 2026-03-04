<script setup lang="ts">
/**
 * PatientDetailPage.vue — Dashboard patient (détail + édition)
 *
 * Page de visualisation et d'édition d'un dossier patient dans l'espace Admin.
 * Pattern calqué sur UserDetailPage.vue (TenantDetailPage.vue) :
 *   - Header avec infos clés + actions
 *   - Sections : identité, coordonnées, évaluations, statut
 *   - Panel latéral d'édition (futur)
 *
 * 🆕 01/03/2026 — Améliorations UX Phase 1 :
 *   - Icônes Lucide (cohérence wizard)
 *   - Tooltip explicatif sur "Archiver"
 *   - Bouton "Nouvelle évaluation" avec lien vers wizard
 *   - Badges visuels enrichis
 *
 * Route : /admin/patients/:id
 * Layout : AdminLayout
 *
 * Destination : src/pages/admin/patients/PatientDetailPage.vue
 */
import { computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// PrimeVue Components
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import Skeleton from 'primevue/skeleton'
import Message from 'primevue/message'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'

// Lucide icons
import {
  IdCard,
  MapPin,
  FileText,
  Info,
  ShieldCheck,
  Archive,
  CheckCircle2,
  RotateCcw,
  Phone,
  Mail,
  CalendarDays,
  Building2,
  Clock,
  ClipboardPlus,
  ExternalLink,
  CircleDashed,
} from 'lucide-vue-next'

// Store
import { useAdminStore } from '@/stores/admin.store'
import type { PatientStatus } from '@/types/patient'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()
const confirm = useConfirm()

// =============================================================================
// STATE
// =============================================================================

const patientId = computed(() => Number(route.params.id))
const patient = computed(() => adminStore.currentPatient)
const isLoading = computed(() => adminStore.isLoadingPatient)
const error = computed(() => adminStore.patientError)

// =============================================================================
// COMPUTED — Données formatées
// =============================================================================

const fullName = computed(() => {
  if (!patient.value) return ''
  const parts = [patient.value.last_name, patient.value.first_name].filter(Boolean)
  return parts.join(' ') || 'Patient sans nom'
})

const age = computed(() => {
  if (!patient.value?.birth_date) return null
  const birth = new Date(patient.value.birth_date)
  const today = new Date()
  let a = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    a--
  }
  return a
})

const formattedBirthDate = computed(() => {
  if (!patient.value?.birth_date) return '—'
  const date = new Date(patient.value.birth_date)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
})

const formattedCreatedAt = computed(() => {
  if (!patient.value?.created_at) return '—'
  const date = new Date(patient.value.created_at)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
})

const evaluationCount = computed(() => {
  return patient.value?.evaluations?.length ?? 0
})

function getStatusConfig(status?: PatientStatus): { label: string; severity: string } {
  switch (status) {
    case 'ACTIVE':
      return { label: 'Actif', severity: 'success' }
    case 'INACTIVE':
      return { label: 'Inactif', severity: 'warn' }
    case 'ARCHIVED':
      return { label: 'Archivé', severity: 'secondary' }
    case 'DECEASED':
      return { label: 'Décédé', severity: 'danger' }
    default:
      return { label: status ?? '—', severity: 'info' }
  }
}

function getGirConfig(gir?: number): { label: string; class: string } | null {
  if (!gir) return null
  if (gir <= 2) return { label: `GIR ${gir}`, class: 'bg-red-100 text-red-700' }
  if (gir <= 4) return { label: `GIR ${gir}`, class: 'bg-amber-100 text-amber-700' }
  return { label: `GIR ${gir}`, class: 'bg-emerald-100 text-emerald-700' }
}

// =============================================================================
// ACTIONS
// =============================================================================

function startNewEvaluation() {
  router.push({
    name: 'soins-evaluation-create',
    params: { patientId: patientId.value },
  })
}

/** Archiver le patient avec confirmation */
function archivePatient() {
  if (!patient.value) return

  confirm.require({
    message: `Voulez-vous vraiment archiver le dossier de ${fullName.value} ?\n\nLe patient ne sera plus visible dans les listes actives mais toutes ses données seront conservées et pourront être réactivées à tout moment.`,
    header: 'Archiver le dossier patient',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Archiver',
    rejectLabel: 'Annuler',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', variant: 'outlined' },
    accept: async () => {
      await adminStore.updatePatient(patientId.value, { status: 'ARCHIVED' })
    },
  })
}

/** Réactiver le patient */
async function reactivatePatient() {
  await adminStore.updatePatient(patientId.value, { status: 'ACTIVE' })
}

// =============================================================================
// LIFECYCLE
// =============================================================================

onMounted(() => {
  adminStore.fetchPatient(patientId.value)
})

watch(patientId, (newId) => {
  if (newId) {
    adminStore.fetchPatient(newId)
  }
})

// Cleanup
onBeforeUnmount(() => {
  adminStore.clearCurrentPatient()
})
</script>

<template>
  <div class="space-y-6">
    <ConfirmDialog />

    <!-- ─── LOADING ─── -->
    <div v-if="isLoading" class="space-y-4">
      <Skeleton width="60%" height="2rem" />
      <Skeleton width="40%" height="1rem" />
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <Skeleton height="12rem" class="lg:col-span-2" />
        <Skeleton height="12rem" />
      </div>
    </div>

    <!-- ─── ERROR ─── -->
    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- ─── CONTENU ─── -->
    <template v-else-if="patient">

      <!-- ─── HEADER ─── -->
      <div class="flex gap-2">
        <!-- Action principale : nouvelle évaluation -->
        <button
          v-if="patient.status === 'ACTIVE'"
          class="new-eval-btn"
          @click="startNewEvaluation"
        >
          <ClipboardPlus :size="16" :stroke-width="1.8" />
          Nouvelle évaluation
        </button>

        <!-- Bouton Archiver + icône info avec tooltip CSS -->
        <div v-if="patient.status === 'ACTIVE'" class="archive-group">
          <button
            class="archive-btn"
            @click="archivePatient"
          >
            <Archive :size="16" :stroke-width="1.8" />
            Archiver
          </button>
          <span class="info-bubble-trigger">
            <Info :size="14" :stroke-width="1.8" />
            <span class="info-bubble">
              Archiver le dossier. Le patient ne sera plus visible
              dans les listes actives, mais ses données sont conservées
              et réactivables à tout moment.
            </span>
          </span>
        </div>

        <!-- Bouton Réactiver -->
        <button
          v-else-if="patient.status === 'ARCHIVED' || patient.status === 'INACTIVE'"
          class="reactivate-btn"
          @click="reactivatePatient"
        >
          <RotateCcw :size="16" :stroke-width="1.8" />
          Réactiver
        </button>
      </div>

      <!-- ─── GRILLE PRINCIPALE ─── -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- ── Colonne gauche (2/3) ── -->
        <div class="lg:col-span-2 space-y-6">

          <!-- Identité -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--blue">
                  <IdCard :size="18" :stroke-width="1.8" />
                </div>
                Identité
              </div>
            </template>
            <template #content>
              <div class="grid grid-cols-2 gap-y-4 gap-x-8 text-sm">
                <div>
                  <p class="field-label">Nom</p>
                  <p class="field-value">{{ patient.last_name || '—' }}</p>
                </div>
                <div>
                  <p class="field-label">Prénom</p>
                  <p class="field-value">{{ patient.first_name || '—' }}</p>
                </div>
                <div>
                  <p class="field-label">Date de naissance</p>
                  <p class="field-value">
                    {{ formattedBirthDate }}
                    <span v-if="age" class="text-slate-400 font-normal">({{ age }} ans)</span>
                  </p>
                </div>
                <div>
                  <p class="field-label">NIR</p>
                  <p class="field-value font-mono">{{ patient.nir || '—' }}</p>
                </div>
                <div>
                  <p class="field-label">INS</p>
                  <p class="field-value font-mono">{{ patient.ins || '—' }}</p>
                </div>
              </div>
            </template>
          </Card>

          <!-- Coordonnées -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--teal">
                  <MapPin :size="18" :stroke-width="1.8" />
                </div>
                Coordonnées
              </div>
            </template>
            <template #content>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-8 text-sm">
                <div class="md:col-span-2">
                  <p class="field-label">Adresse</p>
                  <p class="field-value">{{ patient.address || '—' }}</p>
                </div>
                <div>
                  <p class="field-label">Téléphone</p>
                  <p class="field-value">
                    <a
                      v-if="patient.phone"
                      :href="`tel:${patient.phone}`"
                      class="contact-link"
                    >
                      <Phone :size="14" :stroke-width="1.8" class="text-slate-400" />
                      {{ patient.phone }}
                    </a>
                    <span v-else class="text-slate-300">—</span>
                  </p>
                </div>
                <div>
                  <p class="field-label">Email</p>
                  <p class="field-value">
                    <a
                      v-if="patient.email"
                      :href="`mailto:${patient.email}`"
                      class="contact-link"
                    >
                      <Mail :size="14" :stroke-width="1.8" class="text-slate-400" />
                      {{ patient.email }}
                    </a>
                    <span v-else class="text-slate-300">—</span>
                  </p>
                </div>
              </div>
            </template>
          </Card>

          <!-- Évaluations -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--amber">
                  <FileText :size="18" :stroke-width="1.8" />
                </div>
                Évaluations
                <span v-if="evaluationCount > 0" class="eval-count-badge">
                  {{ evaluationCount }}
                </span>
              </div>
            </template>
            <template #content>
              <!-- État vide -->
              <div v-if="evaluationCount === 0" class="eval-empty-state">
                <div class="eval-empty-icon">
                  <CircleDashed :size="36" :stroke-width="1.2" />
                </div>
                <p class="eval-empty-title">Aucune évaluation</p>
                <p class="eval-empty-hint">
                  Lancez une première évaluation AGGIR pour déterminer le niveau d'autonomie du patient.
                </p>
              </div>

              <!-- TODO: Liste des évaluations existantes quand evaluationCount > 0 -->
              <div v-else class="text-center py-4 text-slate-400 text-sm">
                <p>{{ evaluationCount }} évaluation{{ evaluationCount > 1 ? 's' : '' }} enregistrée{{ evaluationCount > 1 ? 's' : '' }}</p>
                <Button
                  label="Voir dans l'espace soins"
                  severity="secondary"
                  text
                  size="small"
                  class="mt-2"
                  @click="router.push({ name: 'patient-detail', params: { id: patientId } })"
                >
                  <template #icon>
                    <ExternalLink :size="14" :stroke-width="1.8" class="mr-1" />
                  </template>
                </Button>
              </div>
            </template>
          </Card>
        </div>

        <!-- ── Colonne droite (1/3) ── -->
        <div class="space-y-6">

          <!-- Informations dossier -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--slate">
                  <Info :size="18" :stroke-width="1.8" />
                </div>
                Dossier
              </div>
            </template>
            <template #content>
              <div class="space-y-3 text-sm">
                <div>
                  <p class="field-label">Statut</p>
                  <Tag
                    :value="getStatusConfig(patient.status).label"
                    :severity="getStatusConfig(patient.status).severity as any"
                  />
                </div>
                <Divider />
                <div>
                  <p class="field-label">Score GIR</p>
                  <p class="mt-1">
                    <span
                      v-if="getGirConfig(patient.current_gir)"
                      class="text-xs font-semibold px-2.5 py-1 rounded-full"
                      :class="getGirConfig(patient.current_gir)!.class"
                    >
                      {{ getGirConfig(patient.current_gir)!.label }}
                    </span>
                    <span v-else class="gir-not-evaluated">
                      <CircleDashed :size="14" :stroke-width="1.8" />
                      Non évalué
                    </span>
                  </p>
                </div>
                <Divider />
                <div>
                  <p class="field-label">Entité</p>
                  <p class="field-value flex items-center gap-1.5">
                    <Building2 :size="14" :stroke-width="1.8" class="text-slate-400" />
                    {{ patient.entity_name || `Entité #${patient.entity_id}` }}
                  </p>
                </div>
                <Divider />
                <div>
                  <p class="field-label">Créé le</p>
                  <p class="field-value flex items-center gap-1.5">
                    <CalendarDays :size="14" :stroke-width="1.8" class="text-slate-400" />
                    {{ formattedCreatedAt }}
                  </p>
                </div>
              </div>
            </template>
          </Card>

          <!-- Sécurité & Conformité -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--emerald">
                  <ShieldCheck :size="18" :stroke-width="1.8" />
                </div>
                Sécurité
              </div>
            </template>
            <template #content>
              <div class="space-y-2.5 text-sm">
                <div class="security-item security-item--ok">
                  <CheckCircle2 :size="15" :stroke-width="2" />
                  <span>Données chiffrées (AES-256-GCM)</span>
                </div>
                <div class="security-item security-item--ok">
                  <CheckCircle2 :size="15" :stroke-width="2" />
                  <span>Isolation multi-tenant (RLS)</span>
                </div>
                <div class="security-item security-item--pending">
                  <Clock :size="15" :stroke-width="1.8" />
                  <span>Journal d'accès RGPD — à venir</span>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ── Avatar patient ──────────────────────────────────────────────────── */
.patient-avatar {
  @apply w-14 h-14 rounded-2xl flex items-center justify-center text-lg font-bold flex-shrink-0;
  transition: all 0.2s ease;
}

.patient-avatar--active {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  color: #2563eb;
}

.patient-avatar--inactive {
  @apply bg-slate-100 text-slate-400;
}

/* ── Titres de section ───────────────────────────────────────────────── */
.section-title {
  @apply flex items-center gap-2.5 text-base font-semibold text-slate-800;
}

.section-icon {
  @apply flex items-center justify-center flex-shrink-0;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
}

.section-icon--blue    { background: #eff6ff; color: #3b82f6; }
.section-icon--teal    { background: #f0fdfa; color: #0d9488; }
.section-icon--amber   { background: #fffbeb; color: #d97706; }
.section-icon--slate   { background: #f1f5f9; color: #475569; }
.section-icon--emerald { background: #ecfdf5; color: #059669; }

/* ── Champs (label / value) ──────────────────────────────────────────── */
.field-label {
  @apply text-slate-400 text-xs font-medium uppercase tracking-wide mb-0.5;
}

.field-value {
  @apply font-medium text-slate-800;
}

/* ── Liens de contact ────────────────────────────────────────────────── */
.contact-link {
  @apply inline-flex items-center gap-1.5 text-teal-600 hover:text-teal-800 transition-colors;
}

/* ── Bouton Archiver ─────────────────────────────────────────────────── */
.archive-btn {
  @apply inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
         text-slate-500 border border-slate-200 cursor-pointer;
  background: white;
  transition: all 0.2s ease;
}

.archive-btn:hover {
  @apply text-red-600 border-red-200;
  background: #fef2f2;
}

/* ── Bouton Réactiver ────────────────────────────────────────────────── */
.reactivate-btn {
  @apply inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
         text-emerald-600 border border-emerald-200 cursor-pointer;
  background: #ecfdf5;
  transition: all 0.2s ease;
}

.reactivate-btn:hover {
  @apply border-emerald-300;
  background: #d1fae5;
}

/* ── Bouton Nouvelle évaluation ──────────────────────────────────────── */
.new-eval-btn {
  @apply inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold
         text-teal-700 cursor-pointer;
  background: #f0fdfa;
  border: 1.5px solid #99f6e4;
  transition: all 0.2s ease;
}

.new-eval-btn:hover {
  background: #ccfbf1;
  border-color: #5eead4;
  box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
}

/* ── État vide évaluations ───────────────────────────────────────────── */
.eval-empty-state {
  @apply flex flex-col items-center justify-center py-8 text-center;
}

.eval-empty-icon {
  @apply mb-3;
  color: #cbd5e1;
}

.eval-empty-title {
  @apply text-sm font-semibold text-slate-500 mb-1;
}

.eval-empty-hint {
  @apply text-xs text-slate-400 max-w-xs leading-relaxed;
}

.eval-count-badge {
  @apply inline-flex items-center justify-center text-xs font-bold rounded-full;
  width: 1.375rem;
  height: 1.375rem;
  background: #f0fdfa;
  color: #0d9488;
  margin-left: 0.25rem;
}

/* ── GIR non évalué ──────────────────────────────────────────────────── */
.gir-not-evaluated {
  @apply inline-flex items-center gap-1.5 text-sm text-slate-400;
}

/* ── Sécurité ────────────────────────────────────────────────────────── */
.security-item {
  @apply flex items-center gap-2;
}

.security-item--ok {
  @apply text-emerald-600;
}

.security-item--pending {
  @apply text-slate-400;
}

/* ── Groupe Archiver + info ──────────────────────────────────────────── */
.archive-group {
  @apply flex items-center gap-1;
}

/* ── Tooltip info bulle ──────────────────────────────────────────────── */
.info-bubble-trigger {
  @apply relative inline-flex items-center justify-center text-slate-400 cursor-help;
  padding: 0.25rem;
}

.info-bubble-trigger:hover {
  @apply text-slate-600;
}

.info-bubble {
  @apply absolute z-50 hidden w-64 text-xs text-slate-600 leading-relaxed rounded-xl p-3;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%);
  background: white;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.10);
  pointer-events: none;
}

.info-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: white;
}

.info-bubble-trigger:hover .info-bubble {
  display: block;
}
</style>