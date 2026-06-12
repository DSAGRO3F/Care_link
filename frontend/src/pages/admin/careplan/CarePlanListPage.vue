<script setup lang="ts">
  /**
   * CarePlanListPage.vue — Liste des plans d'aide
   *
   * 🆕 v5.32 — Phase 4, étape F5
   *
   * 🔄 Pagination + filtrage SERVEUR (DataTable lazy mode) :
   *   - Chargement initial via carePlanStore.loadPlans()
   *   - Pagination : @page → carePlanStore.setPage()
   *   - Filtre statut : watch → carePlanStore.setFilters()
   *   - DataTable lazy : aucun découpage client, totalRecords = store.totalPlans
   *
   * Colonnes : titre, statut (Tag severity), dates, services (+ affectation),
   * budget, actions
   *
   * TODO Phase 4+ :
   *   - Recherche textuelle : nécessite ajout d'un champ `search` dans
   *     CarePlanFilters côté backend (actuellement absent du schema Pydantic)
   *   - Tri serveur : nécessite paramètre `sort_by` côté backend
   *
   * Destination : src/pages/admin/careplan/CarePlanListPage.vue
   */
  import { onMounted, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import Button from 'primevue/button';
  import Column from 'primevue/column';
  import DataTable, {
    type DataTablePageEvent,
    type DataTableRowClickEvent,
  } from 'primevue/datatable';
  import Select from 'primevue/select';
  import Tag from 'primevue/tag';
  import { useCarePlanStore } from '@/stores';
  import type { CarePlanStatus, CarePlanSummary } from '@/types';

  const router = useRouter();
  const carePlanStore = useCarePlanStore();

  // ─── Filtres locaux ──────────────────────────────────────────────────────────

  const selectedStatus = ref<CarePlanStatus | null>(null);

  interface SelectOption {
    value: CarePlanStatus | null;
    label: string;
  }

  const statusOptions: SelectOption[] = [
    { value: null, label: 'Tous les statuts' },
    { value: 'DRAFT', label: 'Brouillon' },
    { value: 'PENDING_VALIDATION', label: 'En attente' },
    { value: 'ACTIVE', label: 'Actif' },
    { value: 'SUSPENDED', label: 'Suspendu' },
    { value: 'COMPLETED', label: 'Terminé' },
    { value: 'CANCELLED', label: 'Annulé' },
  ];

  // ─── Branchement filtre serveur ──────────────────────────────────────────────

  watch(selectedStatus, async (newStatus) => {
    await carePlanStore.setFilters({
      status: newStatus,
    });
  });

  function resetFilters(): void {
    selectedStatus.value = null;
  }

  // ─── Severity mapping ────────────────────────────────────────────────────────

  type TagSeverity = 'info' | 'warn' | 'success' | 'danger' | 'secondary' | 'contrast';

  const statusSeverityMap: Record<CarePlanStatus, TagSeverity> = {
    DRAFT: 'secondary',
    PENDING_VALIDATION: 'warn',
    ACTIVE: 'success',
    SUSPENDED: 'danger',
    COMPLETED: 'info',
    CANCELLED: 'contrast',
  };

  const statusLabelMap: Record<CarePlanStatus, string> = {
    DRAFT: 'Brouillon',
    PENDING_VALIDATION: 'En attente',
    ACTIVE: 'Actif',
    SUSPENDED: 'Suspendu',
    COMPLETED: 'Terminé',
    CANCELLED: 'Annulé',
  };

  function getStatusSeverity(status: CarePlanStatus): TagSeverity {
    return statusSeverityMap[status] ?? 'secondary';
  }

  function getStatusLabel(status: CarePlanStatus): string {
    return statusLabelMap[status] ?? status;
  }

  // ─── Formatage ───────────────────────────────────────────────────────────────

  function formatDate(dateStr: string | null | undefined): string {
    if (dateStr === null || dateStr === undefined) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  function formatBudget(value: number | null | undefined): string {
    if (value === null || value === undefined) return '—';
    return `${Number(value).toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} €`;
  }

  // ─── Pagination serveur ──────────────────────────────────────────────────────

  async function onPage(event: DataTablePageEvent): Promise<void> {
    // PrimeVue page event : { first, rows, page, pageCount }
    // Notre backend attend une page 1-indexée
    await carePlanStore.setPage(event.page + 1);
  }

  // ─── Navigation ──────────────────────────────────────────────────────────────

  function goToCreate(): void {
    router.push({ name: 'admin-care-plans-create' });
  }

  function goToDetail(plan: CarePlanSummary): void {
    router.push({ name: 'admin-care-plans-detail', params: { id: plan.id } });
  }

  function onRowClick(event: DataTableRowClickEvent): void {
    goToDetail(event.data as CarePlanSummary);
  }

  /** Classe CSS de surlignage de la ligne active dans la DataTable */
  function rowClassForCarePlan(data: CarePlanSummary): string {
    return data.status === 'ACTIVE' ? 'care-plan-row--active' : '';
  }

  // ─── Chargement initial ──────────────────────────────────────────────────────

  onMounted(async () => {
    await carePlanStore.loadPlans();
  });
</script>

<template>
  <div class="space-y-4">
    <!-- ─── Header ──────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Plans d'aide</h1>
        <p class="text-sm text-slate-500 mt-1">
          Gestion des plans d'aide et parcours de soins coordonnés
        </p>
      </div>
      <Button icon="pi pi-plus" label="Nouveau plan d'aide" severity="info" @click="goToCreate" />
    </div>

    <!-- ─── Filtres ─────────────────────────────────────────────────────── -->
    <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div class="flex flex-col md:flex-row gap-3">
        <Select
          v-model="selectedStatus"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Statut"
          class="w-full md:w-48"
        />

        <Button
          v-if="selectedStatus !== null"
          v-tooltip="'Réinitialiser les filtres'"
          icon="pi pi-filter-slash"
          severity="secondary"
          variant="outlined"
          @click="resetFilters"
        />
      </div>
    </div>

    <!-- ─── DataTable (mode lazy = pagination serveur) ─────────────────── -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <DataTable
        :loading="carePlanStore.loading"
        :rowClass="rowClassForCarePlan"
        :value="carePlanStore.plans"
        :rows="carePlanStore.pageSize"
        :totalRecords="carePlanStore.totalPlans"
        :first="(carePlanStore.currentPage - 1) * carePlanStore.pageSize"
        dataKey="id"
        class="p-datatable-sm"
        emptyMessage="Aucun plan d'aide trouvé."
        lazy
        paginator
        stripedRows
        @page="onPage"
        @row-click="onRowClick"
      >
        <Column field="title" header="Titre" style="min-width: 14rem">
          <template #body="slotProps">
            <span class="font-medium text-slate-800">
              {{ (slotProps.data as CarePlanSummary).title }}
            </span>
          </template>
        </Column>

        <Column field="status" header="Statut" style="min-width: 8rem">
          <template #body="slotProps">
            <Tag
              :severity="getStatusSeverity((slotProps.data as CarePlanSummary).status)"
              :value="getStatusLabel((slotProps.data as CarePlanSummary).status)"
            />
          </template>
        </Column>

        <Column field="start_date" header="Début" style="min-width: 7rem">
          <template #body="slotProps">
            <span class="text-sm text-slate-600">
              {{ formatDate((slotProps.data as CarePlanSummary).start_date) }}
            </span>
          </template>
        </Column>

        <Column field="end_date" header="Fin" style="min-width: 7rem">
          <template #body="slotProps">
            <span class="text-sm text-slate-600">
              {{ formatDate((slotProps.data as CarePlanSummary).end_date) }}
            </span>
          </template>
        </Column>

        <Column field="services_count" header="Services" style="min-width: 8rem">
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-slate-700">
                {{ (slotProps.data as CarePlanSummary).services_count }}
              </span>
              <Tag
                v-if="(slotProps.data as CarePlanSummary).is_fully_assigned"
                v-tooltip="'Tous les services sont affectés'"
                severity="success"
                value="affectés"
                class="text-xs"
              />
              <Tag
                v-else-if="(slotProps.data as CarePlanSummary).services_count > 0"
                v-tooltip="'Certains services restent à affecter'"
                severity="warn"
                value="partiel"
                class="text-xs"
              />
            </div>
          </template>
        </Column>

        <Column field="budget_allocated" header="Budget" style="min-width: 7rem">
          <template #body="slotProps">
            <span class="text-sm font-medium text-slate-700">
              {{ formatBudget((slotProps.data as CarePlanSummary).budget_allocated) }}
            </span>
          </template>
        </Column>

        <Column :exportable="false" header="Actions" style="width: 5rem">
          <template #body="slotProps">
            <Button
              v-tooltip="'Voir le détail'"
              icon="pi pi-eye"
              severity="secondary"
              variant="text"
              rounded
              @click.stop="goToDetail(slotProps.data as CarePlanSummary)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style>
  /* Règles non-scoped : les <tr>/<td> PrimeVue ne portent pas l'attribut
     data-v-xxx, donc un bloc scoped ne peut pas les atteindre
     (cf. PrimeVue issue #4549). Classe .care-plan-row--active utilisée
     uniquement dans ce fichier et PatientDetailPage_soins.vue. */
  .care-plan-row--active > td {
    background-color: #f0fdfa; /* teal-50 */
  }
  .care-plan-row--active > td:first-child {
    box-shadow: inset 4px 0 0 0 #14b8a6; /* teal-500, liseré gauche */
  }
</style>
