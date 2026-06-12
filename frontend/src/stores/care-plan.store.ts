/**
 * Store Pinia — Module Plan d'aide (Phase 4).
 *
 * Chemin : frontend/src/stores/care-plan.store.ts
 *
 * Rôle : état global du module plan d'aide.
 * - Liste des plans (page liste, filtres, pagination)
 * - Plan courant (détail / édition)
 * - Panier de services draft (création — F2)
 * - Semaine type : placements hebdomadaires (F3)
 * - Actions CRUD + workflow state machine (incl. revise B28b)
 *
 * Convention Pinia : defineStore + computed pour état réactif.
 * Convention #80 : import via barrel uniquement.
 * Convention #67 : tri explicite sur les computed ordonnées.
 *
 * 🆕 v01/05 — Ajout de reviseCarePlan() (B28b Jalon 4 / F3).
 */

import { computed, ref } from 'vue';

import { defineStore } from 'pinia';

import { carePlanService } from '@/services';
import type {
  CarePlanCreate,
  CarePlanFilters,
  CarePlanReplaceServicesRequest,
  CarePlanReviseRequest,
  CarePlanServiceCreate,
  CarePlanServiceDraft,
  CarePlanServiceResponse,
  CarePlanStatusChange,
  CarePlanSummary,
  CarePlanUpdate,
  CarePlanWithServices,
  PeriodDefinition,
  WeeklyPlacement,
} from '@/types';
import { PERIODS } from '@/types';

export const useCarePlanStore = defineStore('care-plan', () => {
  // =========================================================================
  // STATE — Liste
  // =========================================================================

  const plans = ref<CarePlanSummary[]>([]);
  const totalPlans = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const filters = ref<CarePlanFilters>({});

  // =========================================================================
  // STATE — Plan courant (détail / édition)
  // =========================================================================

  const currentPlan = ref<CarePlanWithServices | null>(null);

  // =========================================================================
  // STATE — Panier de services draft (création — F2)
  // =========================================================================

  /** Services en cours d'ajout avant sauvegarde du plan */
  const draftServices = ref<CarePlanServiceDraft[]>([]);

  // =========================================================================
  // STATE — Semaine type (F3)
  // =========================================================================

  /** Placements dans la grille hebdomadaire (un par combinaison draft × jour × heure) */
  const weeklyPlacements = ref<WeeklyPlacement[]>([]);

  /** Auto-incrémenté pour générer les id de placement */
  let nextPlacementId = 1;

  // =========================================================================
  // STATE — UI
  // =========================================================================

  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);

  // =========================================================================
  // COMPUTED — Plan courant
  // =========================================================================

  /** Le plan courant est-il éditable ? */
  const isEditable = computed(() => currentPlan.value?.is_editable ?? false);

  /** Le plan courant est-il en brouillon ? */
  const isDraft = computed(() => currentPlan.value?.is_draft ?? false);

  /** Services du plan courant triés par id (convention #67) */
  const currentServices = computed<CarePlanServiceResponse[]>(() => {
    if (!currentPlan.value) return [];
    return [...currentPlan.value.services].sort((a, b) => a.id - b.id);
  });

  /** Budget consommé du plan courant */
  const budgetConsumed = computed(() => currentPlan.value?.budget_consumed ?? 0);

  /** Budget alloué du plan courant */
  const budgetAllocated = computed(() => currentPlan.value?.budget_allocated ?? 0);

  /** Ratio budget consommé / alloué (0-1, null si pas de budget) */
  const budgetRatio = computed<number | null>(() => {
    if (!currentPlan.value?.budget_allocated) return null;
    const consumed = currentPlan.value.budget_consumed ?? 0;
    return consumed / currentPlan.value.budget_allocated;
  });

  // =========================================================================
  // COMPUTED — Panier draft (F2 — calculs locaux avant sauvegarde)
  // =========================================================================

  /** Total heures/semaine du panier draft */
  const draftTotalHoursWeek = computed(() => {
    return draftServices.value.reduce((sum: number, s: CarePlanServiceDraft) => {
      return sum + (s.duration_minutes * s.quantity_per_week) / 60;
    }, 0);
  });

  /** Budget draft estimé hebdomadaire (Σ tarif × quantité/semaine) */
  const draftBudgetWeekly = computed(() => {
    return draftServices.value.reduce((sum: number, s: CarePlanServiceDraft) => {
      const tarif = s._display_tarif ?? 0;
      return sum + tarif * s.quantity_per_week;
    }, 0);
  });

  /** Nombre de services dans le panier draft */
  const draftServicesCount = computed(() => draftServices.value.length);

  // =========================================================================
  // COMPUTED — Semaine type (F3)
  // =========================================================================

  /** Nombre total de placements dans la grille */
  const placementsCount = computed(() => weeklyPlacements.value.length);

  /** Total minutes placées dans la semaine */
  const totalPlacedMinutes = computed(() =>
    weeklyPlacements.value.reduce((sum: number, p: WeeklyPlacement) => sum + p.duration, 0),
  );

  /** Total heures placées formaté ('12h30') */
  const totalPlacedHoursFormatted = computed(() => {
    const total = totalPlacedMinutes.value;
    const h = Math.floor(total / 60);
    const m = total % 60;
    return `${h}h${String(m).padStart(2, '0')}`;
  });

  /**
   * Nombre de doublons détectés.
   * Un doublon = même prestation (même draftIndex) placée au même créneau
   * (même jour + chevauchement horaire). Deux prestations DIFFÉRENTES au
   * même créneau ne sont PAS un doublon (professionnels différents).
   */
  const doublonCount = computed(() => {
    let count = 0;
    for (let d = 0; d < 7; d++) {
      const dayItems = weeklyPlacements.value.filter((p: WeeklyPlacement) => p.day === d);
      for (let i = 0; i < dayItems.length; i++) {
        for (let j = i + 1; j < dayItems.length; j++) {
          const a = dayItems[i];
          const b = dayItems[j];
          if (a.draftIndex !== b.draftIndex) continue;
          const aStart = parseTimeToMin(a.startTime);
          const aEnd = aStart + a.duration;
          const bStart = parseTimeToMin(b.startTime);
          const bEnd = bStart + b.duration;
          if (aStart < bEnd && bStart < aEnd) count++;
        }
      }
    }
    return count;
  });

  // =========================================================================
  // ACTIONS — Liste
  // =========================================================================

  /** Charge la liste des plans avec les filtres courants */
  async function loadPlans(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const result = await carePlanService.list(currentPage.value, pageSize.value, filters.value);
      plans.value = result.items;
      totalPlans.value = result.total;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Met à jour les filtres et recharge la liste */
  async function setFilters(newFilters: CarePlanFilters): Promise<void> {
    filters.value = newFilters;
    currentPage.value = 1;
    await loadPlans();
  }

  /** Change de page et recharge */
  async function setPage(page: number): Promise<void> {
    currentPage.value = page;
    await loadPlans();
  }

  // =========================================================================
  // ACTIONS — Plan courant CRUD
  // =========================================================================

  /** Charge un plan par son ID */
  async function loadPlan(planId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.get(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Plan non trouvé';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** Crée un plan d'aide */
  async function createPlan(payload: CarePlanCreate): Promise<CarePlanWithServices> {
    saving.value = true;
    error.value = null;
    try {
      const plan = await carePlanService.create(payload);
      currentPlan.value = plan;
      return plan;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la création';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  /** Met à jour le plan courant */
  async function updatePlan(planId: number, payload: CarePlanUpdate): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.update(planId, payload);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la mise à jour';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  /** Supprime le plan (brouillon uniquement) */
  async function deletePlan(planId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      await carePlanService.remove(planId);
      currentPlan.value = null;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la suppression';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  // =========================================================================
  // ACTIONS — Workflow (State Machine)
  // =========================================================================

  async function submitPlan(planId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.submit(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la soumission';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function validatePlan(planId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.validate(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la validation';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  /**
   * Crée une révision du plan parent (B28b).
   * Retourne le DRAFT enfant créé pour que le composant appelant puisse
   * rediriger vers le wizard miroir avec ?revise_from=N.
   *
   * Note : NE met PAS à jour `currentPlan` ici car la révision crée un
   * nouveau plan distinct du parent visualisé. Le composant décide de
   * la suite (redirection vers /care-plans/new?revise_from=N typiquement).
   */
  async function reviseCarePlan(
    parentId: number,
    payload: CarePlanReviseRequest,
  ): Promise<CarePlanWithServices> {
    saving.value = true;
    error.value = null;
    try {
      const draft = await carePlanService.revise(parentId, payload);
      return draft;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la révision';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  /**
   * Remplace l'intégralité du panier de services d'un plan DRAFT (B28c).
   *
   * Sémantique « panier complet » : le payload contient la liste cible
   * finale ; le backend gère le delete-all + insert-all en transaction.
   * Statut éligible : DRAFT uniquement (autre statut → 409 CONFLICT).
   *
   * Met à jour currentPlan avec le plan rechargé contenant les nouveaux
   * services. Différence avec reviseCarePlan() : ici on édite le plan
   * courant, donc on actualise currentPlan.value avec la réponse —
   * contrairement à la révision qui crée un plan distinct du courant.
   *
   * Cas d'usage principal : sauvegarde du wizard de révision (F6.6).
   */
  async function replaceServices(
    planId: number,
    payload: CarePlanReplaceServicesRequest,
  ): Promise<CarePlanWithServices> {
    saving.value = true;
    error.value = null;
    try {
      const plan = await carePlanService.replaceServices(planId, payload);
      currentPlan.value = plan;
      return plan;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du remplacement des services';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function suspendPlan(planId: number, payload?: CarePlanStatusChange): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.suspend(planId, payload);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la suspension';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function reactivatePlan(planId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.reactivate(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la réactivation';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function completePlan(planId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.complete(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la complétion';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  async function cancelPlan(planId: number, payload?: CarePlanStatusChange): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      currentPlan.value = await carePlanService.cancel(planId, payload);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Erreur lors de l'annulation";
      throw err;
    } finally {
      saving.value = false;
    }
  }

  // =========================================================================
  // ACTIONS — Services du plan (API)
  // =========================================================================

  /** Ajoute un service au plan (appel API) et recharge le plan */
  async function addPlanService(planId: number, payload: CarePlanServiceCreate): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      await carePlanService.addService(planId, payload);
      // Recharger le plan pour avoir le budget_consumed à jour
      currentPlan.value = await carePlanService.get(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : "Erreur lors de l'ajout";
      throw err;
    } finally {
      saving.value = false;
    }
  }

  /** Supprime un service du plan et recharge */
  async function removePlanService(planId: number, serviceId: number): Promise<void> {
    saving.value = true;
    error.value = null;
    try {
      await carePlanService.removeService(planId, serviceId);
      currentPlan.value = await carePlanService.get(planId);
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors de la suppression';
      throw err;
    } finally {
      saving.value = false;
    }
  }

  // =========================================================================
  // ACTIONS — Panier draft (local, pas d'appel API)
  // =========================================================================

  /** Ajoute un service au panier draft */
  function addDraftService(service: CarePlanServiceDraft): void {
    draftServices.value.push(service);
  }

  /** Retire un service du panier draft */
  function removeDraftService(index: number): void {
    draftServices.value.splice(index, 1);
  }

  /** Met à jour un service du panier draft */
  function updateDraftService(index: number, data: Partial<CarePlanServiceDraft>): void {
    const current = draftServices.value[index];
    if (current) {
      draftServices.value[index] = { ...current, ...data };
    }
  }

  /** Vide le panier draft */
  function clearDraft(): void {
    draftServices.value = [];
  }

  /**
   * F6.3 — Hydrate le panier draft depuis une liste préparée (mode révision).
   *
   * Le store reste un porteur d'état pur : la transformation
   * CarePlanServiceResponse → CarePlanServiceDraft est faite par l'appelant
   * (CarePlanCreatePage.vue, qui a accès au catalogStore pour enrichir
   * les champs _display_profession_name et _display_domain absents de Response).
   */
  function hydrateDraftServices(drafts: CarePlanServiceDraft[]): void {
    draftServices.value = drafts;
  }

  // =========================================================================
  // ACTIONS — Semaine type (F3 — local, pas d'appel API)
  // =========================================================================

  /** Ajoute un placement unitaire dans la grille */
  function addPlacement(
    draftIndex: number,
    day: number,
    period: string,
    startTime: string,
    duration: number,
  ): WeeklyPlacement {
    const placement: WeeklyPlacement = {
      id: nextPlacementId++,
      draftIndex,
      day,
      period,
      startTime,
      duration,
    };
    weeklyPlacements.value.push(placement);
    return placement;
  }

  /** Retire un placement par son id */
  function removePlacement(placementId: number): void {
    weeklyPlacements.value = weeklyPlacements.value.filter(
      (p: WeeklyPlacement) => p.id !== placementId,
    );
  }

  /** Met à jour l'heure de début d'un placement (+ recalcul de la période) */
  function updatePlacementTime(
    placementId: number,
    newStartTime: string,
  ): void {
    const placement = weeklyPlacements.value.find(
      (p: WeeklyPlacement) => p.id === placementId,
    );
    if (!placement) return;
    placement.startTime = newStartTime;
    placement.period = periodFromStartTime(newStartTime);  // F6.4 — helper extrait
  }

  /**
   * F6.4 — Dérive la clé de période depuis une heure de début 'HH:MM'.
   *
   * Logique : extrait l'heure (0-23), itère sur PERIODS et retourne la `key`
   * de la première période dont l'intervalle [startH, endH) contient l'heure.
   * Pour la période 'nuit' (22h → 08h lendemain, endH=32), on plafonne endH à 24
   * pour gérer la transition naturellement (h=22 ou 23 → 'nuit', h<8 → ne match
   * pas 'nuit' mais retombera sur la première période matching qui sera 'matin'
   * via fallback — voir comportement attendu dans les tests).
   *
   * Edge cases :
   *   - Heure invalide ('25:00', etc.) → retourne 'matin' par défaut (pas de match)
   *   - Heure entre minuit et 7h (h<8) → fallback 'matin' (PAS 'nuit', à dessein :
   *     les placements nuit du jour J sont projetés sur le jour J, pas J+1)
   */
  function periodFromStartTime(startTime: string): string {
    const h = parseInt(startTime.split(':')[0], 10);
    for (const period of PERIODS) {
      const endH = period.endH > 24 ? 24 : period.endH;
      if (h >= period.startH && h < endH) {
        return period.key;
      }
    }
    return 'matin'; // fallback safety
  }

  /**
   * Applique une récurrence : place la même prestation sur N jours
   * à la même heure. Ignore les doublons exacts (même draft + jour + heure).
   */
  function applyRecurrence(
    draftIndex: number,
    days: number[],
    period: string,
    startTime: string,
    duration: number,
  ): void {
    days.forEach((day) => {
      const exists = weeklyPlacements.value.some(
        (p: WeeklyPlacement) =>
          p.draftIndex === draftIndex && p.day === day && p.startTime === startTime,
      );
      if (!exists) {
        addPlacement(draftIndex, day, period, startTime, duration);
      }
    });
  }

  /** Vide tous les placements */
  function clearPlacements(): void {
    weeklyPlacements.value = [];
    nextPlacementId = 1;
  }

  /**
   * Calcule l'heure de début auto-stackée pour une période donnée.
   * Si la période contient déjà des items, le nouveau commence après
   * la fin du dernier. Sinon, il commence à l'heure de début de la période.
   */
  function getAutoStackedTime(day: number, periodKey: string): string {
    const period = PERIODS.find((p: PeriodDefinition) => p.key === periodKey);
    if (!period) return '08:00';

    const existing = weeklyPlacements.value
      .filter((p: WeeklyPlacement) => p.day === day && p.period === periodKey)
      .sort(
        (a: WeeklyPlacement, b: WeeklyPlacement) =>
          parseTimeToMin(a.startTime) - parseTimeToMin(b.startTime),
      );

    if (existing.length === 0) {
      return formatMin(period.startH * 60);
    }

    const last = existing[existing.length - 1];
    const lastEnd = parseTimeToMin(last.startTime) + last.duration;
    return formatMin(lastEnd);
  }

  /**
   * Synchronise les draftServices[] depuis les placements.
   * Pour chaque draft, agrège ses placements en frequency_days[] et
   * preferred_time_start (heure du premier placement).
   * Appelé avant la sauvegarde du plan.
   */
  function syncDraftsFromPlacements(): void {
    draftServices.value.forEach((draft: CarePlanServiceDraft, index: number) => {
      const placements = weeklyPlacements.value
        .filter((p: WeeklyPlacement) => p.draftIndex === index)
        .sort(
          (a: WeeklyPlacement, b: WeeklyPlacement) =>
            parseTimeToMin(a.startTime) - parseTimeToMin(b.startTime),
        );

      if (placements.length === 0) return;

      // frequency_days : jours uniques triés (1=Lun … 7=Dim, convention backend)
      const days: number[] = Array.from(
        new Set(placements.map((p: WeeklyPlacement) => p.day + 1)),
      ).sort((a: number, b: number) => a - b);
      draft.frequency_days = days;

      // frequency_type : SPECIFIC_DAYS si plusieurs jours, DAILY si 7 jours
      draft.frequency_type = days.length === 7 ? 'DAILY' : 'SPECIFIC_DAYS';

      // quantity_per_week : nombre de placements
      draft.quantity_per_week = placements.length;

      // Heure et durée du premier placement (approche A)
      draft.preferred_time_start = placements[0].startTime;
      const endMin = parseTimeToMin(placements[0].startTime) + placements[0].duration;
      draft.preferred_time_end = formatMin(endMin);
      draft.duration_minutes = placements[0].duration;
    });
  }

  // =========================================================================
  // HELPERS — Semaine type (F3)
  // =========================================================================

  /** Parse 'HH:MM' → minutes depuis minuit */
  function parseTimeToMin(time: string): number {
    const [h, m] = time.split(':').map(Number);
    return h * 60 + (m || 0);
  }

  /** Minutes depuis minuit → 'HH:MM' */
  function formatMin(totalMin: number): string {
    const h = Math.floor(totalMin / 60) % 24;
    const m = totalMin % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  // =========================================================================
  // ACTIONS — Reset
  // =========================================================================

  /** Reset complet du store */
  function $reset(): void {
    plans.value = [];
    totalPlans.value = 0;
    currentPage.value = 1;
    filters.value = {};
    currentPlan.value = null;
    draftServices.value = [];
    weeklyPlacements.value = [];
    nextPlacementId = 1;
    loading.value = false;
    saving.value = false;
    error.value = null;
  }

  // =========================================================================
  // EXPOSE
  // =========================================================================

  return {
    // State — Liste
    plans,
    totalPlans,
    currentPage,
    pageSize,
    filters,

    // State — Plan courant
    currentPlan,

    // State — Draft
    draftServices,

    // State — Semaine type (F3)
    weeklyPlacements,

    // State — UI
    loading,
    saving,
    error,

    // Computed — Plan courant
    isEditable,
    isDraft,
    currentServices,
    budgetConsumed,
    budgetAllocated,
    budgetRatio,

    // Computed — Draft
    draftTotalHoursWeek,
    draftBudgetWeekly,
    draftServicesCount,

    // Computed — Semaine type (F3)
    placementsCount,
    totalPlacedMinutes,
    totalPlacedHoursFormatted,
    doublonCount,

    // Actions — Liste
    loadPlans,
    setFilters,
    setPage,

    // Actions — Plan CRUD
    loadPlan,
    createPlan,
    updatePlan,
    deletePlan,

    // Actions — Workflow
    submitPlan,
    validatePlan,
    reviseCarePlan,
    replaceServices,
    suspendPlan,
    reactivatePlan,
    completePlan,
    cancelPlan,

    // Actions — Services (API)
    addPlanService,
    removePlanService,

    // Actions — Draft (local)
    addDraftService,
    removeDraftService,
    updateDraftService,
    clearDraft,
    hydrateDraftServices, // F6.3

    // Actions — Semaine type (F3)
    addPlacement,
    removePlacement,
    updatePlacementTime,
    applyRecurrence,
    clearPlacements,
    getAutoStackedTime,
    syncDraftsFromPlacements,
    periodFromStartTime,  // F6.4 — exposé pour réutilisation depuis CarePlanCreatePage révision

    // Reset
    $reset,
  };
});
