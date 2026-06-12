<script setup lang="ts">
  /**
   * CarePlanDetailPage.vue — Consultation et pilotage d'un plan d'aide
   *
   * 🆕 v5.41 — Phase 4, F4+F6 (remplace le stub F5)
   * 🆕 v5.45 — Jalon 4 / F4+F5 B28b : bouton « Réviser » + dialog de motif
   *           de révision (Select 7 motifs FR + textarea conditionnel).
   *           Appelle store.reviseCarePlan() qui retourne le DRAFT enfant,
   *           puis redirige vers le wizard miroir avec ?revise_from=N.
   *           Refactor DRY-strict : utilise classes main.css (.form-group,
   *           .form-label[--required], .form-legend-icon--violet,
   *           .form-field-counter, .message-with-lucide-icon).
   * 🆕 v5.46 — Patch d'affichage post-test : bloc Filiation affichant motif
   *           FR humain + lien vers plan parent + commentaire de révision.
   *           Visible uniquement si is_revision ET status !== 'CANCELLED'.
   *           Décision : la note d'audit `[RÉVISION B28b ...]` du champ notes
   *           reste machine-readable (traçabilité), le bloc Filiation est
   *           l'affichage human-readable complémentaire.
   *
   * Fonctionnalités :
   *   - Consultation complète : métadonnées, prestations, budget
   *   - Workflow state machine : soumettre / valider / suspendre / réactiver / terminer / annuler
   *   - 🆕 Réviser un plan ACTIVE/SUSPENDED (B28b — décision 37 partielle, gating COMPLETED-récent en backlog Bxx)
   *   - Gating par rôle : COORDINATEUR soumet, ADMIN valide (cf. décision 20/04)
   *   - Navigation space-aware admin ↔ soins (pattern CarePlanCreatePage)
   *   - Budget : barre progressive vert → orange → rouge (pattern SelectedServicesPanel)
   *
   * Route : /admin/care-plans/:id  ou  /soins/care-plans/:id
   * Layout : DefaultLayout (cross-space /admin et /soins — B48 Palier 3)
   *
   * Destination : src/pages/admin/careplan/CarePlanDetailPage.vue
   */
  import { computed, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { isAxiosError } from 'axios';

  // PrimeVue
  import Button from 'primevue/button';
  import Card from 'primevue/card';
  import Tag from 'primevue/tag';
  import Message from 'primevue/message';
  import Skeleton from 'primevue/skeleton';
  import ConfirmDialog from 'primevue/confirmdialog';
  import Dialog from 'primevue/dialog';
  import Select from 'primevue/select';
  import Textarea from 'primevue/textarea';
  import { useConfirm } from 'primevue/useconfirm';
  import { useToast } from 'primevue/usetoast';

  // Lucide icons
  import {
    FileText,
    Building2,
    CalendarDays,
    ClipboardList,
    CircleDashed,
    Clock,
    CheckCircle2,
    PauseCircle,
    CheckCheck,
    XCircle,
    Send,
    ShieldCheck,
    Pause,
    Play,
    Ban,
    Trash2,
    Wallet,
    AlertTriangle,
    History,
    Info,
    ExternalLink,
  } from 'lucide-vue-next';

  // Stores & services
  import { useCarePlanStore, useAuthStore, usePatientStore } from '@/stores';
  import { entityService } from '@/services';
  import type { CarePlanStatus, CarePlanServiceResponse, RevisionReason } from '@/types';
  import { REVISION_REASON_LABELS, REVISION_REASON_ORDER } from '@/types';
  import { formatEuro, formatPercent } from '@/utils/format';

  const route = useRoute();
  const router = useRouter();
  const carePlanStore = useCarePlanStore();
  const authStore = useAuthStore();
  const patientStore = usePatientStore();
  const confirm = useConfirm();
  const toast = useToast();

  // =============================================================================
  // STATE
  // =============================================================================

  const planId = computed(() => Number(route.params.id));
  const plan = computed(() => carePlanStore.currentPlan);
  const patient = computed(() => patientStore.currentPatient);
  const loading = computed(() => carePlanStore.loading);
  const saving = computed(() => carePlanStore.saving);
  const error = computed(() => carePlanStore.error);

  /** Nom de l'entité (chargé via entityService après loadPlan) */
  const entityName = ref<string | null>(null);

  /** Navigation space-aware (pattern CarePlanCreatePage) */
  const isInSoinsSpace = computed(() => route.path.startsWith('/soins'));

  // =============================================================================
  // COMPUTED — Statut
  // =============================================================================

  interface StatusConfig {
    label: string;
    severity: 'success' | 'info' | 'warn' | 'danger' | 'secondary';
    icon: typeof CircleDashed;
    description: string;
  }

  const STATUS_MAP: Record<CarePlanStatus, StatusConfig> = {
    DRAFT: {
      label: 'Brouillon',
      severity: 'secondary',
      icon: CircleDashed,
      description: 'Le plan est en cours de rédaction.',
    },
    PENDING_VALIDATION: {
      label: 'En attente de validation',
      severity: 'warn',
      icon: Clock,
      description: "Le plan a été soumis et attend la validation d'un responsable.",
    },
    ACTIVE: {
      label: 'Actif',
      severity: 'success',
      icon: CheckCircle2,
      description: 'Le plan est validé et les soins sont en cours.',
    },
    SUSPENDED: {
      label: 'Suspendu',
      severity: 'danger',
      icon: PauseCircle,
      description: 'Le plan est temporairement suspendu.',
    },
    COMPLETED: {
      label: 'Terminé',
      severity: 'info',
      icon: CheckCheck,
      description: 'Le plan est arrivé à son terme.',
    },
    CANCELLED: {
      label: 'Annulé',
      severity: 'secondary',
      icon: XCircle,
      description: 'Le plan a été annulé.',
    },
  };

  const statusConfig = computed<StatusConfig>(() => {
    if (!plan.value) return STATUS_MAP.DRAFT;
    return STATUS_MAP[plan.value.status] ?? STATUS_MAP.DRAFT;
  });

  // =============================================================================
  // COMPUTED — Budget
  // =============================================================================

  const budgetAllocated = computed(() => plan.value?.budget_allocated ?? 0);
  const budgetConsumed = computed(() => plan.value?.budget_consumed ?? 0);

  const budgetMonthly = computed(() => budgetConsumed.value);

  const budgetPercent = computed(() => {
    if (budgetAllocated.value <= 0) return 0;
    return (budgetMonthly.value / budgetAllocated.value) * 100;
  });

  const budgetBarClass = computed(() => {
    if (budgetPercent.value >= 100) return 'bg-red-500';
    if (budgetPercent.value >= 80) return 'bg-amber-500';
    return 'bg-teal-500';
  });

  const isOverBudget = computed(() => budgetPercent.value >= 100 && budgetAllocated.value > 0);

  // =============================================================================
  // COMPUTED — Permissions workflow
  // =============================================================================

  const isAdmin = computed(() => authStore.isAdmin);
  const canCreate = computed(() => authStore.canCreateCarePlan);

  const canSubmit = computed(() => plan.value?.status === 'DRAFT' && canCreate.value);
  const canValidate = computed(() => plan.value?.status === 'PENDING_VALIDATION' && isAdmin.value);
  const canSuspend = computed(() => plan.value?.status === 'ACTIVE' && isAdmin.value);
  const canReactivate = computed(() => plan.value?.status === 'SUSPENDED' && isAdmin.value);
  const canComplete = computed(() => plan.value?.status === 'ACTIVE' && isAdmin.value);
  const canCancel = computed(
    () =>
      ['DRAFT', 'PENDING_VALIDATION', 'ACTIVE', 'SUSPENDED'].includes(plan.value?.status ?? '') &&
      isAdmin.value,
  );
  const canDelete = computed(() => plan.value?.status === 'DRAFT' && canCreate.value);

  /**
   * Peut-on réviser ce plan ? (B28b — F4 approche prudente)
   *
   * Gating partiel : ACTIVE ou SUSPENDED uniquement.
   * Le cas COMPLETED-récent (décision 37) est reporté en backlog Bxx
   * (backend `is_revisable` calculé). Le filet 400 backend protège déjà
   * contre les requêtes invalides.
   *
   * Permission : COORDINATEUR (canCreate) ou ADMIN.
   */
  const canRevise = computed(() => {
    if (!plan.value) return false;
    const status = plan.value.status;
    if (status !== 'ACTIVE' && status !== 'SUSPENDED') return false;
    return canCreate.value || isAdmin.value;
  });

  /**
   * F4-ter — Peut-on reprendre l'édition d'un DRAFT-révision ?
   *
   * Conditions :
   *   - Status DRAFT (le plan n'est pas encore soumis pour validation)
   *   - supersedes_plan_id non-null (c'est bien un DRAFT-révision, pas
   *     un DRAFT créé ex nihilo qui aurait sa propre logique de reprise)
   *   - Permission COORDINATEUR ou ADMIN (cohérent avec canRevise)
   *
   * Mutuellement exclusif avec canRevise (qui requiert ACTIVE/SUSPENDED).
   *
   * Note : pas de filtre `created_by === currentUser.id` — tout IDEC
   * autorisé peut reprendre un DRAFT-révision de la structure (logique
   * collaborative cohérente avec l'absence de filtre sur canRevise).
   */
  const canResumeRevision = computed(() => {
    if (!plan.value) return false;
    if (plan.value.status !== 'DRAFT') return false;
    if (plan.value.supersedes_plan_id === null) return false;
    return canCreate.value || isAdmin.value;
  });

  // =============================================================================
  // COMPUTED — Bloc Filiation (B28b — patch v5.46 affichage human-readable)
  // =============================================================================

  /**
   * Affiche le bloc Filiation si le plan est issu d'une révision ET
   * n'est pas annulé (un plan annulé ne mérite pas une mise en avant
   * de sa filiation).
   */
  const showFiliationBlock = computed(() => {
    if (!plan.value) return false;
    if (!plan.value.is_revision) return false;
    if (plan.value.status === 'CANCELLED') return false;
    return true;
  });

  /**
   * Libellé FR du motif de révision pour affichage humain.
   * Utilise la table de traduction REVISION_REASON_LABELS (F1).
   */
  const revisionReasonLabel = computed<string>(() => {
    const reason = plan.value?.revision_reason;
    if (!reason) return '—';
    return REVISION_REASON_LABELS[reason] ?? reason;
  });

  /**
   * Cible de navigation vers le plan parent (path-based pour robustesse).
   * Space-aware admin/soins selon le contexte courant.
   * Retourne null si pas de parent (cas défensif).
   */
  const parentPlanLinkTo = computed(() => {
    const parentId = plan.value?.supersedes_plan_id;
    if (!parentId) return null;
    const prefix = isInSoinsSpace.value ? '/soins' : '/admin';
    return `${prefix}/care-plans/${parentId}`;
  });

  // =============================================================================
  // COMPUTED — Verrou révision en cours (B28c F4-bis)
  // =============================================================================

  /**
   * Verrou F4-bis (B28c décision 38) : true si le plan est révisable mais
   * porte déjà un DRAFT-révision en cours. Le bouton « Réviser » reste
   * visible mais grisé, et un Message info pédagogique propose à l'IDEC
   * de rejoindre le brouillon existant via pendingRevisionDraftLinkTo.
   */
  const hasPendingRevisionLock = computed<boolean>(() => {
    return canRevise.value && plan.value?.has_pending_revision === true;
  });

  /**
   * Cible de navigation vers le DRAFT-révision en cours (B51 option A).
   * Path-based pour robustesse, space-aware admin/soins.
   * Retourne null si aucun DRAFT exposé (cas défensif).
   */
  const pendingRevisionDraftLinkTo = computed<string | null>(() => {
    const draftId = plan.value?.pending_revision_draft_id;
    if (!draftId) return null;
    const prefix = isInSoinsSpace.value ? '/soins' : '/admin';
    return `${prefix}/care-plans/${draftId}`;
  });

  /** Navigue vers le DRAFT-révision en cours (lien Message info F4-bis). */

  function goToPendingRevisionDraft(): void {
    if (!pendingRevisionDraftLinkTo.value) return;
    void router.push(pendingRevisionDraftLinkTo.value);
  }

  /**
   * Notes affichées dans l'UI — filtre les lignes machine-readable d'audit B28a/B28b
   * posées par le backend dans `validate()` et `revise()`, ainsi que la ligne
   * « Commentaire: ... » qui les suit immédiatement (redondante avec le bloc
   * « Révision de plan » dédié qui affiche `revision_comment` proprement).
   *
   * Décision Session 12 « tampon greffier » respectée : la note d'audit reste
   * intacte côté DB (valeur juridique/réglementaire) ; seul l'affichage filtre.
   */
  const displayNotes = computed<string>(() => {
    const raw = plan.value?.notes ?? '';
    if (!raw) return '';

    const lines = raw.split('\n');
    const filtered: string[] = [];
    let skipNextCommentLine = false;

    for (const line of lines) {
      // Détecte une ligne d'audit B28a/B28b/B28c (pattern ouvert pour futures variantes)
      if (/^\[RÉVISION B28[a-z]? \d{4}-\d{2}-\d{2}T.+\] /.test(line)) {
        skipNextCommentLine = true;
        continue;
      }
      // Skip la ligne « Commentaire: ... » qui suit immédiatement une note d'audit
      if (skipNextCommentLine && line.startsWith('Commentaire: ')) {
        skipNextCommentLine = false;
        continue;
      }
      skipNextCommentLine = false;
      filtered.push(line);
    }

    return filtered.join('\n').trim();
  });

  // =============================================================================
  // COMPUTED — Services triés
  // =============================================================================

  const sortedServices = computed<CarePlanServiceResponse[]>(() => {
    if (!plan.value) return [];
    return [...plan.value.services].sort((a, b) => a.id - b.id);
  });

  // =============================================================================
  // COMPUTED — Patient & Entité (noms enrichis)
  // =============================================================================

  const patientFullName = computed(() => {
    if (!patient.value) return `Patient #${plan.value?.patient_id ?? '—'}`;
    const parts = [patient.value.last_name, patient.value.first_name].filter(Boolean);
    return parts.join(' ') || `Patient #${plan.value?.patient_id}`;
  });

  const entityDisplayName = computed(
    () => entityName.value ?? `Entité #${plan.value?.entity_id ?? '—'}`,
  );

  // =============================================================================
  // COMPUTED — Formatage
  // =============================================================================

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    if (!/^\d{4}-\d{2}-\d{2}/.test(iso)) return iso;
    const [y, m, d] = iso.substring(0, 10).split('-');
    return `${d}/${m}/${y}`;
  }

  function formatPriority(priority: string): {
    label: string;
    severity: 'danger' | 'warn' | 'info' | 'secondary';
  } {
    switch (priority) {
      case 'CRITICAL':
        return { label: 'Critique', severity: 'danger' };
      case 'HIGH':
        return { label: 'Haute', severity: 'warn' };
      case 'MEDIUM':
        return { label: 'Moyenne', severity: 'info' };
      default:
        return { label: 'Basse', severity: 'secondary' };
    }
  }

  // =============================================================================
  // ACTIONS — Navigation
  // =============================================================================

  function goBack(): void {
    if (isInSoinsSpace.value) {
      // Espace soins : retour fiche patient avec onglet plans-aide actif
      // (pas de page liste /soins/care-plans — l'onglet la remplace)
      if (plan.value?.patient_id) {
        router.push({
          name: 'soins-patient-detail',
          params: { id: String(plan.value.patient_id) },
          query: { tab: 'plans-aide' },
        });
      } else {
        // Fallback si plan indisponible (erreur de chargement)
        router.push({ name: 'soins-patients' });
      }
    } else {
      // Espace admin : retour liste plans d'aide (inchangé)
      router.push({ name: 'admin-care-plans' });
    }
  }

  /**
   * Navigation vers le plan parent depuis le bloc Filiation (B28b).
   * Path-based pour éviter la dépendance au nom de route exact.
   */
  function goToParent(): void {
    if (parentPlanLinkTo.value) {
      router.push(parentPlanLinkTo.value);
    }
  }

  // =============================================================================
  // ACTIONS — Workflow (chaque action = confirm + appel store + toast)
  // =============================================================================

  function onSubmit(): void {
    confirm.require({
      message: 'Soumettre ce plan pour validation ? Il ne sera plus modifiable.',
      header: 'Soumettre le plan',
      acceptLabel: 'Soumettre',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.submitPlan(planId.value);
            toast.add({
              severity: 'success',
              summary: 'Plan soumis',
              detail: 'Le plan a été transmis pour validation.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de soumettre le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onValidate(): void {
    confirm.require({
      message: 'Valider et activer ce plan ? Les soins pourront démarrer.',
      header: 'Valider le plan',
      acceptLabel: 'Valider',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.validatePlan(planId.value);
            toast.add({
              severity: 'success',
              summary: 'Plan validé',
              detail: 'Le plan est désormais actif.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de valider le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onSuspend(): void {
    confirm.require({
      message: 'Suspendre ce plan ? Les interventions seront temporairement interrompues.',
      header: 'Suspendre le plan',
      acceptLabel: 'Suspendre',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.suspendPlan(planId.value);
            toast.add({
              severity: 'warn',
              summary: 'Plan suspendu',
              detail: 'Le plan a été suspendu.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de suspendre le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onReactivate(): void {
    confirm.require({
      message: 'Réactiver ce plan ? Les interventions reprendront.',
      header: 'Réactiver le plan',
      acceptLabel: 'Réactiver',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.reactivatePlan(planId.value);
            toast.add({
              severity: 'success',
              summary: 'Plan réactivé',
              detail: 'Le plan est de nouveau actif.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de réactiver le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onComplete(): void {
    confirm.require({
      message: 'Marquer ce plan comme terminé ? Cette action est définitive.',
      header: 'Terminer le plan',
      acceptLabel: 'Terminer',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.completePlan(planId.value);
            toast.add({
              severity: 'info',
              summary: 'Plan terminé',
              detail: 'Le plan a été clôturé.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de terminer le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onCancel(): void {
    confirm.require({
      message: 'Annuler définitivement ce plan ? Cette action est irréversible.',
      header: 'Annuler le plan',
      acceptLabel: "Confirmer l'annulation",
      rejectLabel: 'Retour',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.cancelPlan(planId.value);
            toast.add({
              severity: 'warn',
              summary: 'Plan annulé',
              detail: 'Le plan a été définitivement annulé.',
              life: 4000,
            });
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? "Impossible d'annuler le plan.",
              life: 5000,
            });
          }
        })();
      },
    });
  }

  function onDelete(): void {
    confirm.require({
      message: 'Supprimer ce brouillon ? Toutes les prestations associées seront perdues.',
      header: 'Supprimer le brouillon',
      acceptLabel: 'Supprimer',
      rejectLabel: 'Annuler',
      accept: () => {
        confirm.close();
        void (async () => {
          try {
            await carePlanStore.deletePlan(planId.value);
            toast.add({ severity: 'info', summary: 'Brouillon supprimé', life: 3000 });
            goBack();
          } catch {
            toast.add({
              severity: 'error',
              summary: 'Erreur',
              detail: carePlanStore.error ?? 'Impossible de supprimer le plan.',
              life: 5000,
            });
          }
        })();
      },
    });
  }

  // =============================================================================
  // ACTIONS — Réviser (F4 + F5 — dialog motif puis appel store)
  // =============================================================================

  /** Visibilité du dialog de motif de révision (F5) */
  const reviseDialogVisible = ref(false);

  /** Motif sélectionné dans le Select (F5) */
  const reviseReason = ref<RevisionReason | null>(null);

  /** Commentaire libre — obligatoire si reviseReason === 'OTHER' */
  const reviseComment = ref<string>('');

  /**
   * Options du Select de motif (F5) — pré-formatées pour PrimeVue Select
   * (label affiché en FR, value envoyée au backend).
   */
  const reviseReasonOptions = computed(() =>
    REVISION_REASON_ORDER.map((code) => ({
      label: REVISION_REASON_LABELS[code],
      value: code,
    })),
  );

  /** Le commentaire est-il requis ? (uniquement si motif === OTHER) */
  const reviseCommentRequired = computed(() => reviseReason.value === 'OTHER');

  /** Le formulaire est-il valide pour soumission ? */
  const canSubmitRevision = computed(() => {
    if (!reviseReason.value) return false;
    if (reviseCommentRequired.value && reviseComment.value.trim().length === 0) {
      return false;
    }
    return true;
  });

  /** Ouvre le dialog (handler du bouton « Réviser ») */
  function onRevise(): void {
    // Reset des champs (au cas où l'IDEC aurait fermé puis rouvert)
    reviseReason.value = null;
    reviseComment.value = '';
    reviseDialogVisible.value = true;
  }

  /**
   * F4-ter — Reprendre l'édition d'un DRAFT-révision.
   *
   * Réutilise le wizard mode unifié (option B verrouillée F6) via la query
   * `?revise_from=N` qui hydrate la page d'après `currentPlan` chargé.
   *
   * Pas d'API call — juste une redirection vers le wizard. Le DRAFT est
   * déjà persisté en DB, le wizard se chargera de l'hydrater (F6.2-F6.4)
   * et de proposer le save 2-temps replaceServices+updatePlan (F6.6).
   */
  async function onResumeRevision(): Promise<void> {
    if (!canResumeRevision.value) return;
    const targetRouteName = isInSoinsSpace.value
      ? 'soins-care-plans-create'
      : 'admin-care-plans-create';
    await router.push({
      name: targetRouteName,
      query: { revise_from: String(planId.value) },
    });
  }

  /** Ferme le dialog sans valider */
  function onRevisionCancel(): void {
    reviseDialogVisible.value = false;
  }

  /**
   * Valide le formulaire et lance la révision (F5 → API → redirection F6).
   *
   * Flow :
   * 1. Appel store.reviseCarePlan(parentId, payload) → DRAFT enfant
   * 2. Toast succès
   * 3. Redirection vers le wizard miroir : /soins|/admin/care-plans/new?revise_from=N
   *    (mode unifié option B — décision F6 verrouillée)
   */
  function onRevisionConfirm(): void {
    if (!canSubmitRevision.value || !reviseReason.value) return;

    void (async () => {
      try {
        const draft = await carePlanStore.reviseCarePlan(planId.value, {
          revision_reason: reviseReason.value!,
          revision_comment: reviseComment.value.trim() || null,
          // inherit_services et inherit_gir : on laisse les défauts backend (true / true)
        });

        reviseDialogVisible.value = false;
        toast.add({
          severity: 'success',
          summary: 'Brouillon de révision créé',
          detail: 'Vous pouvez le compléter dans le wizard.',
          life: 4000,
        });

        // Redirection vers le wizard miroir (F6 mode unifié — option B)
        const targetRouteName = isInSoinsSpace.value
          ? 'soins-care-plans-create'
          : 'admin-care-plans-create';
        await router.push({
          name: targetRouteName,
          query: { revise_from: String(draft.id) },
        });
      } catch (err: unknown) {
        // F4-bis c) — Traduction 409 PENDING_REVISION_EXISTS (B28c).
        // Cas marginal grâce au gating proactif F4-bis a/b ; protège contre
        // les races et les forçages API. On ferme le dialog et on rafraîchit
        // le plan : le bouton se grise et le Message info pédagogique apparaît
        // sur la page — UX plus claire qu'un toast éphémère redondant.
        if (isAxiosError(err) && err.response?.status === 409) {
          const detail = err.response.data?.detail;
          if (detail && typeof detail === 'object' && detail.code === 'PENDING_REVISION_EXISTS') {
            reviseDialogVisible.value = false;
            await carePlanStore.loadPlan(planId.value);
            return;
          }
        }
        // Fallback générique pour les autres erreurs (réseau, 500 imprévu, etc.)
        toast.add({
          severity: 'error',
          summary: 'Erreur',
          detail: carePlanStore.error ?? 'Impossible de créer la révision.',
          life: 5000,
        });
      }
    })();
  }

  // =============================================================================
  // COMPUTED — GIR
  // =============================================================================

  const girClass = computed(() => {
    const gir = plan.value?.gir_at_creation;
    if (!gir) return '';
    if (gir <= 2) return 'gir-chip--severe';
    if (gir <= 4) return 'gir-chip--moderate';
    return 'gir-chip--light';
  });

  // =============================================================================
  // LIFECYCLE
  // =============================================================================

  // Watch sur planId avec immediate: true → déclenche au mount initial ET à
  // chaque changement de paramètre URL (ex: navigation /care-plans/13 →
  // /care-plans/16 via le lien « Voir le brouillon »). Vue Router 4 réutilise
  // le composant pour deux URLs matchant la même route pattern, donc
  // onMounted ne suffit pas — il faut réagir au changement de planId.
  watch(
    planId,
    async (newId) => {
      if (Number.isNaN(newId)) return;
      await carePlanStore.loadPlan(newId);

      // Enrichir avec les noms patient + entité (éviter les IDs numériques)
      if (plan.value) {
        try {
          await patientStore.fetchPatient(plan.value.patient_id);
        } catch {
          /* patient non trouvé — on garde l'ID */
        }
        try {
          const entity = await entityService.get(plan.value.entity_id);
          entityName.value = entity.name ?? null;
        } catch {
          /* entité non trouvée — on garde l'ID */
        }
      }
    },
    { immediate: true },
  );
</script>

<template>
  <div class="space-y-6">
    <ConfirmDialog />

    <!-- ─── LOADING ──────────────────────────────────────────────────────── -->
    <div v-if="loading && !plan" class="space-y-4">
      <Skeleton width="50%" height="2rem" />
      <Skeleton width="30%" height="1rem" />
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <Skeleton height="16rem" class="lg:col-span-2" />
        <Skeleton height="10rem" />
      </div>
    </div>

    <!-- ─── ERROR ────────────────────────────────────────────────────────── -->
    <Message v-else-if="error && !plan" :closable="false" severity="error">
      {{ error }}
    </Message>

    <!-- ─── CONTENU ──────────────────────────────────────────────────────── -->
    <template v-else-if="plan">
      <!-- HEADER -->
      <div class="flex items-center gap-3">
        <Button
          v-tooltip="'Retour à la liste'"
          :icon="'pi pi-arrow-left'"
          severity="secondary"
          variant="text"
          rounded
          @click="goBack"
        />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-bold text-slate-800 truncate">{{ plan.title }}</h1>
            <Tag :value="statusConfig.label" :severity="statusConfig.severity" />
          </div>
          <p class="text-sm text-slate-500 mt-0.5">
            Créé le {{ formatDate(plan.created_at) }}
            <span v-if="plan.reference_number"> · Réf. {{ plan.reference_number }}</span>
          </p>
        </div>
      </div>

      <!-- ACTIONS HEADER -->
      <div
        v-if="canSubmit || canValidate || canRevise || canDelete || canResumeRevision"
        class="flex flex-wrap gap-2"
      >
        <button
          v-if="canResumeRevision"
          :disabled="saving"
          class="workflow-btn workflow-btn--revise"
          @click="onResumeRevision"
        >
          <History :size="16" :stroke-width="1.8" />
          Reprendre l'édition
        </button>
        <button
          v-if="canSubmit"
          :disabled="saving"
          class="workflow-btn workflow-btn--submit"
          @click="onSubmit"
        >
          <Send :size="16" :stroke-width="1.8" />
          Soumettre pour validation
        </button>
        <button
          v-if="canValidate"
          :disabled="saving"
          class="workflow-btn workflow-btn--validate"
          @click="onValidate"
        >
          <ShieldCheck :size="16" :stroke-width="1.8" />
          Valider et activer
        </button>
        <button
          v-if="canRevise"
          :disabled="saving || hasPendingRevisionLock"
          class="workflow-btn workflow-btn--revise"
          @click="onRevise"
        >
          <History :size="16" :stroke-width="1.8" />
          Réviser
        </button>
        <button
          v-if="canDelete"
          :disabled="saving"
          class="workflow-btn workflow-btn--danger"
          @click="onDelete"
        >
          <Trash2 :size="16" :stroke-width="1.8" />
          Supprimer
        </button>
      </div>

      <!-- F4-bis — Verrou révision en cours (B28c décision 38) -->
      <Message v-if="hasPendingRevisionLock" :closable="false" severity="info">
        <div class="message-with-lucide-icon">
          <Info :size="16" :stroke-width="1.8" class="message-with-lucide-icon__icon" />
          <span>
            Une révision est déjà en cours
            <strong v-if="plan?.pending_revision_draft_id">
              (brouillon #{{ plan.pending_revision_draft_id }}) </strong
            >. Terminez-la ou supprimez-la avant d'en démarrer une nouvelle.
            <button
              v-if="pendingRevisionDraftLinkTo"
              type="button"
              class="filiation-link"
              @click="goToPendingRevisionDraft"
            >
              Voir le brouillon
              <ExternalLink :size="13" :stroke-width="1.8" />
            </button>
          </span>
        </div>
      </Message>

      <!-- GRILLE PRINCIPALE -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- ═══ COLONNE GAUCHE (2/3) ═══ -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Card Informations -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--teal">
                  <FileText :size="18" :stroke-width="1.8" />
                </div>
                Informations
              </div>
            </template>
            <template #content>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div>
                  <div class="field-label">Entité</div>
                  <div class="field-value flex items-center gap-1.5">
                    <Building2 :size="14" class="text-slate-400" />
                    {{ entityDisplayName }}
                  </div>
                </div>
                <div>
                  <div class="field-label">Patient</div>
                  <div class="field-value text-display-uppercase">{{ patientFullName }}</div>
                </div>
                <div>
                  <div class="field-label">GIR à la création</div>
                  <div class="field-value">
                    <span v-if="plan.gir_at_creation" :class="girClass" class="gir-chip">
                      GIR {{ plan.gir_at_creation }}
                    </span>
                    <span v-else class="text-slate-400">—</span>
                  </div>
                </div>
                <div>
                  <div class="field-label">Date début</div>
                  <div class="field-value flex items-center gap-1.5">
                    <CalendarDays :size="14" class="text-slate-400" />
                    {{ formatDate(plan.start_date) }}
                  </div>
                </div>
                <div>
                  <div class="field-label">Date fin</div>
                  <div class="field-value">{{ formatDate(plan.end_date) }}</div>
                </div>
                <div>
                  <div class="field-label">Heures / semaine</div>
                  <div class="field-value">
                    {{ plan.total_hours_week ? `${plan.total_hours_week}h` : '—' }}
                  </div>
                </div>
              </div>
              <div v-if="displayNotes" class="mt-4 pt-4 border-t border-slate-100">
                <div class="field-label">Notes</div>
                <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                  {{ displayNotes }}
                </p>
              </div>
            </template>
          </Card>

          <!-- Card Filiation (B28b — patch v5.46, visible si is_revision et !CANCELLED) -->
          <Card v-if="showFiliationBlock" class="filiation-card">
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--violet">
                  <History :size="18" :stroke-width="1.8" />
                </div>
                Révision de plan
              </div>
            </template>
            <template #content>
              <div class="filiation-grid">
                <!-- Plan parent (lien) -->
                <div>
                  <div class="field-label">Plan parent</div>
                  <button
                    v-if="parentPlanLinkTo"
                    type="button"
                    class="filiation-link"
                    @click="goToParent"
                  >
                    Plan #{{ plan.supersedes_plan_id }}
                    <ExternalLink :size="13" :stroke-width="1.8" />
                  </button>
                  <span v-else class="text-sm text-slate-400">—</span>
                </div>

                <!-- Motif (libellé FR) -->
                <div>
                  <div class="field-label">Motif</div>
                  <p class="text-sm text-slate-700 font-medium">{{ revisionReasonLabel }}</p>
                </div>
              </div>

              <!-- Commentaire (sur toute la largeur si présent) -->
              <div v-if="plan.revision_comment" class="filiation-comment">
                <div class="field-label">Commentaire de révision</div>
                <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                  {{ plan.revision_comment }}
                </p>
              </div>
            </template>
          </Card>

          <!-- Card Prestations -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--blue">
                  <ClipboardList :size="18" :stroke-width="1.8" />
                </div>
                Prestations
                <span v-if="plan.services_count > 0" class="services-count-badge">
                  {{ plan.services_count }}
                </span>
              </div>
            </template>
            <template #content>
              <!-- Empty state -->
              <div v-if="sortedServices.length === 0" class="eval-empty-state">
                <ClipboardList :size="40" class="eval-empty-icon" />
                <p class="eval-empty-title">Aucune prestation</p>
                <p class="eval-empty-hint">Ce plan ne contient pas encore de prestations.</p>
              </div>

              <!-- Service list -->
              <div v-else class="service-list">
                <div v-for="service in sortedServices" :key="service.id" class="service-list-item">
                  <div class="service-list-info">
                    <div class="service-list-name">
                      <span class="font-mono text-xs text-teal-600 mr-1.5">{{
                        service.service_code ?? '—'
                      }}</span>
                      {{ service.service_name ?? 'Prestation' }}
                    </div>
                    <div class="service-list-meta">
                      <span v-if="service.entity_name">{{ service.entity_name }}</span>
                      <span>{{ service.duration_minutes }} min</span>
                      <span>{{ service.frequency_display }}</span>
                    </div>
                  </div>
                  <div class="service-list-right">
                    <Tag
                      :value="formatPriority(service.priority).label"
                      :severity="formatPriority(service.priority).severity"
                      class="text-xs"
                    />
                    <div v-if="service.effective_tarif !== null" class="service-list-tarif">
                      {{ formatEuro(service.effective_tarif * service.quantity_per_week) }}/sem
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <!-- ═══ COLONNE DROITE (1/3) ═══ -->
        <div class="space-y-6">
          <!-- Card Workflow -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--indigo">
                  <component :is="statusConfig.icon" :size="18" :stroke-width="1.8" />
                </div>
                Statut
              </div>
            </template>
            <template #content>
              <div class="flex items-center gap-2 mb-3">
                <Tag
                  :value="statusConfig.label"
                  :severity="statusConfig.severity"
                  class="text-sm"
                />
              </div>
              <p class="text-xs text-slate-500 leading-relaxed mb-4">
                {{ statusConfig.description }}
              </p>

              <div v-if="plan.validated_at" class="text-xs text-slate-400 mb-4">
                Validé le {{ formatDate(plan.validated_at) }}
              </div>

              <!-- Workflow actions -->
              <div class="flex flex-col gap-2">
                <button
                  v-if="canResumeRevision"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--revise w-full"
                  @click="onResumeRevision"
                >
                  <History :size="15" :stroke-width="1.8" />
                  Reprendre l'édition
                </button>
                <button
                  v-if="canSubmit"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--submit w-full"
                  @click="onSubmit"
                >
                  <Send :size="15" :stroke-width="1.8" />
                  Soumettre
                </button>
                <button
                  v-if="canValidate"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--validate w-full"
                  @click="onValidate"
                >
                  <ShieldCheck :size="15" :stroke-width="1.8" />
                  Valider et activer
                </button>
                <button
                  v-if="canSuspend"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--warning w-full"
                  @click="onSuspend"
                >
                  <Pause :size="15" :stroke-width="1.8" />
                  Suspendre
                </button>
                <button
                  v-if="canReactivate"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--submit w-full"
                  @click="onReactivate"
                >
                  <Play :size="15" :stroke-width="1.8" />
                  Réactiver
                </button>
                <button
                  v-if="canRevise"
                  :disabled="saving || hasPendingRevisionLock"
                  class="workflow-btn workflow-btn--revise w-full"
                  @click="onRevise"
                >
                  <History :size="15" :stroke-width="1.8" />
                  Réviser
                </button>
                <button
                  v-if="canComplete"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--info w-full"
                  @click="onComplete"
                >
                  <CheckCheck :size="15" :stroke-width="1.8" />
                  Terminer
                </button>
                <button
                  v-if="canCancel"
                  :disabled="saving"
                  class="workflow-btn workflow-btn--danger w-full"
                  @click="onCancel"
                >
                  <Ban :size="15" :stroke-width="1.8" />
                  Annuler le plan
                </button>
              </div>
            </template>
          </Card>

          <!-- Card Budget -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--amber">
                  <Wallet :size="18" :stroke-width="1.8" />
                </div>
                Budget
              </div>
            </template>
            <template #content>
              <div v-if="budgetAllocated > 0" class="space-y-3">
                <!-- Consommé / Alloué -->
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-500">Consommé</span>
                  <span class="font-bold text-slate-700">{{ formatEuro(budgetMonthly) }}</span>
                </div>
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-500">Alloué</span>
                  <span class="font-bold text-slate-700">{{ formatEuro(budgetAllocated) }}</span>
                </div>

                <!-- Barre budget -->
                <div>
                  <div class="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Utilisation</span>
                    <span>{{ formatPercent(Math.min(budgetPercent, 999)) }}</span>
                  </div>
                  <div class="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      :class="budgetBarClass"
                      :style="{ width: `${Math.min(budgetPercent, 100)}%` }"
                      class="h-full rounded-full transition-all duration-300"
                    />
                  </div>
                </div>

                <!-- Alerte dépassement -->
                <div
                  v-if="isOverBudget"
                  class="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5"
                >
                  <AlertTriangle :size="16" class="text-red-500 mt-0.5 shrink-0" />
                  <p class="text-xs text-red-700 leading-relaxed">
                    Le budget consommé dépasse l'enveloppe allouée de
                    <strong>{{ formatEuro(budgetMonthly - budgetAllocated) }}</strong
                    >.
                  </p>
                </div>
              </div>

              <!-- Pas de budget alloué -->
              <div v-else class="text-center py-4">
                <Wallet :size="32" class="mx-auto mb-2 text-slate-300" />
                <p class="text-sm text-slate-400">Aucun budget alloué</p>
                <p class="text-xs text-slate-400 mt-1">
                  Le budget peut être défini lors de la création du plan.
                </p>
              </div>
            </template>
          </Card>

          <!-- Card Affectation (résumé) -->
          <Card>
            <template #title>
              <div class="section-title">
                <div class="section-icon section-icon--emerald">
                  <CheckCircle2 :size="18" :stroke-width="1.8" />
                </div>
                Affectation
              </div>
            </template>
            <template #content>
              <div class="space-y-2">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-slate-500">Services affectés</span>
                  <span class="font-bold text-slate-700">
                    {{ plan.assigned_services_count }} / {{ plan.services_count }}
                  </span>
                </div>
                <div class="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    :style="{ width: `${plan.assignment_completion_rate}%` }"
                    class="h-full rounded-full bg-emerald-500 transition-all duration-300"
                  />
                </div>
                <Tag
                  :value="plan.is_fully_assigned ? 'Complet' : 'Partiel'"
                  :severity="plan.is_fully_assigned ? 'success' : 'warn'"
                  class="text-xs"
                />
              </div>
            </template>
          </Card>
        </div>
      </div>

      <!-- ─── DIALOG F5 — Motif de révision (B28b) ───────────────────────── -->
      <Dialog
        v-model:visible="reviseDialogVisible"
        :closable="!saving"
        :close-on-escape="!saving"
        :draggable="false"
        :style="{ width: '32rem' }"
        class="revise-dialog"
        modal
      >
        <template #header>
          <div class="flex items-center gap-3">
            <div class="form-legend-icon form-legend-icon--violet revise-dialog__icon-wrapper">
              <History :size="20" :stroke-width="1.8" />
            </div>
            <div>
              <h2 class="revise-dialog__title">Réviser le plan d'aide</h2>
              <p class="revise-dialog__subtitle">
                Une copie en brouillon sera créée à partir du plan actuel. Vous pourrez la modifier
                avant validation.
              </p>
            </div>
          </div>
        </template>

        <div class="revise-dialog__body">
          <!-- Champ : Motif (Select obligatoire) -->
          <div class="form-group revise-dialog__field">
            <label for="revise-reason" class="form-label form-label--required">
              Motif de la révision
            </label>
            <Select
              id="revise-reason"
              v-model="reviseReason"
              :options="reviseReasonOptions"
              :disabled="saving"
              option-label="label"
              option-value="value"
              placeholder="Sélectionner un motif"
              class="w-full"
            />
          </div>

          <!-- Champ : Commentaire (obligatoire si OTHER, sinon facultatif) -->
          <div class="form-group revise-dialog__field">
            <label
              :class="['form-label', { 'form-label--required': reviseCommentRequired }]"
              for="revise-comment"
            >
              {{ reviseCommentRequired ? 'Précisez le motif' : 'Commentaire (facultatif)' }}
            </label>
            <Textarea
              id="revise-comment"
              v-model="reviseComment"
              :maxlength="1000"
              :placeholder="
                reviseCommentRequired
                  ? 'Précisez la raison de la révision'
                  : 'Notes complémentaires sur la révision (optionnel)'
              "
              :disabled="saving"
              rows="3"
              class="w-full"
            />
            <p class="form-field-counter">{{ reviseComment.length }} / 1000 caractères</p>
          </div>

          <!-- Alerte info — clôture automatique du plan parent -->
          <Message :closable="false" severity="info" class="revise-dialog__alert">
            <div class="message-with-lucide-icon">
              <Info :size="16" :stroke-width="1.8" class="message-with-lucide-icon__icon" />
              <span>
                Le plan <strong>#{{ plan?.id ?? '—' }}</strong> actuellement
                <strong>{{ plan?.status === 'ACTIVE' ? 'actif' : 'suspendu' }}</strong>
                sera <strong>automatiquement clôturé</strong>
                au moment où vous validerez la révision.
              </span>
            </div>
          </Message>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <Button
              :disabled="saving"
              label="Annuler"
              severity="secondary"
              outlined
              @click="onRevisionCancel"
            />
            <Button
              :loading="saving"
              :disabled="!canSubmitRevision || saving"
              label="Créer la révision"
              severity="primary"
              @click="onRevisionConfirm"
            />
          </div>
        </template>
      </Dialog>
    </template>
  </div>
</template>

<style scoped>
  /* ─── Section titles (pattern PatientDetailPage_admin) ─────────────────── */
  .section-title {
    @apply flex items-center gap-2.5 text-base font-semibold text-slate-800;
  }
  .section-icon {
    @apply flex items-center justify-center flex-shrink-0;
    width: 2rem;
    height: 2rem;
    border-radius: 0.5rem;
  }
  .section-icon--teal {
    background: #f0fdfa;
    color: #0d9488;
  }
  .section-icon--blue {
    background: #eff6ff;
    color: #3b82f6;
  }
  .section-icon--amber {
    background: #fffbeb;
    color: #d97706;
  }
  .section-icon--indigo {
    background: #eef2ff;
    color: #6366f1;
  }
  .section-icon--emerald {
    background: #ecfdf5;
    color: #059669;
  }
  /* Variante violette : sémantique « révision » (cohérent avec workflow-btn--revise) */
  .section-icon--violet {
    background: #f5f3ff;
    color: #7c3aed;
  }

  /* ─── Field labels (pattern PatientDetailPage_admin) ───────────────────── */
  .field-label {
    @apply text-slate-400 text-xs font-medium uppercase tracking-wide mb-0.5;
  }
  .field-value {
    @apply font-medium text-slate-800;
  }

  /* ─── GIR chip ─────────────────────────────────────────────────────────── */
  .gir-chip {
    @apply inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold text-white;
  }
  .gir-chip--severe {
    background: #ef4444;
  }
  .gir-chip--moderate {
    background: #f59e0b;
  }
  .gir-chip--light {
    background: #22c55e;
  }

  /* ─── Services count badge ─────────────────────────────────────────────── */
  .services-count-badge {
    @apply inline-flex items-center justify-center text-xs font-bold rounded-full;
    width: 1.375rem;
    height: 1.375rem;
    background: #f0fdfa;
    color: #0d9488;
    margin-left: 0.25rem;
  }

  /* ─── Service list ─────────────────────────────────────────────────────── */
  .service-list {
    @apply divide-y divide-slate-100;
  }
  .service-list-item {
    @apply flex items-center justify-between gap-3 py-3;
  }
  .service-list-item:first-child {
    padding-top: 0;
  }
  .service-list-info {
    @apply flex-1 min-w-0;
  }
  .service-list-name {
    @apply text-sm font-semibold text-slate-700 truncate;
  }
  .service-list-meta {
    @apply flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-400 mt-0.5;
  }
  .service-list-right {
    @apply flex items-center gap-3 shrink-0;
  }
  .service-list-tarif {
    @apply text-sm font-bold text-slate-700 tabular-nums;
  }

  /* ─── Workflow buttons ─────────────────────────────────────────────────── */
  .workflow-btn {
    @apply inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold cursor-pointer;
    border: 1.5px solid transparent;
    transition: all 0.2s ease;
  }
  .workflow-btn:disabled {
    @apply opacity-50 cursor-not-allowed;
  }

  .workflow-btn--submit {
    @apply text-teal-700;
    background: #f0fdfa;
    border-color: #99f6e4;
  }
  .workflow-btn--submit:hover:not(:disabled) {
    background: #ccfbf1;
    border-color: #5eead4;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.12);
  }

  .workflow-btn--validate {
    @apply text-emerald-700;
    background: #ecfdf5;
    border-color: #a7f3d0;
  }
  .workflow-btn--validate:hover:not(:disabled) {
    background: #d1fae5;
    border-color: #6ee7b7;
    box-shadow: 0 2px 8px rgba(5, 150, 105, 0.12);
  }

  .workflow-btn--warning {
    @apply text-amber-700;
    background: #fffbeb;
    border-color: #fde68a;
  }
  .workflow-btn--warning:hover:not(:disabled) {
    background: #fef3c7;
    border-color: #fcd34d;
    box-shadow: 0 2px 8px rgba(217, 119, 6, 0.12);
  }

  .workflow-btn--info {
    @apply text-blue-700;
    background: #eff6ff;
    border-color: #bfdbfe;
  }
  .workflow-btn--info:hover:not(:disabled) {
    background: #dbeafe;
    border-color: #93c5fd;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12);
  }

  /* Réviser : palette violette pour différencier des autres actions workflow */
  .workflow-btn--revise {
    @apply text-violet-700;
    background: #f5f3ff;
    border-color: #ddd6fe;
  }
  .workflow-btn--revise:hover:not(:disabled) {
    background: #ede9fe;
    border-color: #c4b5fd;
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.12);
  }

  .workflow-btn--danger {
    @apply text-red-600;
    background: white;
    border-color: #fecaca;
  }
  .workflow-btn--danger:hover:not(:disabled) {
    background: #fef2f2;
    border-color: #fca5a5;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.12);
  }

  /* ─── Empty state (pattern PatientDetailPage_admin) ────────────────────── */
  .eval-empty-state {
    @apply flex flex-col items-center justify-center py-8 text-center;
  }
  .eval-empty-icon {
    @apply mb-3;
    color: #cbd5e1;
  }
  .eval-empty-title {
    @apply text-sm font-semibold text-slate-500 mb-1;
  }
  .eval-empty-hint {
    @apply text-xs text-slate-400 max-w-xs leading-relaxed;
  }

  /* ─── Card Filiation (B28b — patch v5.46) ─────────────────────────────── */
  /* Layout 2 colonnes pour Plan parent + Motif, comme la card Informations.
   Le commentaire de révision se place en-dessous, sur toute la largeur. */
  .filiation-grid {
    @apply grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4;
  }

  .filiation-comment {
    @apply mt-4 pt-4 border-t border-slate-100;
  }

  /* Lien vers le plan parent : style discret violet, cohérent avec
   la sémantique « révision » du fichier (cf. workflow-btn--revise). */
  .filiation-link {
    @apply inline-flex items-center gap-1 text-sm font-semibold;
    @apply text-violet-700 hover:text-violet-800;
    @apply transition-colors cursor-pointer;
    background: transparent;
    border: none;
    padding: 0;
    text-decoration: none;
  }
  .filiation-link:hover {
    text-decoration: underline;
  }
  .filiation-link:focus-visible {
    outline: 2px solid #c4b5fd;
    outline-offset: 2px;
    border-radius: 0.25rem;
  }

  /* ─── Dialog F5 — Motif de révision (B28b) ────────────────────────────── */
  /* Le gros du styling vit dans main.css :
   - .form-group, .form-label[--required]   (groupes de champs)
   - .form-legend-icon--violet              (pastille icône violette)
   - .form-field-counter                    (compteur 0/1000)
   - .message-with-lucide-icon              (alerte icône Lucide)
   Ce bloc ne garde que les styles vraiment spécifiques au dialog. */

  /* Override de taille pour la pastille icône du header (main.css = 32px,
   ici on veut 36px pour équilibrer la hauteur du titre + sous-titre). */
  .revise-dialog__icon-wrapper {
    width: 2.25rem;
    height: 2.25rem;
  }

  .revise-dialog__title {
    @apply text-base font-bold text-slate-800 leading-tight;
    margin: 0;
  }

  .revise-dialog__subtitle {
    @apply text-xs text-slate-500 leading-relaxed mt-1;
    margin: 0.25rem 0 0 0;
  }

  .revise-dialog__body {
    @apply flex flex-col gap-4 py-2;
  }

  /* Override du mt-5 que .form-group porte par défaut (rythme adapté au dialog). */
  .revise-dialog__field {
    @apply mt-0;
  }

  .revise-dialog__alert {
    margin-top: 0.25rem;
  }
</style>