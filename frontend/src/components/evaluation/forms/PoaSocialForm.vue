<!--
  CareLink - PoaSocialForm
  Chemin : frontend/src/components/evaluation/forms/PoaSocialForm.vue

  Rôle : Formulaire de saisie du Plan d'Actions Social (POA Social).
         Structure : tableau de problèmes (`problemes[]`), chacun avec un sous-tableau
         d'actions (`planActions[]`). 5 blocs fixes : Contexte, Habitat, Vie Sociale,
         Prise En Charge, Aides techniques.
         Émet @update:data et @update:status vers le wizard parent.

  Identité visuelle : fieldset orange, classes wizard-* de main.css
-->
<template>
  <div class="space-y-7">
    <!-- ── Fieldset POA Social ──────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--orange">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--orange">
          <ClipboardList :size="16" :stroke-width="2" />
        </span>
        Plan d'actions — Social
      </legend>

      <!-- Liste des problèmes -->
      <div class="mt-5 space-y-4">
        <template v-for="(prob, idx) in problemes" :key="prob.nomBloc">
          <!-- Séparateur entre les cartes (sauf avant la première) -->
          <div v-if="idx > 0" class="bloc-separator">
            <div class="bloc-separator__dot" />
          </div>

          <PoaProblemeCard v-model:probleme="problemes[idx]" :index="idx" />
        </template>
      </div>

      <!-- État vide (ne devrait pas arriver avec les 5 blocs fixes) -->
      <div
        v-if="problemes.length === 0"
        class="flex flex-col items-center py-8 text-slate-400 text-sm"
      >
        <ClipboardList :size="32" :stroke-width="1.2" class="mb-2 text-slate-300" />
        Aucun problème défini
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - PoaSocialForm
   * Chemin : frontend/src/components/evaluation/forms/PoaSocialForm.vue
   */
  import { ref, watch, onMounted } from 'vue';
  import { ClipboardList } from 'lucide-vue-next';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import {
    type PoaProbleme,
    createEmptyProbleme,
    hydrateProbleme,
    computePoaStatus,
  } from './poaShared';
  import { joinDateParts } from './dateHelpers';
  import PoaProblemeCard from './PoaProblemeCard.vue';

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

  // ── Référentiel local (propre au POA Social) ─────────────────────────

  /**
   * Les 5 blocs du POA Social (ordre Bachelard).
   * Chaque bloc est créé automatiquement au montage s'il n'est pas
   * déjà présent dans initialData.
   */
  const BLOCS_SOCIAL = [
    'Contexte',
    'Habitat',
    'Vie Sociale',
    'Prise En Charge',
    'Aides techniques',
  ] as const;

  // ── État réactif ─────────────────────────────────────────────────────

  const problemes = ref<PoaProbleme[]>([]);

  // ── Initialisation depuis initialData ────────────────────────────────

  onMounted(() => {
    const source = props.initialData;
    const validBlocs = new Set<string>(BLOCS_SOCIAL);

    if (source?.problemes && Array.isArray(source.problemes)) {
      // Hydratation depuis données existantes (wizard ou Bachelard)
      // Ne garder que les blocs appartenant à cette section
      const rawProblemes = source.problemes as Record<string, unknown>[];
      const loaded = rawProblemes
        .filter((p) => typeof p.nomBloc === 'string' && validBlocs.has(p.nomBloc))
        .map(hydrateProbleme);

      // Compléter avec les blocs manquants (si un brouillon partiel)
      const loadedBlocs = new Set(loaded.map((p) => p.nomBloc));
      for (const bloc of BLOCS_SOCIAL) {
        if (!loadedBlocs.has(bloc)) {
          loaded.push(createEmptyProbleme(bloc));
        }
      }
      problemes.value = loaded;
    } else {
      // Aucune donnée : créer les 5 blocs vides
      problemes.value = BLOCS_SOCIAL.map((bloc) => createEmptyProbleme(bloc));
    }

    // Émission initiale
    emitData();
  });

  // ── Sérialisation & émission ─────────────────────────────────────────

  function emitData() {
    const data: WizardSectionData = {
      problemes: problemes.value.map((p) => ({
        nomBloc: p.nomBloc,
        statut: p.statut,
        problemePose: p.problemePose,
        objectifs: p.objectifs,
        preoccupationPatient: p.preoccupationPatient,
        preoccupationProfessionel: p.preoccupationProfessionel,
        planActions: p.planActions.map((a) => ({
          nomAction: a.nomAction.trim(),
          detailAction: a.detailAction.trim(),
          personneChargeAction: a.personneChargeAction.trim(),
          dateDebutAction: joinDateParts(a.dateDebutJour, a.dateDebutMois, a.dateDebutAnnee),
          dureeAction: a.dureeAction.trim(),
          recurrenceAction: a.recurrenceAction.trim(),
          momentJournee: [...a.momentJournee],
        })),
        critereEvaluation: p.critereEvaluation,
        resultatActions: p.resultatActions,
        message: p.message,
      })),
    };
    emit('update:data', data);
    emit('update:status', computePoaStatus(problemes.value));
  }

  // ── Watchers ─────────────────────────────────────────────────────────

  watch(
    problemes,
    () => {
      emitData();
    },
    { deep: true },
  );
</script>