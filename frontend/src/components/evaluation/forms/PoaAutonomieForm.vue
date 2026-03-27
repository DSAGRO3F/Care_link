<!--
  CareLink - PoaAutonomieForm
  Chemin : frontend/src/components/evaluation/forms/PoaAutonomieForm.vue

  Rôle : Formulaire de saisie du Plan d'Actions Autonomie (POA Autonomie).
         Structure différente des POA Social/Santé :
         - Préoccupations patient/professionnel au niveau global (racine)
         - Liste libre d'interventions (`actions[]`) décrivant les passages à domicile
         Chaque intervention contient : typeAction, personneChargeAction[], joursIntervention[],
         momentJournee[], typeAide[], actions[] (gestes), dureePassage, etc.
         Émet @update:data et @update:status vers le wizard parent.

  Bachelard : 6 interventions (Aide à domicile × 6 passages, Lever→Nuit).
  Identité visuelle : fieldset teal, classes wizard-* de main.css
-->
<template>
  <div class="space-y-7">
    <!-- ── Fieldset POA Autonomie ───────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--teal">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--teal">
          <Target :size="16" :stroke-width="2" />
        </span>
        Plan d'actions — Maintien de l'autonomie
      </legend>

      <!-- Préoccupations globales -->
      <div class="form-grid-2 mt-5">
        <div class="form-group mt-0">
          <label class="form-label">Préoccupation patient</label>
          <Select
            v-model="preoccupationPatient"
            :options="PREOCCUPATION_OPTIONS"
            option-label="label"
            option-value="value"
            placeholder="Niveau"
            class="w-full"
          />
        </div>
        <div class="form-group mt-0">
          <label class="form-label">Préoccupation professionnel</label>
          <Select
            v-model="preoccupationProfessionel"
            :options="PREOCCUPATION_OPTIONS"
            option-label="label"
            option-value="value"
            placeholder="Niveau"
            class="w-full"
          />
        </div>
      </div>

      <!-- ── Liste des interventions ─────────────────────────────────── -->
      <div class="mt-6">
        <h4 class="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-3">
          <CalendarClock :size="15" :stroke-width="2" class="text-slate-400" />
          Interventions planifiées
          <span v-if="interventions.length > 0" class="text-xs font-normal text-slate-400">
            ({{ interventions.length }})
          </span>
        </h4>

        <div v-if="interventions.length > 0" class="space-y-3">
          <div v-for="(interv, idx) in interventions" :key="idx" class="autonomie-card">
            <!-- En-tête — clic pour déplier -->
            <div class="autonomie-card-header" @click="toggleCard(idx)">
              <div class="flex items-center gap-2 min-w-0">
                <span class="autonomie-card-num">{{ idx + 1 }}</span>
                <span class="font-medium text-slate-800 truncate">
                  {{ interv.typeAction || 'Nouvelle intervention' }}
                </span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span v-if="interv.momentJournee.length > 0" class="autonomie-card-moment">
                  {{ interv.momentJournee.join(', ') }}
                </span>
                <span v-if="interv.dureePassage" class="autonomie-card-duree">
                  {{ interv.dureePassage }}
                </span>
                <button
                  class="wizard-delete-row"
                  title="Supprimer cette intervention"
                  @click.stop="removeIntervention(idx)"
                >
                  <Trash2 :size="14" :stroke-width="2" />
                </button>
                <ChevronDown
                  :size="16"
                  :stroke-width="2"
                  :class="{ 'rotate-180': expandedCards.has(idx) }"
                  class="text-slate-400 transition-transform duration-200"
                />
              </div>
            </div>

            <!-- Corps dépliable -->
            <div v-if="expandedCards.has(idx)" class="autonomie-card-body">
              <!-- Ligne 1 : Type d'action + Durée passage -->
              <div class="form-grid-2 mt-3">
                <div class="form-group mt-0">
                  <label class="form-label">Type d'action</label>
                  <Select
                    v-model="interv.typeAction"
                    :options="TYPE_ACTION_OPTIONS"
                    option-label="label"
                    option-value="value"
                    placeholder="Type"
                    class="w-full"
                  />
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Durée du passage</label>
                  <InputText
                    v-model="interv.dureePassage"
                    placeholder="Ex : 30mn, 60mn…"
                    class="w-full"
                  />
                </div>
              </div>

              <!-- Ligne 2 : Date début + Durée action -->
              <div class="form-grid-2 mt-3">
                <div class="form-group mt-0">
                  <label class="form-label">Date de début</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="interv.dateDebutJour"
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="interv.dateDebutMois"
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="interv.dateDebutAnnee"
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                    />
                  </div>
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Durée de l'action</label>
                  <InputText
                    v-model="interv.dureeAction"
                    placeholder="Ex : 3 mois, 1 an…"
                    class="w-full"
                  />
                </div>
              </div>

              <!-- Personne(s) en charge (saisie libre, virgule-séparée) -->
              <div class="form-group mt-5">
                <label class="form-label">Personne(s) en charge</label>
                <InputText
                  v-model="interv.personneChargeDisplay"
                  placeholder="Ex : Employé de maison, Famille…"
                  class="w-full"
                />
                <span class="text-xs text-slate-400 mt-0.5">
                  Séparer par des virgules si plusieurs
                </span>
              </div>

              <!-- Moments de la journée — Semaine 1 & 2 -->
              <div class="form-group mt-5">
                <label class="form-label">Moments de la journée</label>
                <div class="poa-week-grid">
                  <div class="poa-week-block">
                    <span class="poa-week-label">Semaine 1</span>
                    <div class="flex flex-wrap gap-3">
                      <label
                        v-for="moment in MOMENT_JOURNEE_OPTIONS"
                        :key="'m1-' + moment"
                        class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                      >
                        <Checkbox v-model="interv.momentJournee" :value="moment" />
                        {{ moment }}
                      </label>
                    </div>
                  </div>
                  <div class="poa-week-block">
                    <span class="poa-week-label">Semaine 2</span>
                    <div class="flex flex-wrap gap-3">
                      <label
                        v-for="moment in MOMENT_JOURNEE_OPTIONS"
                        :key="'m2-' + moment"
                        class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                      >
                        <Checkbox v-model="interv.secondMomentJournee" :value="moment" />
                        {{ moment }}
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Jours d'intervention — Semaine 1 & 2 -->
              <div class="form-group mt-5">
                <label class="form-label">Jours d'intervention</label>
                <div class="poa-week-grid">
                  <div class="poa-week-block">
                    <span class="poa-week-label">Semaine 1</span>
                    <div class="flex flex-wrap gap-3 items-center">
                      <label
                        v-for="jour in JOURS_OPTIONS"
                        :key="'j1-' + jour"
                        class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                      >
                        <Checkbox v-model="interv.joursIntervention" :value="jour" />
                        {{ jour }}
                      </label>
                      <button
                        class="autonomie-toggle-all"
                        @click.stop="toggleAllDays(interv.joursIntervention)"
                      >
                        {{
                          interv.joursIntervention.length === JOURS_OPTIONS.length
                            ? 'Aucun'
                            : 'Tous les jours'
                        }}
                      </button>
                    </div>
                  </div>
                  <div class="poa-week-block">
                    <span class="poa-week-label">Semaine 2</span>
                    <div class="flex flex-wrap gap-3 items-center">
                      <label
                        v-for="jour in JOURS_OPTIONS"
                        :key="'j2-' + jour"
                        class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                      >
                        <Checkbox v-model="interv.secondJoursIntervention" :value="jour" />
                        {{ jour }}
                      </label>
                      <button
                        class="autonomie-toggle-all"
                        @click.stop="toggleAllDays(interv.secondJoursIntervention)"
                      >
                        {{
                          interv.secondJoursIntervention.length === JOURS_OPTIONS.length
                            ? 'Aucun'
                            : 'Tous les jours'
                        }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Type d'aide -->
              <div class="form-group mt-5">
                <label class="form-label">Type d'aide</label>
                <div class="flex flex-wrap gap-3 mt-1">
                  <label
                    v-for="aide in TYPE_AIDE_OPTIONS"
                    :key="aide"
                    class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                  >
                    <Checkbox v-model="interv.typeAide" :value="aide" />
                    {{ aide }}
                  </label>
                </div>
              </div>

              <!-- Gestes / Actions à réaliser -->
              <div class="form-group mt-5">
                <label class="form-label">Actions à réaliser</label>
                <div class="flex flex-wrap gap-2 mt-1">
                  <label
                    v-for="geste in gestesForType(interv.typeAction)"
                    :key="geste"
                    class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                  >
                    <Checkbox v-model="interv.actions" :value="geste" />
                    {{ geste }}
                  </label>
                  <!-- Actions personnalisées (ajoutées via texte libre) -->
                  <label
                    v-for="custom in interv.actions.filter(
                      (a) => !gestesForType(interv.typeAction).includes(a),
                    )"
                    :key="'custom-' + custom"
                    class="flex items-center gap-1.5 text-sm text-indigo-600 cursor-pointer"
                  >
                    <Checkbox v-model="interv.actions" :value="custom" />
                    {{ custom }}
                  </label>
                </div>
                <!-- Saisie libre pour action hors catalogue -->
                <div class="flex items-center gap-2 mt-3">
                  <InputText
                    v-model="interv.autreAction"
                    placeholder="Autre action (préciser)…"
                    class="flex-1 text-sm"
                    @keydown.enter.prevent="addCustomAction(interv)"
                  />
                  <Button
                    :disabled="!interv.autreAction?.trim()"
                    label="Ajouter"
                    size="small"
                    variant="outlined"
                    @click="addCustomAction(interv)"
                  />
                </div>
              </div>

              <!-- Détail + Message -->
              <div class="form-group mt-5">
                <label class="form-label">Détail de l'intervention</label>
                <Textarea
                  v-model="interv.detailAction"
                  :auto-resize="true"
                  :rows="2"
                  placeholder="Précisions complémentaires…"
                  class="w-full"
                />
              </div>

              <div class="form-group mt-3">
                <label class="form-label">Message / Consignes</label>
                <Textarea
                  v-model="interv.message"
                  :auto-resize="true"
                  :rows="2"
                  placeholder="Consignes particulières pour cette intervention…"
                  class="w-full"
                />
              </div>

              <!-- Évaluation / Résultats -->
              <div class="autonomie-eval-section">
                <div class="form-grid-2 mt-3">
                  <div class="form-group mt-0">
                    <label class="form-label">Critère d'évaluation</label>
                    <Textarea
                      v-model="interv.critereEvaluation"
                      :auto-resize="true"
                      :rows="2"
                      placeholder="Comment mesurer l'efficacité…"
                      class="w-full"
                    />
                  </div>
                  <div class="form-group mt-0">
                    <label class="form-label">Résultat des actions</label>
                    <Textarea
                      v-model="interv.resultatActions"
                      :auto-resize="true"
                      :rows="2"
                      placeholder="Résultats obtenus…"
                      class="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- État vide -->
        <div
          v-if="interventions.length === 0"
          class="flex flex-col items-center py-8 text-slate-400 text-sm"
        >
          <CalendarClock :size="32" :stroke-width="1.2" class="mb-2 text-slate-300" />
          Aucune intervention planifiée
        </div>

        <!-- Bouton ajouter -->
        <button class="wizard-add-row mt-3" @click="addIntervention">
          <Plus :size="15" :stroke-width="2" />
          Ajouter une intervention
        </button>
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - PoaAutonomieForm
   * Chemin : frontend/src/components/evaluation/forms/PoaAutonomieForm.vue
   */
  import { ref, watch, onMounted } from 'vue';
  import { Target, CalendarClock, ChevronDown, Plus, Trash2 } from 'lucide-vue-next';
  import InputText from 'primevue/inputtext';
  import Textarea from 'primevue/textarea';
  import Select from 'primevue/select';
  import Checkbox from 'primevue/checkbox';
  import Button from 'primevue/button';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import { parseDateParts, joinDateParts, getCurrentMonth, getCurrentYear } from './dateHelpers';

  // ── Types ────────────────────────────────────────────────────────────

  interface AutonomieIntervention {
    typeAction: string;
    personneChargeAction: string[];
    /** Champ d'affichage pour la saisie virgule-séparée */
    personneChargeDisplay: string;
    joursIntervention: string[];
    secondJoursIntervention: string[];
    /** Date de début — 3 champs séparés (pattern birth-date-input) */
    dateDebutJour: string;
    dateDebutMois: string;
    dateDebutAnnee: string;
    dureeAction: string;
    dureePassage: string;
    momentJournee: string[];
    secondMomentJournee: string[];
    typeAide: string[];
    actions: string[];
    /** Champ temporaire pour saisie libre d'action hors catalogue */
    autreAction: string;
    detailAction: string;
    critereEvaluation: string;
    resultatActions: string;
    message: string;
  }

  // ── Props ─────────────────────────────────────────────────────────────

  interface Props {
    patient: PatientResponse | null;
    initialData?: WizardSectionData;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'update:data', data: WizardSectionData): void;
    (e: 'update:status', status: SectionStatus): void;
  }>();

  // ── Référentiels ─────────────────────────────────────────────────────

  const PREOCCUPATION_OPTIONS = [
    { label: 'Élevée', value: 'Élevée' },
    { label: 'Assez élevée', value: 'Assez élevée' },
    { label: 'Moyenne', value: 'Moyenne' },
    { label: 'Assez faible', value: 'Assez faible' },
    { label: 'Faible', value: 'Faible' },
  ];

  const TYPE_ACTION_OPTIONS = [
    { label: 'Aide à domicile', value: 'Aide à domicile' },
    { label: 'Soins infirmiers', value: 'Soins infirmiers' },
    { label: 'Kinésithérapie', value: 'Kinésithérapie' },
    { label: 'Portage de repas', value: 'Portage de repas' },
    { label: 'Téléassistance', value: 'Téléassistance' },
    { label: 'Accueil de jour', value: 'Accueil de jour' },
    { label: 'Hébergement temporaire', value: 'Hébergement temporaire' },
  ];

  const MOMENT_JOURNEE_OPTIONS = ['Lever', 'Matin', 'Midi', 'Après-midi', 'Soir', 'Nuit'] as const;

  const JOURS_OPTIONS = [
    'Lundi',
    'Mardi',
    'Mercredi',
    'Jeudi',
    'Vendredi',
    'Samedi',
    'Dimanche',
  ] as const;

  const TYPE_AIDE_OPTIONS = [
    'Aide partielle',
    'Tout faire',
    'Stimulation',
    'Surveillance',
  ] as const;

  /** Catalogues d'actions par type d'intervention (référentiels SAAD/SSIAD) */
  const GESTES_PAR_TYPE: Record<string, string[]> = {
    'Aide à domicile': [
      'Aide au lever et/ou coucher',
      'Aide aux transferts',
      'Aide aux déplacements intérieurs',
      'Aide à la toilette',
      "Aide à l'habillage / déshabillage",
      "Aide à l'hygiène de l'élimination",
      'Aide à la prise des repas',
      'Aide à la préparation des repas',
      'Aide aux courses',
      "Aide à l'entretien du logement",
      'Aide aux activités de loisirs',
      "Accompagnement à l'extérieur",
      'Stimulation cognitive',
      'Garde de jour et/ou de nuit',
    ],
    'Soins infirmiers': [
      'Administration des traitements',
      'Préparation du pilulier',
      'Surveillance des constantes',
      'Soins de nursing',
      'Soins de plaies / pansements',
      'Surveillance cutanée',
      'Surveillance nutritionnelle',
      'Éducation thérapeutique',
      'Aide à la prise de médicaments',
      'Coordination avec le médecin',
    ],
    Kinésithérapie: [
      'Mobilisation active / passive',
      "Travail de l'équilibre",
      'Prévention des chutes',
      'Rééducation à la marche',
    ],
  };

  /** Fallback : tous les gestes fusionnés (pour types sans catalogue dédié) */
  const GESTES_TOUS = [...new Set(Object.values(GESTES_PAR_TYPE).flat())];

  /** Retourne le catalogue adapté au type d'action sélectionné */
  function gestesForType(typeAction: string): string[] {
    return GESTES_PAR_TYPE[typeAction] || GESTES_TOUS;
  }

  // ── Fabrique ─────────────────────────────────────────────────────────

  function createEmptyIntervention(): AutonomieIntervention {
    return {
      typeAction: '',
      personneChargeAction: [],
      personneChargeDisplay: '',
      joursIntervention: [],
      secondJoursIntervention: [],
      dateDebutJour: '',
      dateDebutMois: getCurrentMonth(),
      dateDebutAnnee: getCurrentYear(),
      dureeAction: '',
      dureePassage: '',
      momentJournee: [],
      secondMomentJournee: [],
      typeAide: [],
      actions: [],
      autreAction: '',
      detailAction: '',
      critereEvaluation: '',
      resultatActions: '',
      message: '',
    };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- JSON hydration multi-champs, même pattern que poaShared.hydrateProbleme
  function hydrateIntervention(raw: any): AutonomieIntervention {
    const persCharge = Array.isArray(raw.personneChargeAction) ? [...raw.personneChargeAction] : [];
    const { jour, mois, annee } = parseDateParts(raw.dateDebutAction ?? '');
    return {
      typeAction: raw.typeAction ?? '',
      personneChargeAction: persCharge,
      personneChargeDisplay: persCharge.join(', '),
      joursIntervention: Array.isArray(raw.joursIntervention) ? [...raw.joursIntervention] : [],
      secondJoursIntervention: Array.isArray(raw.secondJoursIntervention)
        ? [...raw.secondJoursIntervention]
        : [],
      dateDebutJour: jour,
      dateDebutMois: mois,
      dateDebutAnnee: annee,
      dureeAction: raw.dureeAction ?? '',
      dureePassage: raw.dureePassage ?? '',
      momentJournee: Array.isArray(raw.momentJournee) ? [...raw.momentJournee] : [],
      secondMomentJournee: Array.isArray(raw.secondMomentJournee)
        ? [...raw.secondMomentJournee]
        : [],
      typeAide: Array.isArray(raw.typeAide) ? [...raw.typeAide] : [],
      actions: Array.isArray(raw.actions) ? [...raw.actions] : [],
      autreAction: '',
      detailAction: raw.detailAction ?? '',
      critereEvaluation: raw.critereEvaluation ?? '',
      resultatActions: raw.resultatActions ?? '',
      message: raw.message ?? '',
    };
  }

  // ── État réactif ─────────────────────────────────────────────────────

  const preoccupationPatient = ref('');
  const preoccupationProfessionel = ref('');
  const interventions = ref<AutonomieIntervention[]>([]);

  /** Set des indices de cartes dépliées */
  const expandedCards = ref<Set<number>>(new Set());

  // ── Initialisation depuis initialData ────────────────────────────────

  onMounted(() => {
    const source = props.initialData;

    if (source) {
      preoccupationPatient.value = source.preoccupationPatient ?? '';
      preoccupationProfessionel.value = source.preoccupationProfessionel ?? '';

      if (Array.isArray(source.actions)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- type propagé depuis hydrateIntervention
        interventions.value = source.actions.map((a: any) => hydrateIntervention(a));
      }
    }

    // Émission initiale
    emitData();
  });

  // ── Actions CRUD ─────────────────────────────────────────────────────

  function addIntervention() {
    interventions.value.push(createEmptyIntervention());
    const newIdx = interventions.value.length - 1;
    expandedCards.value.add(newIdx);
  }

  function removeIntervention(index: number) {
    interventions.value.splice(index, 1);
    expandedCards.value.delete(index);
    const updated = new Set<number>();
    for (const idx of expandedCards.value) {
      updated.add(idx > index ? idx - 1 : idx);
    }
    expandedCards.value = updated;
  }

  /** Ajoute une action saisie en texte libre au tableau actions[] si non dupliquée */
  function addCustomAction(interv: AutonomieIntervention) {
    const action = interv.autreAction?.trim();
    if (action && !interv.actions.includes(action)) {
      interv.actions.push(action);
      interv.autreAction = '';
      emitData();
    }
  }

  function toggleCard(index: number) {
    if (expandedCards.value.has(index)) {
      expandedCards.value.delete(index);
    } else {
      expandedCards.value.add(index);
    }
  }

  // ── Sérialisation & émission ─────────────────────────────────────────

  /**
   * Convertit le champ d'affichage virgule-séparé vers le tableau JSON.
   */
  function parsePersonneCharge(display: string): string[] {
    return display
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s !== '');
  }

  /**
   * Toggle « Tous les jours » sur un tableau de jours.
   * Si les 7 jours sont déjà cochés → tout décocher, sinon → tout cocher.
   */
  function toggleAllDays(jours: string[]) {
    if (jours.length === JOURS_OPTIONS.length) {
      jours.splice(0, jours.length);
    } else {
      jours.splice(0, jours.length, ...JOURS_OPTIONS);
    }
  }

  function emitData() {
    const data: WizardSectionData = {
      preoccupationPatient: preoccupationPatient.value,
      preoccupationProfessionel: preoccupationProfessionel.value,
      actions: interventions.value.map((interv) => ({
        typeAction: interv.typeAction,
        personneChargeAction: parsePersonneCharge(interv.personneChargeDisplay),
        joursIntervention: [...interv.joursIntervention],
        secondJoursIntervention: [...interv.secondJoursIntervention],
        dateDebutAction: joinDateParts(
          interv.dateDebutJour,
          interv.dateDebutMois,
          interv.dateDebutAnnee,
        ),
        dureeAction: interv.dureeAction.trim(),
        dureePassage: interv.dureePassage.trim(),
        momentJournee: [...interv.momentJournee],
        secondMomentJournee: [...interv.secondMomentJournee],
        typeAide: [...interv.typeAide],
        actions: [...interv.actions],
        detailAction: interv.detailAction.trim(),
        critereEvaluation: interv.critereEvaluation,
        resultatActions: interv.resultatActions,
        message: interv.message,
      })),
    };
    emit('update:data', data);
    emit('update:status', computeStatus());
  }

  function computeStatus(): SectionStatus {
    if (interventions.value.length === 0) return 'empty';

    const allComplete = interventions.value.every(
      (interv) =>
        interv.typeAction !== '' && interv.momentJournee.length > 0 && interv.actions.length > 0,
    );

    return allComplete ? 'complete' : 'partial';
  }

  // ── Watchers ─────────────────────────────────────────────────────────

  watch(
    [preoccupationPatient, preoccupationProfessionel, interventions],
    () => {
      emitData();
    },
    { deep: true },
  );
</script>

<style scoped>
  /*
 * Styles propres à PoaAutonomieForm.
 * Les classes form-*, wizard-* viennent de main.css.
 */

  /* ── Carte intervention ──────────────────────────── */
  .autonomie-card {
    @apply border border-slate-200 rounded-xl overflow-hidden bg-white;
  }

  .autonomie-card-header {
    @apply flex justify-between items-center p-3 cursor-pointer
         bg-gradient-to-r from-teal-50 to-cyan-50
         hover:from-teal-100 hover:to-cyan-100
         transition-colors duration-150;
  }
  .autonomie-card-num {
    @apply w-6 h-6 rounded-full bg-teal-500 text-white text-xs font-bold
         flex items-center justify-center shrink-0;
  }
  .autonomie-card-moment {
    @apply px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 text-xs font-medium;
  }
  .autonomie-card-duree {
    @apply px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-xs font-medium;
  }

  .autonomie-card-body {
    @apply p-4 border-t border-slate-100;
  }

  .autonomie-eval-section {
    @apply mt-6 pt-4 border-t border-dashed border-slate-200;
  }

  /* ── Grille Semaine 1 / Semaine 2 ────────────────── */
  .poa-week-grid {
    @apply flex flex-col gap-2 mt-2;
  }
  .poa-week-block {
    @apply flex items-start gap-3 p-2.5 rounded-lg bg-slate-50 border border-slate-100;
  }
  .poa-week-label {
    @apply text-xs font-semibold text-slate-500 whitespace-nowrap pt-0.5 w-20 shrink-0;
  }

  /* ── Toggle "Tous les jours" ─────────────────────── */
  .autonomie-toggle-all {
    @apply text-xs text-teal-600 font-medium px-2 py-0.5 rounded
         border border-teal-200 bg-teal-50
         hover:bg-teal-100 hover:border-teal-300
         transition-colors duration-150 cursor-pointer whitespace-nowrap;
  }
</style>