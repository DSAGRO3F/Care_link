<script setup lang="ts">
  /**
   * ValidationThread.vue — Fil d'échange du dossier de validation (F6).
   *
   * Rendu continu du fil, groupé par VR (segments). Trois registres visuels
   * distincts et assumés :
   *  - « où en est-on » : séparateurs d'étape sur la palette d'étape (STAGE_ACCENT,
   *    teal/bleu/violet), groupés sur les rebonds (un séparateur par changement
   *    d'étape, pas par VR) ;
   *  - « qu'a-t-on fait » : ourlet gauche + chip par `action_type` (conservés) ;
   *  - « qui parle » : rail vertical à gauche + pastille-rôle (monochrome ardoise,
   *    pleine si interne au GCSMS, cerclée si externe ; icône = rôle).
   *
   * Cas particulier (décision Q2-B) : une entrée `TRANSMIT` (genèse d'une VR
   * relayée) n'est PAS rendue en carte mais en marqueur de passage sur la frontière
   * d'étape — la transmission se lit comme une couture, pas comme un message.
   *
   * Lit le store directement (singleton Pinia) : le cycle de vie (chargement /
   * reset) reste porté par la page F5. AUCUN re-filtrage de visibilité ici —
   * le fil arrive déjà filtré du serveur (A1/D32).
   *
   * Destination : src/components/validation/ValidationThread.vue
   */
  import { computed } from 'vue';
  import type { Component } from 'vue';
  import {
    FileText as FileTextIcon,
    Lock as LockIcon,
    CornerDownRight as TransmitArrowIcon,
    ClipboardList as CoordinatorIcon,
    ShieldCheck as InternalValidatorIcon,
    Stethoscope as MedicalIcon,
    Landmark as FundingIcon,
    User as UserIcon,
  } from 'lucide-vue-next';
  import { useValidationThreadStore } from '@/stores';
  import { formatDate } from '@/utils/format';
  import {
    EXCHANGE_ACTION_LABELS,
    EXCHANGE_AUTHOR_ROLE_LABELS,
    VALIDATION_STAGE_LABELS,
    STAGE_ACCENT,
  } from '@/types';
  import type { ExchangeActionType, ExchangeResponse, ValidationStage } from '@/types';

  const store = useValidationThreadStore();

  /** Libellé FR du rôle d'auteur (repli sur la valeur brute si inconnue). */
  function authorLabel(role: string): string {
    return EXCHANGE_AUTHOR_ROLE_LABELS[role] ?? role;
  }

  /** Libellé d'une pièce jointe (structure libre tant que B40-J5 n'a pas figé). */
  function attachmentLabel(att: Record<string, unknown>): string {
    const name = att.filename ?? att.name ?? att.label;
    return typeof name === 'string' ? name : 'Pièce jointe';
  }

  // ===========================================================================
  // IDENTITÉ DE L'AUTEUR — pastille du rail (§8.2 / Q3)
  // ===========================================================================

  /** Icône lucide par rôle d'auteur (repli `User`). */
  const ROLE_ICON: Record<string, Component> = {
    COORDINATOR: CoordinatorIcon,
    INTERNAL_VALIDATOR: InternalValidatorIcon,
    MEDICAL_VALIDATOR: MedicalIcon,
    FUNDING_VALIDATOR: FundingIcon,
  };

  function roleIcon(role: string): Component {
    return ROLE_ICON[role] ?? UserIcon;
  }

  /** Interne au GCSMS (pastille pleine) vs externe (pastille cerclée). */
  function isInternalRole(role: string): boolean {
    return role === 'COORDINATOR' || role === 'INTERNAL_VALIDATOR';
  }

  // ===========================================================================
  // ACTION — ourlet + chip (conservés, choix i)
  // ===========================================================================

  /** Accent (bordure gauche) de la carte selon le type d'action. */
  const ACTION_ACCENT: Record<ExchangeActionType, string> = {
    SUBMIT: 'border-l-slate-300',
    COMMENT: 'border-l-slate-200',
    RESUBMIT: 'border-l-slate-300',
    VALIDATE: 'border-l-emerald-400',
    REQUEST_INFO: 'border-l-amber-400',
    INVALIDATE: 'border-l-red-400',
    TRANSMIT: 'border-l-blue-400',
  };

  /** Couleur du chip d'action. */
  const ACTION_CHIP: Record<ExchangeActionType, string> = {
    SUBMIT: 'bg-slate-100 text-slate-500',
    COMMENT: 'bg-slate-100 text-slate-500',
    RESUBMIT: 'bg-slate-100 text-slate-500',
    VALIDATE: 'bg-emerald-50 text-emerald-600',
    REQUEST_INFO: 'bg-amber-50 text-amber-600',
    INVALIDATE: 'bg-red-50 text-red-600',
    TRANSMIT: 'bg-blue-50 text-blue-600',
  };

  // ===========================================================================
  // SEGMENTS D'AFFICHAGE — groupement d'étape (§8.2) + extraction TRANSMIT (Q2-B)
  // ===========================================================================

  interface DisplaySegment {
    validationRequestId: number;
    /** Séparateur affiché seulement à un changement d'étape (regroupe les rebonds). */
    showSeparator: boolean;
    label: string;
    accent: { line: string; text: string };
    /** Transmission rendue en marqueur de passage (libellé pré-résolu, pas une carte). */
    transmitLabel: string | null;
    transmitMessage: string | null;
    /** Entrées affichées en cartes (TRANSMIT exclu). */
    cards: ExchangeResponse[];
  }

  const NEUTRAL_SEP = { line: 'bg-slate-200', text: 'text-slate-400' };

  /**
   * Dérive les segments d'affichage à partir des segments du store. Côté composant
   * (choix E) : on ne touche pas au store. Trois transformations :
   *  - groupement : un séparateur d'étape n'est rendu qu'au changement d'étape, ce
   *    qui fusionne visuellement les rebonds (plusieurs VR à la même étape) ;
   *  - extraction : l'entrée TRANSMIT (genèse d'une VR relayée) devient un marqueur
   *    de passage sur la frontière, pas une carte (décision Q2-B) ;
   *  - accent : filet + libellé sur la palette d'étape (STAGE_ACCENT.line / .text).
   */
  const displaySegments = computed<DisplaySegment[]>(() => {
    const out: DisplaySegment[] = [];
    let prevStage: ValidationStage | null = null;
    let first = true;
    for (const seg of store.threadSegments) {
      const t = seg.entries.find((e) => e.action_type === 'TRANSMIT');
      const when = t ? formatDate(t.created_at, { style: 'medium' }) : '';
      out.push({
        validationRequestId: seg.validationRequestId,
        showSeparator: first || seg.stage !== prevStage,
        label: seg.stage
          ? VALIDATION_STAGE_LABELS[seg.stage]
          : `Demande #${seg.validationRequestId}`,
        accent: seg.stage
          ? { line: STAGE_ACCENT[seg.stage].line, text: STAGE_ACCENT[seg.stage].text }
          : NEUTRAL_SEP,
        transmitLabel: t ? `Transmis par ${authorLabel(t.author_role)} · ${when}` : null,
        transmitMessage: t?.message ?? null,
        cards: seg.entries.filter((e) => e.action_type !== 'TRANSMIT'),
      });
      prevStage = seg.stage;
      first = false;
    }
    return out;
  });
</script>

<template>
  <div>
    <!-- Vide -->
    <p
      v-if="!store.hasThread && !store.loading"
      class="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-400"
    >
      Aucun échange pour ce dossier.
    </p>

    <!-- Segments -->
    <template v-else>
      <div v-for="seg in displaySegments" :key="seg.validationRequestId">
        <!-- Séparateur d'étape (palette d'étape ; groupé sur les rebonds) -->
        <div v-if="seg.showSeparator" class="my-4 flex items-center gap-3">
          <span :class="seg.accent.line" class="h-px flex-1" />
          <span
            :class="seg.accent.text"
            class="whitespace-nowrap text-[10.5px] font-bold uppercase tracking-wide"
          >
            Étape · {{ seg.label }}
          </span>
          <span :class="seg.accent.line" class="h-px flex-1" />
        </div>

        <!-- Marqueur de passage : la transmission se lit sur la frontière (Q2-B) -->
        <div
          v-if="seg.transmitLabel"
          class="mb-2.5 flex items-start gap-2 px-1 text-[11px] text-slate-500"
        >
          <component
            :is="TransmitArrowIcon"
            class="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-slate-400"
          />
          <span>
            {{ seg.transmitLabel }}
            <span v-if="seg.transmitMessage" class="text-slate-400">
              — {{ seg.transmitMessage }}
            </span>
          </span>
        </div>

        <!-- Entrées en cartes, posées sur le rail d'identité -->
        <div v-for="(entry, ei) in seg.cards" :key="entry.id" class="relative flex gap-3 pb-2.5">
          <!-- Rail + pastille-rôle (identité ; monochrome ardoise) -->
          <div class="relative flex w-7 flex-shrink-0 justify-center">
            <span
              :class="ei < seg.cards.length - 1 ? '-bottom-2.5' : 'bottom-0'"
              class="absolute left-1/2 top-0 w-px -translate-x-1/2 bg-slate-400"
              aria-hidden="true"
            />
            <span
              :class="
                isInternalRole(entry.author_role)
                  ? 'border-slate-600 bg-slate-600 text-white'
                  : 'border-slate-300 bg-white text-slate-500'
              "
              class="relative z-10 mt-2.5 grid h-7 w-7 place-items-center rounded-full border-2"
            >
              <component :is="roleIcon(entry.author_role)" class="h-3.5 w-3.5" />
            </span>
          </div>

          <!-- Carte (ourlet d'action conservé) -->
          <article
            :class="[
              ACTION_ACCENT[entry.action_type],
              'flex-1 rounded-lg border border-l-4 border-slate-200 bg-white p-3.5 shadow-sm',
            ]"
          >
            <header class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-bold text-slate-700">{{ authorLabel(entry.author_role) }}</span>
              <span
                :class="ACTION_CHIP[entry.action_type]"
                class="rounded-full px-2 py-0.5 text-[0.625rem] font-semibold"
              >
                {{ EXCHANGE_ACTION_LABELS[entry.action_type] }}
              </span>
              <span
                v-if="entry.visibility === 'INTERNAL_ONLY'"
                class="inline-flex items-center gap-1 rounded-full bg-slate-700 px-2 py-0.5 text-[0.625rem] font-semibold text-white"
              >
                <component :is="LockIcon" class="h-3 w-3" />
                Interne
              </span>
              <time class="ml-auto text-[11px] text-slate-400">{{ formatDate(entry.created_at, { style: 'medium' }) }}</time>
            </header>

            <p v-if="entry.message" class="mt-2 whitespace-pre-line text-sm text-slate-600">
              {{ entry.message }}
            </p>

            <div v-if="entry.attachments.length" class="mt-2.5 flex flex-wrap gap-1.5">
              <span
                v-for="(att, ai) in entry.attachments"
                :key="ai"
                class="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-500"
              >
                <component :is="FileTextIcon" class="h-3 w-3" />
                {{ attachmentLabel(att) }}
              </span>
            </div>
          </article>
        </div>
      </div>
    </template>
  </div>
</template>
