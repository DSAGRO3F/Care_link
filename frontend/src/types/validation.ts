/**
 * Types TypeScript miroir du module Validation (Phase 4 bis — B40-J2).
 *
 * Miroir strict (convention #78) des schémas Pydantic
 * `app/api/v1/validation/schemas.py` + énumérations `app/models/enums.py`.
 *
 * Les enums sont reproduits en unions de littéraux car les schémas Response
 * backend exposent `use_enum_values=True` (les enums circulent en chaînes).
 *
 * NB EvaluationStatus : l'enrichissement Phase 4 bis (8 valeurs) doit être
 * répercuté dans le fichier de types évaluation existant — voir le snippet
 * fourni en accompagnement — et n'est PAS redéclaré ici pour préserver la
 * source de vérité unique.
 *
 * 🆕 B40-J4 / F1 — ajout du volet fil d'échange consommé par le portail
 *   valideur : enums `ExchangeActionType` (7 membres, `SUBMIT` inclus) /
 *   `ExchangeVisibility`, interfaces `ExchangeResponse` / `ExchangeCreate`,
 *   et libellés FR (Record) pour Tags et séparateurs d'étape. Volet
 *   Notification + VR inchangé (B40-J2).
 */

// ============================================================================
// ENUMS (unions de littéraux)
// ============================================================================

export type ValidationWorkflowType = 'AGGIR_FUNDING' | 'COORDINATION_DOSSIER';

export type ValidationStage = 'INTERNAL_REVIEW' | 'MEDICAL_REVIEW' | 'FUNDING_REVIEW';

export type ValidationDecision =
  | 'VALIDATED'
  | 'INVALIDATED'
  | 'MORE_INFO_REQUESTED'
  | 'WITHDRAWN';

export type InvalidationReason =
  | 'INCOMPLETE_INFO'
  | 'CLINICAL_DISAGREEMENT'
  | 'OUT_OF_SCOPE'
  | 'OTHER';

export type NotificationType =
  | 'VALIDATION_REQUEST_RECEIVED'
  | 'VALIDATION_DECISION_TAKEN'
  | 'VALIDATION_INFO_REQUESTED'
  | 'EVALUATION_FUNDING_REJECTED';

// --- Fil d'échange (B40-J3) -------------------------------------------------

/**
 * Type d'action d'une entrée du fil. 7 membres côté code (`SUBMIT` ouvre le
 * fil) ; seul `COMMENT` est saisi manuellement, les autres sont générés par
 * les actes du workflow (submit / transmit / decide).
 */
export type ExchangeActionType =
  | 'SUBMIT'
  | 'COMMENT'
  | 'RESUBMIT'
  | 'VALIDATE'
  | 'REQUEST_INFO'
  | 'INVALIDATE'
  | 'TRANSMIT';

/**
 * Portée de visibilité d'une entrée. Le besoin-d'en-connaître intra-tenant est
 * porté au service (masquage au serializer), jamais en RLS (D32). L'UI ne
 * re-filtre pas.
 */
export type ExchangeVisibility = 'INTERNAL_ONLY' | 'SHARED_EXTERNAL';

// ============================================================================
// NOTIFICATION
// ============================================================================

export interface NotificationResponse {
  id: number;
  tenant_id: number;
  recipient_user_id: number;
  type: NotificationType;
  title: string;
  body: string;
  link_url: string | null;
  is_read: boolean;
  read_at: string | null;
  related_evaluation_id: number | null;
  related_care_plan_id: number | null;
  related_validation_request_id: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface NotificationList {
  items: NotificationResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface NotificationUnreadCount {
  unread_count: number;
}

// ============================================================================
// VALIDATION REQUEST — RESPONSE
// ============================================================================

export interface ValidationRequestResponse {
  id: number;
  tenant_id: number;
  workflow_type: ValidationWorkflowType;
  evaluation_id: number | null;
  care_plan_id: number | null;
  stage: ValidationStage;

  submitted_by_user_id: number;
  submitted_at: string;
  assigned_validator_user_id: number | null;

  decision: ValidationDecision | null;
  decided_at: string | null;
  decided_by_user_id: number | null;
  decided_on_behalf_of: string | null;

  decision_motif: string | null;
  invalidation_reason: InvalidationReason | null;
  info_request_message: string | null;

  withdrawn_at: string | null;
  withdrawn_by_user_id: number | null;
  withdrawal_reason: string | null;

  attachments: Record<string, unknown>[];
  notes: string;

  created_at: string;
  updated_at: string | null;

  is_pending: boolean;
  is_decided: boolean;
  is_withdrawn: boolean;
}

export interface ValidationRequestSummary {
  id: number;
  workflow_type: ValidationWorkflowType;
  evaluation_id: number | null;
  care_plan_id: number | null;
  stage: ValidationStage;
  submitted_by_user_id: number;
  submitted_at: string;
  assigned_validator_user_id: number | null;
  decision: ValidationDecision | null;
  decided_at: string | null;
  is_pending: boolean;
  is_decided: boolean;
  is_withdrawn: boolean;
  created_at: string;
}

export interface ValidationRequestList {
  items: ValidationRequestSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ValidationRequestFilters {
  workflow_type?: ValidationWorkflowType | null;
  stage?: ValidationStage | null;
  decision?: ValidationDecision | null;
  assigned_validator_user_id?: number | null;
  submitted_by_user_id?: number | null;
  pending_only?: boolean | null;
}

// ============================================================================
// VALIDATION REQUEST — ACTION PAYLOADS
// ============================================================================

export interface ValidationSubmitRequest {
  notes?: string | null;
}

/** Payload de re-soumission après complément demandé (R1 — boucle MORE_INFO). */
export interface ResubmitRequest {
  notes?: string | null;
}

export interface ValidationTransmitRequest {
  assigned_validator_user_id: number;
  notes?: string | null;
}

export interface ValidationDecisionRequest {
  decision: ValidationDecision;
  decision_motif?: string | null;
  invalidation_reason?: InvalidationReason | null;
  info_request_message?: string | null;
  decided_on_behalf_of?: string | null;
  attachments?: Record<string, unknown>[];
}

export interface ValidationWithdrawRequest {
  withdrawal_reason?: string | null;
}

export interface MarkUnderAppealRequest {
  appeal_notes?: string | null;
}

// ============================================================================
// VALIDATION EXCHANGE — FIL D'ÉCHANGE (B40-J3)
// ============================================================================

/**
 * Entrée du fil d'échange. Miroir de `ExchangeResponse`.
 * `author_user_id` nullable (FK ON DELETE SET NULL : journal append-only).
 * `is_decision` est une @property ORM propagée : true pour VALIDATE / REQUEST_INFO
 * / INVALIDATE uniquement (PAS TRANSMIT, ni SUBMIT/COMMENT/RESUBMIT).
 */
export interface ExchangeResponse {
  id: number;
  tenant_id: number;
  validation_request_id: number;
  author_user_id: number | null;
  author_role: string;
  action_type: ExchangeActionType;
  visibility: ExchangeVisibility;
  message: string | null;
  attachments: Record<string, unknown>[];
  created_at: string;
  updated_at: string | null;
  is_decision: boolean;
}

/**
 * Payload d'ajout d'un commentaire manuel au fil. Miroir de `ExchangeCreate`.
 * Pas d'`action_type` : un ajout manuel est toujours `COMMENT` (forcé service).
 * `visibility` optionnelle, défaut SHARED_EXTERNAL ; `message` requis non vide.
 */
export interface ExchangeCreate {
  message: string;
  visibility?: ExchangeVisibility;
  attachments?: Record<string, unknown>[];
}

// ============================================================================
// DOSSIER CONTEXT — ENRICHISSEMENT PORTAIL (S2/S3 — D-α.2)
// ============================================================================

/**
 * Sous-ensemble d'identité patient pour le bandeau du portail valideur.
 * Miroir de `PatientIdentitySchema` (backend). Minimisation RGPD : identité +
 * adresse + GIR uniquement — jamais NIR / INS / téléphone / email. Valeurs
 * déchiffrées côté service. `birth_date` en chaîne ISO (date sérialisée JSON).
 */
export interface PatientIdentity {
  first_name: string | null;
  last_name: string | null;
  birth_date: string | null;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  current_gir: number | null;
}

/**
 * Contexte d'un dossier de validation. Miroir de `DossierContextResponse`.
 * Agrégat backend (A0) : bandeau patient + pipeline des VR du dossier en ordre
 * chronologique. `requests` fiabilise séparateurs d'étape et n° de VR (fini le
 * best-effort par index).
 */
export interface DossierContext {
  patient: PatientIdentity;
  requests: ValidationRequestSummary[];
}

// ============================================================================
// LIBELLÉS UI (FR) — Record exhaustifs des unions ci-dessus
// ============================================================================

export const VALIDATION_STAGE_LABELS: Record<ValidationStage, string> = {
  INTERNAL_REVIEW: 'Relecture interne',
  MEDICAL_REVIEW: 'Validation médicale',
  FUNDING_REVIEW: 'Décision département',
};

export const VALIDATION_DECISION_LABELS: Record<ValidationDecision, string> = {
  VALIDATED: 'Validé',
  INVALIDATED: 'Invalidé',
  MORE_INFO_REQUESTED: 'Complément demandé',
  WITHDRAWN: 'Retiré',
};

export const INVALIDATION_REASON_LABELS: Record<InvalidationReason, string> = {
  INCOMPLETE_INFO: 'Informations manquantes',
  CLINICAL_DISAGREEMENT: 'Désaccord clinique',
  OUT_OF_SCOPE: 'Hors périmètre',
  OTHER: 'Autre',
};

export const INVALIDATION_REASON_ORDER: InvalidationReason[] = [
  'INCOMPLETE_INFO',
  'CLINICAL_DISAGREEMENT',
  'OUT_OF_SCOPE',
  'OTHER',
];

export const EXCHANGE_ACTION_LABELS: Record<ExchangeActionType, string> = {
  SUBMIT: 'Soumis',
  COMMENT: 'Commentaire',
  RESUBMIT: 'Re-soumis',
  VALIDATE: 'Validé',
  REQUEST_INFO: 'Complément',
  INVALIDATE: 'Invalidé',
  TRANSMIT: 'Transmis',
};

export const EXCHANGE_VISIBILITY_LABELS: Record<ExchangeVisibility, string> = {
  INTERNAL_ONLY: 'Interne',
  SHARED_EXTERNAL: 'Partagé',
};

export const VALIDATION_WORKFLOW_LABELS: Record<ValidationWorkflowType, string> = {
  AGGIR_FUNDING: 'Évaluation AGGIR',
  COORDINATION_DOSSIER: 'Dossier de coordination',
};

/**
 * Libellés FR des rôles d'auteur du fil. `author_role` est une chaîne figée
 * (instantané du rôle au moment de l'écriture, String(50) côté ORM — pas un
 * enum), d'où un Record<string, string> non exhaustif : prévoir un repli côté
 * composant pour toute valeur absente.
 */
export const EXCHANGE_AUTHOR_ROLE_LABELS: Record<string, string> = {
  COORDINATOR: 'Coordinateur',
  INTERNAL_VALIDATOR: 'Validateur interne',
  MEDICAL_VALIDATOR: 'Médecin',
  FUNDING_VALIDATOR: 'Agent département',
};

// ============================================================================
// PALETTE UI — ACCENT PAR ÉTAPE (promu de ValidationCompose ; 2e occurrence : T4)
// ============================================================================

/**
 * Quadruplet de classes Tailwind d'accentuation d'une étape de validation.
 * Jamais de hex : on expose des classes utilitaires (idiome { bg, text, border }
 * du projet). `bar` = ourlet gauche épais (border-l-*), `band` = fond du bandeau,
 * `text` = couleur du libellé, `line` = filet du séparateur de journal (bg-*-200,
 * ajouté à T4 pour la palette des séparateurs de ValidationThread — décision D).
 */
export interface StageAccent {
  bar: string;
  band: string;
  text: string;
  line: string;
}

/**
 * Accent par étape du pipeline de validation. Source de vérité unique partagée
 * par l'espace d'action (ValidationCompose — bandeau prospectif) et le journal
 * (ValidationThread — séparateurs d'étape, T4) : teal interne / bleu médical /
 * violet département.
 */
export const STAGE_ACCENT: Record<ValidationStage, StageAccent> = {
  INTERNAL_REVIEW: {
    bar: 'border-l-teal-500',
    band: 'bg-teal-50',
    text: 'text-teal-700',
    line: 'bg-teal-200',
  },
  MEDICAL_REVIEW: {
    bar: 'border-l-blue-500',
    band: 'bg-blue-50',
    text: 'text-blue-700',
    line: 'bg-blue-200',
  },
  FUNDING_REVIEW: {
    bar: 'border-l-violet-500',
    band: 'bg-violet-50',
    text: 'text-violet-700',
    line: 'bg-violet-200',
  },
};
