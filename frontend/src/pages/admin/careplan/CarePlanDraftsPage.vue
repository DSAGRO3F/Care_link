<script setup lang="ts">
  /**
   * CarePlanDraftsPage.vue — « Mes brouillons » centralisée
   *
   * 🆕 v5.54 — Phase 4, étape F8 — clôture Phase 4
   *
   * Vue transverse multi-patients des plans d'aide en statut DRAFT, qu'ils
   * soient ex nihilo ou issus d'une révision (B28b). Permet au coordinateur
   * de retrouver tous ses brouillons en cours sans naviguer patient par patient.
   *
   * Choix architecturaux :
   *   - State local plutôt que store partagé (évite la pollution
   *     carePlanStore mono-liste utilisé par CarePlanListPage).
   *     Pattern aligné F6.5 (chargement direct via service).
   *   - Pagination "Voir plus" explicite plutôt qu'infinite scroll :
   *     déclenchement utilisateur prévisible, économe en requêtes.
   *   - Cards riches (pas DataTable) : pattern F8a Session 18 dupliqué.
   *     Helper getCardAccent local (cohérent décision 54 Session 18,
   *     cleanup limité, pas d'extraction composable hors cadrage F8).
   *   - Espace-aware (admin vs soins) : détection via route.path, route
   *     partagée mais navigation préfixée correctement.
   *
   * Actions par card :
   *   - Clic card entière → navigation fiche détail
   *   - Bouton "Reprendre l'édition" (DRAFT-révision uniquement) → wizard
   *
   * Destination : src/pages/admin/careplan/CarePlanDraftsPage.vue
   */
  import { computed, onMounted, ref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import Button from 'primevue/button';
  import Tag from 'primevue/tag';
  import { carePlanService } from '@/services';
  import {
    formatPatientName,
    PLAN_STATUS_LABELS,
    REVISION_REASON_LABELS,
  } from '@/types';
  import type { CarePlanSummary } from '@/types';

  const router = useRouter();
  const route = useRoute();

  // ─── State local ────────────────────────────────────────────────────────────

  const drafts = ref<CarePlanSummary[]>([]);
  const totalDrafts = ref(0);
  const currentPage = ref(1);
  const pageSize = 20;
  const loading = ref(false);
  const loadingMore = ref(false);
  const error = ref<string | null>(null);

  // ─── Computed ───────────────────────────────────────────────────────────────

  /** Espace courant : /soins vs /admin. Détermine le prefix de navigation. */
  const isInSoinsSpace = computed(() => route.path.startsWith('/soins'));
  const routePrefix = computed(() => (isInSoinsSpace.value ? '/soins' : '/admin'));

  /** Reste-t-il des brouillons à charger ? */
  const hasMore = computed(() => drafts.value.length < totalDrafts.value);

  /** Label du compteur singulier/pluriel */
  const counterLabel = computed(() =>
    totalDrafts.value === 1 ? 'brouillon' : 'brouillons',
  );

  // ─── Helpers d'affichage (cohérence F8a Session 18) ─────────────────────────

  interface CardAccent {
    borderClass: string;
    badgeSeverity: 'secondary' | 'info';
    label: string;
  }

  /**
   * Distingue visuellement DRAFT-révision (issu de B28b) vs DRAFT ex nihilo.
   * Pattern cohérent F8a Session 18 (helper dupliqué intentionnellement —
   * décision 54 Session 18 : cleanup limité, pas d'extraction composable
   * hors cadrage F8).
   */
  function getCardAccent(plan: CarePlanSummary): CardAccent {
    if (plan.supersedes_plan_id !== null) {
      return {
        borderClass: 'border-l-teal-300',
        badgeSeverity: 'info',
        label: 'Brouillon de révision',
      };
    }
    return {
      borderClass: 'border-l-slate-400',
      badgeSeverity: 'secondary',
      label: PLAN_STATUS_LABELS.DRAFT,
    };
  }

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  function formatRelativeDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "aujourd'hui";
    if (diffDays === 1) return 'hier';
    if (diffDays < 7) return `il y a ${diffDays} jours`;
    if (diffDays < 30) return `il y a ${Math.floor(diffDays / 7)} semaines`;
    return formatDate(dateStr);
  }

  // ─── Chargement ──────────────────────────────────────────────────────────────

  async function loadDrafts(page: number, append = false): Promise<void> {
    if (append) {
      loadingMore.value = true;
    } else {
      loading.value = true;
    }
    error.value = null;
    try {
      const result = await carePlanService.list(page, pageSize, { status: 'DRAFT' });
      if (append) {
        drafts.value = [...drafts.value, ...result.items];
      } else {
        drafts.value = result.items;
      }
      totalDrafts.value = result.total;
      currentPage.value = page;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Erreur lors du chargement';
    } finally {
      loading.value = false;
      loadingMore.value = false;
    }
  }

  async function loadMore(): Promise<void> {
    if (!hasMore.value || loadingMore.value) return;
    await loadDrafts(currentPage.value + 1, true);
  }

  // ─── Navigation ──────────────────────────────────────────────────────────────

  function goToDetail(plan: CarePlanSummary): void {
    router.push(`${routePrefix.value}/care-plans/${plan.id}`);
  }

  function goToResume(plan: CarePlanSummary): void {
    if (plan.supersedes_plan_id === null) return;
    // Hydrater depuis le DRAFT lui-même (services à jour), pas depuis le parent
    // Cohérent avec le bouton "Reprendre l'édition" de CarePlanDetailPage Session 15.
    router.push(
      `${routePrefix.value}/care-plans/create?revise_from=${plan.id}`,
    );
  }

  // ─── Lifecycle ───────────────────────────────────────────────────────────────

  onMounted(async () => {
    await loadDrafts(1);
  });
</script>

<template>
  <div class="space-y-4">
    <!-- ─── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Mes brouillons</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tous les plans d'aide en cours d'édition (brouillons ex nihilo et révisions)
        </p>
      </div>
      <div v-if="!loading && totalDrafts > 0" class="flex items-center gap-2">
        <Tag :value="totalDrafts" severity="info" />
        <span class="text-sm text-slate-500">{{ counterLabel }}</span>
      </div>
    </div>

    <!-- ─── Loading initial ─────────────────────────────────────────────── -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <i class="pi pi-spin pi-spinner text-3xl text-teal-500"></i>
    </div>

    <!-- ─── Error ────────────────────────────────────────────────────────── -->
    <div
      v-else-if="error"
      class="bg-red-50 border border-red-200 rounded-xl p-6 text-center space-y-3"
    >
      <i class="pi pi-exclamation-triangle text-2xl text-red-500"></i>
      <p class="text-sm text-red-700">{{ error }}</p>
      <Button
        label="Réessayer"
        icon="pi pi-refresh"
        severity="secondary"
        @click="loadDrafts(1)"
      />
    </div>

    <!-- ─── Empty state ──────────────────────────────────────────────────── -->
    <div
      v-else-if="totalDrafts === 0"
      class="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3"
    >
      <i class="pi pi-inbox text-4xl text-slate-300"></i>
      <h3 class="text-lg font-semibold text-slate-700">Aucun brouillon en cours</h3>
      <p class="text-sm text-slate-500 max-w-md mx-auto">
        Vous n'avez aucun plan d'aide en cours d'édition. Les brouillons apparaîtront
        ici dès que vous en créerez un ou en réviserez un.
      </p>
    </div>

    <!-- ─── Stack de Cards ──────────────────────────────────────────────── -->
    <template v-else>
      <article
        v-for="plan in drafts"
        :key="plan.id"
        :class="['care-plan-card', getCardAccent(plan).borderClass]"
        @click="goToDetail(plan)"
      >
        <!-- Header card -->
        <div class="flex items-center justify-between mb-2 flex-wrap gap-2">
          <div class="flex items-center gap-2 flex-wrap">
            <Tag
              :value="getCardAccent(plan).label"
              :severity="getCardAccent(plan).badgeSeverity"
            />
            <span class="text-xs font-medium text-slate-400">#{{ plan.id }}</span>
            <span class="text-xs text-slate-300">·</span>
            <span class="text-sm font-medium text-slate-700">
              <i class="pi pi-user text-xs mr-1 text-slate-400"></i>
              {{ formatPatientName(plan) }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <Button
              v-if="plan.supersedes_plan_id !== null"
              v-tooltip="'Reprendre l\'édition'"
              icon="pi pi-pencil"
              severity="info"
              variant="text"
              size="small"
              rounded
              @click.stop="goToResume(plan)"
            />
            <span class="text-xs text-teal-600 font-medium">Voir la fiche →</span>
          </div>
        </div>

        <!-- Titre -->
        <h3 class="text-base font-semibold text-slate-800 mb-1">
          {{ plan.title }}
        </h3>

        <!-- Mention filiation (DRAFT-révision uniquement) -->
        <p
          v-if="plan.supersedes_plan_id !== null"
          class="text-xs text-slate-500 mb-2 flex items-center gap-1 flex-wrap"
        >
          <i class="pi pi-history text-xs"></i>
          <span>Révision du plan #{{ plan.supersedes_plan_id }}</span>
          <span v-if="plan.revision_reason">
            — {{ REVISION_REASON_LABELS[plan.revision_reason] }}
          </span>
        </p>

        <!-- Méta -->
        <div class="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
          <span class="flex items-center gap-1">
            <i class="pi pi-calendar text-xs"></i>
            Du {{ formatDate(plan.start_date) }} au {{ formatDate(plan.end_date) }}
          </span>
          <span class="flex items-center gap-1">
            <i class="pi pi-list text-xs"></i>
            {{ plan.services_count }}
            {{ plan.services_count === 1 ? 'prestation' : 'prestations' }}
          </span>
          <span v-if="plan.gir_at_creation !== null" class="flex items-center gap-1">
            GIR {{ plan.gir_at_creation }}
          </span>
          <span class="flex items-center gap-1 text-slate-400 ml-auto">
            Créé {{ formatRelativeDate(plan.created_at) }}
          </span>
        </div>
      </article>

      <!-- ─── Bouton "Voir plus" ───────────────────────────────────────── -->
      <div v-if="hasMore" class="flex justify-center pt-2">
        <Button
          :loading="loadingMore"
          icon="pi pi-chevron-down"
          severity="secondary"
          variant="outlined"
          @click="loadMore"
        >
          <span class="ml-1">Voir plus ({{ totalDrafts - drafts.length }} restants)</span>
        </Button>
      </div>
    </template>
  </div>
</template>

<style scoped>
  .care-plan-card {
    background: white;
    border: 1px solid #e2e8f0; /* slate-200 */
    border-left-width: 4px;
    border-radius: 0.75rem;
    padding: 1rem 1.25rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .care-plan-card:hover {
    border-color: #cbd5e1; /* slate-300 */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transform: translateY(-1px);
  }
  .care-plan-card:active {
    transform: translateY(0);
  }
</style>