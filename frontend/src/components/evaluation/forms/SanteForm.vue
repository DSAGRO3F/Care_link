<!--
  CareLink - SanteForm
  Chemin : frontend/src/components/evaluation/forms/SanteForm.vue

  Rôle : Section 5/10 du wizard saisie évaluation — État de santé du patient.
         15 blocs : 13 blocs QR (Anxiété, Cardio-respiratoire, Cognition,
         Dépression, Élimination, Général et ressenti, Préparations médicamenteuses,
         Mobilité, Nutrition, Douleur, Polymédications, Sensoriel, Peau)
         + 2 blocs structurés (Seuils, Comorbidités).

         NOTE : les blocs `test[]` sont calculés côté backend — ce formulaire ne
         les renseigne pas. Le formatter SanteBlocSection.vue les affichera depuis
         les données retournées par le serveur.

  Conventions :
  - form-fieldset / form-legend / form-legend-icon--{color}
  - form-grid-2 / form-group / form-label (main.css)
  - Palette slate-* + teal-500/600
  - Icônes Lucide uniquement
  - Emit : @update:data + @update:status
  - null pour "pas de valeur", jamais undefined
-->
<template>
  <div class="space-y-7">
    <template v-for="(bloc, blocIdx) in state.blocs" :key="bloc.nom">
      <!-- ── Séparateur entre blocs ──────────────────────────────────── -->
      <div v-if="blocIdx > 0" class="bloc-separator">
        <div class="bloc-separator__dot"></div>
      </div>

      <!-- ── Bloc SEUILS ────────────────────────────────────────────── -->
      <fieldset v-if="bloc.nom === 'Seuils'" class="form-fieldset">
        <legend class="form-legend">
          <span class="form-legend-icon form-legend-icon--slate">
            <SlidersHorizontal :size="15" />
          </span>
          Seuils de surveillance
        </legend>

        <!-- Tableau des seuils -->
        <div v-if="bloc.seuil && bloc.seuil.length > 0" class="overflow-x-auto mb-4">
          <table class="wizard-inline-table">
            <thead>
              <tr>
                <th>Paramètre</th>
                <th>Min</th>
                <th>Max</th>
                <th>Unité</th>
                <th>Surveillance</th>
                <th class="w-10"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(seuil, seuilIdx) in bloc.seuil" :key="seuilIdx">
                <td class="px-2 py-1.5">
                  <Select
                    v-model="seuil.typeConstante"
                    :options="OPTIONS_TYPE_CONSTANTE"
                    placeholder="Sélectionner..."
                    class="w-full text-sm"
                  />
                </td>
                <td class="px-2 py-1.5 w-24">
                  <InputText
                    v-model="seuil.min"
                    type="number"
                    placeholder="min"
                    class="w-full text-sm"
                  />
                </td>
                <td class="px-2 py-1.5 w-24">
                  <InputText
                    v-model="seuil.max"
                    type="number"
                    placeholder="max"
                    class="w-full text-sm"
                  />
                </td>
                <td class="px-2 py-1.5 w-28">
                  <InputText v-model="seuil.unit" placeholder="mmHg…" class="w-full text-sm" />
                </td>
                <td class="px-2 py-1.5">
                  <InputText
                    v-model="seuil.surveillance"
                    placeholder="1 fois/jour…"
                    class="w-full text-sm"
                  />
                </td>
                <td class="px-2 py-1.5 text-center">
                  <button
                    type="button"
                    class="wizard-delete-row"
                    title="Supprimer ce seuil"
                    @click="removeSeuil(blocIdx, seuilIdx)"
                  >
                    <Trash2 :size="14" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="text-sm text-slate-400 italic mb-4 px-1">
          Aucun seuil défini. Cliquez sur "+ Ajouter" pour en créer un.
        </div>

        <button type="button" class="wizard-add-row" @click="addSeuil(blocIdx)">
          <Plus :size="14" />
          Ajouter un seuil
        </button>
      </fieldset>

      <!-- ── Bloc COMORBIDITÉS ──────────────────────────────────────── -->
      <fieldset v-else-if="bloc.nom === 'Comorbidités'" class="form-fieldset">
        <legend class="form-legend">
          <span class="form-legend-icon form-legend-icon--red">
            <AlertTriangle :size="15" />
          </span>
          Comorbidités
        </legend>

        <div class="space-y-4 mb-4">
          <div
            v-for="(c, cIdx) in bloc.comorbidites"
            :key="cIdx"
            :class="{
              'border-l-4 border-l-red-400': c.Etat === 'Confirmé',
              'border-l-4 border-l-amber-400': c.Etat === 'Suspicion',
              'border-l-4 border-l-violet-400': c.Etat === 'Antécédent',
            }"
            class="border border-slate-200 rounded-lg p-4 bg-slate-50"
          >
            <div class="flex justify-between items-start mb-3">
              <span class="text-sm font-semibold text-slate-700">Comorbidité {{ cIdx + 1 }}</span>
              <button
                type="button"
                class="wizard-delete-row"
                @click="removeComorbidie(blocIdx, cIdx)"
              >
                <Trash2 :size="14" />
              </button>
            </div>

            <div class="form-grid-2">
              <div class="form-group">
                <label class="form-label form-label--required">Affection</label>
                <Select
                  v-model="c.Affection"
                  :options="OPTIONS_AFFECTION"
                  placeholder="Sélectionner..."
                  class="w-full"
                />
              </div>
              <div class="form-group">
                <label class="form-label form-label--required">État pathologique</label>
                <InputText
                  v-model="c['Etat pathologique']"
                  placeholder="Ex : AVC ischémique"
                  class="w-full"
                />
              </div>
            </div>

            <div class="form-grid-2">
              <div class="form-group">
                <label class="form-label">État</label>
                <Select
                  v-model="c.Etat"
                  :options="OPTIONS_ETAT_COMORB"
                  placeholder="Sélectionner..."
                  class="w-full"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Date de diagnostic</label>
                <div class="split-date-input">
                  <InputText
                    v-model="c._diagJour"
                    placeholder="JJ"
                    class="split-date-input__jour"
                    maxlength="2"
                  />
                  <span class="split-date-input__sep">/</span>
                  <InputText
                    v-model="c._diagMois"
                    placeholder="MM"
                    class="split-date-input__mois"
                    maxlength="2"
                  />
                  <span class="split-date-input__sep">/</span>
                  <InputText
                    v-model="c._diagAnnee"
                    placeholder="AAAA"
                    class="split-date-input__annee"
                    maxlength="4"
                  />
                </div>
              </div>
            </div>

            <div class="form-group mt-3">
              <label class="form-label">Diagnostic / précision</label>
              <InputText v-model="c.Diagnostique" class="w-full" />
            </div>

            <div class="form-group mt-3">
              <label class="form-label">Commentaires</label>
              <Textarea v-model="c.Commentaires" rows="2" class="w-full" auto-resize />
            </div>
          </div>

          <div
            v-if="!bloc.comorbidites || bloc.comorbidites.length === 0"
            class="text-sm text-slate-400 italic px-1"
          >
            Aucune comorbidité enregistrée.
          </div>
        </div>

        <button type="button" class="wizard-add-row" @click="addComorbidie(blocIdx)">
          <Plus :size="14" />
          Ajouter une comorbidité
        </button>
      </fieldset>

      <!-- ── Blocs Q/R génériques ───────────────────────────────────── -->
      <fieldset v-else :class="getBlocFieldsetClass(bloc.nom)" class="form-fieldset">
        <legend class="form-legend">
          <span
            :class="`form-legend-icon--${BLOC_META[bloc.nom]?.color ?? 'slate'}`"
            class="form-legend-icon"
          >
            <component :is="BLOC_META[bloc.nom]?.icon ?? 'Activity'" :size="15" />
          </span>
          {{ bloc.nom }}
        </legend>

        <!-- Questions/Réponses principales (exclut les sous-blocs) -->
        <div class="space-y-4">
          <template v-for="(qr, qrIdx) in bloc.questionReponse" :key="qrIdx">
            <template v-if="!isSubBlocQuestion(qr.question) && isQuestionVisible(bloc, qr.question)">
              <!-- Champ commentaire → Textarea pleine largeur -->
              <div v-if="getFieldType(qr.question) === 'textarea'" class="form-group">
                <label class="form-label">{{ qr.question }}</label>
                <Textarea
                  v-model="state.blocs[blocIdx].questionReponse![qrIdx].reponse"
                  rows="2"
                  class="w-full"
                  auto-resize
                />
              </div>

              <!-- Champ OUI/NON → Select -->
              <div v-else-if="getFieldType(qr.question) === 'oui-non'" class="form-group">
                <label class="form-label">{{ getDisplayLabel(qr.question, bloc, qrIdx) }}</label>
                <Select
                  v-model="state.blocs[blocIdx].questionReponse![qrIdx].reponse"
                  :options="OPTIONS_OUI_NON"
                  placeholder="Sélectionner..."
                  class="w-72"
                />
              </div>

              <!-- Champ Select avec options dédiées (ex : sous-questions déficit moteur) -->
              <div v-else-if="getFieldType(qr.question) === 'select'" class="form-group">
                <label class="form-label">{{ qr.question }}</label>
                <Select
                  v-model="state.blocs[blocIdx].questionReponse![qrIdx].reponse"
                  :options="QUESTION_SELECT_OPTIONS[qr.question] ?? []"
                  placeholder="Sélectionner..."
                  class="w-72"
                />
              </div>

              <!-- Champ numérique -->
              <div v-else-if="getFieldType(qr.question) === 'number'" class="form-group">
                <label class="form-label">{{ qr.question }}</label>
                <InputText
                  v-model="state.blocs[blocIdx].questionReponse![qrIdx].reponse"
                  type="number"
                  class="w-40"
                />
              </div>

              <!-- Champ texte libre -->
              <div v-else class="form-group">
                <label class="form-label">{{ getDisplayLabel(qr.question, bloc, qrIdx) }}</label>
                <InputText
                  v-model="state.blocs[blocIdx].questionReponse![qrIdx].reponse"
                  class="w-full"
                />
              </div>
            </template>
          </template>
        </div>

        <!-- ── Sous-bloc amber : mesures physiques SPPB (Mobilité) ──── -->
        <div
          v-if="getSubBlocQRs(bloc, MEASUREMENT_QUESTIONS).length > 0"
          class="mt-4 rounded-lg border-l-4 border-amber-300 bg-amber-50 p-4"
        >
          <div class="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-3">
            <Timer :size="15" />
            <span>Mesures physiques — SPPB</span>
          </div>

          <!-- Grille 3 colonnes : nom du test | durée | date -->
          <div class="space-y-0">
            <template v-for="(test, tIdx) in SPPB_TESTS" :key="'sppb-' + tIdx">
              <div
                :class="{ 'border-t border-amber-200/50': tIdx > 0 }"
                class="grid items-end gap-3 py-2"
                style="grid-template-columns: 1fr 130px 180px"
              >
                <div>
                  <div class="text-sm font-semibold text-amber-800">{{ test.label }}</div>
                  <div class="text-xs text-amber-600/70">{{ test.desc }}</div>
                </div>
                <div
                  v-if="findQRIdx(bloc, test.durationQ) >= 0"
                  class="form-group"
                  style="margin: 0"
                >
                  <label class="form-label text-xs">Durée (s)</label>
                  <InputText
                    v-model="
                      state.blocs[blocIdx].questionReponse![findQRIdx(bloc, test.durationQ)].reponse
                    "
                    type="number"
                    step="0.01"
                    placeholder="ex : 12.62"
                    class="w-full text-sm"
                  />
                </div>
                <div v-if="findQRIdx(bloc, test.dateQ) >= 0" class="form-group" style="margin: 0">
                  <label class="form-label text-xs">Date du test</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="
                        state.blocs[blocIdx].questionReponse![findQRIdx(bloc, test.dateQ)]._jour
                      "
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                      @change="propagateSppbDate(blocIdx, test.dateQ)"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="
                        state.blocs[blocIdx].questionReponse![findQRIdx(bloc, test.dateQ)]._mois
                      "
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                      @change="propagateSppbDate(blocIdx, test.dateQ)"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="
                        state.blocs[blocIdx].questionReponse![findQRIdx(bloc, test.dateQ)]._annee
                      "
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                      @change="propagateSppbDate(blocIdx, test.dateQ)"
                    />
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Résultats calculés (lecture seule) -->
          <div v-if="displayableTests(bloc).length > 0" class="mt-3 space-y-2">
            <div class="text-xs font-medium text-amber-700 uppercase tracking-wide mb-1">
              Résultats
            </div>
            <div
              v-for="(t, tIdx) in displayableTests(bloc)"
              :key="'tr-' + tIdx"
              :class="resultBadgeClasses(t.resultat)"
              class="rounded-md px-3 py-2 text-sm"
            >
              <span class="font-medium">{{ t.nom }} — </span>
              <span>{{ t.resultat }}</span>
            </div>
          </div>
          <p v-else class="mt-3 text-xs text-amber-600 italic">
            Les résultats seront calculés à la soumission de l'évaluation.
          </p>
        </div>

        <!-- ── Sous-bloc indigo : tests auto-scorés (dates + résultats) ── -->
        <div
          v-else-if="getSubBlocQRs(bloc, TEST_DATE_QUESTIONS).length > 0"
          class="mt-4 rounded-lg border-l-4 border-indigo-400 bg-indigo-50 p-4"
        >
          <div class="flex items-center gap-2 text-sm font-semibold text-indigo-800 mb-3">
            <FlaskConical :size="15" />
            <span>Tests cliniques</span>
          </div>

          <!-- Dates d'administration -->
          <div class="flex flex-wrap gap-4 mb-3">
            <template
              v-for="{ qr, idx } in getSubBlocQRs(bloc, TEST_DATE_QUESTIONS)"
              :key="'dt-' + idx"
            >
              <div class="form-group">
                <label class="form-label text-sm">{{ qr.question }}</label>
                <div class="split-date-input">
                  <InputText
                    v-model="state.blocs[blocIdx].questionReponse![idx]._jour"
                    placeholder="JJ"
                    class="split-date-input__jour"
                    maxlength="2"
                  />
                  <span class="split-date-input__sep">/</span>
                  <InputText
                    v-model="state.blocs[blocIdx].questionReponse![idx]._mois"
                    placeholder="MM"
                    class="split-date-input__mois"
                    maxlength="2"
                  />
                  <span class="split-date-input__sep">/</span>
                  <InputText
                    v-model="state.blocs[blocIdx].questionReponse![idx]._annee"
                    placeholder="AAAA"
                    class="split-date-input__annee"
                    maxlength="4"
                  />
                </div>
              </div>
            </template>
          </div>

          <!-- Résultats calculés (lecture seule) -->
          <div v-if="displayableTests(bloc).length > 0" class="space-y-2">
            <div class="text-xs font-medium text-indigo-700 uppercase tracking-wide mb-1">
              Résultats
            </div>
            <div
              v-for="(t, tIdx) in displayableTests(bloc)"
              :key="'tr-' + tIdx"
              :class="resultBadgeClasses(t.resultat)"
              class="rounded-md px-3 py-2 text-sm"
            >
              <span class="font-medium">{{ t.nom }} — </span>
              <span>{{ t.resultat }}</span>
            </div>
          </div>
          <p v-else class="text-xs text-indigo-600 italic">
            Les résultats seront calculés à la soumission de l'évaluation.
          </p>
        </div>
      </fieldset>
    </template>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - SanteForm
   * Chemin : frontend/src/components/evaluation/forms/SanteForm.vue
   */
  import { reactive, watch, onMounted } from 'vue';
  import InputText from 'primevue/inputtext';
  import Textarea from 'primevue/textarea';
  import Select from 'primevue/select';
  import {
    Brain,
    Heart,
    CloudRain,
    Droplets,
    Stethoscope,
    Pill,
    Activity,
    Utensils,
    Zap,
    Package,
    Eye,
    Layers,
    SlidersHorizontal,
    AlertTriangle,
    Plus,
    Trash2,
    FlaskConical,
    Timer,
  } from 'lucide-vue-next';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import type { Component } from 'vue';
  import { parseDateParts, joinDateParts, prefillDateParts } from './dateHelpers';

  // ── Types ────────────────────────────────────────────────────────────

  interface QR {
    question: string;
    reponse: string;
    /** Champs UI-only pour les questions de type date (non sérialisés) */
    _jour?: string;
    _mois?: string;
    _annee?: string;
  }

  interface Seuil {
    typeConstante: string;
    min: string;
    max: string;
    unit: string;
    surveillance: string;
  }

  interface Comorbidite {
    Affection: string;
    'Etat pathologique': string;
    Etat: string;
    'Date de diagnostic': string;
    _diagJour: string;
    _diagMois: string;
    _diagAnnee: string;
    Diagnostique: string;
    Commentaires: string;
  }

  interface TestResult {
    nom: string;
    resultat: string;
  }

  interface BlocSante {
    nom: string;
    questionReponse?: QR[];
    seuil?: Seuil[];
    comorbidites?: Comorbidite[];
    test?: TestResult[];
  }

  // ── Props & Emits ─────────────────────────────────────────────────────

  interface Props {
    patient: PatientResponse | null;
    initialData?: WizardSectionData;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'update:data', data: WizardSectionData): void;
    (e: 'update:status', status: SectionStatus): void;
  }>();

  // ── Référentiels ──────────────────────────────────────────────────────

  const OPTIONS_OUI_NON = ['OUI', 'NON'];

  const OPTIONS_AFFECTION = [
    'Affection Neurologique',
    'Affection Cardio-vasculaire',
    'Affection Respiratoire',
    'Affection Rhumatologique et orthopédique',
    'Affection Endocrinienne et métabolique',
    'Affection Psychiatrique',
    'Affection Digestive',
    'Affection Uro-néphrologique',
    'Affection Oncologique',
    'Affection Sensorielle',
    'Autre',
  ];

  const OPTIONS_ETAT_COMORB = ['Confirmé', 'Suspicion', 'Antécédent', 'Résolu'];

  /** 🔧 B2 : Enum identique à seuilVital.typeConstante dans evaluation_v1.json */
  const OPTIONS_TYPE_CONSTANTE = [
    'Fréquence cardiaque',
    'Tension artérielle systolique',
    'Tension artérielle diastolique',
    'Glycémie capillaire (hémoglucotest)',
    'Hémoglucotest post-prandial',
    'Poids',
    'Saturation en Oxygène',
    'Fréquence respiratoire',
    'Température',
  ];

  // ── Métadonnées par bloc (couleur CSS + icône Lucide) ─────────────────

  const BLOC_META: Record<string, { color: string; icon: Component }> = {
    Anxiété: { color: 'amber', icon: Brain },
    'Cardio-respiratoire': { color: 'red', icon: Heart },
    Cognition: { color: 'violet', icon: Brain },
    Dépression: { color: 'slate', icon: CloudRain },
    Élimination: { color: 'teal', icon: Droplets },
    'Général et ressenti': { color: 'emerald', icon: Stethoscope },
    'Préparations et prise médicamenteuse': { color: 'cyan', icon: Pill },
    Mobilité: { color: 'blue', icon: Activity },
    Nutrition: { color: 'lime', icon: Utensils },
    Douleur: { color: 'pink', icon: Zap },
    Polymédications: { color: 'orange', icon: Package },
    Sensoriel: { color: 'purple', icon: Eye },
    Peau: { color: 'rose', icon: Layers },
  };

  // ── Détection du type de champ ────────────────────────────────────────
  //
  // Priorité : map d'exceptions explicites > textarea pattern > OUI/NON > text

  type FieldType = 'oui-non' | 'select' | 'textarea' | 'text' | 'number' | 'date';

  const QUESTION_TYPE_OVERRIDES: Record<string, FieldType> = {
    // Force 'text' : réponse n'est pas OUI/NON
    'Le patient a-t-il des difficultés pour respirer ?': 'text',
    'Le patient a-t-il des troubles de la sensibilité ?': 'text',
    'Le patient a-t-il présenté une baisse des prises alimentaires ces 3 derniers mois ?': 'text',
    'Le patient a-t-il eu une perte récente de poids au cours des 3 derniers mois ?': 'text',
    'Par rapport aux personnes du même âge, comment le patient, juge-t-il son état de santé ?':
      'text',
    'Localisation de la douleur :': 'text',
    'Type de douleur :': 'select',
    'Évolution temporelle :': 'select',
    'Rythme de la douleur :': 'select',
    'Intensité (EN 0-10) :': 'select',
    'Facteurs aggravants / soulageants :': 'textarea',
    'Recueil de la personne sur son état de santé, ses maladies ?': 'textarea',
    'Voici un cercle, qui représente une horloge. Pouvez vous y écrire les heures (seuls 12-3-6-9 ok), puis dessiner 11 heures 10 (pas besoin de préciser si petite ou grande aiguille) :':
      'text',
    "Pouvez-vous me redonner les 3 mots que je vous ai cité tout à l'heure ?": 'text',
    'Télécharger le dessin réalisé :': 'text',
    // Textareas explicites
    'Ajouter un commentaire :': 'textarea',
    'Ajouter des commentaires :': 'textarea',
    "Ajouter un commentaire (localisation, description, mode d'apparition, etc..) :": 'textarea',
    'Lesquelles ? Précisez les contre-indications médicamenteuses :': 'textarea',
    'Description  des manifestations somatiques de la douleur :': 'textarea',
    'Description des autres problèmes de peau et téguments :': 'textarea',
    'Localisation actuelle des escarres :': 'textarea',
    // Texte libre
    'Difficulté à certains efforts ou ports de charges de la vie quotidienne ?': 'text',
    'Mode de préparation des médicaments :': 'select',
    'Qui prépare les médicaments ?': 'select',
    'Fréquence de la prise médicamenteuse': 'text',
    'Quels traitements ?': 'text',
    'Résultat du test Oreille Droite :': 'text',
    'Résultat du test Oreille Gauche :': 'text',
    'Si oui quel type de régime (plusieurs choix possibles) :': 'text',
    'Sous quelle forme de texture les aliments vous sont-ils présentés ?': 'text',
    'Quels aliments ?': 'text',
    'Quelles difficultés pour mâcher ou avaler les aliments ?': 'text',
    'Qui gère les changements de poche ?': 'text',
    'Qui gère les changements de support de la stomie ?': 'text',
    "Qui gère les changements du collecteur d'urine ?": 'text',
    "Qui s'occupe de sa nutrition entérale ?": 'text',
    "Si oui, de quel(s) type(s) de stomie(s) s'agit-il ?": 'text',
    "Description de la prothèse ou de l'orthèse :": 'textarea',
    // Mobilité — sous-questions déficit moteur (Select avec options dédiées)
    'Déficit moteur — côté atteint :': 'select',
    'Déficit moteur — segment(s) atteint(s) :': 'select',
    'Déficit moteur — étendue :': 'select',
    'Déficit moteur — origine :': 'select',
    'Précisez la localisation :': 'text',
    "Si oui, précisez l'origine de l'aphasie :": 'text',
    'Taille (en cm) :': 'number',
    'Poids (en kg) :': 'number',
    // Sous-blocs mesures physiques (Séquence 4)
    'Durée lever de chaise (secondes) :': 'number',
    'Durée équilibre (secondes) :': 'number',
    'Durée marche 4m (secondes) :': 'number',
    // Dates d'administration des tests
    'Date du test GAI-SF :': 'date',
    'Date des tests cognitifs :': 'date',
    'Date du test Mini-GDS :': 'date',
    'Date du test lever de chaise :': 'date',
    "Date du test d'équilibre :": 'date',
    'Date du test de marche :': 'date',
    'Date des tests nutritionnels :': 'date',
    'Date du test de vision :': 'date',
    "Date du test d'audition :": 'date',
    "Date de l'évaluation Norton :": 'date',
  };

  // ── Options des Selects par question ──────────────────────────────────

  const QUESTION_SELECT_OPTIONS: Record<string, string[]> = {
    'Déficit moteur — côté atteint :': ['Droite', 'Gauche', 'Bilatéral'],
    'Déficit moteur — segment(s) atteint(s) :': [
      'Membre supérieur',
      'Membre inférieur',
      'Membre supérieur et membre inférieur',
    ],
    'Déficit moteur — étendue :': ['Complet', 'Incomplet'],
    'Déficit moteur — origine :': ['Vasculaire', 'Dégénérative', 'Traumatique', 'Autre'],

    'Mode de préparation des médicaments :': [
    'Boîtes d\'origine (pas de reconditionnement)',
    'Pilulier / semainier manuel',
    'Pilulier connecté',
    'PDA en pharmacie (sachets-doses)',
    'Autre',
    ],
    'Qui prépare les médicaments ?': [
    'Le patient lui-même',
    'Un aidant familial / proche',
    'Infirmière (IDEL)',
    'Pharmacie d\'officine (PDA)',
    'Aide-soignant(e)',
    'Autre',
    ],

    'Type de douleur :': [
    'Nociceptive (mécanique)',
    'Nociceptive (inflammatoire)',
    'Neuropathique',
    'Mixte',
    'Non déterminé',
    ],
  'Évolution temporelle :': [
    'Aiguë (< 3 mois)',
    'Chronique (> 3 mois)',
    ],
  'Rythme de la douleur :': [
    'Continue',
    'Intermittente',
    'Par accès',
    'Nocturne prédominante',
    ],
  'Intensité (EN 0-10) :': [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
    ],
  };

  // ── Visibilité conditionnelle ─────────────────────────────────────────
  //
  // Certaines questions ne sont affichées que si une question filtre du
  // même bloc a une valeur spécifique. Ex : les sous-questions "Déficit
  // moteur — …" n'apparaissent que si "Présence d'un déficit moteur ?" = "OUI".

  const CONDITIONAL_QUESTIONS: Record<string, { dependsOn: string; showWhen: string }> = {
    'Déficit moteur — côté atteint :': {
      dependsOn: "Présence d'un déficit moteur ?",
      showWhen: 'OUI',
    },
    'Déficit moteur — segment(s) atteint(s) :': {
      dependsOn: "Présence d'un déficit moteur ?",
      showWhen: 'OUI',
    },
    'Déficit moteur — étendue :': {
      dependsOn: "Présence d'un déficit moteur ?",
      showWhen: 'OUI',
    },
    'Déficit moteur — origine :': {
      dependsOn: "Présence d'un déficit moteur ?",
      showWhen: 'OUI',
    },
    "Description de la prothèse ou de l'orthèse :": {
      dependsOn: 'Porte des prothèses ou orthèses ?',
      showWhen: 'OUI',
    },
    // ── B9 — Polymédication : masquer polymédication si pas de médicaments
    "Le patient prend-il plus de 5 médicaments par jour ? (prescrits ou non)": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "L'ordonnance comprend-elle 1 benzodiazépine ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "L'ordonnance comprend-elle 1 neuroleptique ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "L'ordonnance comprend-elle 1 antidépresseur ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "L'ordonnance comprend-elle 1 AINS per os ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "Le patient prend-il des antalgiques de palier 2 ou 3 ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "Le patient prend-il des anticholinergiques ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "Le patient prend-il des anticoagulants ?": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    "Ajouter un commentaire :": {
    dependsOn: 'Le patient prend-il des médicaments ?',
    showWhen: 'OUI',
  },
    // ── B8 — Douleur : masquer les dimensions si pas de douleurs signalées
  'Localisation de la douleur :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Type de douleur :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Évolution temporelle :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Rythme de la douleur :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Intensité (EN 0-10) :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Facteurs aggravants / soulageants :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Manifestations somatiques de la douleur :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  'Description  des manifestations somatiques de la douleur :': {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  "Ajouter un commentaire (localisation, description, mode d'apparition, etc..) :": {
    dependsOn: 'Le patient signale-t-il des douleurs ?',
    showWhen: 'OUI',
  },
  };

  function isQuestionVisible(bloc: BlocSante, question: string): boolean {
    const cond = CONDITIONAL_QUESTIONS[question];
    if (!cond) return true;
    const depQR = bloc.questionReponse?.find((q) => q.question === cond.dependsOn);
    return depQR?.reponse === cond.showWhen;
  }

  function getFieldType(question: string): FieldType {
    if (question in QUESTION_TYPE_OVERRIDES) return QUESTION_TYPE_OVERRIDES[question];
    if (/ajouter.*commentaire|commentaire|précisez|décrire|description/i.test(question))
      return 'textarea';
    // Questions se terminant par "?" sans mot interrogatif de choix → OUI/NON
    if (
      /\?$/.test(question.trim()) &&
      !/^(comment|quel|lesquel|qu'est|où|sur une)/i.test(question.trim())
    )
      return 'oui-non';
    return 'text';
  }

  /**
   * Libellé affiché pour les questions qui apparaissent plusieurs fois
   * dans le même bloc.
   * Ajoute (2), (3)… pour les occurrences suivantes.
   */
  function getDisplayLabel(question: string, bloc: BlocSante, currentIdx: number): string {
    const qrs = bloc.questionReponse ?? [];
    const sameCount = qrs.filter((q, i) => q.question === question && i < currentIdx).length;
    if (sameCount === 0) return question;
    return `${question} (${sameCount + 1})`;
  }

  // ── Sous-blocs tests cliniques ──────────────────────────────────────
  //
  // Questions rendues dans les sous-blocs dédiés (amber/indigo), pas
  // dans la boucle QR principale.

  const MEASUREMENT_QUESTIONS = new Set([
    'Durée lever de chaise (secondes) :',
    'Durée équilibre (secondes) :',
    'Durée marche 4m (secondes) :',
  ]);

  const TEST_DATE_QUESTIONS = new Set([
    'Date du test GAI-SF :',
    'Date des tests cognitifs :',
    'Date du test Mini-GDS :',
    'Date du test lever de chaise :',
    "Date du test d'équilibre :",
    'Date du test de marche :',
    'Date des tests nutritionnels :',
    'Date du test de vision :',
    "Date du test d'audition :",
    "Date de l'évaluation Norton :",
  ]);

  const SUB_BLOC_QUESTIONS = new Set([...MEASUREMENT_QUESTIONS, ...TEST_DATE_QUESTIONS]);

  /** Définition structurée des 3 tests SPPB pour le layout 3 colonnes */
  const SPPB_TESTS = [
    {
      label: 'Lever de chaise',
      desc: '5 levers chronométrés',
      durationQ: 'Durée lever de chaise (secondes) :',
      dateQ: 'Date du test lever de chaise :',
    },
    {
      label: 'Équilibre statique',
      desc: 'Pieds joints, semi-tandem, tandem',
      durationQ: 'Durée équilibre (secondes) :',
      dateQ: "Date du test d'équilibre :",
    },
    {
      label: 'Marche 4 mètres',
      desc: 'Vitesse de marche chronométrée',
      durationQ: 'Durée marche 4m (secondes) :',
      dateQ: 'Date du test de marche :',
    },
  ];

  /** Retrouve l'index d'une question dans le bloc */
  function findQRIdx(bloc: BlocSante, question: string): number {
    return (bloc.questionReponse ?? []).findIndex((qr) => qr.question === question);
  }

  /**
   * Propage la date saisie dans un test SPPB aux autres tests du même bloc,
   * uniquement si leur champ date est encore vide.
   * Les 3 tests SPPB sont généralement administrés le même jour.
   */
  function propagateSppbDate(blocIdx: number, sourceQuestion: string) {
    const bloc = state.blocs[blocIdx];
    const srcIdx = findQRIdx(bloc, sourceQuestion);
    if (srcIdx < 0) return;

    const src = bloc.questionReponse![srcIdx];
    // Ne propager que si les 3 parties sont renseignées
    if (!src._jour || !src._mois || !src._annee) return;

    for (const test of SPPB_TESTS) {
      const idx = findQRIdx(bloc, test.dateQ);
      if (idx >= 0 && !bloc.questionReponse![idx]._jour) {
        bloc.questionReponse![idx]._jour = src._jour;
        bloc.questionReponse![idx]._mois = src._mois;
        bloc.questionReponse![idx]._annee = src._annee;
      }
    }
  }

  /**
   * Retourne la classe CSS qui colore le fieldset selon le bloc.
   * Les classes .form-fieldset--{color} sont définies dans main.css.
   */
  function getBlocFieldsetClass(blocNom: string): string {
    const color = BLOC_META[blocNom]?.color ?? 'slate';
    return `form-fieldset--${color}`;
  }

  function isSubBlocQuestion(question: string): boolean {
    return SUB_BLOC_QUESTIONS.has(question);
  }

  function getSubBlocQRs(bloc: BlocSante, filterSet: Set<string>): { qr: QR; idx: number }[] {
    return (bloc.questionReponse ?? [])
      .map((qr, idx) => ({ qr, idx }))
      .filter(({ qr }) => filterSet.has(qr.question));
  }

  /**
   * Sévérité pour le badge coloré d'un résultat de test.
   * Les dates (format DD/MM/YYYY) ne reçoivent pas de badge.
   */
  function getResultSeverity(resultat: string): 'green' | 'amber' | 'red' | 'slate' {
    const l = resultat.toLowerCase();
    if (/^\s*\d{2}\/\d{2}\/\d{4}\s*$/.test(resultat)) return 'slate';
    if (/avérée|sévère|significati|élevé|très perturbé|impossible|très ralenti/.test(l))
      return 'red';
    if (/risque|modéré|perturbé|surveiller|légèrement|ralenti|1\/5|2\/5/.test(l)) return 'amber';
    if (/normal|pas de |ne fait pas|ne présente pas|correct|excellent/.test(l)) return 'green';
    return 'slate';
  }

  /** Set des questions date SPPB (pour initDatePartsOnQRs) */
  const MEASUREMENT_DATE_SET = new Set(SPPB_TESTS.map((t) => t.dateQ));

  /**
   * Initialise les champs _jour/_mois/_annee sur les QR de type date.
   * Si la QR a déjà une reponse (hydratation), la parse en 3 parties.
   * Sinon pré-remplit mois+année courants.
   */
  function initDatePartsOnQRs() {
    const dp = prefillDateParts();
    for (const bloc of state.blocs) {
      if (bloc.questionReponse) {
        for (const qr of bloc.questionReponse) {
          if (TEST_DATE_QUESTIONS.has(qr.question) || MEASUREMENT_DATE_SET.has(qr.question)) {
            if (qr.reponse) {
              const parts = parseDateParts(qr.reponse);
              qr._jour = parts.jour;
              qr._mois = parts.mois || dp.mois;
              qr._annee = parts.annee || dp.annee;
            } else {
              qr._jour = dp.jour;
              qr._mois = dp.mois;
              qr._annee = dp.annee;
            }
          }
        }
      }
      if (bloc.comorbidites) {
        for (const c of bloc.comorbidites) {
          if (c['Date de diagnostic']) {
            const parts = parseDateParts(c['Date de diagnostic']);
            c._diagJour = parts.jour;
            c._diagMois = parts.mois || dp.mois;
            c._diagAnnee = parts.annee || dp.annee;
          } else {
            c._diagJour = dp.jour;
            c._diagMois = dp.mois;
            c._diagAnnee = dp.annee;
          }
        }
      }
    }
  }

  /**
   * Synchronise les _jour/_mois/_annee → reponse (DD/MM/YYYY) sur les QR date,
   * et _diagJour/_diagMois/_diagAnnee → 'Date de diagnostic' sur les comorbidités.
   * Appelé dans le watcher avant émission.
   */
  function syncDatePartsToValues() {
    for (const bloc of state.blocs) {
      if (bloc.questionReponse) {
        for (const qr of bloc.questionReponse) {
          if (qr._jour !== undefined) {
            const iso = joinDateParts(qr._jour ?? '', qr._mois ?? '', qr._annee ?? '');
            // Stocker en DD/MM/YYYY pour compatibilité existante
            if (iso) {
              const [y, m, d] = iso.split('-');
              qr.reponse = `${d}/${m}/${y}`;
            } else {
              qr.reponse = '';
            }
          }
        }
      }
      if (bloc.comorbidites) {
        for (const c of bloc.comorbidites) {
          c['Date de diagnostic'] = joinDateParts(c._diagJour, c._diagMois, c._diagAnnee);
        }
      }
    }
  }

  /**
   * Filtre les entrées test[] en retirant les lignes date-only
   * (déjà couvertes par les champs date du sous-bloc).
   */
  function displayableTests(bloc: BlocSante): TestResult[] {
    return (bloc.test ?? []).filter(
      (t) => !/^\s*\d{2}\/\d{2}\/\d{4}\s*$/.test(t.resultat) && t.resultat.trim() !== '',
    );
  }

  /**
   * Classes Tailwind pour le badge coloré d'un résultat de test.
   */
  function resultBadgeClasses(resultat: string): string {
    const severity = getResultSeverity(resultat);
    const map: Record<string, string> = {
      green: 'bg-emerald-50 text-emerald-800 border border-emerald-200',
      amber: 'bg-amber-50 text-amber-800 border border-amber-200',
      red: 'bg-red-50 text-red-800 border border-red-200',
      slate: 'bg-slate-50 text-slate-600 border border-slate-200',
    };
    return map[severity] ?? map.slate;
  }

  // ── Template initial des blocs ────────────────────────────────────────
  //
  // Miroir exact du format JSON attendu par SanteBlocSection.vue.
  // Les blocs test[] sont omis (calculés backend).

  const SANTE_TEMPLATE: BlocSante[] = [
    {
      nom: 'Anxiété',
      questionReponse: [
        { question: "Le patient vit-il beaucoup dans l'inquiétude ?", reponse: '' },
        { question: 'Un rien le dérange ?', reponse: '' },
        { question: 'Le patient se considère-t-il comme étant de nature inquiète ?', reponse: '' },
        { question: 'Le patient se sent-il souvent nerveux ?', reponse: '' },
        {
          question:
            "Lui arrive-t-il souvent que ses propres pensées suscitent de l'anxiété chez lui ?",
          reponse: '',
        },
        { question: 'Date du test GAI-SF :', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Cardio-respiratoire',
      questionReponse: [
        { question: 'Le patient a-t-il des difficultés pour respirer ?', reponse: '' },
        { question: "Le patient reçoit-il de l'oxygène sur prescription médicale ?", reponse: '' },
        { question: 'Le patient dort-il en position demi assise ?', reponse: '' },
        { question: "Le patient est-il porteur(se) d'un Pace maker ?", reponse: '' },
        { question: 'Le patient a-t-il les jambes qui gonflent ?', reponse: '' },
        {
          question:
            'Le patient dort-il avec les jambes surélevées et/ou porte-t-il des bas de contention ?',
          reponse: '',
        },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Cognition',
      questionReponse: [
        { question: "Le patient perd-il ses mots quand il s'exprime ?", reponse: '' },
        { question: 'Le patient présente-t-il une aphasie ?', reponse: '' },
        { question: "Si oui, précisez l'origine de l'aphasie :", reponse: '' },
        { question: "Le patient a-t-il des problèmes de mémoire ou d'orientation ?", reponse: '' },
        {
          question: 'Ces problèmes se sont-ils aggravés au cours des 4 derniers mois ?',
          reponse: '',
        },
        {
          question:
            'Répétez ces 3 mots après moi — saisir les 3 mots rappelés ci-dessous (liste 1 : DRAPEAU, FLEUR, PORTE) :',
          reponse: '',
        },
        {
          question:
            'Voici un cercle, qui représente une horloge. Pouvez vous y écrire les heures (seuls 12-3-6-9 ok), puis dessiner 11 heures 10 (pas besoin de préciser si petite ou grande aiguille) :',
          reponse: '',
        },
        {
          question: "Pouvez-vous me redonner les 3 mots que je vous ai cité tout à l'heure ?",
          reponse: '',
        },
        { question: 'Date des tests cognitifs :', reponse: '' },
        { question: 'Télécharger le dessin réalisé :', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Dépression',
      questionReponse: [
        { question: 'Le patient se sent-il découragé et triste ?', reponse: '' },
        { question: 'Le patient est-il heureux la plupart du temps ?', reponse: '' },
        {
          question:
            "A-t-il le sentiment que sa vie est vide, qu'il a perdu l'intérêt ou le plaisir de faire les choses ?",
          reponse: '',
        },
        {
          question: "Le patient a-t-il l'impression que sa situation est désespérée ?",
          reponse: '',
        },
        {
          question:
            "Cela l'empêche-t-il de s'engager dans des activités ou d'entreprendre certaines choses ?",
          reponse: '',
        },
        { question: 'Date du test Mini-GDS :', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Élimination',
      questionReponse: [
        { question: 'Le patient est-il stomisé ?', reponse: '' },
        { question: "Si oui, de quel(s) type(s) de stomie(s) s'agit-il ?", reponse: '' },
        { question: 'Qui gère les changements de poche ?', reponse: '' },
        { question: 'Qui gère les changements de support de la stomie ?', reponse: '' },
        { question: 'Le patient ressent-il des troubles du transit intestinal ?', reponse: '' },
        {
          question:
            "Le patient est-il porteur d'une sonde vésicale à demeure ou d'un étui pénien ?",
          reponse: '',
        },
        { question: "Qui gère les changements du collecteur d'urine ?", reponse: '' },
        {
          question: 'Le patient éprouve-t-il habituellement des difficultés pour uriner ?',
          reponse: '',
        },
        { question: 'Le patient porte-t-il des protections ?', reponse: '' },
        { question: 'Si oui, précisez le type et le moment de port :', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Général et ressenti',
      questionReponse: [
        { question: 'Recueil de la personne sur son état de santé, ses maladies ?', reponse: '' },
        {
          question:
            'Par rapport aux personnes du même âge, comment le patient, juge-t-il son état de santé ?',
          reponse: '',
        },
        {
          question: 'Le patient a-t-il été hospitalisé au cours des 6 derniers mois ?',
          reponse: '',
        },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Préparations et prise médicamenteuse',
      questionReponse: [
        { question: 'Contre-indications médicamenteuses ?', reponse: '' },
        { question: 'Lesquelles ? Précisez les contre-indications médicamenteuses :', reponse: '' },
        { question: 'Fréquence de la prise médicamenteuse', reponse: '' },
        { question: 'Quels traitements ?', reponse: '' },
        { question: 'Mode de préparation des médicaments :', reponse: '' }, // comment sont ils préparés ?
        { question: 'Qui prépare les médicaments ?', reponse: '' }, // dispensé par
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Mobilité',
      questionReponse: [
        // Déficit moteur : 1 filtre + 4 sous-questions conditionnelles
        { question: "Présence d'un déficit moteur ?", reponse: '' },
        { question: 'Déficit moteur — côté atteint :', reponse: '' },
        { question: 'Déficit moteur — segment(s) atteint(s) :', reponse: '' },
        { question: 'Déficit moteur — étendue :', reponse: '' },
        { question: 'Déficit moteur — origine :', reponse: '' },
        // Efforts
        {
          question: 'Difficulté à certains efforts ou ports de charges de la vie quotidienne ?',
          reponse: '',
        },
        // Prothèses/orthèses : filtres OUI/NON puis description conditionnelle
        { question: 'Porte des prothèses ou orthèses ?', reponse: '' },
        { question: 'Porte des chaussures orthopédiques ?', reponse: '' },
        { question: "Description de la prothèse ou de l'orthèse :", reponse: '' },
        // SPPB
        { question: 'Durée lever de chaise (secondes) :', reponse: '' },
        { question: 'Date du test lever de chaise :', reponse: '' },
        { question: 'Durée équilibre (secondes) :', reponse: '' },
        { question: "Date du test d'équilibre :", reponse: '' },
        { question: 'Durée marche 4m (secondes) :', reponse: '' },
        { question: 'Date du test de marche :', reponse: '' },
        { question: 'Ajouter des commentaires :', reponse: '' },
      ],
    },
    {
      nom: 'Nutrition',
      questionReponse: [
        { question: "Le patient s'alimente-t-il via une sonde ?", reponse: '' },
        { question: 'Quel type de sonde est utilisée pour sa nutrition ?', reponse: '' },
        {
          question:
            'Le patient a-t-il présenté une baisse des prises alimentaires ces 3 derniers mois ?',
          reponse: '',
        },
        {
          question:
            'Le patient a-t-il eu une perte récente de poids au cours des 3 derniers mois ?',
          reponse: '',
        },
        {
          question:
            'Le patient a-t-il eu une maladie aigüe ou un stress psychologique au cours des 3 derniers mois :',
          reponse: '',
        },
        {
          question: 'Un régime est-il médicalement prescrit et suivi par le patient ?',
          reponse: '',
        },
        { question: 'Si oui quel type de régime (plusieurs choix possibles) :', reponse: '' },
        { question: 'Le patient est-il allergique à certains aliments ?', reponse: '' },
        { question: 'Quels aliments ?', reponse: '' },
        {
          question: 'Le patient éprouve-t-il des difficultés pour mâcher ou avaler les aliments ?',
          reponse: '',
        },
        { question: 'Quelles difficultés pour mâcher ou avaler les aliments ?', reponse: '' },
        {
          question: 'Sous quelle forme de texture les aliments vous sont-ils présentés ?',
          reponse: '',
        },
        { question: 'Le patient porte-t-il un appareil dentaire ?', reponse: '' },
        { question: "Continue-t-il à s'hydrater par la bouche ?", reponse: '' },
        { question: "Qui s'occupe de sa nutrition entérale ?", reponse: '' },
        { question: 'Taille (en cm) :', reponse: '' },
        { question: 'Poids (en kg) :', reponse: '' },
        { question: 'Date des tests nutritionnels :', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Douleur',
      questionReponse: [
        { question: 'Le patient est-il en mesure de communiquer sur ses douleurs ?', reponse: '' },
        { question: 'Le patient signale-t-il des douleurs ?', reponse: '' },
        // ── B8 — 6 dimensions cliniques SFETD/HAS ──
        { question: 'Localisation de la douleur :', reponse: '' },
        { question: 'Type de douleur :', reponse: '' },
        { question: 'Évolution temporelle :', reponse: '' },
        { question: 'Rythme de la douleur :', reponse: '' },
        { question: 'Intensité (EN 0-10) :', reponse: '' },
        { question: 'Facteurs aggravants / soulageants :', reponse: '' },
        // ── Manifestations et commentaires ──
        { question: 'Manifestations somatiques de la douleur :', reponse: '' },
        { question: 'Description  des manifestations somatiques de la douleur :', reponse: '' },
        {
          question:
            "Ajouter un commentaire (localisation, description, mode d'apparition, etc..) :",
          reponse: '',
        },
      ],
    },
    {
      nom: 'Polymédications',
      questionReponse: [
        { question: 'Le patient prend-il des médicaments ?', reponse: '' },
        {
          question: 'Le patient prend-il plus de 5 médicaments par jour ? (prescrits ou non)',
          reponse: '',
        },
        { question: "L'ordonnance comprend-elle 1 benzodiazépine ?", reponse: '' },
        { question: "L'ordonnance comprend-elle 1 neuroleptique ?", reponse: '' },
        { question: "L'ordonnance comprend-elle 1 antidépresseur ?", reponse: '' },
        { question: "L'ordonnance comprend-elle 1 AINS per os ?", reponse: '' },
        { question: 'Le patient prend-il des antalgiques de palier 2 ou 3 ?', reponse: '' },
        { question: 'Le patient prend-il des anticholinergiques ?', reponse: '' },
        { question: 'Le patient prend-il des anticoagulants ?', reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Sensoriel',
      questionReponse: [
        {
          question: 'Le patient porte-t-il des lunettes ou des lentilles de contact ?',
          reponse: '',
        },
        {
          question:
            "Le patient a-t-il des problèmes oculaires et non oculaires, des difficultés pour voir de loin ou pour lire ? Des maladies oculaires ? Du diabète ? De l'HTA ?",
          reponse: '',
        },
        { question: 'Le patient a-t-il des troubles de la sensibilité ?', reponse: '' },
        { question: 'Précisez la localisation :', reponse: '' },
        {
          question:
            "Le patient a-t-il l'impression que son audition a baissé au cours des 4 derniers mois ou depuis votre dernière évaluation ?",
          reponse: '',
        },
        { question: 'Le patient a-t-il un appareil auditif ?', reponse: '' },
        { question: 'Résultat du test Oreille Droite :', reponse: '' },
        { question: 'Résultat du test Oreille Gauche :', reponse: '' },
        { question: 'Date du test de vision :', reponse: '' },
        { question: "Date du test d'audition :", reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Peau',
      questionReponse: [
        { question: "Le patient a-t-il des antécédents d'escarres ?", reponse: '' },
        { question: 'Le patient présente-t-il actuellement des escarres ?', reponse: '' },
        { question: 'Localisation actuelle des escarres :', reponse: '' },
        {
          question: "Le patient possède-t-il d'autres problèmes de peau et téguments ?",
          reponse: '',
        },
        { question: 'Description des autres problèmes de peau et téguments :', reponse: '' },
        { question: "Date de l'évaluation Norton :", reponse: '' },
        { question: 'Ajouter un commentaire :', reponse: '' },
      ],
    },
    {
      nom: 'Seuils',
      seuil: [],
    },
    {
      nom: 'Comorbidités',
      comorbidites: [],
    },
  ];

  // ── État réactif ──────────────────────────────────────────────────────

  const state = reactive<{ blocs: BlocSante[] }>({ blocs: [] });

  // ── Helpers Seuils / Comorbidités ─────────────────────────────────────

  function addSeuil(blocIdx: number) {
    state.blocs[blocIdx].seuil!.push({
      typeConstante: '',
      min: '',
      max: '',
      unit: '',
      surveillance: '',
    });
  }

  function removeSeuil(blocIdx: number, seuilIdx: number) {
    state.blocs[blocIdx].seuil!.splice(seuilIdx, 1);
  }

  function addComorbidie(blocIdx: number) {
    const dp = prefillDateParts();
    state.blocs[blocIdx].comorbidites!.push({
      Affection: '',
      'Etat pathologique': '',
      Etat: '',
      'Date de diagnostic': '',
      _diagJour: dp.jour,
      _diagMois: dp.mois,
      _diagAnnee: dp.annee,
      Diagnostique: '',
      Commentaires: '',
    });
  }

  function removeComorbidie(blocIdx: number, cIdx: number) {
    state.blocs[blocIdx].comorbidites!.splice(cIdx, 1);
  }

  // ── Sérialisation ─────────────────────────────────────────────────────
  //
  // Retourne { blocs } — format attendu par SanteBlocSection.vue.
  // Les blocs test[] sont préservés s'ils existent (calculés backend).

  function buildData(): WizardSectionData {
    // Sérialise les seuils en convertissant min/max string → number pour le backend
    const blocs = state.blocs.map((bloc) => {
      const out: Record<string, unknown> = { ...bloc };
      if (bloc.nom === 'Seuils' && bloc.seuil) {
        out.seuil = bloc.seuil.map((s) => ({
          ...s,
          min: s.min !== '' ? parseFloat(s.min) : null,
          max: s.max !== '' ? parseFloat(s.max) : null,
        }));
      }
      // Préserver test[] s'il existe (retourné par le backend après soumission)
      if (bloc.test && bloc.test.length > 0) {
        out.test = bloc.test;
      }
      return out;
    });
    return { blocs };
  }

  // ── Calcul du statut ──────────────────────────────────────────────────
  //
  // complete  : au moins 5 blocs avec 1+ réponse non vide
  // partial   : au moins 1 champ quelconque renseigné
  // empty     : aucun champ renseigné

  function computeStatus(): SectionStatus {
    let blocsRenseignes = 0;

    for (const bloc of state.blocs) {
      if (bloc.questionReponse) {
        const hasAnswer = bloc.questionReponse.some((qr) => qr.reponse.trim() !== '');
        if (hasAnswer) blocsRenseignes++;
      }
      if (bloc.seuil && bloc.seuil.length > 0) blocsRenseignes++;
      if (bloc.comorbidites && bloc.comorbidites.length > 0) blocsRenseignes++;
    }

    if (blocsRenseignes >= 5) return 'complete';
    if (blocsRenseignes > 0) return 'partial';
    return 'empty';
  }

  // ── Chargement depuis initialData ─────────────────────────────────────
  //
  // Charge les données de la réévaluation (mode pré-remplissage).
  // Matching : par nom de bloc, puis par question+index pour les QR.

  function loadFromInitialData(data: WizardSectionData) {
    const incomingBlocs: BlocSante[] = data?.blocs ?? [];
    const incomingByName: Record<string, BlocSante> = {};
    for (const b of incomingBlocs) {
      incomingByName[b.nom] = b;
    }

    for (const bloc of state.blocs) {
      const src = incomingByName[bloc.nom];
      if (!src) continue;

      if (bloc.questionReponse && src.questionReponse) {
        // Remplir par index (préserve les entrées multivaluées)
        for (let i = 0; i < bloc.questionReponse.length; i++) {
          if (src.questionReponse[i]) {
            bloc.questionReponse[i].reponse = src.questionReponse[i].reponse ?? '';
          }
        }
      }
      if (bloc.nom === 'Seuils' && src.seuil) {
        bloc.seuil = src.seuil.map((s) => ({
          ...s,
          min: s.min !== null ? String(s.min) : '',
          max: s.max !== null ? String(s.max) : '',
        }));
      }
      if (bloc.nom === 'Comorbidités' && src.comorbidites) {
        bloc.comorbidites = src.comorbidites.map((c) => ({ ...c }));
      }
      // Charger test[] s'ils existent (résultats calculés backend)
      if (src.test && src.test.length > 0) {
        bloc.test = src.test.map((t) => ({ ...t }));
      }
    }
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────

  onMounted(() => {
    // Deep clone du template pour éviter toute mutation du const
    state.blocs = JSON.parse(JSON.stringify(SANTE_TEMPLATE));

    if (props.initialData && Object.keys(props.initialData).length > 0) {
      loadFromInitialData(props.initialData);
    }

    // Initialiser les champs split-date sur toutes les QR date et comorbidités
    initDatePartsOnQRs();

    emit('update:data', buildData());
    emit('update:status', computeStatus());
  });

  // ── Réactivité ────────────────────────────────────────────────────────

  watch(
    () => state.blocs,
    () => {
      syncDatePartsToValues();
      emit('update:data', buildData());
      emit('update:status', computeStatus());
    },
    { deep: true },
  );
</script>