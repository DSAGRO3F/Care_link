<script setup lang="ts">
  /**
   * PatientDetailPage.vue — Dossier patient (composant partagé admin / soins)
   * Chemin : frontend/src/pages/shared/patient/PatientDetailPage.vue
   *
   * Composant unique référencé par router/routes/app.ts (B48 Palier 4).
   * Issu de la fusion de PatientDetailPage_admin.vue (1357 L) et
   * PatientDetailPage_soins.vue (1542 L) — B48 Palier 2, Lot B.
   *
   * Structure canonique = shell à onglets Soins (bannière enrichie + 6 onglets
   * PrimeVue 4). Les 3 extras admin y sont re-logés :
   *  (a) actions CRUD       → boutons permission-gated dans la bannière
   *  (b) clinicalScores (S6) → section « Bilan clinique » de l'onglet Synthèse
   *  (c) EvaluationDraftProgress → tête de l'onglet Évaluations
   *
   * Chargement : Approche 3 — patient = ref() + patientService.getById +
   * onglets lazy. Le store `patients` (currentPatient) n'est PAS consommé ici.
   *
   * Navigation espace-aware : route.path.startsWith('/soins') (pattern A2).
   * Rafraîchissement post-CRUD : patch local de `patient.value` depuis la
   * réponse de la mutation (aucun re-getById).
   */
  import { ref, onMounted, computed, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { carePlanService, patientService } from '@/services';
  import { useAuthStore } from '@/stores';
  import { formatEuro, formatDate as formatDateUtil } from '@/utils/format';
  import { computeAge } from '@/utils/date';
  import type {
    PatientResponse,
    PatientEvaluationResponse,
    PatientVitalsResponse,
    CarePlanSummary,
  } from '@/types';
  import {
    PLAN_STATUS_LABELS,
    PLAN_STATUS_SEVERITY,
    REVISION_REASON_LABELS,
    PATIENT_STATUS_LABELS,
    EVALUATION_STATUS_LABELS,
    EVALUATION_STATUS_SEVERITY,
    getGirLevel,
  } from '@/types';

  // PrimeVue 4 — API Tabs native
  import Tabs from 'primevue/tabs';
  import TabList from 'primevue/tablist';
  import Tab from 'primevue/tab';
  import TabPanels from 'primevue/tabpanels';
  import TabPanel from 'primevue/tabpanel';
  import Button from 'primevue/button';
  import Tag from 'primevue/tag';
  import Skeleton from 'primevue/skeleton';
  import DataTable from 'primevue/datatable';
  import Column from 'primevue/column';
  import ConfirmDialog from 'primevue/confirmdialog';
  import { useConfirm } from 'primevue/useconfirm';

  // Lucide — icônes onglets, chips bannière, bilan clinique
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
    NotebookPen,
    Eye,
  } from 'lucide-vue-next';

  // Composants évaluation + édition patient
  import EvaluationDetailDialog from '@/components/evaluation/EvaluationDetailDialog.vue';
  import EvaluationDraftProgress from '@/components/evaluation/EvaluationDraftProgress.vue';
  import type { EvaluationDraft } from '@/components/evaluation/EvaluationDraftProgress.vue';
  import PatientEditDialog from '@/components/patients/PatientEditDialog.vue';

  const route = useRoute();
  const router = useRouter();
  const authStore = useAuthStore();
  const confirm = useConfirm();

  const props = defineProps<{
    id: string;
  }>();

  // ============================================================
  // ESPACE COURANT — navigation espace-aware (pattern A2, Lot A)
  // ============================================================

  /**
   * Le composant est référencé par deux route files. L'espace courant se
   * déduit du préfixe d'URL ; il pilote les noms de route cibles (`soins-*`
   * vs `admin-*`) et la cible de redirection en cas d'erreur de chargement.
   */
  const isSoinsSpace = computed(() => route.path.startsWith('/soins'));

  // ============================================================
  // ÉTAT
  // ============================================================

  const patient = ref<PatientResponse | null>(null);
  const isLoading = ref(true);

  /** v4 : activeTab = valeur string de l'onglet actif (API native Tabs). */
  const activeTab = ref('synthese');

  // État évaluations
  const evaluations = ref<PatientEvaluationResponse[]>([]);
  const evaluationsLoading = ref(false);
  const evaluationsLoaded = ref(false);

  // État plans d'aide (F7/F8)
  const carePlans = ref<CarePlanSummary[]>([]);
  const carePlansLoading = ref(false);
  const carePlansLoaded = ref(false);
  const carePlansError = ref<string | null>(null);
  /** F8b — Toggle expand inline de la DataTable historique. */
  const historiqueExpanded = ref(false);

  // État constantes vitales (synthèse)
  const latestVitals = ref<Record<string, PatientVitalsResponse | null>>({
    TA_SYS: null,
    FC: null,
    TEMP: null,
    SPO2: null,
  });
  const vitalsLoading = ref(false);
  const vitalsLoaded = ref(false);

  // Modal détail évaluation
  const showEvaluationModal = ref(false);
  const selectedEvaluation = ref<PatientEvaluationResponse | null>(null);
  const evaluationDetailLoading = ref(false);

  // Panel d'édition patient (extra admin re-logé)
  const editDialogVisible = ref(false);

  // Valeurs valides pour les onglets (validation du paramètre URL ?tab=)
  const VALID_TABS = [
    'synthese',
    'evaluations',
    'plans-aide',
    'constantes',
    'liaison',
    'documents',
  ];

  // ============================================================
  // PERMISSIONS — gating Option A (masquer-vs-griser)
  // ============================================================

  /**
   * Modifier le dossier patient. Action CRUD sur un objet visible : le bouton
   * est toujours rendu (quand le statut le permet) et se grise + tooltip si la
   * permission manque — il ne se masque jamais (Arbitrage 3 du plan Palier 2).
   */
  const canEditPatient = computed(() => authStore.hasPermission('PATIENT_EDIT'));

  /**
   * Archiver / réactiver le dossier patient. Gating provisoire sur ADMIN_FULL
   * faute de code dédié — la gravure d'un `PATIENT_ARCHIVE` est tracée en
   * backlog Palier 2-bis.
   */
  const canArchivePatient = computed(() => authStore.hasPermission('ADMIN_FULL'));

  // ============================================================
  // COMPUTED — Identité & dérivés patient
  // ============================================================

  /** Âge calculé depuis la date de naissance (algo calendaire consolidé). */
  const age = computed(() => computeAge(patient.value?.birth_date));

  /** Initiales du patient (avatar bannière). */
  const initials = computed(() => {
    if (!patient.value) return '';
    return (patient.value.first_name?.[0] || '') + (patient.value.last_name?.[0] || '');
  });

  /** Nom complet — utilisé pour les libellés de dialog. */
  const fullName = computed(() => {
    if (!patient.value) return '';
    const parts = [patient.value.first_name, patient.value.last_name].filter(Boolean);
    return parts.join(' ') || 'Patient sans nom';
  });

  /** Classe CSS du badge GIR (bannière) — niveau dérivé du helper consolidé. */
  const girBadgeClass = computed(() => {
    switch (getGirLevel(patient.value?.current_gir)) {
      case 'severe':
        return 'patient-gir-badge--severe';
      case 'moderate':
        return 'patient-gir-badge--moderate';
      case 'light':
        return 'patient-gir-badge--light';
      default:
        return '';
    }
  });

  /** Label FR du statut patient — via le dictionnaire consolidé. */
  const statusLabel = computed(() => {
    const status = patient.value?.status;
    return status ? PATIENT_STATUS_LABELS[status] : '';
  });

  // ============================================================
  // COMPUTED — Évaluations
  // ============================================================

  /** Dernière évaluation, toutes confondues (tri date desc). */
  const latestEvaluation = computed(() => {
    if (!evaluations.value.length) return null;
    return evaluations.value
      .slice()
      .sort(
        (a, b) => new Date(b.evaluation_date).getTime() - new Date(a.evaluation_date).getTime(),
      )[0];
  });

  /**
   * Évaluations soumises / validées (tout sauf DRAFT et IN_PROGRESS),
   * triées par date desc puis id desc. Alimente le bilan clinique (S6).
   */
  const submittedEvaluations = computed(() =>
    evaluations.value
      .filter((e) => e.status !== 'DRAFT' && e.status !== 'IN_PROGRESS')
      .sort((a, b) => {
        const dateCompare =
          new Date(b.evaluation_date).getTime() - new Date(a.evaluation_date).getTime();
        if (dateCompare !== 0) return dateCompare;
        return b.id - a.id;
      }),
  );

  /**
   * Brouillon d'évaluation actif (DRAFT / IN_PROGRESS) — alimente
   * EvaluationDraftProgress en tête de l'onglet Évaluations.
   */
  const draftEvaluation = computed<EvaluationDraft | null>(
    () =>
      evaluations.value.find((e) => e.status === 'DRAFT' || e.status === 'IN_PROGRESS') ?? null,
  );

  /** Au moins une évaluation existe — prérequis pour le plan d'aide. */
  const hasValidatedEvaluation = computed(() => evaluations.value.length > 0);

  /** Dernière évaluation validée — suggestion active. */
  const latestEvalIsValidated = computed(() => latestEvaluation.value?.status === 'VALIDATED');

  /** Bouton plan d'aide visible ? (patient actif + éval + permission). */
  const canShowCarePlanButton = computed(
    () =>
      patient.value?.status === 'ACTIVE' &&
      hasValidatedEvaluation.value &&
      authStore.canCreateCarePlan,
  );

  // ============================================================
  // COMPUTED — Bilan clinique (S6) : scores extraits de l'évaluation
  // ============================================================

  interface ClinicalScore {
    label: string;
    severity: 'alert' | 'warning' | 'ok' | 'info';
  }

  /**
   * GIR à afficher : patient.current_gir si renseigné, sinon le gir_score de
   * la dernière évaluation soumise. Alimente la chip GIR du bilan clinique.
   */
  const displayGir = computed<number | null>(() => {
    if (patient.value?.current_gir) return patient.value.current_gir;
    return submittedEvaluations.value[0]?.gir_score ?? null;
  });

  /**
   * Extrait et catégorise les scores cliniques depuis
   * evaluation_data.sante.blocs[].test[] de la dernière évaluation soumise.
   * Retourne un tableau de chips colorées (vert / ambre / rouge).
   */
  const clinicalScores = computed((): ClinicalScore[] => {
    const latest = submittedEvaluations.value[0];
    if (!latest?.evaluation_data) return [];

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

  // ============================================================
  // COMPUTED — Plans d'aide (F8a / F8b)
  // ============================================================

  /**
   * F8a — Plans en cours : tout sauf COMPLETED et CANCELLED.
   * Tri clinique : ACTIVE > SUSPENDED > PENDING_VALIDATION > DRAFT (révision)
   * > DRAFT (ex nihilo). À statut égal, tri par `start_date` desc.
   */
  const plansEnCours = computed<CarePlanSummary[]>(() => {
    const STATUS_ORDER: Record<string, number> = {
      ACTIVE: 0,
      SUSPENDED: 1,
      PENDING_VALIDATION: 2,
      DRAFT: 3,
      COMPLETED: 99,
      CANCELLED: 99,
    };
    return carePlans.value
      .filter((p) => p.status !== 'COMPLETED' && p.status !== 'CANCELLED')
      .slice()
      .sort((a, b) => {
        const orderA = STATUS_ORDER[a.status] ?? 50;
        const orderB = STATUS_ORDER[b.status] ?? 50;
        if (orderA !== orderB) return orderA - orderB;
        // À statut égal : DRAFT-révision (supersedes != null) prioritaire
        if (a.status === 'DRAFT' && b.status === 'DRAFT') {
          const aIsRev = a.supersedes_plan_id !== null;
          const bIsRev = b.supersedes_plan_id !== null;
          if (aIsRev !== bIsRev) return aIsRev ? -1 : 1;
        }
        return new Date(b.start_date).getTime() - new Date(a.start_date).getTime();
      });
  });

  /** F8b — Plans historiques : COMPLETED + CANCELLED, triés par start_date desc. */
  const plansHistorique = computed<CarePlanSummary[]>(() => {
    return carePlans.value
      .filter((p) => p.status === 'COMPLETED' || p.status === 'CANCELLED')
      .slice()
      .sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime());
  });

  // ============================================================
  // WIDGETS CONSTANTES — Configuration & helpers
  // ============================================================

  interface VitalWidgetConfig {
    key: string;
    label: string;
    unit: string;
    icon: string;
  }

  const vitalWidgets: VitalWidgetConfig[] = [
    { key: 'TA_SYS', label: 'Tension', unit: 'mmHg', icon: 'pi pi-heart' },
    { key: 'FC', label: 'Fréq. cardiaque', unit: 'bpm', icon: 'pi pi-bolt' },
    { key: 'TEMP', label: 'Température', unit: '°C', icon: 'pi pi-sun' },
    { key: 'SPO2', label: 'Saturation O2', unit: '%', icon: 'pi pi-wave-pulse' },
  ];

  /** Classe de couleur du widget selon l'état de la mesure. */
  function getVitalStatusClass(vital: PatientVitalsResponse | null): string {
    if (!vital) return 'vital-widget--empty';
    if (vital.is_critical) return 'vital-widget--critical';
    if (vital.is_abnormal) return 'vital-widget--warning';
    return 'vital-widget--ok';
  }

  /** Valeur formatée de la constante. */
  function formatVitalValue(vital: PatientVitalsResponse | null): string {
    if (!vital) return '\u2014';
    return String(vital.value);
  }

  /** Date relative de la mesure. */
  function formatVitalDate(vital: PatientVitalsResponse | null): string {
    if (!vital?.measured_at) return '';
    const measured = new Date(vital.measured_at);
    const now = new Date();
    const diffMs = now.getTime() - measured.getTime();
    const diffH = Math.floor(diffMs / (1000 * 60 * 60));
    const diffD = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffH < 1) return "À l'instant";
    if (diffH < 24) return 'Il y a ' + diffH + 'h';
    if (diffD === 1) return 'Hier';
    if (diffD < 7) return 'Il y a ' + diffD + 'j';
    return measured.toLocaleDateString('fr-FR');
  }

  // ============================================================
  // HELPERS D'AFFICHAGE
  // ============================================================

  /**
   * Date au format court (« 12/01/2026 ») — délègue à formatDate de utils,
   * avec tiret « — » si la date est absente.
   */
  const formatDate = (dateStr: string | null | undefined): string =>
    formatDateUtil(dateStr, { emptyValue: '—' });

  /**
   * F8a — Accent visuel d'une card plan en cours : classes Tailwind pour la
   * bordure gauche + le badge statut, et libellé FR contextualisé.
   */
  function getCarePlanCardAccent(plan: CarePlanSummary): {
    borderClass: string;
    badgeClass: string;
    label: string;
  } {
    const isRevisionDraft = plan.status === 'DRAFT' && plan.supersedes_plan_id !== null;

    if (plan.status === 'ACTIVE') {
      return {
        borderClass: 'border-l-teal-500',
        badgeClass: 'bg-teal-100 text-teal-700',
        label: PLAN_STATUS_LABELS.ACTIVE,
      };
    }
    if (plan.status === 'SUSPENDED') {
      return {
        borderClass: 'border-l-amber-500',
        badgeClass: 'bg-amber-100 text-amber-700',
        label: PLAN_STATUS_LABELS.SUSPENDED,
      };
    }
    if (plan.status === 'PENDING_VALIDATION') {
      return {
        borderClass: 'border-l-violet-500',
        badgeClass: 'bg-violet-100 text-violet-700',
        label: PLAN_STATUS_LABELS.PENDING_VALIDATION,
      };
    }
    if (isRevisionDraft) {
      return {
        borderClass: 'border-l-teal-300',
        badgeClass: 'bg-teal-50 text-teal-600',
        label: 'Brouillon de révision',
      };
    }
    return {
      borderClass: 'border-l-slate-400',
      badgeClass: 'bg-slate-100 text-slate-600',
      label: 'Brouillon',
    };
  }

  // ============================================================
  // CHARGEMENT DES DONNÉES
  // ============================================================

  /** Initialiser l'onglet depuis le paramètre URL ?tab= */
  function initTab() {
    const tabParam = route.query.tab as string;
    if (tabParam && VALID_TABS.includes(tabParam)) {
      activeTab.value = tabParam;
    }
  }

  /** Charger les dernières constantes vitales. */
  async function loadLatestVitals() {
    if (vitalsLoaded.value || vitalsLoading.value) return;

    vitalsLoading.value = true;
    const patientId = Number(props.id);
    const vitalTypes = ['TA_SYS', 'FC', 'TEMP', 'SPO2'];

    try {
      const results = await Promise.allSettled(
        vitalTypes.map((type) => patientService.getLatestVital(patientId, type)),
      );

      results.forEach((result, index) => {
        latestVitals.value[vitalTypes[index]] = result.status === 'fulfilled' ? result.value : null;
      });
      vitalsLoaded.value = true;
    } catch (error) {
      if (import.meta.env.DEV) console.warn('[PatientDetail] Erreur chargement vitals:', error);
    } finally {
      vitalsLoading.value = false;
    }
  }

  /** Charger les évaluations du patient. */
  async function loadEvaluations() {
    if (evaluationsLoaded.value || evaluationsLoading.value) return;

    evaluationsLoading.value = true;
    try {
      const response = await patientService.getEvaluations(Number(props.id));
      evaluations.value = response.items || [];
      evaluationsLoaded.value = true;
    } catch (error) {
      if (import.meta.env.DEV)
        console.error('[PatientDetail] Erreur chargement évaluations:', error);
    } finally {
      evaluationsLoading.value = false;
    }
  }

  /** Charger les plans d'aide du patient (lazy, déclenché par l'onglet). */
  async function loadCarePlans() {
    if (carePlansLoaded.value || carePlansLoading.value) return;

    carePlansLoading.value = true;
    carePlansError.value = null;
    try {
      const response = await carePlanService.list(1, 50, { patient_id: Number(props.id) });
      carePlans.value = response.items || [];
      carePlansLoaded.value = true;
    } catch (error) {
      if (import.meta.env.DEV)
        console.error("[PatientDetail] Erreur chargement plans d'aide:", error);
      carePlansError.value = "Impossible de charger les plans d'aide.";
    } finally {
      carePlansLoading.value = false;
    }
  }

  // ============================================================
  // ACTIONS — Évaluation
  // ============================================================

  /** Ouvrir le modal de détail d'une évaluation. */
  async function openEvaluationDetail(evaluation: PatientEvaluationResponse) {
    if (evaluation.evaluation_data && Object.keys(evaluation.evaluation_data).length > 0) {
      selectedEvaluation.value = evaluation;
      showEvaluationModal.value = true;
      return;
    }

    evaluationDetailLoading.value = true;
    try {
      const fullEvaluation = await patientService.getEvaluation(Number(props.id), evaluation.id);
      selectedEvaluation.value = fullEvaluation;
      showEvaluationModal.value = true;
    } catch (error) {
      if (import.meta.env.DEV)
        console.error('[PatientDetail] Erreur chargement détail évaluation:', error);
    } finally {
      evaluationDetailLoading.value = false;
    }
  }

  function closeEvaluationModal() {
    showEvaluationModal.value = false;
    setTimeout(() => {
      selectedEvaluation.value = null;
    }, 300);
  }

  // ============================================================
  // ACTIONS — Navigation (espace-aware, pattern A2)
  // ============================================================

  function callPhone(phone: string) {
    window.location.href = 'tel:' + phone;
  }

  /** Lancer une nouvelle évaluation AGGIR (le wizard vit côté Soins). */
  function startNewEvaluation() {
    router.push({
      name: 'soins-evaluation-create',
      params: { patientId: Number(props.id) },
    });
  }

  /** Construire un plan d'aide — route cible selon l'espace courant. */
  function goToCarePlan() {
    router.push({
      name: isSoinsSpace.value ? 'soins-care-plans-create' : 'admin-care-plans-create',
      query: {
        patient_id: props.id,
        entity_id: patient.value?.entity_id ? String(patient.value.entity_id) : undefined,
        from_evaluation: latestEvaluation.value?.id
          ? String(latestEvaluation.value.id)
          : undefined,
      },
    });
  }

  /** Ouvrir le détail d'un plan d'aide — route cible selon l'espace courant. */
  function goToCarePlanDetail(id: number) {
    void router.push({
      name: isSoinsSpace.value ? 'soins-care-plans-detail' : 'admin-care-plans-detail',
      params: { id: String(id) },
    });
  }

  // ============================================================
  // ACTIONS — CRUD patient (extra admin re-logé, permission-gated)
  // ============================================================

  function openEditDialog() {
    editDialogVisible.value = true;
  }

  /**
   * Patch local post-édition (convention #52) : PatientEditDialog émet le
   * patient mis à jour, on remplace le ref local sans re-getById.
   */
  function onPatientSaved(updated: PatientResponse) {
    patient.value = updated;
  }

  /**
   * Archiver le dossier. Rafraîchissement par patch local : la réponse du
   * PATCH porte le PatientResponse à jour, on remplace le ref directement.
   * Note : aucun effet de bord hors mutation (évaluations / plans d'aide ne
   * bougent pas) → re-getById superflu. Bascule possible en backlog si la
   * prod révèle un effet de bord.
   */
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
        try {
          const updated = await patientService.update(Number(props.id), { status: 'ARCHIVED' });
          patient.value = updated;
        } catch (error) {
          if (import.meta.env.DEV)
            console.error('[PatientDetail] Erreur archivage patient:', error);
        }
      },
    });
  }

  /** Réactiver le dossier — patch local depuis la réponse du PATCH. */
  async function reactivatePatient() {
    try {
      const updated = await patientService.update(Number(props.id), { status: 'ACTIVE' });
      patient.value = updated;
    } catch (error) {
      if (import.meta.env.DEV)
        console.error('[PatientDetail] Erreur réactivation patient:', error);
    }
  }

  // ============================================================
  // LIFECYCLE
  // ============================================================

  /**
   * Charge le patient et les données de l'onglet actif. Réinitialise les
   * flags lazy en amont — réutilisable au montage ET sur changement de `id`
   * (le composant partagé peut être réutilisé d'une route patient à l'autre).
   */
  async function initPatient() {
    isLoading.value = true;

    // Réinitialisation des états lazy (changement de patient)
    evaluations.value = [];
    evaluationsLoaded.value = false;
    carePlans.value = [];
    carePlansLoaded.value = false;
    carePlansError.value = null;
    historiqueExpanded.value = false;
    vitalsLoaded.value = false;
    latestVitals.value = { TA_SYS: null, FC: null, TEMP: null, SPO2: null };

    try {
      patient.value = await patientService.getById(Number(props.id));

      // Évaluations toujours chargées (synthèse + bilan clinique en dépendent)
      await loadEvaluations();

      // Données complémentaires de l'onglet actif
      if (activeTab.value === 'synthese') await loadLatestVitals();
      if (activeTab.value === 'plans-aide') await loadCarePlans();
    } catch (error) {
      if (import.meta.env.DEV) console.error('[PatientDetail] Erreur chargement patient:', error);
      router.push(isSoinsSpace.value ? '/soins/patients' : '/admin/patients');
    } finally {
      isLoading.value = false;
    }
  }

  onMounted(() => {
    initTab();
    initPatient();
  });

  /** Le composant partagé est réutilisable entre deux routes patient. */
  watch(
    () => props.id,
    () => {
      initPatient();
    },
  );

  // Sync URL + chargement lazy par onglet
  watch(activeTab, async (newTab) => {
    router.replace({ query: { ...route.query, tab: newTab } });

    if (newTab === 'synthese') await loadLatestVitals();
    if (newTab === 'evaluations') await loadEvaluations();
    if (newTab === 'plans-aide') await loadCarePlans();
  });
</script>

<template>
  <div class="patient-detail">
    <ConfirmDialog />

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
            :class="{ 'patient-avatar__status--active': patient.status === 'ACTIVE' }"
            class="patient-avatar__status"
          />
        </div>

        <!-- Identité + chips info -->
        <div class="patient-banner__identity">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="patient-banner__name text-display-uppercase">
              {{ patient.first_name }} {{ patient.last_name }}
            </h1>

            <!-- Badge GIR -->
            <span v-if="patient.current_gir" :class="girBadgeClass" class="patient-gir-badge">
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
            <span v-if="patient.address" :title="patient.address" class="patient-chip">
              <MapPin :size="13" class="patient-chip__icon" />
              <span class="patient-chip__truncate">{{ patient.address }}</span>
            </span>
          </div>
        </div>

        <!-- Actions rapides -->
        <!-- Le bouton « Nouveau plan d'aide » a été retiré de la bannière     -->
        <!-- (doublon avec l'onglet Plans d'aide + suggestion Synthèse — B54). -->
        <!-- Les actions CRUD (Modifier / Archiver / Réactiver) sont des       -->
        <!-- extras admin re-logés ici, permission-gated (Option A) :          -->
        <!-- objet visible → bouton grisé + tooltip, jamais masqué.            -->
        <div class="patient-banner__actions">
          <Button
            v-if="patient.status === 'ACTIVE' && !draftEvaluation"
            label="Nouvelle évaluation"
            icon="pi pi-plus"
            size="small"
            @click="startNewEvaluation"
          />
          <Button
            label="Constantes"
            icon="pi pi-chart-line"
            size="small"
            variant="outlined"
            @click="activeTab = 'constantes'"
          />

          <!-- Modifier — gated PATIENT_EDIT -->
          <span
            v-if="patient.status === 'ACTIVE'"
            v-tooltip.bottom="
              canEditPatient ? undefined : 'Permission requise : modification du patient'
            "
          >
            <Button
              :disabled="!canEditPatient"
              label="Modifier"
              icon="pi pi-pencil"
              size="small"
              variant="outlined"
              @click="openEditDialog"
            />
          </span>

          <!-- Archiver — gated ADMIN_FULL -->
          <span
            v-if="patient.status === 'ACTIVE'"
            v-tooltip.bottom="
              canArchivePatient ? undefined : 'Permission requise : archivage du patient'
            "
          >
            <Button
              :disabled="!canArchivePatient"
              label="Archiver"
              icon="pi pi-inbox"
              size="small"
              severity="danger"
              variant="outlined"
              @click="archivePatient"
            />
          </span>

          <!-- Réactiver — gated ADMIN_FULL -->
          <span
            v-else-if="patient.status === 'ARCHIVED' || patient.status === 'INACTIVE'"
            v-tooltip.bottom="
              canArchivePatient ? undefined : 'Permission requise : réactivation du patient'
            "
          >
            <Button
              :disabled="!canArchivePatient"
              label="Réactiver"
              icon="pi pi-replay"
              size="small"
              severity="success"
              variant="outlined"
              @click="reactivatePatient"
            />
          </span>
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
        <Tab value="plans-aide">
          <NotebookPen :size="14" :stroke-width="1.8" class="tab-icon" />
          Plans d'aide
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

              <div v-if="vitalsLoading" class="vital-grid">
                <div v-for="n in 4" :key="n" class="vital-widget vital-widget--empty">
                  <Skeleton width="60%" height="1rem" class="mb-2" />
                  <Skeleton width="40%" height="2rem" />
                </div>
              </div>

              <div v-else class="vital-grid">
                <div
                  v-for="config in vitalWidgets"
                  :key="config.key"
                  :class="getVitalStatusClass(latestVitals[config.key])"
                  class="vital-widget"
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

            <!-- Bilan clinique (S6) — extra admin re-logé en Synthèse.       -->
            <!-- Visible uniquement si des scores ont été extraits.            -->
            <section v-if="clinicalScores.length > 0" class="mb-6">
              <h3 class="tab-section-title bilan-title">
                Bilan clinique
                <span v-if="submittedEvaluations.length > 0" class="bilan-date">
                  {{ formatDate(submittedEvaluations[0].evaluation_date) }}
                </span>
              </h3>
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
              <div class="bilan-footer">
                <button
                  class="bilan-link"
                  @click="openEvaluationDetail(submittedEvaluations[0])"
                >
                  Voir l'évaluation complète
                  <Eye :size="14" :stroke-width="1.8" />
                </button>
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
                          :value="EVALUATION_STATUS_LABELS[latestEvaluation.status]"
                          :severity="EVALUATION_STATUS_SEVERITY[latestEvaluation.status]"
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

                <!-- Suggestion plan d'aide post-évaluation -->
                <div
                  v-if="canShowCarePlanButton && latestEvalIsValidated"
                  class="synthese-info-card synthese-info-card--suggestion"
                  @click="goToCarePlan"
                >
                  <FileText :size="16" class="synthese-info-card__icon" />
                  <div>
                    <p class="synthese-info-card__label">Plan d'aide</p>
                    <p class="synthese-info-card__value synthese-info-card__value--accent">
                      Évaluation validée — Construire le plan d'aide →
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
            <!-- Brouillon en cours (extra admin re-logé) -->
            <EvaluationDraftProgress
              v-if="draftEvaluation"
              :draft="draftEvaluation"
              :patient-id="Number(id)"
              class="mb-4"
            />

            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">Évaluations AGGIR</h3>
              <Button
                v-if="patient && patient.status === 'ACTIVE' && !draftEvaluation"
                label="Nouvelle évaluation"
                icon="pi pi-plus"
                size="small"
                @click="startNewEvaluation"
              />
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
              class="p-datatable-sm"
              stripedRows
            >
              <Column field="evaluation_date" header="Date" sortable>
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  {{ formatDate(data.evaluation_date) }}
                </template>
              </Column>

              <Column field="gir_score" header="GIR" sortable>
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  <span
                    v-if="data.gir_score"
                    :class="{
                      'patient-gir-badge--severe': data.gir_score <= 2,
                      'patient-gir-badge--moderate': data.gir_score > 2 && data.gir_score <= 4,
                      'patient-gir-badge--light': data.gir_score > 4,
                    }"
                    class="patient-gir-badge"
                  >
                    GIR {{ data.gir_score }}
                  </span>
                  <span v-else class="text-slate-400">-</span>
                </template>
              </Column>

              <Column field="status" header="Statut" sortable>
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  <Tag
                    :value="EVALUATION_STATUS_LABELS[data.status] ?? data.status"
                    :severity="EVALUATION_STATUS_SEVERITY[data.status]"
                  />
                </template>
              </Column>

              <Column field="completion_percent" header="Complétion">
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  <div class="flex items-center gap-2">
                    <div class="w-20 bg-slate-200 rounded-full h-2">
                      <div
                        :style="{ width: (data.completion_percent || 0) + '%' }"
                        class="bg-teal-500 h-2 rounded-full transition-all"
                      />
                    </div>
                    <span class="text-sm text-slate-600">
                      {{ data.completion_percent || 0 }}%
                    </span>
                  </div>
                </template>
              </Column>

              <Column field="validated_at" header="Validation">
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  <span v-if="data.validated_at" class="text-emerald-600 font-medium">
                    {{ formatDate(data.validated_at) }}
                  </span>
                  <span v-else class="text-slate-400">En attente</span>
                </template>
              </Column>

              <Column header="Actions" style="width: 100px">
                <template #body="{ data }: { data: PatientEvaluationResponse }">
                  <Button
                    :loading="evaluationDetailLoading && selectedEvaluation?.id === data.id"
                    icon="pi pi-eye"
                    size="small"
                    variant="text"
                    title="Voir l'évaluation"
                    rounded
                    @click="openEvaluationDetail(data)"
                  />
                  <Button
                    v-if="data.status === 'DRAFT'"
                    icon="pi pi-pencil"
                    size="small"
                    variant="text"
                    title="Modifier"
                    rounded
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

        <!-- ── Plans d'aide (F8a + F8b) ───────────────────────────────── -->
        <TabPanel value="plans-aide">
          <div class="tab-content">
            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">Plans d'aide</h3>
              <Button
                v-if="canShowCarePlanButton"
                label="Nouveau plan d'aide"
                icon="pi pi-plus"
                size="small"
                @click="goToCarePlan"
              />
            </div>

            <!-- Loading -->
            <div v-if="carePlansLoading" class="space-y-3">
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
            </div>

            <!-- Erreur -->
            <div v-else-if="carePlansError" class="text-sm text-red-600">
              {{ carePlansError }}
            </div>

            <!-- État chargé -->
            <template v-else>
              <!-- ===== F8a — Cards Plans en cours ===== -->
              <div v-if="plansEnCours.length > 0" class="space-y-3">
                <div
                  v-for="plan in plansEnCours"
                  :key="plan.id"
                  :class="[
                    'group cursor-pointer overflow-hidden rounded-xl border-l-4 bg-white shadow-sm ring-1 ring-slate-100 transition-all hover:ring-slate-200 hover:shadow-md',
                    getCarePlanCardAccent(plan).borderClass,
                  ]"
                  role="button"
                  tabindex="0"
                  @click="goToCarePlanDetail(plan.id)"
                  @keydown.enter="goToCarePlanDetail(plan.id)"
                >
                  <div class="px-4 py-3">
                    <!-- Header : badge statut + ID + CTA "Voir la fiche" -->
                    <div class="mb-2 flex items-center justify-between gap-2">
                      <div class="flex items-center gap-2">
                        <span
                          :class="[
                            'rounded-full px-2 py-0.5 text-[0.625rem] font-bold uppercase tracking-wide',
                            getCarePlanCardAccent(plan).badgeClass,
                          ]"
                        >
                          {{ getCarePlanCardAccent(plan).label }}
                        </span>
                        <span class="text-xs text-slate-400">#{{ plan.id }}</span>
                      </div>
                      <span
                        class="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 transition-colors group-hover:text-teal-700"
                      >
                        Voir la fiche
                        <i class="pi pi-arrow-right text-[0.625rem]" aria-hidden="true" />
                      </span>
                    </div>

                    <!-- Titre -->
                    <div class="mb-1 text-sm font-semibold text-slate-800">
                      {{ plan.title }}
                    </div>

                    <!-- Filiation (si DRAFT-révision) -->
                    <div
                      v-if="plan.supersedes_plan_id !== null"
                      class="mb-2 flex items-center gap-1 text-xs text-slate-500"
                    >
                      <i class="pi pi-history text-[0.625rem]" aria-hidden="true" />
                      <span>
                        Révision du plan #{{ plan.supersedes_plan_id }}
                        <template v-if="plan.revision_reason">
                          &middot; {{ REVISION_REASON_LABELS[plan.revision_reason] }}
                        </template>
                      </span>
                    </div>

                    <!-- Méta : période / prestations / budget / GIR -->
                    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span class="inline-flex items-center gap-1">
                        <i class="pi pi-calendar text-[0.625rem]" aria-hidden="true" />
                        <span>
                          {{ formatDate(plan.start_date) }}
                          <template v-if="plan.end_date">
                            → {{ formatDate(plan.end_date) }}
                          </template>
                        </span>
                      </span>
                      <span class="inline-flex items-center gap-1">
                        <i class="pi pi-list text-[0.625rem]" aria-hidden="true" />
                        <span>
                          {{ plan.services_count }} prestation{{
                            plan.services_count > 1 ? 's' : ''
                          }}
                        </span>
                      </span>
                      <span v-if="plan.budget_allocated" class="inline-flex items-center gap-1">
                        <i class="pi pi-euro text-[0.625rem]" aria-hidden="true" />
                        <span>{{ formatEuro(plan.budget_allocated, { decimals: 0 }) }}</span>
                      </span>
                      <span v-if="plan.gir_at_creation" class="inline-flex items-center gap-1">
                        <span class="font-semibold text-slate-600">
                          GIR {{ plan.gir_at_creation }}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Aucun plan en cours -->
              <div v-else-if="plansHistorique.length === 0" class="empty-state">
                <NotebookPen :size="48" class="empty-state-icon" />
                <p class="empty-state-title">Aucun plan d'aide</p>
                <p class="empty-state-description">
                  <span v-if="canShowCarePlanButton">
                    Cliquez sur Nouveau plan d'aide pour commencer.
                  </span>
                  <span v-else> Les plans d'aide apparaîtront ici une fois créés. </span>
                </p>
              </div>

              <!-- ===== F8b — Toggle expand inline Historique ===== -->
              <div v-if="plansHistorique.length > 0" class="mt-6">
                <button
                  type="button"
                  class="inline-flex items-center gap-2 text-sm font-medium text-slate-600 transition-colors hover:text-teal-700"
                  @click="historiqueExpanded = !historiqueExpanded"
                >
                  <i
                    :class="[
                      'pi text-xs transition-transform',
                      historiqueExpanded ? 'pi-chevron-down' : 'pi-chevron-right',
                    ]"
                    aria-hidden="true"
                  />
                  {{ historiqueExpanded ? 'Masquer' : 'Voir' }} l'historique ({{
                    plansHistorique.length
                  }})
                </button>

                <!-- DataTable historique -->
                <div v-if="historiqueExpanded" class="mt-4">
                  <DataTable :value="plansHistorique" class="p-datatable-sm" stripedRows>
                    <Column field="id" header="#" style="width: 60px">
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span class="text-xs text-slate-500">#{{ data.id }}</span>
                      </template>
                    </Column>

                    <Column field="title" header="Titre" sortable>
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span class="text-sm font-medium text-slate-700">{{ data.title }}</span>
                      </template>
                    </Column>

                    <Column field="status" header="Statut" sortable>
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <Tag
                          :value="PLAN_STATUS_LABELS[data.status] ?? data.status"
                          :severity="PLAN_STATUS_SEVERITY[data.status]"
                        />
                      </template>
                    </Column>

                    <Column field="start_date" header="Période" sortable>
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span class="text-sm">
                          {{ formatDate(data.start_date) }}
                          <span v-if="data.end_date"> → {{ formatDate(data.end_date) }}</span>
                        </span>
                      </template>
                    </Column>

                    <Column field="gir_at_creation" header="GIR" style="width: 70px">
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span
                          v-if="data.gir_at_creation"
                          class="text-sm font-semibold text-slate-600"
                        >
                          GIR {{ data.gir_at_creation }}
                        </span>
                        <span v-else class="text-slate-400 text-sm">—</span>
                      </template>
                    </Column>

                    <Column field="supersedes_plan_id" header="Filiation">
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span v-if="data.supersedes_plan_id" class="text-sm">
                          Révision de #{{ data.supersedes_plan_id }}
                        </span>
                        <span v-else class="text-slate-400 text-sm">—</span>
                      </template>
                    </Column>

                    <Column field="revision_reason" header="Motif">
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span v-if="data.revision_reason" class="text-sm">
                          {{ REVISION_REASON_LABELS[data.revision_reason] }}
                        </span>
                        <span v-else class="text-slate-400 text-sm">—</span>
                      </template>
                    </Column>

                    <Column field="created_at" header="Créé le" sortable>
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <span class="text-xs text-slate-500">
                          {{ formatDate(data.created_at) }}
                        </span>
                      </template>
                    </Column>

                    <Column header="Actions" style="width: 80px">
                      <template #body="{ data }: { data: CarePlanSummary }">
                        <Button
                          icon="pi pi-eye"
                          size="small"
                          variant="text"
                          title="Voir le détail"
                          rounded
                          @click="goToCarePlanDetail(data.id)"
                        />
                      </template>
                    </Column>
                  </DataTable>
                </div>
              </div>
            </template>
          </div>
        </TabPanel>

        <!-- ── Constantes ─────────────────────────────────────────────── -->
        <TabPanel value="constantes">
          <div class="tab-content">
            <div class="flex justify-between items-center mb-4">
              <h3 class="tab-section-title" style="margin-bottom: 0">
                Historique des constantes
              </h3>
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
            <p class="text-slate-500 text-sm">Carnet de liaison filtré sur ce patient.</p>
            <p class="mt-2 text-xs text-slate-400">(Contenu à implémenter)</p>
          </div>
        </TabPanel>

        <!-- ── Documents ──────────────────────────────────────────────── -->
        <TabPanel value="documents">
          <div class="tab-content">
            <h3 class="tab-section-title">Documents générés</h3>
            <p class="text-slate-500 text-sm">Documents PPA, PPCS, recommandations.</p>
            <p class="mt-2 text-xs text-slate-400">(Contenu à implémenter)</p>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Modal détail évaluation -->
    <EvaluationDetailDialog
      v-model:visible="showEvaluationModal"
      :evaluation="selectedEvaluation"
      :patient-name="fullName"
      @close="closeEvaluationModal"
    />

    <!-- Panel édition patient (extra admin re-logé) -->
    <PatientEditDialog
      :visible="editDialogVisible"
      :patient="patient"
      @update:visible="editDialogVisible = $event"
      @saved="onPatientSaved"
    />
  </div>
</template>

<style scoped>
  /* =================================================================
   PATIENT DETAIL — Styles scoped (composant partagé admin / soins)
   Palette : slate-* / teal-500/600 (FRONTEND_CONVENTIONS PATCH 1)
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
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.1),
      0 1px 2px rgba(0, 0, 0, 0.06);
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
    flex-wrap: wrap;
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

  .patient-gir-badge--severe {
    background: #fee2e2;
    color: #dc2626;
  }
  .patient-gir-badge--moderate {
    background: #fef3c7;
    color: #d97706;
  }
  .patient-gir-badge--light {
    background: #dcfce7;
    color: #16a34a;
  }

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

  .patient-tabs {
    background: white;
    border-radius: 0.75rem;
    box-shadow:
      0 1px 3px rgba(0, 0, 0, 0.1),
      0 1px 2px rgba(0, 0, 0, 0.06);
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
  .vital-widget--ok {
    background: #f0fdf4;
    border-color: #bbf7d0;
    color: #166534;
  }
  .vital-widget--warning {
    background: #fff7ed;
    border-color: #fed7aa;
    color: #9a3412;
  }
  .vital-widget--critical {
    background: #fef2f2;
    border-color: #fecaca;
    color: #991b1b;
  }
  .vital-widget--empty {
    background: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
  }

  .vital-widget--ok .vital-widget__icon {
    color: #16a34a;
  }
  .vital-widget--warning .vital-widget__icon {
    color: #ea580c;
  }
  .vital-widget--critical .vital-widget__icon {
    color: #dc2626;
  }

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

  .synthese-info-card--suggestion {
    border-color: #99f6e4;
    background: #f0fdfa;
    cursor: pointer;
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

  .synthese-info-card__value--accent {
    color: #0d9488;
    font-weight: 600;
  }

  /* -- Bilan clinique (S6) — extra admin re-logé en Synthèse ----------- */

  .bilan-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
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

  /* -- États vides ------------------------------------------------------ */

  .empty-state {
    @apply flex flex-col items-center justify-center py-10 text-center;
  }
  .empty-state-icon {
    color: #cbd5e1;
    margin-bottom: 0.75rem;
  }
  .empty-state-title {
    @apply text-sm font-semibold text-slate-500 mb-1;
  }
  .empty-state-description {
    @apply text-xs text-slate-400 max-w-xs leading-relaxed;
  }
</style>

<style>
  /* Règles non-scoped : les <tr>/<td> PrimeVue ne portent pas l'attribut
     data-v-xxx, donc un bloc scoped ne peut pas les atteindre.
     Préfixe .care-plan-row--active suffisamment spécifique pour éviter
     tout conflit (classe fonctionnelle utilisée uniquement ici et dans
     CarePlanListPage.vue). */
  .care-plan-row--active > td {
    background-color: #f0fdfa; /* teal-50 */
  }
  .care-plan-row--active > td:first-child {
    box-shadow: inset 4px 0 0 0 #14b8a6; /* teal-500, liseré gauche */
  }
</style>