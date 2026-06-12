<script setup lang="ts">
  /**
   * ValidationCompose.vue — Zone d'action du dossier de validation (F7).
   *
   * Deux zones :
   *  1. Commentaire (tout détenteur de VALIDATION_VIEW) → addComment, avec toggle
   *     de visibilité. Garde-fou : l'option INTERNAL_ONLY n'est offerte qu'à un
   *     interne (hasPermission VALIDATION_INTERNAL_REVIEW) ; l'externe ne poste
   *     qu'en SHARED_EXTERNAL.
   *  2. Décision (si is_pending ∩ hasPermission VALIDATION_{stage}) → 3 gestes.
   *     « Valider » est absorbé par transmit_* aux étapes non terminales du
   *     workflow long (relais), sinon decide(VALIDATED) (terminal / court).
   *     Validation UI stricte calquée sur le model_validator backend.
   *
   * Sélecteur de valideur (transmit) : utilisateurs actifs du tenant — miroir
   * du _get_validator V1 (aucun contrôle d'éligibilité ; raffinement = J4/J5).
   * Règle des quatre yeux : NON anticipée ici (garantie backend 403 → store.error).
   *
   * Destination : src/components/validation/ValidationCompose.vue
   */
  import { ref, computed, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { Check as CheckIcon, Info as InfoIcon, X as XIcon, Lock as LockIcon, Send as SendIcon } from 'lucide-vue-next';
  import { useValidationThreadStore, useAuthStore } from '@/stores';
  import { userService } from '@/services';
  import { formatDate } from '@/utils/format';
  import { INVALIDATION_REASON_ORDER, INVALIDATION_REASON_LABELS, VALIDATION_STAGE_LABELS, STAGE_ACCENT } from '@/types';
  import type { ExchangeVisibility, InvalidationReason, UserSummary } from '@/types';

  type Gesture = 'validate' | 'more_info' | 'invalidate';

  const store = useValidationThreadStore();
  const auth = useAuthStore();
  const router = useRouter();

  const vr = computed(() => store.currentRequest);

  /** Peut agir : VR en attente ∩ permission de l'étape courante (ADMIN_FULL absorbé). */
  const canAct = computed(
    () => !!vr.value && vr.value.is_pending && auth.hasPermission(`VALIDATION_${vr.value.stage}`),
  );

  /** Peut poser une note INTERNAL_ONLY (marqueur interne GCSMS). */
  const canPostInternal = computed(() => auth.hasPermission('VALIDATION_INTERNAL_REVIEW'));

  /**
   * L'utilisateur courant est-il l'auteur de la soumission ? Principe des quatre
   * yeux (D24) : on n'est pas valideur de sa propre soumission. Anticipation UI
   * du garde-fou backend (403 SelfValidationForbiddenError).
   */
  const isSelfSubmission = computed(
    () => !!vr.value && auth.user?.id === vr.value.submitted_by_user_id,
  );

  /** Mode de la validation positive selon (workflow, étape). */
  const validateMode = computed<'transmit-medical' | 'transmit-funding' | 'decide'>(() => {
    const v = vr.value;
    if (!v) return 'decide';
    if (v.workflow_type === 'AGGIR_FUNDING' && v.stage === 'INTERNAL_REVIEW') return 'transmit-medical';
    if (v.workflow_type === 'AGGIR_FUNDING' && v.stage === 'MEDICAL_REVIEW') return 'transmit-funding';
    return 'decide';
  });

  const needsValidatorPick = computed(() => validateMode.value !== 'decide');

  // ===========================================================================
  // HIÉRARCHIE VISUELLE (refonte UX — registre prospectif vs journal)
  // ===========================================================================

  /** Peut décider (au-delà du commentaire) : son tour ∩ pas sa propre soumission (D24). */
  const canDecide = computed(() => canAct.value && !isSelfSubmission.value);

  /** Mode décision actif : un geste est en cours → zone de texte unique (D2). */
  const inDecisionMode = computed(() => canDecide.value && gesture.value !== null);

  /**
   * Accent par étape active (ourlet gauche + bandeau-titre) : couleur d'étape
   * seulement quand le lecteur peut décider, registre neutre sinon (lecture/avis).
   * `STAGE_ACCENT` provient désormais du barrel @/types (source partagée, promue T2).
   */

  const NEUTRAL_ACCENT = { bar: 'border-l-slate-200', band: 'bg-slate-50', text: 'text-slate-500' };

  const accent = computed(() =>
    vr.value && canDecide.value ? (STAGE_ACCENT[vr.value.stage] ?? NEUTRAL_ACCENT) : NEUTRAL_ACCENT,
  );

  // ===========================================================================
  // VR DÉCIDÉE — registre rétrospectif (§8.1 : suivi / attente)
  // ===========================================================================

  /** VR tranchée (décision posée) : bascule l'espace d'action en suivi/attente. */
  const isDecided = computed(() => !!vr.value?.is_decided);

  /**
   * L'utilisateur courant est-il l'auteur de la décision ? Pilote le point de
   * vue de la ligne de statut (arbitrage B) : « vous » seulement pour le décideur,
   * tournure neutre pour les autres lecteurs du dossier.
   */
  const isDecider = computed(() => !!vr.value && auth.user?.id === vr.value.decided_by_user_id);

  /**
   * Ligne de statut affichée sur une VR décidée (§8.1). Formulations verrouillées ;
   * le « vous » de MORE_INFO n'apparaît que pour l'auteur de la décision (sinon
   * tournure neutre). VALIDATED distingue le relais (transmise) du terminal via
   * `needsValidatorPick` (réemploi du même prédicat que les gestes de décision).
   */
  const statusLine = computed(() => {
    const v = vr.value;
    if (!v || !v.is_decided || !v.decision) return '';
    const date = v.decided_at ? formatDate(v.decided_at, { style: 'medium' }) : '';
    switch (v.decision) {
      case 'MORE_INFO_REQUESTED':
        return isDecider.value
          ? `Vous avez demandé un complément le ${date}. La demande est repartie côté émetteur (relecture interne). Aucune action n'est attendue de vous pour l'instant.`
          : `Un complément a été demandé le ${date}. La demande est repartie côté émetteur (relecture interne). Aucune action n'est attendue ici pour l'instant.`;
      case 'VALIDATED':
        return needsValidatorPick.value ? "Validée, transmise à l'étape suivante." : 'Validée.';
      case 'INVALIDATED':
        return `Invalidée le ${date}.`;
      default:
        return '';
    }
  });

  // ===========================================================================
  // DOSSIER GARÉ — re-soumission par l'émetteur (R1)
  // ===========================================================================

  /** Aucune VR du dossier n'est en attente (garde-fou R-T2 : sinon 409 backend). */
  const noPendingInDossier = computed(
    () => !(store.dossierContext?.requests ?? []).some((r) => r.is_pending),
  );

  /**
   * Le lecteur peut re-soumettre (R1). Dossier « garé » : la VR médicale en focus
   * a renvoyé le dossier en interne — complément OU invalidation (R-T1) — aucune VR
   * pendante au pipeline (R-T2), et le lecteur porte VALIDATION_SUBMIT (l'émetteur,
   * ce qui exclut naturellement le médecin). `evaluation_id` requis (workflow AGGIR).
   */
  const canResubmit = computed(() => {
    const v = vr.value;
    return (
      !!v &&
      v.is_decided &&
      v.stage === 'MEDICAL_REVIEW' &&
      (v.decision === 'MORE_INFO_REQUESTED' || v.decision === 'INVALIDATED') &&
      v.evaluation_id !== null &&
      auth.hasPermission('VALIDATION_SUBMIT') &&
      noPendingInDossier.value
    );
  });

  /**
   * L'utilisateur a-t-il une action attendue dans ce panneau (décider OU
   * re-soumettre) ? Pilote le halo permanent « c'est votre tour » (attention cue).
   */
  const awaitingMyAction = computed(() => canDecide.value || canResubmit.value);

  /** Intro contextuelle du composeur (selon la décision médicale du retour). */
  const resubmitIntro = computed(() => {
    const v = vr.value;
    if (!v) return '';
    const date = v.decided_at ? formatDate(v.decided_at, { style: 'medium' }) : '';
    return v.decision === 'INVALIDATED'
      ? `Le médecin a invalidé l'évaluation le ${date}. Après correction, re-soumettez-la pour relecture interne.`
      : `Le médecin a demandé un complément le ${date}. Complétez le dossier, puis re-soumettez-le pour relecture interne.`;
  });

  const resubmitNotes = ref('');

  /** Re-soumet le dossier garé, puis suit la nouvelle VR interne (R-T4). */
  async function submitResubmit(): Promise<void> {
    const v = vr.value;
    if (!v || v.evaluation_id === null || store.posting) return;
    try {
      const newVr = await store.resubmitEvaluation(v.evaluation_id, {
        notes: resubmitNotes.value.trim() || null,
      });
      resubmitNotes.value = '';
      await router.push(`/soins/validation/${newVr.id}`);
    } catch {
      // store.error porte le message
    }
  }

  /** Titre dynamique du bandeau (D3 + §8.1 : titre d'état sur VR décidée). */
  const panelTitle = computed(() => {
    const v = vr.value;
    if (canResubmit.value) return 'Reprendre le dossier — re-soumission';
    if (v?.is_decided) {
      switch (v.decision) {
        case 'MORE_INFO_REQUESTED':
          return "Demande traitée — en attente de l'émetteur";
        case 'VALIDATED':
          return 'Demande validée';
        case 'INVALIDATED':
          return 'Demande invalidée';
        default:
          return 'Demande traitée';
      }
    }
    return v && canDecide.value
      ? `Votre intervention, ${VALIDATION_STAGE_LABELS[v.stage]}`
      : 'Pour lecture et avis';
  });

  // ===========================================================================
  // ZONE COMMENTAIRE
  // ===========================================================================

  const commentText = ref('');
  const commentVisibility = ref<ExchangeVisibility>('SHARED_EXTERNAL');

  const canSubmitComment = computed(() => commentText.value.trim().length > 0 && !store.posting);

  async function submitComment(): Promise<void> {
    if (!vr.value || !canSubmitComment.value) return;
    try {
      await store.addComment(vr.value.id, {
        message: commentText.value.trim(),
        visibility: commentVisibility.value,
      });
      commentText.value = '';
      commentVisibility.value = 'SHARED_EXTERNAL';
    } catch {
      // store.error porte le message
    }
  }

  // ===========================================================================
  // ZONE DÉCISION
  // ===========================================================================

  const gesture = ref<Gesture | null>(null);
  const decisionMotif = ref('');
  const invalidationReason = ref<InvalidationReason | null>(null);
  const infoMessage = ref('');
  const transmitNotes = ref('');
  const validateNotes = ref('');
  const assignedValidatorId = ref<number | null>(null);

  const validators = ref<UserSummary[]>([]);
  const loadingValidators = ref(false);
  const validatorsError = ref<string | null>(null);

  async function loadValidators(): Promise<void> {
    if (validators.value.length > 0 || loadingValidators.value) return;
    loadingValidators.value = true;
    validatorsError.value = null;
    try {
      // Borne du contrat backend : size ≤ 100 (422 au-delà). Suffisant V1 ;
      // au-delà de 100 utilisateurs actifs, l'endpoint d'éligibilité par
      // étape (dette D16) prendra le relais avec filtrage par permission.
      const result = await userService.list({ is_active: true, size: 100 });
      validators.value = result.items;
    } catch {
      validatorsError.value = 'Impossible de charger la liste des valideurs';
    } finally {
      loadingValidators.value = false;
    }
  }

  function selectGesture(g: Gesture): void {
    gesture.value = g;
    if (g === 'validate' && needsValidatorPick.value) void loadValidators();
  }

  /** Validation UI stricte (miroir du model_validator Pydantic). */
  const canSubmitDecision = computed(() => {
    if (!gesture.value || store.posting) return false;
    if (gesture.value === 'validate') {
      return needsValidatorPick.value ? assignedValidatorId.value !== null : true;
    }
    if (gesture.value === 'more_info') return infoMessage.value.trim().length > 0;
    // invalidate
    return invalidationReason.value !== null && decisionMotif.value.trim().length > 0;
  });

  function resetDecision(): void {
    gesture.value = null;
    decisionMotif.value = '';
    invalidationReason.value = null;
    infoMessage.value = '';
    transmitNotes.value = '';
    validateNotes.value = '';
    assignedValidatorId.value = null;
    resubmitNotes.value = '';
  }

  async function submitDecision(): Promise<void> {
    const v = vr.value;
    if (!v || !canSubmitDecision.value || !gesture.value) return;
    try {
      if (gesture.value === 'validate') {
        if (validateMode.value === 'transmit-medical') {
          await store.transmitMedical(v.id, {
            assigned_validator_user_id: assignedValidatorId.value as number,
            notes: transmitNotes.value.trim() || null,
          });
        } else if (validateMode.value === 'transmit-funding') {
          await store.transmitFunding(v.id, {
            assigned_validator_user_id: assignedValidatorId.value as number,
            notes: transmitNotes.value.trim() || null,
          });
        } else {
          await store.decide(v.id, {
            decision: 'VALIDATED',
            decision_motif: validateNotes.value.trim() || null,
          });
        }
      } else if (gesture.value === 'more_info') {
        await store.decide(v.id, {
          decision: 'MORE_INFO_REQUESTED',
          info_request_message: infoMessage.value.trim(),
        });
      } else {
        await store.decide(v.id, {
          decision: 'INVALIDATED',
          invalidation_reason: invalidationReason.value,
          decision_motif: decisionMotif.value.trim(),
        });
      }
      resetDecision();
    } catch {
      // store.error porte le message
    }
  }

  /** Libellé contextuel du bouton de soumission de la décision. */
  const submitLabel = computed(() => {
    if (gesture.value === 'more_info') return 'Demander un complément';
    if (gesture.value === 'invalidate') return 'Invalider';
    if (gesture.value === 'validate') return needsValidatorPick.value ? 'Valider et transmettre' : 'Valider';
    return 'Confirmer';
  });

  // Si la VR change (après un acte), on remet la zone décision à zéro.
  watch(
    () => vr.value?.id,
    () => resetDecision(),
  );
</script>

<template>
  <div
    :class="[
      accent.bar,
      awaitingMyAction ? 'ring-2 ring-teal-200' : '',
      'overflow-hidden rounded-lg border border-l-4 border-slate-200 bg-white shadow-sm',
    ]"
  >
    <!-- Bandeau-titre dynamique : registre prospectif, distinct du journal (D2/D3) -->
    <div
      :class="[accent.band, accent.text, 'flex items-center gap-2 px-4 py-2.5 text-[10.5px] font-bold uppercase tracking-wide']"
    >
      {{ panelTitle }}
    </div>

    <div class="p-4">
      <!-- Gestes de décision : uniquement si le lecteur peut décider (son tour) -->
      <div v-if="canDecide" class="flex flex-wrap gap-2">
        <button
          :class="
            gesture === 'validate'
              ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
              : 'border-slate-200 text-slate-500 hover:border-slate-300'
          "
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors"
          @click="selectGesture('validate')"
        >
          <component :is="CheckIcon" class="h-4 w-4" />
          Valider
        </button>
        <button
          :class="
            gesture === 'more_info'
              ? 'border-amber-400 bg-amber-50 text-amber-700'
              : 'border-slate-200 text-slate-500 hover:border-slate-300'
          "
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors"
          @click="selectGesture('more_info')"
        >
          <component :is="InfoIcon" class="h-4 w-4" />
          Demander un complément
        </button>
        <button
          :class="
            gesture === 'invalidate'
              ? 'border-red-400 bg-red-50 text-red-700'
              : 'border-slate-200 text-slate-500 hover:border-slate-300'
          "
          type="button"
          class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors"
          @click="selectGesture('invalidate')"
        >
          <component :is="XIcon" class="h-4 w-4" />
          Invalider
        </button>
      </div>

      <!-- Indice : la saisie accompagne la décision (le commentaire autonome est retiré du mode décision) -->
      <p v-if="canDecide && !inDecisionMode" class="mt-2.5 text-xs text-slate-400">
        Choisissez une action ci-dessus ; vous pourrez y joindre un message.
      </p>

      <!-- ============ MODE DÉCISION : un geste choisi → zone de texte unique (D2) ============ -->
      <div v-if="inDecisionMode" class="mt-3">
        <!-- Valider → transmission (relais) -->
        <div v-if="gesture === 'validate' && needsValidatorPick">
          <label class="text-xs font-medium text-slate-500">
            Transmettre à
            <span class="text-slate-400">
              ({{ validateMode === 'transmit-medical' ? 'médecin' : 'agent département' }})
            </span>
          </label>
          <select
            v-model.number="assignedValidatorId"
            :disabled="loadingValidators"
            class="mt-1 w-full rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
          >
            <option :value="null" disabled>
              {{ loadingValidators ? 'Chargement…' : 'Sélectionner un valideur' }}
            </option>
            <option v-for="u in validators" :key="u.id" :value="u.id">{{ u.full_name }}</option>
          </select>
          <p v-if="validatorsError" class="mt-1 text-xs text-red-600">{{ validatorsError }}</p>
          <textarea
            v-model="transmitNotes"
            rows="2"
            placeholder="Note de transmission (facultative)…"
            class="mt-2 w-full resize-y rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
          />
        </div>

        <!-- Valider → terminal / court : note facultative (R1 polish) -->
        <div v-else-if="gesture === 'validate'">
          <p class="text-sm text-slate-500">Cette validation clôt favorablement la demande.</p>
          <textarea
            v-model="validateNotes"
            rows="2"
            placeholder="Note de validation (facultative)…"
            class="mt-2 w-full resize-y rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
          />
        </div>

        <!-- Complément -->
        <textarea
          v-else-if="gesture === 'more_info'"
          v-model="infoMessage"
          rows="3"
          placeholder="Précisez les informations ou pièces attendues (obligatoire)…"
          class="w-full resize-y rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-200"
        />

        <!-- Invalidation -->
        <div v-else-if="gesture === 'invalidate'">
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="reason in INVALIDATION_REASON_ORDER"
              :key="reason"
              :class="
                invalidationReason === reason
                  ? 'border-red-400 bg-red-50 text-red-700'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300'
              "
              type="button"
              class="rounded-full border px-2.5 py-1 text-xs font-medium transition-colors"
              @click="invalidationReason = reason"
            >
              {{ INVALIDATION_REASON_LABELS[reason] }}
            </button>
          </div>
          <textarea
            v-model="decisionMotif"
            rows="3"
            placeholder="Motif détaillé (obligatoire)…"
            class="mt-2 w-full resize-y rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-200"
          />
        </div>

        <!-- Soumission -->
        <div class="mt-3 flex items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-slate-600"
            @click="resetDecision"
          >
            Annuler
          </button>
          <button
            :disabled="!canSubmitDecision"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-3.5 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            @click="submitDecision"
          >
            {{ submitLabel }}
          </button>
        </div>
      </div>

      <!-- ============ DOSSIER GARÉ : l'émetteur répond et re-soumet (R1) ============ -->
      <div v-else-if="canResubmit">
        <div class="flex items-start gap-2 text-sm text-slate-500">
          <component :is="InfoIcon" class="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400" />
          <p>{{ resubmitIntro }}</p>
        </div>
        <textarea
          v-model="resubmitNotes"
          rows="3"
          placeholder="Réponse au médecin / note de re-soumission (facultative)…"
          class="mt-3 w-full resize-y rounded-md border border-slate-200 p-2.5 text-sm text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
        />
        <div class="mt-3 flex items-center justify-end">
          <button
            :disabled="store.posting"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-3.5 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            @click="submitResubmit"
          >
            <component :is="SendIcon" class="h-3.5 w-3.5" />
            Répondre et re-soumettre
          </button>
        </div>
      </div>

      <!-- ============ VR DÉCIDÉE : registre rétrospectif — ligne de statut, pas de saisie (§8.1) ============ -->
      <div v-else-if="isDecided" class="flex items-start gap-2 text-sm text-slate-500">
        <component :is="InfoIcon" class="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400" />
        <p>{{ statusLine }}</p>
      </div>

      <!-- ============ MODE COMMENTAIRE : réservé aux NON-décideurs (spectateurs, quatre-yeux, lecture/avis) ; retiré du registre décisionnel (R1 polish) ============ -->
      <div v-else-if="!canDecide">
        <label class="text-[10.5px] font-bold uppercase tracking-wide text-slate-400">
          Ajouter un commentaire
        </label>
        <textarea
          v-model="commentText"
          rows="2"
          placeholder="Votre message…"
          class="mt-1.5 w-full resize-y rounded-md border border-slate-200 p-2.5 text-sm text-slate-700 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-200"
        />
        <div class="mt-2 flex items-center justify-between gap-3">
          <!-- Toggle visibilité (INTERNAL_ONLY réservé aux internes) -->
          <div v-if="canPostInternal" class="flex items-center gap-1 text-xs">
            <button
              :class="
                commentVisibility === 'SHARED_EXTERNAL'
                  ? 'bg-teal-50 text-teal-700'
                  : 'text-slate-400 hover:bg-slate-50'
              "
              type="button"
              class="rounded px-2 py-1 font-medium transition-colors"
              @click="commentVisibility = 'SHARED_EXTERNAL'"
            >
              Partagé
            </button>
            <button
              :class="
                commentVisibility === 'INTERNAL_ONLY'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:bg-slate-50'
              "
              type="button"
              class="inline-flex items-center gap-1 rounded px-2 py-1 font-medium transition-colors"
              @click="commentVisibility = 'INTERNAL_ONLY'"
            >
              <component :is="LockIcon" class="h-3 w-3" />
              Interne
            </button>
          </div>
          <span v-else class="text-[11px] text-slate-400">Visible des acteurs du dossier</span>

          <button
            :disabled="!canSubmitComment"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            @click="submitComment"
          >
            <component :is="SendIcon" class="h-3.5 w-3.5" />
            Commenter
          </button>
        </div>

        <!-- Quatre yeux : le lecteur agit sur sa propre soumission -->
        <p v-if="canAct && isSelfSubmission" class="mt-2.5 text-xs text-slate-400">
          Vous ne pouvez pas être valideur de votre propre soumission (principe des quatre yeux).
        </p>
      </div>

      <!-- Erreur d'acte -->
      <p v-if="store.error" class="mt-3 text-xs text-red-600">{{ store.error }}</p>
    </div>
  </div>
</template>
