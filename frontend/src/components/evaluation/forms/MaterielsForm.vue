<!--
  CareLink - MaterielsForm
  Chemin : frontend/src/components/evaluation/forms/MaterielsForm.vue

  Rôle : Formulaire de saisie des matériels et équipements du patient.
         Chaque item a un nom (sélection ou saisie libre) et un statut (EXISTANT, A PREVOIR, COMMANDE, LIVRE).
         Émet @update:data et @update:status vers le wizard parent.

  Identité visuelle : fieldset emerald, classes wizard-* de main.css
-->
<template>
  <div class="space-y-7">
    <!-- ── Fieldset Matériels ──────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--emerald">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--emerald">
          <Armchair :size="16" :stroke-width="2" />
        </span>
        Matériels & équipements
      </legend>

      <!-- Toggle "Aucun matériel" -->
      <div class="form-grid-2 mt-5">
        <div class="form-group mt-0 col-span-2">
          <label class="flex items-center gap-2 cursor-pointer text-sm text-slate-600">
            <Checkbox v-model="noMateriel" :binary="true" />
            Aucun matériel nécessaire ou en place
          </label>
        </div>
      </div>

      <!-- Tableau de matériels -->
      <div v-if="!noMateriel" class="mt-5">
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
              Tous les équipements du catalogue ont été ajoutés
            </span>
          </div>
        </div>

        <!-- Table des matériels saisis -->
        <table v-if="materiels.length > 0" class="wizard-inline-table">
          <thead>
            <tr>
              <th style="width: 55%">Matériel</th>
              <th style="width: 30%">Statut</th>
              <th style="width: 15%"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(mat, idx) in materiels" :key="idx">
              <td>
                <InputText
                  v-model="mat.materiel"
                  placeholder="Nom du matériel"
                  class="w-full"
                  @input="emitData"
                />
              </td>
              <td>
                <Select
                  v-model="mat.statut"
                  :options="STATUT_OPTIONS"
                  option-label="label"
                  option-value="value"
                  placeholder="Statut"
                  class="w-full"
                  @change="emitData"
                />
              </td>
              <td class="text-center">
                <button
                  class="wizard-delete-row"
                  title="Supprimer ce matériel"
                  @click="removeMateriel(idx)"
                >
                  <Trash2 :size="15" :stroke-width="2" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- État vide -->
        <div
          v-if="materiels.length === 0"
          class="flex flex-col items-center py-8 text-slate-400 text-sm"
        >
          <Package :size="32" :stroke-width="1.2" class="mb-2 text-slate-300" />
          Aucun matériel ajouté — utilisez le catalogue ou le bouton ci-dessous
        </div>

        <!-- Bouton ajouter -->
        <button class="wizard-add-row mt-3" @click="addMateriel">
          <Plus :size="15" :stroke-width="2" />
          Ajouter un matériel (saisie libre)
        </button>
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - MaterielsForm
   * Chemin : frontend/src/components/evaluation/forms/MaterielsForm.vue
   */
  import { ref, computed, watch, onMounted } from 'vue';
  import { Armchair, Plus, Trash2, Package } from 'lucide-vue-next';
  import InputText from 'primevue/inputtext';
  import Select from 'primevue/select';
  import Checkbox from 'primevue/checkbox';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';

  // ── Types ─────────────────────────────────────────────────────────────

  interface MaterielItem {
    materiel: string;
    statut: string | null;
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
    { label: 'À prévoir', value: 'A PREVOIR' },
    { label: 'Commandé', value: 'COMMANDE' },
    { label: 'Livré', value: 'LIVRE' },
  ];

  /**
   * Catalogue de matériels gériatriques courants.
   * Permet un ajout rapide en un clic, sans saisie libre.
   */
  const CATALOGUE = [
    'Lit médicalisé à hauteur variable',
    'Matelas anti-escarres',
    'Potence de lit fixe pour lit médicalisé',
    'Fauteuil roulant',
    'Fauteuil de douche roulant',
    'Déambulateur',
    'Canne de marche',
    "Barre d'appui WC",
    "Barre d'appui douche",
    'Réhausseur WC',
    'Bassin de lit',
    'Urinal',
    'Lève-personne',
    'Verticalisateur',
    'Table de lit roulante',
  ] as const;

  // ── État réactif ──────────────────────────────────────────────────────

  const noMateriel = ref(false);
  const materiels = ref<MaterielItem[]>([]);

  // ── Initialisation depuis initialData ─────────────────────────────────

  onMounted(() => {
    if (props.initialData) {
      // Gérer les deux formats possibles :
      //   - Objet wizard : { noMateriel: bool, items: [...] }
      //   - Tableau Bachelard : [ { materiel, statut }, ... ]
      if (props.initialData.noMateriel === true) {
        noMateriel.value = true;
      /* eslint-disable @typescript-eslint/no-explicit-any -- dual format wizard/EvalSchema, items polymorphes */
      } else if (Array.isArray(props.initialData.items)) {
        materiels.value = props.initialData.items.map((m: any) => ({
          materiel: m.materiel ?? '',
          statut: m.statut ?? null,
        }));
      } else if (Array.isArray(props.initialData)) {
        materiels.value = (props.initialData as any[]).map((m: any) => ({
          materiel: m.materiel ?? '',
          statut: m.statut ?? null,
        }));
      }
      /* eslint-enable @typescript-eslint/no-explicit-any */
    }

    // Émission initiale
    emitData();
  });

  // ── Catalogue : items non encore ajoutés ──────────────────────────────

  const availableCatalogItems = computed(() => {
    const added = new Set(materiels.value.map((m) => m.materiel.trim().toLowerCase()));
    return CATALOGUE.filter((item) => !added.has(item.toLowerCase()));
  });

  // ── Actions ───────────────────────────────────────────────────────────

  function addMateriel() {
    materiels.value.push({ materiel: '', statut: null });
  }

  function addFromCatalog(name: string) {
    materiels.value.push({ materiel: name, statut: 'A PREVOIR' });
    emitData();
  }

  function removeMateriel(index: number) {
    materiels.value.splice(index, 1);
    emitData();
  }

  // ── Sérialisation & émission ──────────────────────────────────────────

  function emitData() {
    const data: WizardSectionData = {
      noMateriel: noMateriel.value,
      items: materiels.value.map((m) => ({
        materiel: m.materiel.trim(),
        statut: m.statut,
      })),
    };
    emit('update:data', data);
    emit('update:status', computeStatus());
  }

  function computeStatus(): SectionStatus {
    // "Aucun matériel" coché → complet
    if (noMateriel.value) return 'complete';

    // Aucun item → vide
    if (materiels.value.length === 0) return 'empty';

    // Tous les items ont un nom et un statut → complet
    const allComplete = materiels.value.every((m) => m.materiel.trim() !== '' && m.statut !== null);
    if (allComplete) return 'complete';

    return 'partial';
  }

  // ── Watchers ──────────────────────────────────────────────────────────

  watch(noMateriel, () => {
    emitData();
  });
</script>

<style scoped>
  /*
 * Chips du catalogue — boutons discrets pour ajout rapide.
 * Le reste du style vient de main.css (form-fieldset, wizard-inline-table, etc.)
 */
  .catalog-chip {
    @apply inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
         border border-emerald-200 text-emerald-700 bg-emerald-50
         hover:bg-emerald-100 hover:border-emerald-300
         transition-colors duration-150 cursor-pointer;
  }
</style>