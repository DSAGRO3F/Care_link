/**
 * CareLink - useEvaluationWizard
 * Chemin : frontend/src/composables/useEvaluationWizard.ts
 *
 * Rôle : Gestion d'état du wizard de saisie d'évaluation.
 *        Navigation entre sections, suivi de complétion,
 *        sauvegarde brouillon et soumission.
 */
import { ref, reactive, computed, type Ref } from 'vue';
import axios from 'axios';
import { evaluationService } from '@/services';
import { adaptSectionData, reverseAdaptSectionData, sanitizePhone } from '@/components/evaluation/evaluationAdapters';
import type { PatientResponse } from '@/types/patient';

// =============================================================================
// TYPES
// =============================================================================

export type SectionStatus = 'empty' | 'partial' | 'complete';

/**
 * Données de section du wizard — polymorphes par design.
 * Chaque section (usager, contacts, social…) produit une structure différente.
 * Le typage précis vit à l'intérieur de chaque formulaire ;
 * au niveau du hub wizard, le contenu reste opaque.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WizardSectionData = Record<string, any>;

export interface WizardSectionConfig {
  /** Clé technique (correspond aux clés du JSON evaluation_data) */
  id: string;
  /** Label affiché */
  label: string;
  /** Description courte sous le label */
  subtitle: string;
  /** Nom du composant icône Lucide (résolu par WizardSectionNav) */
  icon: string;
  /** Suffixe de la classe CSS wizard-icon--{colorClass} */
  colorClass: string;
  /** Obligatoire pour la soumission (validation complète) */
  requiredForSubmit: boolean;
}

export interface SectionState {
  status: SectionStatus;
  /** Données du formulaire pour cette section */
  data: WizardSectionData;
}

export interface WizardState {
  /** ID de l'évaluation (null si création en cours) */
  evaluationId: number | null;
  /** ID du patient */
  patientId: number;
  /** Statut global de l'évaluation */
  evaluationStatus: 'DRAFT' | 'SUBMITTED' | 'VALIDATED' | 'ARCHIVED';
  /** ID de la session de saisie en cours */
  sessionId: number | null;
  /** Date de dernière sauvegarde */
  lastSavedAt: string | null;
  /** Opération en cours */
  saving: boolean;
  /** Erreur éventuelle */
  error: string | null;
  /**
   * Mode du wizard :
   * - 'initial'      : première évaluation, aucune données pré-remplies depuis une éval précédente
   * - 'reevaluation' : évaluation suivante, données pré-remplies depuis la dernière éval VALIDATED
   */
  evaluationMode: 'initial' | 'reevaluation';
  /**
   * Données de la dernière évaluation VALIDATED (null en mode initial).
   * Utilisées pour le pré-remplissage et le bouton "Inchangé — confirmer".
   */
  previousEvaluationData: WizardSectionData | null;
}

// =============================================================================
// CONFIGURATION DES SECTIONS
// =============================================================================

export const WIZARD_SECTIONS: readonly WizardSectionConfig[] = Object.freeze([
  {
    id: 'usager',
    label: 'Usager',
    subtitle: 'État civil & adresse',
    icon: 'User',
    colorClass: 'blue',
    requiredForSubmit: true,
  },
  {
    id: 'contacts',
    label: 'Contacts',
    subtitle: "Cercle d'aide",
    icon: 'BookUser',
    colorClass: 'violet',
    requiredForSubmit: false,
  },
  {
    id: 'aggir',
    label: 'AGGIR',
    subtitle: "Grille d'autonomie",
    icon: 'Grid3x3',
    colorClass: 'teal',
    requiredForSubmit: true,
  },
  {
    id: 'social',
    label: 'Social',
    subtitle: 'Habitat & vie sociale',
    icon: 'Home',
    colorClass: 'amber',
    requiredForSubmit: false,
  },
  {
    id: 'sante',
    label: 'Santé',
    subtitle: '7 blocs cliniques',
    icon: 'HeartPulse',
    colorClass: 'pink',
    requiredForSubmit: false,
  },
  {
    id: 'materiels',
    label: 'Matériels',
    subtitle: 'Équipements',
    icon: 'Armchair',
    colorClass: 'emerald',
    requiredForSubmit: false,
  },
  {
    id: 'dispositifs',
    label: 'Dispositifs',
    subtitle: 'Appareillages',
    icon: 'Cpu',
    colorClass: 'slate',
    requiredForSubmit: false,
  },
  {
    id: 'poaSocial',
    label: 'POA Social',
    subtitle: "Plan d'aide social",
    icon: 'HandHeart',
    colorClass: 'orange',
    requiredForSubmit: false,
  },
  {
    id: 'poaSante',
    label: 'POA Santé',
    subtitle: "Plan d'aide santé",
    icon: 'Pill',
    colorClass: 'red',
    requiredForSubmit: false,
  },
  {
    id: 'poaAutonomie',
    label: 'POA Autonomie',
    subtitle: 'Maintien autonomie',
    icon: 'Target',
    colorClass: 'indigo',
    requiredForSubmit: false,
  },
]);

// =============================================================================
// LABELS DE STATUT
// =============================================================================

export const STATUS_LABELS: Record<SectionStatus, string> = {
  empty: 'Non commencé',
  partial: 'En cours',
  complete: 'Complet',
};

// =============================================================================
// ESTIMATION DE STATUT (fallback sans _wizard_meta)
// =============================================================================

/**
 * Compte récursivement les champs feuilles renseignés et le total de champs
 * dans un objet de données de section.
 * Un champ est considéré "renseigné" si sa valeur n'est ni null, ni undefined,
 * ni chaîne vide, ni tableau vide.
 */
function countFields(data: unknown): { filled: number; total: number } {
  if (data === null || data === undefined) return { filled: 0, total: 0 };

  if (Array.isArray(data)) {
    // Un tableau non vide compte comme 1 champ renseigné
    return { filled: data.length > 0 ? 1 : 0, total: 1 };
  }

  if (typeof data === 'object') {
    let filled = 0;
    let total = 0;
    for (const value of Object.values(data as Record<string, unknown>)) {
      if (value !== null && value !== undefined && typeof value === 'object') {
        const sub = countFields(value);
        filled += sub.filled;
        total += sub.total;
      } else {
        total += 1;
        if (value !== null && value !== undefined && value !== '') {
          filled += 1;
        }
      }
    }
    return { filled, total };
  }

  // Valeur scalaire
  const isFilled = data !== null && data !== undefined && data !== '';
  return { filled: isFilled ? 1 : 0, total: 1 };
}

/**
 * Estime le statut d'une section à partir de ses données brutes,
 * sans monter le formulaire correspondant.
 *
 * Heuristique : ratio champs renseignés / champs totaux.
 * - 0 champ renseigné          → 'empty'
 * - ratio ≥ 50 % des champs    → 'complete'
 * - sinon                       → 'partial'
 *
 * C'est une estimation volontairement approximative :
 * certains champs sont optionnels selon le contexte du patient.
 * Le statut exact est recalculé dès que l'utilisateur visite la section
 * (le formulaire émet @update:status) puis persisté dans _wizard_meta
 * à la prochaine sauvegarde.
 */
function estimateSectionStatus(data: WizardSectionData): SectionStatus {
  const { filled, total } = countFields(data);
  if (filled === 0) return 'empty';
  if (total === 0) return 'empty';
  return filled / total >= 0.5 ? 'complete' : 'partial';
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useEvaluationWizard(patientId: Ref<number>) {
  // ── État ─────────────────────────────────────────────────────────────

  const activeSection = ref<string>(WIZARD_SECTIONS[0].id);

  const sectionStates = reactive<Record<string, SectionState>>(
    Object.fromEntries(
      WIZARD_SECTIONS.map((s) => [s.id, { status: 'empty' as SectionStatus, data: {} }]),
    ),
  );

  const wizardState = reactive<WizardState>({
    evaluationId: null,
    patientId: patientId.value,
    evaluationStatus: 'DRAFT',
    sessionId: null,
    lastSavedAt: null,
    saving: false,
    error: null,
    evaluationMode: 'initial',
    previousEvaluationData: null,
  });

  /** Passe à true au premier clic "Soumettre" — active la validation visuelle dans UsagerForm */
  const submitAttempted = ref(false);

  // ── Computed ─────────────────────────────────────────────────────────

  const activeSectionConfig = computed(
    () => WIZARD_SECTIONS.find((s) => s.id === activeSection.value)!,
  );

  const completedCount = computed(
    () => Object.values(sectionStates).filter((s) => s.status === 'complete').length,
  );

  const partialCount = computed(
    () => Object.values(sectionStates).filter((s) => s.status === 'partial').length,
  );

  const completionPercent = computed(() => {
    let total = 0;
    for (const state of Object.values(sectionStates)) {
      if (state.status === 'complete') total += 10;
      else if (state.status === 'partial') total += 4;
    }
    return Math.min(total, 100);
  });

  const canSubmit = computed(() => {
    const requiredSections = WIZARD_SECTIONS.filter((s) => s.requiredForSubmit);
    return requiredSections.every((s) => sectionStates[s.id]?.status === 'complete');
  });

  const currentSectionIndex = computed(() =>
    WIZARD_SECTIONS.findIndex((s) => s.id === activeSection.value),
  );

  const hasNext = computed(() => currentSectionIndex.value < WIZARD_SECTIONS.length - 1);
  const hasPrev = computed(() => currentSectionIndex.value > 0);

  // ── Navigation ───────────────────────────────────────────────────────

  /**
   * Vérifie que les champs structurants de la section Usager sont renseignés.
   * État civil : civilité, sexe, nom, prénom, date de naissance.
   * Adresse : rue, code postal, commune.
   * Utilisé pour bloquer la navigation tant que ces champs de base sont vides.
   */
  const USAGER_REQUIRED_KEYS = [
    'civilite',
    'sexe',
    'nomFamille',
    'prenomUtilise',
    'dateNaissance',
    'adresseLigne',
    'codePostal',
    'commune',
  ] as const;

  function isUsagerRequiredFieldsFilled(): boolean {
    const data = sectionStates.usager?.data;
    if (!data) return false;
    return USAGER_REQUIRED_KEYS.every((key) => {
      const val = data[key];
      if (val === null || val === undefined) return false;
      if (typeof val === 'string' && val.trim() === '') return false;
      return true;
    });
  }

  function selectSection(sectionId: string) {
    if (WIZARD_SECTIONS.some((s) => s.id === sectionId)) {
      // Bloquer la navigation si on quitte Usager avec civilité/sexe vides
      if (activeSection.value === 'usager' && sectionId !== 'usager') {
        if (!isUsagerRequiredFieldsFilled()) {
          submitAttempted.value = true;
          return; // ← blocage : reste sur Usager
        }
      }
      activeSection.value = sectionId;
    }
  }

  function nextSection() {
    if (hasNext.value) {
      // Bloquer la navigation si on quitte Usager avec civilité/sexe vides
      if (activeSection.value === 'usager') {
        if (!isUsagerRequiredFieldsFilled()) {
          submitAttempted.value = true;
          return; // ← blocage : reste sur Usager
        }
      }
      activeSection.value = WIZARD_SECTIONS[currentSectionIndex.value + 1].id;
    }
  }

  function prevSection() {
    if (hasPrev.value) {
      activeSection.value = WIZARD_SECTIONS[currentSectionIndex.value - 1].id;
    }
  }

  // ── Données de section ───────────────────────────────────────────────

  function updateSectionData(sectionId: string, data: WizardSectionData) {
    if (sectionStates[sectionId]) {
      sectionStates[sectionId].data = { ...data };
    }
  }

  function updateSectionStatus(sectionId: string, status: SectionStatus) {
    if (sectionStates[sectionId]) {
      sectionStates[sectionId].status = status;
    }
  }

  // ── Mode réévaluation ────────────────────────────────────────────────

  /**
   * Set des sections confirmées "inchangées" par le praticien.
   * Une section confirmée copie les données de previousEvaluationData
   * et passe en status 'complete' sans resaisie.
   * La section 'aggir' ne peut jamais être confirmée inchangée (obligation légale).
   */
  const confirmedSections = reactive(new Set<string>());

  /**
   * Marque une section comme inchangée par rapport à la dernière évaluation.
   * Interdit pour la section 'aggir' (recotation obligatoire à chaque évaluation).
   */
  function confirmSectionUnchanged(sectionId: string): void {
    if (sectionId === 'aggir') return;
    if (!WIZARD_SECTIONS.some((s) => s.id === sectionId)) return;

    // Copier les données de la dernière éval validée si disponibles
    const prevData = wizardState.previousEvaluationData?.[sectionId];
    if (prevData && typeof prevData === 'object') {
      sectionStates[sectionId].data = { ...prevData };
    }
    sectionStates[sectionId].status = 'complete';
    confirmedSections.add(sectionId);

    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[EvaluationWizard] Section confirmée inchangée:', sectionId);
    }
  }

  // ── Nettoyage téléphones (ceinture pré-save) ───────────────────────

  /**
   * Sanitize in-place les champs téléphone dans le wizardState.
   * Appliqué avant buildEvaluationData() dans saveDraft et submitEvaluation
   * pour garantir que même le brouillon stocke des chiffres purs.
   * Les adapters Bachelard (evaluationAdapters.ts) appliquent le même
   * sanitize — double protection (ceinture + bretelles).
   */
  function sanitizePhoneFields(): void {
    // Usager : telMobile, telDomicile
    const usagerData = sectionStates.usager?.data;
    if (usagerData) {
      if (usagerData.telMobile) usagerData.telMobile = sanitizePhone(usagerData.telMobile);
      if (usagerData.telDomicile) usagerData.telDomicile = sanitizePhone(usagerData.telDomicile);
    }

    // Contacts : mobile + numRpps dans chaque ContactItem
    const contactsData = sectionStates.contacts?.data;
    if (contactsData?.contacts && Array.isArray(contactsData.contacts)) {
      for (const c of contactsData.contacts) {
        if (c.mobile) c.mobile = sanitizePhone(c.mobile);
        if (c.numRpps) c.numRpps = sanitizePhone(c.numRpps);
      }
    }
  }

  // ── Assemblage JSON evaluation_data ──────────────────────────────────

  function buildEvaluationData(): WizardSectionData {
    const data: WizardSectionData = {};
    for (const section of WIZARD_SECTIONS) {
      const state = sectionStates[section.id];
      if (state && state.status !== 'empty' && Object.keys(state.data).length > 0) {
        data[section.id] = state.data;
      }
    }

    // Persister les statuts de section pour restauration au rechargement.
    // Clé préfixée _ pour signaler qu'il s'agit de métadonnées internes,
    // pas de données cliniques exportables.
    const statuses: Record<string, SectionStatus> = {};
    for (const section of WIZARD_SECTIONS) {
      statuses[section.id] = sectionStates[section.id]?.status ?? 'empty';
    }
    data._wizard_meta = { sectionStatuses: statuses };

    return data;
  }

  // ── Chargement (édition d'un brouillon existant) ─────────────────────

  function loadEvaluationData(evaluationData: WizardSectionData) {
    // Restaurer les statuts persistés si disponibles (sauvegardés par buildEvaluationData).
    const savedStatuses: Record<string, SectionStatus> | null =
      evaluationData._wizard_meta?.sectionStatuses ?? null;

    for (const section of WIZARD_SECTIONS) {
      const sectionData = evaluationData[section.id];
      if (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) {
        sectionStates[section.id].data = { ...sectionData };
        // Utiliser le statut persisté si disponible, sinon estimer depuis les données.
        // L'estimation est un fallback pour les brouillons sauvegardés avant l'ajout
        // de _wizard_meta. Le statut exact sera recalculé au montage du formulaire.
        sectionStates[section.id].status =
          savedStatuses?.[section.id] ?? estimateSectionStatus(sectionData);
      }
    }
  }

  // ── Pré-remplissage sélectif (nouvelle évaluation) ─────────────────

  /**
   * Sections stables reprises depuis la dernière évaluation soumise.
   * Les sections cliniques (aggir, sante, POA) restent vides car elles
   * doivent refléter l'état du patient au moment de la nouvelle évaluation.
   */
  const PREFILL_SECTIONS = ['usager', 'contacts', 'social', 'materiels', 'dispositifs'];

  /**
   * Pré-remplit les sections stables depuis la dernière évaluation soumise.
   * Les sections sont marquées 'partial' pour que l'évaluateur les vérifie.
   */
  function prefillFromPreviousEvaluation(evaluationData: WizardSectionData): void {
    for (const sectionId of PREFILL_SECTIONS) {
      const rawSectionData = evaluationData[sectionId];
      if (rawSectionData && typeof rawSectionData === 'object') {
        // Reverse adapt : EvalSchema nested → wizard flat format
        // (usager, contacts, dispositifs ont besoin de transformation ;
        //  materiels, social passent tels quels)
        const adapted = reverseAdaptSectionData(sectionId, rawSectionData);
        const wizardData =
          adapted && typeof adapted === 'object' && !Array.isArray(adapted)
            ? { ...(adapted as WizardSectionData) }
            : {};

        if (Object.keys(wizardData).length > 0) {
          sectionStates[sectionId].data = wizardData;
          sectionStates[sectionId].status = 'partial';
        }
      }
    }

    // Stocker les données précédentes pour le bouton "Inchangé — confirmer"
    wizardState.evaluationMode = 'reevaluation';
    wizardState.previousEvaluationData = evaluationData;

    if (import.meta.env.DEV) {
      const filled = PREFILL_SECTIONS.filter(
        (id) => Object.keys(sectionStates[id].data).length > 0,
      );
      // eslint-disable-next-line no-console
      console.log('[EvaluationWizard] Pré-remplissage depuis éval précédente:', filled);
    }
  }

  /**
   * Pré-remplit la section Usager depuis la fiche patient SQL (fallback).
   * Utilisé uniquement si aucune évaluation soumise n'existe (premier passage).
   */
  function prefillFromPatient(patient: PatientResponse): void {
    const usagerData: WizardSectionData = {};

    // Mapper les champs patient SQL → clés UsagerForm (serializeFormData / loadFromBrouillon)
    if (patient.last_name) {
      usagerData.nomFamille = patient.last_name;
      usagerData.nomUtilise = patient.last_name;
    }
    if (patient.first_name) {
      usagerData.prenomUtilise = patient.first_name;
      usagerData.prenomsActeNaissance = patient.first_name;
    }

    // Date de naissance : format ISO string (loadFromBrouillon parse via new Date())
    if (patient.birth_date) {
      const d = new Date(patient.birth_date);
      if (!isNaN(d.getTime())) {
        usagerData.dateNaissance = d.toISOString();
      }
    }

    if (patient.nir) usagerData.nir = patient.nir;
    if (patient.ins) usagerData.ins = patient.ins;
    if (patient.address) usagerData.adresseLigne = patient.address;
    if (patient.postal_code) usagerData.codePostal = patient.postal_code;
    if (patient.city) usagerData.commune = patient.city;
    if (patient.phone) usagerData.telMobile = patient.phone;
    if (patient.email) usagerData.email = patient.email;

    if (Object.keys(usagerData).length > 0) {
      sectionStates.usager.data = usagerData;
      sectionStates.usager.status = 'partial';

      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.log(
          '[EvaluationWizard] Pré-remplissage depuis fiche patient:',
          Object.keys(usagerData),
        );
      }
    }
  }

  // ── Persistance ──────────────────────────────────────────────────────

  async function saveDraft(): Promise<boolean> {
    // Activer la validation visuelle dès la première sauvegarde
    submitAttempted.value = true;
    wizardState.saving = true;
    wizardState.error = null;

    try {
      sanitizePhoneFields();
      const evaluationData = buildEvaluationData();
      const payload = {
        evaluation_data: evaluationData,
        completion_percent: completionPercent.value,
      };

      if (wizardState.evaluationId) {
        // Mise à jour d'un brouillon existant
        await evaluationService.update(wizardState.patientId, wizardState.evaluationId, payload);
      } else {
        // Création d'une nouvelle évaluation
        try {
          const response = await evaluationService.create(wizardState.patientId, {
            ...payload,
            evaluation_type: 'AGGIR',
            schema_type: 'evaluation_complete',
            schema_version: 'v1',
            evaluation_date: new Date().toISOString().split('T')[0],
          });
          wizardState.evaluationId = response.data.id;
        } catch (createErr: unknown) {
          // ✅ Fix 409 EVALUATION_IN_PROGRESS → récupère l'ID existant et bascule en PATCH.
          // Cas typique : rechargement de page ou redémarrage serveur → evaluationId perdu en mémoire.
          if (axios.isAxiosError(createErr) && createErr.response?.status === 409) {
            const detail = createErr.response?.data?.detail;
            if (detail?.code === 'EVALUATION_IN_PROGRESS' && detail?.existing_evaluation_id) {
              wizardState.evaluationId = detail.existing_evaluation_id as number;
              // ✅ Fix TS : const local pour garantir number (non-null) à TypeScript
              const recoveredId: number = wizardState.evaluationId;
              await evaluationService.update(wizardState.patientId, recoveredId, payload);
            } else {
              throw createErr;
            }
          } else {
            throw createErr;
          }
        }
      }

      wizardState.lastSavedAt = new Date().toISOString();
      return true;
    } catch (err: unknown) {
      wizardState.error = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Erreur lors de la sauvegarde'
        : 'Erreur lors de la sauvegarde';
      if (import.meta.env.DEV) {
        console.error('[EvaluationWizard] Save error:', err);
      }
      return false;
    } finally {
      wizardState.saving = false;
    }
  }

  async function submitEvaluation(): Promise<boolean> {
    submitAttempted.value = true;
    if (!canSubmit.value) return false;

    // 1. S'assurer qu'un brouillon existe (format wizard, pour recharger si échec)
    if (!wizardState.evaluationId) {
      const saved = await saveDraft();
      if (!saved) return false;
    }

    // 2. Sauvegarder les données en format Bachelard (attendu par le JSON schema backend)
    //    Les adapters transforment usager, contacts, materiels, dispositifs ;
    //    les autres sections passent telles quelles.
    wizardState.saving = true;
    wizardState.error = null;

    try {
      sanitizePhoneFields();
      const rawData = buildEvaluationData();
      const adaptedData: WizardSectionData = {};
      for (const [key, value] of Object.entries(rawData)) {
        adaptedData[key] = adaptSectionData(key, value);
      }

      await evaluationService.update(wizardState.patientId, wizardState.evaluationId!, {
        evaluation_data: adaptedData,
        completion_percent: completionPercent.value,
      });
    } catch (err: unknown) {
      wizardState.error = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Erreur lors de la préparation'
        : 'Erreur lors de la préparation';
      if (import.meta.env.DEV) {
        console.error('[EvaluationWizard] Pre-submit save error:', err);
      }
      wizardState.saving = false;
      return false;
    }

    // 3. Soumettre (le backend valide les données adaptées)
    try {
      await evaluationService.submit(wizardState.patientId, wizardState.evaluationId!);
      wizardState.evaluationStatus = 'SUBMITTED';
      return true;
    } catch (err: unknown) {
      wizardState.error = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Erreur lors de la soumission'
        : 'Erreur lors de la soumission';
      if (import.meta.env.DEV) {
        console.error('[EvaluationWizard] Submit error:', err);
      }
      return false;
    } finally {
      wizardState.saving = false;
    }
  }

  // ── Sessions ─────────────────────────────────────────────────────────

  async function startSession(): Promise<void> {
    if (!wizardState.evaluationId) return;

    try {
      const response = await evaluationService.startSession(
        wizardState.patientId,
        wizardState.evaluationId,
        JSON.stringify({
          user_agent: navigator.userAgent,
          screen_width: window.innerWidth,
          screen_height: window.innerHeight,
        }).slice(0, 200),
      );
      wizardState.sessionId = response.data.id;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[EvaluationWizard] Could not start session:', err);
      }
    }
  }

  async function endSession(): Promise<void> {
    if (!wizardState.evaluationId || !wizardState.sessionId) return;

    try {
      const variablesSaved = Object.entries(sectionStates)
        .filter(([, state]) => state.status !== 'empty')
        .map(([id]) => id);

      await evaluationService.endSession(
        wizardState.patientId,
        wizardState.evaluationId,
        wizardState.sessionId,
        { variables_saved: variablesSaved },
      );
      wizardState.sessionId = null;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[EvaluationWizard] Could not end session:', err);
      }
    }
  }

  // ── API publique ─────────────────────────────────────────────────────

  return {
    // Configuration (readonly)
    sections: WIZARD_SECTIONS,

    // État
    activeSection,
    activeSectionConfig,
    sectionStates,
    wizardState,

    // Computed
    completedCount,
    partialCount,
    completionPercent,
    canSubmit,
    hasNext,
    hasPrev,

    // Navigation
    selectSection,
    nextSection,
    prevSection,

    // Données
    updateSectionData,
    updateSectionStatus,
    loadEvaluationData,
    buildEvaluationData,

    // Pré-remplissage (nouvelle évaluation)
    prefillFromPreviousEvaluation,
    prefillFromPatient,

    // Mode réévaluation
    confirmedSections,
    confirmSectionUnchanged,

    // Persistance
    saveDraft,
    submitEvaluation,

    // Validation visuelle pré-submit
    submitAttempted,

    // Sessions
    startSession,
    endSession,
  };
}