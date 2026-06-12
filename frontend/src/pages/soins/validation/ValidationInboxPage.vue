<!--
  CareLink - ValidationInboxPage
  Chemin : frontend/src/pages/soins/validation/ValidationInboxPage.vue

  Rôle : Inbox du portail valideur — liste paginée des demandes de validation
         (ValidationRequest) du tenant, fenêtre RLS : émetteur + valideur
         assigné + admin. Chaque ligne ouvre l'écran unifié « Dossier de
         validation » (/soins/validation/:vrId).

  - Pagination serveur (lazy DataTable) via validationService.list(page, size, filters).
  - Filtre « En attente uniquement » (pending_only, D-β : câblé de bout en bout
    backend) — actif par défaut : l'inbox est d'abord une file de travail.
  - Badge « Votre tour » : is_pending ∩ hasPermission('VALIDATION_' + stage),
    miroir de la logique de tour de l'écran dossier (quatre yeux : le backend
    reste juge, D24).
  - Libellés FR depuis les Records de types/validation.ts (#78).
  - Idiome visuel calqué sur ValidationDossierPage (Tailwind inline,
    conteneur max-w-5xl, chrome de page identique).

  🆕 S6 (04/06/2026) — étoffage du stub posé en B40-J4 / F4.
-->
<template>
  <div class="mx-auto max-w-5xl p-6">
    <!-- En-tête -->
    <header class="mb-4 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-lg font-bold text-slate-800">Validation</h1>
        <p class="mt-1 text-sm text-slate-500">
          Demandes de validation — cliquez sur une ligne pour ouvrir le dossier.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <ToggleSwitch v-model="pendingOnly" input-id="inbox-pending-only" />
        <label for="inbox-pending-only" class="cursor-pointer select-none text-sm text-slate-600">
          En attente uniquement
        </label>
      </div>
    </header>

    <!-- ÉTAT — erreur -->
    <div
      v-if="error"
      class="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
    >
      <AlertTriangle :size="16" :stroke-width="2" class="flex-shrink-0" />
      <span>{{ error }}</span>
    </div>

    <!-- Table des demandes -->
    <DataTable
      :value="items"
      :loading="loading"
      lazy
      paginator
      :rows="PAGE_SIZE"
      :total-records="total"
      :first="(page - 1) * PAGE_SIZE"
      data-key="id"
      row-hover
      class="cursor-pointer"
      @page="onPage"
      @row-click="onRowClick"
    >
      <template #empty>
        <div class="flex flex-col items-center gap-2 py-10 text-sm text-slate-400">
          <Inbox :size="32" :stroke-width="1.5" class="text-slate-300" />
          <span>
            {{ pendingOnly ? 'Aucune demande en attente.' : 'Aucune demande de validation.' }}
          </span>
        </div>
      </template>

      <Column header="N°">
        <template #body="{ data }">
          <span class="font-mono text-xs font-semibold text-slate-600">VR-{{ data.id }}</span>
        </template>
      </Column>

      <Column header="Dossier">
        <template #body="{ data }">
          <span class="text-sm text-slate-700">{{ dossierLabel(data) }}</span>
        </template>
      </Column>

      <Column header="Type">
        <template #body="{ data }">
          <span class="text-sm text-slate-600">
            {{ VALIDATION_WORKFLOW_LABELS[data.workflow_type as ValidationWorkflowType] }}
          </span>
        </template>
      </Column>

      <Column header="Étape">
        <template #body="{ data }">
          <Tag
            :value="VALIDATION_STAGE_LABELS[data.stage as ValidationStage]"
            severity="secondary"
          />
        </template>
      </Column>

      <Column header="Soumise le">
        <template #body="{ data }">
          <span class="text-sm tabular-nums text-slate-500">
            {{ formatDateTime(data.submitted_at) }}
          </span>
        </template>
      </Column>

      <Column header="Statut">
        <template #body="{ data }">
          <div class="flex flex-wrap items-center gap-2">
            <Tag :value="statusOf(data).label" :severity="statusOf(data).severity" />
            <Tag
              v-if="isMyTurn(data)"
              value="Votre tour"
              severity="warn"
              class="flex-shrink-0"
            />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - ValidationInboxPage
   * Chemin : frontend/src/pages/soins/validation/ValidationInboxPage.vue
   */
  import { ref, watch, onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import DataTable from 'primevue/datatable';
  import type { DataTablePageEvent, DataTableRowClickEvent } from 'primevue/datatable';
  import Column from 'primevue/column';
  import Tag from 'primevue/tag';
  import ToggleSwitch from 'primevue/toggleswitch';
  import { Inbox, AlertTriangle } from 'lucide-vue-next';
  import axios from 'axios';

  import { validationService } from '@/services';
  import { useAuthStore } from '@/stores';
  import type {
    ValidationRequestSummary,
    ValidationStage,
    ValidationWorkflowType,
  } from '@/types';
  import {
    VALIDATION_DECISION_LABELS,
    VALIDATION_STAGE_LABELS,
    VALIDATION_WORKFLOW_LABELS,
  } from '@/types';

  const router = useRouter();
  const authStore = useAuthStore();

  // ── État ────────────────────────────────────────────────────────────────

  const PAGE_SIZE = 20;

  const items = ref<ValidationRequestSummary[]>([]);
  const total = ref(0);
  const page = ref(1);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** File de travail par défaut : seules les VR pendantes sont affichées. */
  const pendingOnly = ref(true);

  // ── Chargement (pagination serveur) ─────────────────────────────────────

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      const response = await validationService.list(
        page.value,
        PAGE_SIZE,
        pendingOnly.value ? { pending_only: true } : undefined,
      );
      items.value = response.items;
      total.value = response.total;
    } catch (err: unknown) {
      items.value = [];
      total.value = 0;
      error.value = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Erreur lors du chargement des demandes de validation'
        : 'Erreur lors du chargement des demandes de validation';
      if (import.meta.env.DEV) {
        console.error('[ValidationInboxPage] Load error:', err);
      }
    } finally {
      loading.value = false;
    }
  }

  function onPage(event: DataTablePageEvent) {
    page.value = event.page + 1; // PrimeVue : 0-based
    load();
  }

  // Changement de filtre → retour page 1
  watch(pendingOnly, () => {
    page.value = 1;
    load();
  });

  onMounted(load);

  // ── Navigation ──────────────────────────────────────────────────────────

  function onRowClick(event: DataTableRowClickEvent) {
    const vr = event.data as ValidationRequestSummary;
    router.push(`/soins/validation/${vr.id}`);
  }

  // ── Présentation ────────────────────────────────────────────────────────

  function dossierLabel(vr: ValidationRequestSummary): string {
    if (vr.evaluation_id !== null) return `Évaluation #${vr.evaluation_id}`;
    if (vr.care_plan_id !== null) return `Plan d'aide #${vr.care_plan_id}`;
    return '—';
  }

  type TagSeverity = 'info' | 'success' | 'warn' | 'danger' | 'secondary';

  const DECISION_SEVERITIES: Record<string, TagSeverity> = {
    VALIDATED: 'success',
    INVALIDATED: 'danger',
    MORE_INFO_REQUESTED: 'warn',
    WITHDRAWN: 'secondary',
  };

  function statusOf(vr: ValidationRequestSummary): { label: string; severity: TagSeverity } {
    if (vr.is_withdrawn) {
      return { label: VALIDATION_DECISION_LABELS.WITHDRAWN, severity: 'secondary' };
    }
    if (vr.is_decided && vr.decision) {
      return {
        label: VALIDATION_DECISION_LABELS[vr.decision],
        severity: DECISION_SEVERITIES[vr.decision] ?? 'secondary',
      };
    }
    return { label: 'En attente', severity: 'info' };
  }

  /**
   * Tour de l'utilisateur courant : VR pendante ET permission de l'étape.
   * Miroir UI de la logique de l'écran dossier (le backend reste juge — D24).
   */
  function isMyTurn(vr: ValidationRequestSummary): boolean {
    return vr.is_pending && authStore.hasPermission(`VALIDATION_${vr.stage}`);
  }

  // ── Format ──────────────────────────────────────────────────────────────

  function formatDateTime(iso: string): string {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    const date = d.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
    const time = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return `${date} ${time}`;
  }
</script>