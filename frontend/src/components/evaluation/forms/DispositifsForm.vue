<!--
  CareLink - DispositifsForm
  Chemin : frontend/src/components/evaluation/forms/DispositifsForm.vue

  Rôle : Formulaire de saisie des dispositifs médicaux du patient
         (pace-maker, appareils auditifs, prothèses, etc.).
         Chaque dispositif a un nom, un statut, 3 dates optionnelles et des notes.
         Émet @update:data et @update:status vers le wizard parent.

  Identité visuelle : fieldset slate, classes wizard-* de main.css
-->
<template>
  <div class="space-y-7">
    <!-- ── Fieldset Dispositifs ────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--slate">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--slate">
          <Cpu :size="16" :stroke-width="2" />
        </span>
        Appareillages & dispositifs médicaux
      </legend>

      <!-- Toggle "Aucun dispositif" -->
      <div class="form-grid-2 mt-5">
        <div class="form-group mt-0 col-span-2">
          <label class="flex items-center gap-2 cursor-pointer text-sm text-slate-600">
            <Checkbox v-model="noDispositif" :binary="true" />
            Aucun dispositif médical en place ou à prévoir
          </label>
        </div>
      </div>

      <!-- Liste des dispositifs -->
      <div v-if="!noDispositif" class="mt-5">
        <!-- Ajout rapide depuis le catalogue -->
        <div class="mb-4">
          <p class="text-xs text-slate-500 mb-2 font-medium">Ajout rapide :</p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="item in availableCatalogItems"
              :key="item"
              :title="`Ajouter « ${item} »`"
              class="catalog-chip"
              @click="addFromCatalog(item)"
            >
              <Plus :size="12" :stroke-width="2.5" />
              {{ item }}
            </button>
            <span
              v-if="availableCatalogItems.length === 0"
              class="text-xs text-slate-400 italic py-1"
            >
              Tous les dispositifs du catalogue ont été ajoutés
            </span>
          </div>
        </div>

        <!-- Cartes dispositifs -->
        <div v-if="dispositifs.length > 0" class="space-y-3">
          <div v-for="(disp, idx) in dispositifs" :key="idx" class="dispositif-card">
            <!-- Ligne principale : nom + statut + actions -->
            <div class="dispositif-card__header">
              <div class="flex-1 min-w-0">
                <InputText
                  v-model="disp.dispositif"
                  placeholder="Nom du dispositif"
                  class="w-full"
                  @input="emitData"
                />
              </div>
              <div class="w-40 shrink-0">
                <Select
                  v-model="disp.statut"
                  :options="STATUT_OPTIONS"
                  option-label="label"
                  option-value="value"
                  placeholder="Statut"
                  class="w-full"
                  @change="emitData"
                />
              </div>
              <button
                :title="disp._expanded ? 'Replier les détails' : 'Déplier les détails'"
                class="dispositif-card__toggle"
                @click="toggleExpand(idx)"
              >
                <ChevronDown
                  :size="16"
                  :stroke-width="2"
                  :class="{ 'rotate-180': disp._expanded }"
                  class="transition-transform duration-200"
                />
              </button>
              <button
                class="wizard-delete-row"
                title="Supprimer ce dispositif"
                @click="removeDispositif(idx)"
              >
                <Trash2 :size="15" :stroke-width="2" />
              </button>
            </div>

            <!-- Détails (dates + notes) — dépliable -->
            <div v-if="disp._expanded" class="dispositif-card__details">
              <div class="form-grid-2 mt-3">
                <div class="form-group mt-0">
                  <label class="form-label">Date de pose / installation</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="disp.datePoseJour"
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.datePoseMois"
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.datePoseAnnee"
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                      @input="emitData"
                    />
                  </div>
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Date prochain contrôle</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="disp.dateControleJour"
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.dateControleMois"
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.dateControleAnnee"
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                      @input="emitData"
                    />
                  </div>
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Date de retrait prévue</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="disp.dateRetraitJour"
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.dateRetraitMois"
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                      @input="emitData"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="disp.dateRetraitAnnee"
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                      @input="emitData"
                    />
                  </div>
                </div>
              </div>
              <div class="form-group mt-3">
                <label class="form-label">Notes & observations</label>
                <Textarea
                  v-model="disp.notes"
                  rows="2"
                  placeholder="Informations complémentaires..."
                  class="w-full"
                  auto-resize
                  @input="emitData"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- État vide -->
        <div
          v-if="dispositifs.length === 0"
          class="flex flex-col items-center py-8 text-slate-400 text-sm"
        >
          <Cpu :size="32" :stroke-width="1.2" class="mb-2 text-slate-300" />
          Aucun dispositif ajouté — utilisez le catalogue ou le bouton ci-dessous
        </div>

        <!-- Bouton ajouter -->
        <button class="wizard-add-row mt-3" @click="addDispositif">
          <Plus :size="15" :stroke-width="2" />
          Ajouter un dispositif (saisie libre)
        </button>
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - DispositifsForm
   * Chemin : frontend/src/components/evaluation/forms/DispositifsForm.vue
   */
  import { ref, computed, watch, onMounted } from 'vue';
  import { Cpu, Plus, Trash2, ChevronDown } from 'lucide-vue-next';
  import InputText from 'primevue/inputtext';
  import Select from 'primevue/select';
  import Textarea from 'primevue/textarea';
  import Checkbox from 'primevue/checkbox';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import { parseDateParts, joinDateParts, prefillDateParts } from './dateHelpers';

  // ── Types ─────────────────────────────────────────────────────────────

  interface DispositifItem {
    dispositif: string;
    statut: string | null;
    datePoseJour: string;
    datePoseMois: string;
    datePoseAnnee: string;
    dateControleJour: string;
    dateControleMois: string;
    dateControleAnnee: string;
    dateRetraitJour: string;
    dateRetraitMois: string;
    dateRetraitAnnee: string;
    notes: string;
    /** État UI interne — non sérialisé */
    _expanded: boolean;
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

  // ── Constantes ────────────────────────────────────────────────────────

  const STATUT_OPTIONS = [
    { label: 'Existant', value: 'EXISTANT' },
    { label: 'À prévoir', value: 'PREVOIR' },
    { label: 'Retiré', value: 'RETIRE' },
  ];

  /**
   * Catalogue de dispositifs médicaux courants en gériatrie.
   */
  const CATALOGUE = [
    'Pace-maker',
    'Appareils auditifs',
    'Lunettes / lentilles',
    'Prothèse de hanche',
    'Prothèse de genou',
    'Prothèse dentaire',
    'Sonde urinaire',
    'Sonde gastrique',
    'Pompe à insuline',
    'Oxygénothérapie',
    'Stimulateur neurologique',
    'Défibrillateur implantable',
    'Orthèse',
  ] as const;

  // ── État réactif ──────────────────────────────────────────────────────

  const noDispositif = ref(false);
  const dispositifs = ref<DispositifItem[]>([]);

  // ── Initialisation depuis initialData ─────────────────────────────────

  onMounted(() => {
    if (props.initialData) {
      if (props.initialData.noDispositif === true) {
        noDispositif.value = true;
      } else if (Array.isArray(props.initialData.items)) {
        dispositifs.value = props.initialData.items.map(parseDispositif);
      } else if (Array.isArray(props.initialData)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- dual format wizard/EvalSchema
        dispositifs.value = (props.initialData as any[]).map(parseDispositif);
      }
    }

    emitData();
  });

  /**
   * Parse un dispositif depuis les données sauvegardées ou le JSON Bachelard.
   * Les dates ISO sont parsées en 3 parties (jour / mois / année).
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- JSON hydration multi-champs avec dates parsées
  function parseDispositif(d: any): DispositifItem {
    const pose = parseDateParts(d.datePose ?? '');
    const controle = parseDateParts(d.dateControle ?? '');
    const retrait = parseDateParts(d.dateRetrait ?? '');
    return {
      dispositif: d.dispositif ?? '',
      statut: d.statut ?? null,
      datePoseJour: pose.jour,
      datePoseMois: pose.mois,
      datePoseAnnee: pose.annee,
      dateControleJour: controle.jour,
      dateControleMois: controle.mois,
      dateControleAnnee: controle.annee,
      dateRetraitJour: retrait.jour,
      dateRetraitMois: retrait.mois,
      dateRetraitAnnee: retrait.annee,
      notes: d.notes?.trim() ?? '',
      _expanded: false,
    };
  }

  // ── Catalogue : items non encore ajoutés ──────────────────────────────

  const availableCatalogItems = computed(() => {
    const added = new Set(dispositifs.value.map((d) => d.dispositif.trim().toLowerCase()));
    return CATALOGUE.filter((item) => !added.has(item.toLowerCase()));
  });

  // ── Actions ───────────────────────────────────────────────────────────

  function addDispositif() {
    const dp = prefillDateParts();
    dispositifs.value.push({
      dispositif: '',
      statut: null,
      datePoseJour: dp.jour,
      datePoseMois: dp.mois,
      datePoseAnnee: dp.annee,
      dateControleJour: dp.jour,
      dateControleMois: dp.mois,
      dateControleAnnee: dp.annee,
      dateRetraitJour: '',
      dateRetraitMois: '',
      dateRetraitAnnee: '',
      notes: '',
      _expanded: true,
    });
  }

  function addFromCatalog(name: string) {
    const dp = prefillDateParts();
    dispositifs.value.push({
      dispositif: name,
      statut: 'EXISTANT',
      datePoseJour: dp.jour,
      datePoseMois: dp.mois,
      datePoseAnnee: dp.annee,
      dateControleJour: dp.jour,
      dateControleMois: dp.mois,
      dateControleAnnee: dp.annee,
      dateRetraitJour: '',
      dateRetraitMois: '',
      dateRetraitAnnee: '',
      notes: '',
      _expanded: false,
    });
    emitData();
  }

  function removeDispositif(index: number) {
    dispositifs.value.splice(index, 1);
    emitData();
  }

  function toggleExpand(index: number) {
    dispositifs.value[index]._expanded = !dispositifs.value[index]._expanded;
  }

  // ── Sérialisation & émission ──────────────────────────────────────────

  function emitData() {
    const data: WizardSectionData = {
      noDispositif: noDispositif.value,
      items: dispositifs.value.map((d) => ({
        dispositif: d.dispositif.trim(),
        statut: d.statut,
        datePose: joinDateParts(d.datePoseJour, d.datePoseMois, d.datePoseAnnee) || null,
        dateControle:
          joinDateParts(d.dateControleJour, d.dateControleMois, d.dateControleAnnee) || null,
        dateRetrait:
          joinDateParts(d.dateRetraitJour, d.dateRetraitMois, d.dateRetraitAnnee) || null,
        notes: d.notes.trim(),
      })),
    };
    emit('update:data', data);
    emit('update:status', computeStatus());
  }

  function computeStatus(): SectionStatus {
    if (noDispositif.value) return 'complete';
    if (dispositifs.value.length === 0) return 'empty';

    // Tous les items ont un nom et un statut → complet
    // (les dates et notes sont optionnelles selon le contexte clinique)
    const allComplete = dispositifs.value.every(
      (d) => d.dispositif.trim() !== '' && d.statut !== null,
    );
    if (allComplete) return 'complete';

    return 'partial';
  }

  // ── Watchers ──────────────────────────────────────────────────────────

  watch(noDispositif, () => {
    emitData();
  });
</script>

<style scoped>
  /*
 * Cartes dispositif + chips catalogue.
 * Le reste vient de main.css (form-fieldset, form-grid-2, form-group, etc.)
 */
  .catalog-chip {
    @apply inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
         border border-slate-200 text-slate-600 bg-slate-50
         hover:bg-slate-100 hover:border-slate-300
         transition-colors duration-150 cursor-pointer;
  }

  .dispositif-card {
    @apply rounded-xl border border-slate-200 bg-white p-4;
    transition: box-shadow 0.15s ease;
  }

  .dispositif-card:hover {
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  .dispositif-card__header {
    @apply flex items-center gap-3;
  }

  .dispositif-card__toggle {
    @apply flex items-center justify-center w-8 h-8 rounded-lg
         text-slate-400 hover:text-slate-600 hover:bg-slate-100
         transition-colors duration-150 cursor-pointer;
  }

  .dispositif-card__details {
    @apply mt-3 pt-3 border-t border-slate-100;
  }
</style>