<!--
  CareLink - PoaProblemeCard
  Chemin : frontend/src/components/evaluation/forms/PoaProblemeCard.vue

  Rôle : Carte dépliable pour un problème POA (Social ou Santé).
         Affiche en-tête compact (nomBloc + statut + compteur actions + chevron)
         et volet détails avec champs éditables + sous-tableau CRUD d'actions.

         Composant partagé entre PoaSocialForm (section 8) et PoaSanteForm (section 9).
         Utilise defineModel() pour `probleme` — le parent binde via v-model:probleme.

  Identité visuelle : palette slate-*, classes form-* et wizard-* de main.css
-->
<template>
  <div :class="{ 'poa-card--inactive': probleme.statut === 'Inactif' }" class="poa-card">
    <!-- ── En-tête — clic pour déplier/replier ─────────────────────── -->
    <div class="poa-card-header" @click="expanded = !expanded">
      <div class="flex items-center gap-2 min-w-0">
        <span class="poa-card-num">{{ index + 1 }}</span>
        <span class="font-medium text-slate-800 truncate">{{ probleme.nomBloc }}</span>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span v-if="probleme.planActions.length > 0" class="poa-card-count">
          {{ probleme.planActions.length }} action{{ probleme.planActions.length > 1 ? 's' : '' }}
        </span>
        <span :class="probleme.statut === 'Actif' ? 'actif' : 'inactif'" class="poa-card-badge">
          {{ probleme.statut }}
        </span>
        <ChevronDown
          :size="16"
          :stroke-width="2"
          :class="{ 'rotate-180': expanded }"
          class="text-slate-400 transition-transform duration-200"
        />
      </div>
    </div>

    <!-- ── Corps dépliable ─────────────────────────────────────────── -->
    <div v-if="expanded" class="poa-card-body">
      <!-- Statut + Préoccupations (ligne 1) -->
      <div class="form-grid-3 mt-3">
        <div class="form-group mt-0">
          <label class="form-label">Statut</label>
          <Select
            v-model="probleme.statut"
            :options="STATUT_OPTIONS"
            option-label="label"
            option-value="value"
            placeholder="Statut"
            class="w-full"
          />
        </div>
        <div class="form-group mt-0">
          <label class="form-label">Préoccupation patient</label>
          <Select
            v-model="probleme.preoccupationPatient"
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
            v-model="probleme.preoccupationProfessionel"
            :options="PREOCCUPATION_OPTIONS"
            option-label="label"
            option-value="value"
            placeholder="Niveau"
            class="w-full"
          />
        </div>
      </div>

      <!-- Problème posé -->
      <div class="form-group mt-5">
        <label class="form-label">Problème posé</label>
        <Textarea
          v-model="probleme.problemePose"
          :auto-resize="true"
          :rows="2"
          placeholder="Décrire le problème identifié…"
          class="w-full"
        />
      </div>

      <!-- Objectifs -->
      <div class="form-group mt-5">
        <label class="form-label">Objectifs</label>
        <Textarea
          v-model="probleme.objectifs"
          :auto-resize="true"
          :rows="2"
          placeholder="Objectifs visés…"
          class="w-full"
        />
      </div>

      <!-- ── Plan d'actions ────────────────────────────────────────── -->
      <div class="mt-6">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
            <ListChecks :size="15" :stroke-width="2" class="text-slate-400" />
            Plan d'actions
            <span v-if="probleme.planActions.length > 0" class="text-xs font-normal text-slate-400">
              ({{ probleme.planActions.length }})
            </span>
          </h4>
        </div>

        <!-- Liste des actions -->
        <div v-if="probleme.planActions.length > 0" class="space-y-2">
          <div v-for="(action, aidx) in probleme.planActions" :key="aidx" class="poa-action-card">
            <!-- Ligne principale : numéro + nom + chevron + supprimer -->
            <div class="poa-action-header">
              <span class="poa-action-num">{{ aidx + 1 }}</span>
              <InputText
                v-model="action.nomAction"
                placeholder="Nom de l'action"
                class="flex-1"
                @click.stop
              />
              <button
                class="poa-action-toggle"
                title="Détails de l'action"
                @click.stop="toggleAction(aidx)"
              >
                <ChevronDown
                  :size="14"
                  :stroke-width="2"
                  :class="{ 'rotate-180': expandedActions.has(aidx) }"
                  class="transition-transform duration-150"
                />
              </button>
              <button
                class="wizard-delete-row"
                title="Supprimer cette action"
                @click.stop="removeAction(aidx)"
              >
                <Trash2 :size="14" :stroke-width="2" />
              </button>
            </div>

            <!-- Détails de l'action (dépliable) -->
            <div v-if="expandedActions.has(aidx)" class="poa-action-details">
              <div class="form-grid-2 mt-2">
                <div class="form-group mt-0">
                  <label class="form-label">Personne en charge</label>
                  <InputText
                    v-model="action.personneChargeAction"
                    placeholder="Nom du responsable"
                    class="w-full"
                  />
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Date de début</label>
                  <div class="split-date-input">
                    <InputText
                      v-model="action.dateDebutJour"
                      placeholder="JJ"
                      class="split-date-input__jour"
                      maxlength="2"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="action.dateDebutMois"
                      placeholder="MM"
                      class="split-date-input__mois"
                      maxlength="2"
                    />
                    <span class="split-date-input__sep">/</span>
                    <InputText
                      v-model="action.dateDebutAnnee"
                      placeholder="AAAA"
                      class="split-date-input__annee"
                      maxlength="4"
                    />
                  </div>
                </div>
              </div>
              <div class="form-grid-2 mt-3">
                <div class="form-group mt-0">
                  <label class="form-label">Durée</label>
                  <InputText
                    v-model="action.dureeAction"
                    placeholder="Ex : 3 mois, 1 an…"
                    class="w-full"
                  />
                </div>
                <div class="form-group mt-0">
                  <label class="form-label">Récurrence</label>
                  <InputText
                    v-model="action.recurrenceAction"
                    placeholder="Ex : 1 Jour, 1 Semaine…"
                    class="w-full"
                  />
                </div>
              </div>
              <div class="form-group mt-3">
                <label class="form-label">Détail de l'action</label>
                <Textarea
                  v-model="action.detailAction"
                  :auto-resize="true"
                  :rows="2"
                  placeholder="Précisions complémentaires…"
                  class="w-full"
                />
              </div>
              <!-- Moments de la journée -->
              <div class="form-group mt-3">
                <label class="form-label">Moments de la journée</label>
                <div class="flex flex-wrap gap-3 mt-1">
                  <label
                    v-for="moment in MOMENT_JOURNEE_OPTIONS"
                    :key="moment"
                    class="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer"
                  >
                    <Checkbox v-model="action.momentJournee" :value="moment" />
                    {{ moment }}
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- État vide actions -->
        <div v-else class="text-xs text-slate-400 italic py-3 text-center">
          Aucune action définie
        </div>

        <!-- Bouton ajouter une action -->
        <button class="wizard-add-row mt-2" @click="addAction">
          <Plus :size="15" :stroke-width="2" />
          Ajouter une action
        </button>
      </div>

      <!-- ── Évaluation et résultats ───────────────────────────────── -->
      <div class="poa-eval-section">
        <div class="form-grid-2 mt-3">
          <div class="form-group mt-0">
            <label class="form-label">Critère d'évaluation</label>
            <Textarea
              v-model="probleme.critereEvaluation"
              :auto-resize="true"
              :rows="2"
              placeholder="Comment mesurer l'atteinte de l'objectif…"
              class="w-full"
            />
          </div>
          <div class="form-group mt-0">
            <label class="form-label">Résultat des actions</label>
            <Textarea
              v-model="probleme.resultatActions"
              :auto-resize="true"
              :rows="2"
              placeholder="Résultats obtenus…"
              class="w-full"
            />
          </div>
        </div>
        <div class="form-group mt-3">
          <label class="form-label">Message / Note</label>
          <Textarea
            v-model="probleme.message"
            :auto-resize="true"
            :rows="2"
            placeholder="Note libre…"
            class="w-full"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - PoaProblemeCard
   * Chemin : frontend/src/components/evaluation/forms/PoaProblemeCard.vue
   */
  import { ref } from 'vue';
  import { ChevronDown, Plus, Trash2, ListChecks } from 'lucide-vue-next';
  import InputText from 'primevue/inputtext';
  import Textarea from 'primevue/textarea';
  import Select from 'primevue/select';
  import Checkbox from 'primevue/checkbox';
  import {
    type PoaProbleme,
    createEmptyAction,
    STATUT_OPTIONS,
    PREOCCUPATION_OPTIONS,
    MOMENT_JOURNEE_OPTIONS,
  } from './poaShared';

  // ── Model + Props ────────────────────────────────────────────────────

  /** L'objet problème à éditer (v-model:probleme côté parent) */
  const probleme = defineModel<PoaProbleme>('probleme', { required: true });

  interface Props {
    /** Index dans la liste (pour le badge numéroté) */
    index: number;
    /** Démarrer déplié ? (défaut : false) */
    startExpanded?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    startExpanded: false,
  });

  // ── État local ───────────────────────────────────────────────────────

  const expanded = ref(props.startExpanded);

  /** Set des indices d'actions dont le détail est déplié */
  const expandedActions = ref<Set<number>>(new Set());

  // ── Actions CRUD ─────────────────────────────────────────────────────

  function addAction() {
    probleme.value.planActions.push(createEmptyAction());
    // Déplier automatiquement la nouvelle action
    const newIdx = probleme.value.planActions.length - 1;
    expandedActions.value.add(newIdx);
  }

  function removeAction(index: number) {
    probleme.value.planActions.splice(index, 1);
    // Nettoyer les indices dépliés
    expandedActions.value.delete(index);
    // Recalculer les indices > index
    const updated = new Set<number>();
    for (const idx of expandedActions.value) {
      updated.add(idx > index ? idx - 1 : idx);
    }
    expandedActions.value = updated;
  }

  function toggleAction(index: number) {
    if (expandedActions.value.has(index)) {
      expandedActions.value.delete(index);
    } else {
      expandedActions.value.add(index);
    }
  }
</script>

<style scoped>
  /*
 * Styles propres à PoaProblemeCard.
 * Les classes form-*, wizard-* viennent de main.css.
 */

  /* ── Carte problème ─────────────────────────────── */
  .poa-card {
    @apply border border-slate-200 rounded-xl overflow-hidden bg-white;
  }
  .poa-card--inactive {
    @apply opacity-60;
  }

  /* ── En-tête ────────────────────────────────────── */
  .poa-card-header {
    @apply flex justify-between items-center p-3 cursor-pointer
         bg-gradient-to-r from-teal-50 to-cyan-50
         hover:from-teal-100 hover:to-cyan-100
         transition-colors duration-150;
  }
  .poa-card-num {
    @apply w-6 h-6 rounded-full bg-teal-500 text-white text-xs font-bold
         flex items-center justify-center shrink-0;
  }
  .poa-card-count {
    @apply px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 text-xs font-medium;
  }
  .poa-card-badge {
    @apply px-2 py-0.5 rounded text-xs font-medium;
  }
  .poa-card-badge.actif {
    @apply bg-green-100 text-green-700;
  }
  .poa-card-badge.inactif {
    @apply bg-slate-100 text-slate-500;
  }

  /* ── Corps ───────────────────────────────────────── */
  .poa-card-body {
    @apply p-4 border-t border-slate-100;
  }

  /* ── Section évaluation/résultats ────────────────── */
  .poa-eval-section {
    @apply mt-6 pt-4 border-t border-dashed border-slate-200;
  }

  /* ── Carte action ────────────────────────────────── */
  .poa-action-card {
    @apply border border-slate-200 rounded-lg bg-slate-50 overflow-hidden;
  }
  .poa-action-header {
    @apply flex items-center gap-2 p-2;
  }
  .poa-action-num {
    @apply w-5 h-5 rounded-full bg-slate-300 text-white text-[10px] font-bold
         flex items-center justify-center shrink-0;
  }
  .poa-action-toggle {
    @apply p-1 rounded hover:bg-slate-200 text-slate-400
         transition-colors duration-150 cursor-pointer;
  }
  .poa-action-details {
    @apply px-3 pb-3 border-t border-slate-200 bg-white;
  }
</style>