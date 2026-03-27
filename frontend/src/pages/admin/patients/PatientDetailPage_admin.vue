<script setup lang="ts">
  /**
   * PatientDetailPage_admin.vue — Dashboard patient (détail + édition)
   *
   * Page de visualisation et d'édition d'un dossier patient dans l'espace Admin.
   *
   * 🆕 01/03/2026 — Améliorations UX Phase 1
   * 🆕 05/03/2026 — Phase 10C : EvaluationDraftProgress
   * 🆕 13/03/2026 — S3 : Affichage évaluations soumises/validées + GIR + dialog détail
   *
   * Route : /admin/patients/:id
   * Layout : AdminLayout
   *
   * Destination : src/pages/admin/patients/PatientDetailPage_admin.vue
   */
  import { computed, onMounted, ref, watch, onBeforeUnmount } from 'vue';
  import { useRoute, useRouter } from 'vue-router';

  // PrimeVue Components
  import Tag from 'primevue/tag';
  import Card from 'primevue/card';
  import Divider from 'primevue/divider';
  import Skeleton from 'primevue/skeleton';
  import Message from 'primevue/message';
  import ConfirmDialog from 'primevue/confirmdialog';
  import { useConfirm } from 'primevue/useconfirm';

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
    CircleDashed,
    Eye,
    Stethoscope,
    Activity,
    Pencil,
  } from 'lucide-vue-next';

  // Store & services
  import { usePatientStore } from '@/stores';
  import { evaluationService } from '@/services';
  import { entityService } from '@/services';
  import type { PatientStatus, PatientEvaluationResponse } from '@/types';

  // Composants évaluation
  import EvaluationDraftProgress from '@/components/evaluation/EvaluationDraftProgress.vue';
  import type { EvaluationDraft } from '@/components/evaluation/EvaluationDraftProgress.vue';
  import EvaluationDetailDialog from '@/components/evaluation/EvaluationDetailDialog.vue';
  import PatientEditDialog from '@/components/patients/PatientEditDialog.vue';

  const route = useRoute();
  const router = useRouter();
  const patientStore = usePatientStore();
  const confirm = useConfirm();

  // =============================================================================
  // STATE
  // =============================================================================

  const patientId = computed(() => Number(route.params.id));
  const patient = computed(() => patientStore.currentPatient);
  const isLoading = computed(() => patientStore.isLoadingPatient);
  const error = computed(() => patientStore.error);

  /** Toutes les évaluations du patient */
  const allEvaluations = ref<PatientEvaluationResponse[]>([]);

  /** Brouillon d'évaluation en cours (DRAFT / IN_PROGRESS) */
  const draftEvaluation = ref<EvaluationDraft | null>(null);

  /** Évaluations soumises / validées (tout sauf DRAFT et IN_PROGRESS) */
  const submittedEvaluations = computed(() =>
    allEvaluations.value.filter((e) => e.status !== 'DRAFT' && e.status !== 'IN_PROGRESS'),
  );

  /** Modal de détail évaluation */
  const showEvaluationModal = ref(false);
  const selectedEvaluation = ref<PatientEvaluationResponse | null>(null);

  /** Panel d'édition patient */
  const editDialogVisible = ref(false);

  /** Nom de l'entité de rattachement (chargé via entityService) */
  const entityName = ref<string | null>(null);

  // =============================================================================
  // COMPUTED — Données formatées
  // =============================================================================

  const fullName = computed(() => {
    if (!patient.value) return '';
    const parts = [patient.value.last_name, patient.value.first_name].filter(Boolean);
    return parts.join(' ') || 'Patient sans nom';
  });

  const age = computed(() => {
    if (!patient.value?.birth_date) return null;
    const birth = new Date(patient.value.birth_date);
    const today = new Date();
    let a = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      a--;
    }
    return a;
  });

  const formattedBirthDate = computed(() => {
    if (!patient.value?.birth_date) return '—';
    const date = new Date(patient.value.birth_date);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  });

  const formattedCreatedAt = computed(() => {
    if (!patient.value?.created_at) return '—';
    const date = new Date(patient.value.created_at);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  });

  /** Nombre total d'évaluations (toutes confondues) */
  const evaluationCount = computed(() => allEvaluations.value.length);

  function getStatusConfig(status?: PatientStatus): { label: string; severity: 'success' | 'info' | 'warn' | 'danger' | 'secondary' } {
    switch (status) {
      case 'ACTIVE':
        return { label: 'Actif', severity: 'success' };
      case 'INACTIVE':
        return { label: 'Inactif', severity: 'warn' };
      case 'ARCHIVED':
        return { label: 'Archivé', severity: 'secondary' };
      case 'DECEASED':
        return { label: 'Décédé', severity: 'danger' };
      default:
        return { label: status ?? '—', severity: 'info' };
    }
  }

  function getGirConfig(gir?: number | null): { label: string; class: string } | null {
    if (!gir) return null;
    if (gir <= 2) return { label: `GIR ${gir}`, class: 'bg-red-100 text-red-700' };
    if (gir <= 4) return { label: `GIR ${gir}`, class: 'bg-amber-100 text-amber-700' };
    return { label: `GIR ${gir}`, class: 'bg-emerald-100 text-emerald-700' };
  }

  /** GIR à afficher : patient.current_gir (si colonne existe) ou dernier gir_score d'évaluation */
  const displayGir = computed(() => {
    if (patient.value?.current_gir) return patient.value.current_gir;
    // Fallback : lire le gir_score de la dernière évaluation soumise/validée
    const latest = submittedEvaluations.value[0];
    return latest?.gir_score ?? null;
  });

  // =============================================================================
  // COMPUTED — Bilan clinique (S6) : scores extraits de la dernière évaluation
  // =============================================================================

  interface ClinicalScore {
    label: string;
    severity: 'alert' | 'warning' | 'ok' | 'info';
  }

  /**
   * Extrait et catégorise les scores cliniques depuis evaluation_data.sante.blocs[].test[]
   * de la dernière évaluation soumise. Retourne un tableau de chips à afficher.
   */
  const clinicalScores = computed((): ClinicalScore[] => {
    const latest = submittedEvaluations.value[0];
    if (!latest?.evaluation_data) return [];

    // Narrowing : evaluation_data est Record<string, unknown>, on navigue prudemment
    const sante = latest.evaluation_data.sante as Record<string, unknown> | undefined;
    const blocs = Array.isArray(sante?.blocs) ? sante.blocs : [];
    if (blocs.length === 0) return [];

    // Collecter tous les tests
    const tests: { nom: string; resultat: string }[] = [];
    for (const bloc of blocs as Record<string, unknown>[]) {
      if (Array.isArray(bloc.test)) {
        for (const t of bloc.test as Record<string, unknown>[]) {
          if (typeof t.nom === 'string' && typeof t.resultat === 'string') {
            tests.push({ nom: t.nom, resultat: t.resultat });
          }
        }
      }
    }

    if (tests.length === 0) return [];

    const scores: ClinicalScore[] = [];

    // — Mini-cog (cherche "mini-cog de X/5")
    const minicog = tests.find((t) => t.nom === 'Mini-cog');
    if (minicog) {
      const match = minicog.resultat.match(/(\d+)\/5/);
      if (match) {
        const val = parseInt(match[1]);
        scores.push({
          label: `Mini-cog ${val}/5`,
          severity: val <= 2 ? 'alert' : val <= 3 ? 'warning' : 'ok',
        });
      }
    }

    // — GAI-SF (anxiété)
    const gai = tests.find((t) => t.nom.includes('TEST GAI') && !t.resultat.match(/^\d{2}\/\d{2}/));
    if (gai) {
      const anxious = gai.resultat.toLowerCase().includes('anxiété');
      scores.push({
        label: anxious ? 'GAI-SF Anxiété' : 'GAI-SF Normal',
        severity: anxious ? 'alert' : 'ok',
      });
    }

    // — Mini-GDS (cherche "mini-GDS de X/4")
    const gds = tests.find((t) => t.nom.includes('Mini GDS') && !t.resultat.match(/^\d{2}\/\d{2}/));
    if (gds) {
      const match = gds.resultat.match(/(\d+)\/4/);
      if (match) {
        const val = parseInt(match[1]);
        scores.push({
          label: `Mini-GDS ${val}/4`,
          severity: val >= 2 ? 'alert' : val === 1 ? 'warning' : 'ok',
        });
      }
    }

    // — SPPB (3 sous-tests → somme)
    const chaise = tests.find(
      (t) => t.nom.includes('lever de chaise') && !t.resultat.match(/^\d{2}\/\d{2}/),
    );
    const equilibre = tests.find(
      (t) => t.nom.includes('équilibre') && !t.resultat.match(/^\d{2}\/\d{2}/),
    );
    const marche = tests.find(
      (t) => t.nom.includes('vitesse de marche') && !t.resultat.match(/^\d{2}\/\d{2}/),
    );
    let sppbTotal = 0;
    let sppbCount = 0;
    for (const t of [chaise, equilibre, marche]) {
      if (t) {
        const match = t.resultat.match(/(\d+)\s*points?\s*\/\s*4/);
        if (match) {
          sppbTotal += parseInt(match[1]);
          sppbCount++;
        }
      }
    }
    if (sppbCount === 3) {
      scores.push({
        label: `SPPB ${sppbTotal}/12`,
        severity: sppbTotal <= 4 ? 'alert' : sppbTotal <= 8 ? 'warning' : 'ok',
      });
    }

    // — IMC
    const imc = tests.find((t) => t.nom === 'IMC');
    if (imc) {
      const val = parseFloat(imc.resultat);
      if (!isNaN(val)) {
        const interp = tests.find(
          (t) => t.nom === 'Interprétation IMC' && !t.resultat.match(/^\d{2}\/\d{2}/),
        );
        const isNormal = interp?.resultat?.toLowerCase().includes('normal');
        scores.push({
          label: `IMC ${val.toFixed(1)}`,
          severity: isNormal ? 'ok' : val < 21 || val > 30 ? 'alert' : 'warning',
        });
      }
    }

    // — MNA (dénutrition)
    const mna = tests.find((t) => t.nom.includes('MNA') && !t.resultat.match(/^\d{2}\/\d{2}/));
    if (mna) {
      const r = mna.resultat.toLowerCase();
      if (r.includes('dénutrition avérée')) {
        scores.push({ label: 'MNA Dénutrition', severity: 'alert' });
      } else if (r.includes('risque')) {
        scores.push({ label: 'MNA Risque', severity: 'warning' });
      } else {
        scores.push({ label: 'MNA Normal', severity: 'ok' });
      }
    }

    // — Norton (escarre)
    const norton = tests.find(
      (t) => t.nom.includes('Norton') && !t.resultat.match(/^\d{2}\/\d{2}/),
    );
    if (norton) {
      const r = norton.resultat.toLowerCase();
      if (r.includes('élevé') || r.includes('très élevé')) {
        scores.push({ label: 'Norton Risque élevé', severity: 'alert' });
      } else if (r.includes('modéré')) {
        scores.push({ label: 'Norton Risque modéré', severity: 'warning' });
      } else {
        scores.push({ label: 'Norton Normal', severity: 'ok' });
      }
    }

    return scores;
  });

  // =============================================================================
  // HELPERS — Évaluations (S3)
  // =============================================================================

  function getEvalStatusLabel(status: string): string {
    switch (status) {
      case 'VALIDATED':
        return 'Validée';
      case 'PENDING_DEPARTMENT':
        return 'Attente CD';
      case 'PENDING_MEDICAL':
        return 'Attente médecin';
      case 'SUBMITTED':
        return 'Soumise';
      case 'IN_PROGRESS':
        return 'En cours';
      case 'DRAFT':
        return 'Brouillon';
      case 'ARCHIVED':
        return 'Archivée';
      default:
        return status;
    }
  }

  function getEvalStatusSeverity(status: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
    switch (status) {
      case 'VALIDATED':
        return 'success';
      case 'PENDING_DEPARTMENT':
      case 'PENDING_MEDICAL':
        return 'info';
      case 'SUBMITTED':
        return 'info';
      case 'DRAFT':
      case 'IN_PROGRESS':
        return 'warn';
      default:
        return 'secondary';
    }
  }

  function formatEvalDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  // =============================================================================
  // CHARGEMENT DES ÉVALUATIONS (S3 — refactoré)
  // =============================================================================

  /**
   * Charge TOUTES les évaluations du patient et les répartit :
   * - draftEvaluation : le brouillon actif (DRAFT / IN_PROGRESS)
   * - submittedEvaluations (computed) : tout le reste
   */
  async function loadEvaluations(id: number): Promise<void> {
    try {
      const response = await evaluationService.getAll(id);
      const evaluations: PatientEvaluationResponse[] = response?.data?.items ?? response?.data ?? [];

      allEvaluations.value = evaluations;

      // Isoler le brouillon actif
      draftEvaluation.value =
        evaluations.find((e) => e.status === 'DRAFT' || e.status === 'IN_PROGRESS') ?? null;
    } catch (err) {
      allEvaluations.value = [];
      draftEvaluation.value = null;
      if (import.meta.env.DEV) {
        console.warn('[PatientDetailPage] Impossible de charger les évaluations:', err);
      }
    }
  }

  // =============================================================================
  // ACTIONS — Évaluation (S3)
  // =============================================================================

  /** Ouvrir le dialog de détail d'une évaluation */
  async function openEvaluationDetail(evaluation: PatientEvaluationResponse) {
    if (evaluation.evaluation_data && Object.keys(evaluation.evaluation_data).length > 0) {
      selectedEvaluation.value = evaluation;
      showEvaluationModal.value = true;
      return;
    }

    // Charger les données complètes si pas déjà en mémoire
    try {
      const full = await evaluationService.get(patientId.value, evaluation.id);
      selectedEvaluation.value = full?.data ?? full;
      showEvaluationModal.value = true;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[PatientDetailPage] Erreur chargement détail évaluation:', err);
      }
    }
  }

  function closeEvaluationModal() {
    showEvaluationModal.value = false;
    setTimeout(() => {
      selectedEvaluation.value = null;
    }, 300);
  }

  // =============================================================================
  // ACTIONS — Patient
  // =============================================================================

  function startNewEvaluation() {
    router.push({
      name: 'soins-evaluation-create',
      params: { patientId: patientId.value },
    });
  }

  function openEditDialog() {
    editDialogVisible.value = true;
  }

  async function onPatientSaved() {
    // Recharger le patient et ses évaluations après modification
    await patientStore.fetchPatient(patientId.value);
    await loadEvaluations(patientId.value);
    await loadEntityName();
  }

  function archivePatient() {
    if (!patient.value) return;

    confirm.require({
      message: `Voulez-vous vraiment archiver le dossier de ${fullName.value} ?\n\nLe patient ne sera plus visible dans les listes actives mais toutes ses données seront conservées et pourront être réactivées à tout moment.`,
      header: 'Archiver le dossier patient',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Archiver',
      rejectLabel: 'Annuler',
      acceptProps: { severity: 'danger' },
      rejectProps: { severity: 'secondary', variant: 'outlined' },
      accept: async () => {
        await patientStore.updatePatient(patientId.value, { status: 'ARCHIVED' });
      },
    });
  }

  async function reactivatePatient() {
    await patientStore.updatePatient(patientId.value, { status: 'ACTIVE' });
  }

  // =============================================================================
  // CHARGEMENT NOM ENTITÉ (B5)
  // =============================================================================

  async function loadEntityName(): Promise<void> {
    const p = patient.value;
    if (!p?.entity_id) {
      entityName.value = null;
      return;
    }
    // Si l'API retourne déjà entity_name, pas besoin de fetch supplémentaire
    if (p.entity_name) {
      entityName.value = p.entity_name;
      return;
    }
    try {
      const entity = await entityService.get(p.entity_id);
      entityName.value = entity.name ?? null;
    } catch {
      entityName.value = null;
    }
  }

  // =============================================================================
  // LIFECYCLE
  // =============================================================================

  onMounted(async () => {
    await patientStore.fetchPatient(patientId.value);
    await loadEvaluations(patientId.value);
    await loadEntityName();
  });

  watch(patientId, async (newId) => {
    if (newId) {
      await patientStore.fetchPatient(newId);
      await loadEvaluations(newId);
      await loadEntityName();
    }
  });

  onBeforeUnmount(() => {
    patientStore.clearCurrentPatient();
  });
</script>

<template>
  <div class="space-y-6">
    <ConfirmDialog />

    <!-- LOADING -->
    <div v-if="isLoading" class="space-y-4">
      <Skeleton width="60%" height="2rem" />
      <Skeleton width="40%" height="1rem" />
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <Skeleton height="12rem" class="lg:col-span-2" />
        <Skeleton height="12rem" />
      </div>
    </div>

    <!-- ERROR -->
    <Message v-else-if="error" :closable="false" severity="error">
      {{ error }}
    </Message>

    <!-- CONTENU -->
    <template v-else-if="patient">
      <!-- HEADER -->
      <div class="flex gap-2">
        <button
          v-if="patient.status === 'ACTIVE' && !draftEvaluation"
          class="new-eval-btn"
          @click="startNewEvaluation"
        >
          <ClipboardPlus :size="16" :stroke-width="1.8" />
          Nouvelle évaluation
        </button>

        <button v-if="patient.status === 'ACTIVE'" class="edit-btn" @click="openEditDialog">
          <Pencil :size="16" :stroke-width="1.8" />
          Modifier
        </button>

        <div v-if="patient.status === 'ACTIVE'" class="archive-group">
          <button class="archive-btn" @click="archivePatient">
            <Archive :size="16" :stroke-width="1.8" />
            Archiver
          </button>
          <span class="info-bubble-trigger">
            <Info :size="14" :stroke-width="1.8" />
            <span class="info-bubble">
              Archiver le dossier. Le patient ne sera plus visible dans les listes actives, mais ses
              données sont conservées et réactivables à tout moment.
            </span>
          </span>
        </div>

        <button
          v-else-if="patient.status === 'ARCHIVED' || patient.status === 'INACTIVE'"
          class="reactivate-btn"
          @click="reactivatePatient"
        >
          <RotateCcw :size="16" :stroke-width="1.8" />
          Réactiver
        </button>
      </div>

      <!-- GRILLE PRINCIPALE -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Colonne gauche (2/3) -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Brouillon en cours -->
          <EvaluationDraftProgress
            v-if="draftEvaluation"
            :draft="draftEvaluation"
            :patient-id="patientId"
          />

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
                  <p class="field-value text-display-uppercase">{{ patient.last_name || '—' }}</p>
                </div>
                <div>
                  <p class="field-label">Prénom</p>
                  <p class="field-value text-display-uppercase">{{ patient.first_name || '—' }}</p>
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
                    <a v-if="patient.phone" :href="`tel:${patient.phone}`" class="contact-link">
                      <Phone :size="14" :stroke-width="1.8" class="text-slate-400" />
                      {{ patient.phone }}
                    </a>
                    <span v-else class="text-slate-300">—</span>
                  </p>
                </div>
                <div>
                  <p class="field-label">Email</p>
                  <p class="field-value">
                    <a v-if="patient.email" :href="`mailto:${patient.email}`" class="contact-link">
                      <Mail :size="14" :stroke-width="1.8" class="text-slate-400" />
                      {{ patient.email }}
                    </a>
                    <span v-else class="text-slate-300">—</span>
                  </p>
                </div>
              </div>
            </template>
          </Card>

          <!-- Bilan clinique (S6) — visible uniquement si des scores existent -->
          <Card v-if="clinicalScores.length > 0">
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--pink">
                  <Activity :size="18" :stroke-width="1.8" />
                </div>
                Bilan clinique
                <span v-if="submittedEvaluations.length > 0" class="bilan-date">
                  {{ formatEvalDate(submittedEvaluations[0].evaluation_date) }}
                </span>
              </div>
            </template>
            <template #content>
              <div class="bilan-scores">
                <!-- GIR chip en premier -->
                <span
                  v-if="displayGir"
                  :class="{
                    'bilan-chip--gir-12': displayGir <= 2,
                    'bilan-chip--gir-34': displayGir > 2 && displayGir <= 4,
                    'bilan-chip--gir-56': displayGir > 4,
                  }"
                  class="bilan-chip bilan-chip--gir"
                >
                  GIR {{ displayGir }}
                </span>
                <!-- Score chips -->
                <span
                  v-for="(score, idx) in clinicalScores"
                  :key="idx"
                  :class="`bilan-chip--${score.severity}`"
                  class="bilan-chip"
                >
                  <span class="bilan-chip__dot" />
                  {{ score.label }}
                </span>
              </div>
              <!-- Lien vers le dialog -->
              <div class="bilan-footer">
                <button class="bilan-link" @click="openEvaluationDetail(submittedEvaluations[0])">
                  Voir l'évaluation complète
                  <Eye :size="14" :stroke-width="1.8" />
                </button>
              </div>
            </template>
          </Card>

          <!-- Évaluations (S3) -->
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
              <!-- Liste évaluations soumises/validées -->
              <div v-if="submittedEvaluations.length > 0" class="eval-list">
                <div
                  v-for="evaluation in submittedEvaluations"
                  :key="evaluation.id"
                  class="eval-list-item"
                  @click="openEvaluationDetail(evaluation)"
                >
                  <Tag
                    :value="getEvalStatusLabel(evaluation.status)"
                    :severity="getEvalStatusSeverity(evaluation.status)"
                    class="text-xs"
                  />
                  <div class="eval-list-meta">
                    <p class="eval-list-type">Évaluation AGGIR</p>
                    <p class="eval-list-date">{{ formatEvalDate(evaluation.evaluation_date) }}</p>
                  </div>
                  <div class="eval-list-gir">
                    <span class="eval-list-gir-label">GIR</span>
                    <span
                      v-if="evaluation.gir_score"
                      :class="{
                        'bg-red-100 text-red-700': evaluation.gir_score <= 2,
                        'bg-amber-100 text-amber-700':
                          evaluation.gir_score > 2 && evaluation.gir_score <= 4,
                        'bg-emerald-100 text-emerald-700': evaluation.gir_score > 4,
                      }"
                      class="text-xs font-bold px-2 py-0.5 rounded-full"
                    >
                      {{ evaluation.gir_score }}
                    </span>
                    <span v-else class="text-slate-300 text-xs">—</span>
                  </div>
                  <button class="eval-list-action" title="Voir l'évaluation">
                    <Eye :size="16" :stroke-width="1.8" />
                  </button>
                </div>
              </div>

              <!-- Aucune évaluation du tout -->
              <div v-else-if="evaluationCount === 0" class="eval-empty-state">
                <div class="eval-empty-icon">
                  <CircleDashed :size="36" :stroke-width="1.2" />
                </div>
                <p class="eval-empty-title">Aucune évaluation</p>
                <p class="eval-empty-hint">
                  Lancez une première évaluation AGGIR pour déterminer le niveau d'autonomie du
                  patient.
                </p>
              </div>

              <!-- Seulement un brouillon en cours -->
              <div v-else class="eval-empty-state">
                <div class="eval-empty-icon">
                  <Stethoscope :size="36" :stroke-width="1.2" />
                </div>
                <p class="eval-empty-title">Évaluation en cours de saisie</p>
                <p class="eval-empty-hint">
                  L'évaluation apparaîtra ici une fois soumise pour validation.
                </p>
              </div>
            </template>
          </Card>
        </div>

        <!-- Colonne droite (1/3) -->
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
                    :severity="getStatusConfig(patient.status).severity"
                  />
                </div>
                <Divider />
                <div>
                  <p class="field-label">Score GIR</p>
                  <p class="mt-1">
                    <span
                      v-if="getGirConfig(displayGir)"
                      :class="getGirConfig(displayGir)!.class"
                      class="text-xs font-semibold px-2.5 py-1 rounded-full"
                    >
                      {{ getGirConfig(displayGir)!.label }}
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
                    {{ entityName || patient.entity_name || `Entité #${patient.entity_id}` }}
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

          <!-- Sécurité -->
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

      <!-- S3 — Modal détail évaluation -->
      <EvaluationDetailDialog
        v-model:visible="showEvaluationModal"
        :evaluation="selectedEvaluation"
        :patient-name="fullName"
        @close="closeEvaluationModal"
      />

      <!-- Panel édition patient -->
      <PatientEditDialog
        :visible="editDialogVisible"
        :patient="patient"
        @update:visible="editDialogVisible = $event"
        @saved="onPatientSaved"
      />
    </template>
  </div>
</template>

<style scoped>
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
  .section-title {
    @apply flex items-center gap-2.5 text-base font-semibold text-slate-800;
  }
  .section-icon {
    @apply flex items-center justify-center flex-shrink-0;
    width: 2rem;
    height: 2rem;
    border-radius: 0.5rem;
  }
  .section-icon--blue {
    background: #eff6ff;
    color: #3b82f6;
  }
  .section-icon--teal {
    background: #f0fdfa;
    color: #0d9488;
  }
  .section-icon--amber {
    background: #fffbeb;
    color: #d97706;
  }
  .section-icon--slate {
    background: #f1f5f9;
    color: #475569;
  }
  .section-icon--emerald {
    background: #ecfdf5;
    color: #059669;
  }
  .section-icon--pink {
    background: #fdf2f8;
    color: #db2777;
  }
  .field-label {
    @apply text-slate-400 text-xs font-medium uppercase tracking-wide mb-0.5;
  }
  .field-value {
    @apply font-medium text-slate-800;
  }
  .contact-link {
    @apply inline-flex items-center gap-1.5 text-teal-600 hover:text-teal-800 transition-colors;
  }

  /* S6 — Bilan clinique */
  .bilan-date {
    @apply text-xs font-normal text-slate-400 ml-auto;
  }
  .bilan-scores {
    @apply flex flex-wrap gap-2;
  }
  .bilan-chip {
    @apply inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg;
    border: 1px solid transparent;
  }
  .bilan-chip__dot {
    @apply w-1.5 h-1.5 rounded-full flex-shrink-0;
  }
  .bilan-chip--alert {
    background: #fef2f2;
    color: #dc2626;
    border-color: #fecaca;
  }
  .bilan-chip--alert .bilan-chip__dot {
    background: #ef4444;
  }
  .bilan-chip--warning {
    background: #fffbeb;
    color: #d97706;
    border-color: #fde68a;
  }
  .bilan-chip--warning .bilan-chip__dot {
    background: #f59e0b;
  }
  .bilan-chip--ok {
    background: #f0fdf4;
    color: #16a34a;
    border-color: #bbf7d0;
  }
  .bilan-chip--ok .bilan-chip__dot {
    background: #22c55e;
  }
  .bilan-chip--info {
    background: #eff6ff;
    color: #2563eb;
    border-color: #bfdbfe;
  }
  .bilan-chip--info .bilan-chip__dot {
    background: #3b82f6;
  }
  .bilan-chip--gir {
    @apply font-bold border-none text-white;
  }
  .bilan-chip--gir-12 {
    background: #ef4444;
  }
  .bilan-chip--gir-34 {
    background: #f59e0b;
  }
  .bilan-chip--gir-56 {
    background: #22c55e;
  }
  .bilan-footer {
    @apply flex justify-end mt-3 pt-3 border-t border-slate-100;
  }
  .bilan-link {
    @apply inline-flex items-center gap-1.5 text-xs font-medium text-teal-600 cursor-pointer;
    background: none;
    border: none;
    transition: color 0.15s ease;
  }
  .bilan-link:hover {
    @apply text-teal-800;
  }

  .archive-btn {
    @apply inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-slate-500 border border-slate-200 cursor-pointer;
    background: white;
    transition: all 0.2s ease;
  }
  .archive-btn:hover {
    @apply text-red-600 border-red-200;
    background: #fef2f2;
  }
  .reactivate-btn {
    @apply inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-emerald-600 border border-emerald-200 cursor-pointer;
    background: #ecfdf5;
    transition: all 0.2s ease;
  }
  .reactivate-btn:hover {
    @apply border-emerald-300;
    background: #d1fae5;
  }
  .new-eval-btn {
    @apply inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold text-teal-700 cursor-pointer;
    background: #f0fdfa;
    border: 1.5px solid #99f6e4;
    transition: all 0.2s ease;
  }
  .new-eval-btn:hover {
    background: #ccfbf1;
    border-color: #5eead4;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
  }
  .edit-btn {
    @apply inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium text-slate-600 cursor-pointer;
    background: white;
    border: 1.5px solid #e2e8f0;
    transition: all 0.2s ease;
  }
  .edit-btn:hover {
    @apply text-teal-700;
    background: #f0fdfa;
    border-color: #99f6e4;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.08);
  }

  /* Évaluations — état vide */
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

  /* S3 — Liste évaluations soumises */
  .eval-list {
    @apply divide-y divide-slate-100;
  }
  .eval-list-item {
    @apply flex items-center gap-3 py-3 px-1 cursor-pointer rounded-lg;
    transition: background 0.15s ease;
  }
  .eval-list-item:hover {
    background: #f8fafc;
  }
  .eval-list-item:first-child {
    padding-top: 0;
  }
  .eval-list-meta {
    @apply flex-1 min-w-0;
  }
  .eval-list-type {
    @apply text-sm font-semibold text-slate-700;
  }
  .eval-list-date {
    @apply text-xs text-slate-400 mt-0.5;
  }
  .eval-list-gir {
    @apply flex flex-col items-center gap-0.5;
  }
  .eval-list-gir-label {
    @apply text-slate-400 uppercase tracking-wider;
    font-size: 9px;
    font-weight: 600;
  }
  .eval-list-action {
    @apply flex items-center justify-center w-8 h-8 rounded-lg text-teal-500 cursor-pointer border-0;
    background: transparent;
    transition: all 0.15s ease;
  }
  .eval-list-action:hover {
    background: #f0fdfa;
    color: #0d9488;
  }

  /* GIR non évalué */
  .gir-not-evaluated {
    @apply inline-flex items-center gap-1.5 text-sm text-slate-400;
  }

  /* Sécurité */
  .security-item {
    @apply flex items-center gap-2;
  }
  .security-item--ok {
    @apply text-emerald-600;
  }
  .security-item--pending {
    @apply text-slate-400;
  }

  /* Archiver + info */
  .archive-group {
    @apply flex items-center gap-1;
  }
  .info-bubble-trigger {
    @apply relative inline-flex items-center justify-center text-slate-400 cursor-help;
    padding: 0.25rem;
  }
  .info-bubble-trigger:hover {
    @apply text-slate-600;
  }
  .info-bubble {
    @apply absolute z-50 hidden w-64 text-xs text-slate-600 leading-relaxed rounded-xl p-3;
    top: 50%;
    left: calc(100% + 0.75rem);
    transform: translateY(-50%);
    background: white;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    pointer-events: none;
  }
  .info-bubble::after {
    content: '';
    position: absolute;
    top: 50%;
    right: 100%;
    transform: translateY(-50%);
    border: 6px solid transparent;
    border-right-color: white;
  }
  .info-bubble-trigger:hover .info-bubble {
    display: block;
  }
</style>