<script setup lang="ts">
  /**
   * PatientsPage.vue — Liste des patients (composant partagé admin / soins)
   *
   * 🆕 B48 Palier 2, Lot A — fusion de PatientsPage_admin + PatientsPage_soins.
   *
   * Composant unique référencé par router/routes/app.ts (admin-patients ET
   * soins-patients). « Référence = UI Soins » est
   * visuelle : stack de cards façon CarePlanDraftsPage. La profondeur
   * fonctionnelle est celle de l'admin : PatientFilters (entité / statut /
   * GIR), pagination serveur via usePatientStore, actions CRUD, création.
   *
   * Choix architecturaux (cadrage B48 §5, plan Palier 2 Lot A) :
   *   - Présentation : stack de cards (Décision 1), grammaire CarePlanDraftsPage.
   *   - Liste : usePatientStore conservé (filtres, pagination serveur, total).
   *   - Pagination : « Voir plus » accumulatif — l'accumulation vit dans le
   *     store (action loadMore) ; `patients` devient une pile croissante.
   *   - Espace-aware (admin vs soins) : détection via route.path, navigation
   *     préfixée (même pattern que CarePlanDraftsPage).
   *   - Gating (Option A) : Voir libre · Modifier → PATIENT_EDIT ·
   *     Archiver/Réactiver → ADMIN_FULL · Nouveau patient → PATIENT_CREATE.
   *     Règle masquer-vs-griser : action sur objet visible → grisée + tooltip.
   *   - Liseré gauche de card : encode la sévérité GIR (pile = carte de chaleur
   *     scannable de la charge en dépendance).
   *
   * Destination : src/pages/shared/patient/PatientsPage.vue
   */
  import { computed, onMounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useDebounceFn } from '@vueuse/core';

  import Tag from 'primevue/tag';
  import Button from 'primevue/button';

  import PatientFilters from '@/components/patients/PatientFilters.vue';

  import { usePatientStore, useAuthStore } from '@/stores';
  import { entityService } from '@/services';

  import type { PatientSummary, PatientStatus, EntityResponse } from '@/types';
  import { PATIENT_STATUS_LABELS, PATIENT_STATUS_SEVERITY, getGirLevel } from '@/types';
  import { computeAge } from '@/utils/date';
  import { formatDate } from '@/utils/format';

  const route = useRoute();
  const router = useRouter();
  const patientStore = usePatientStore();
  const authStore = useAuthStore();

  // ─── Espace courant (A2 — détection via route.path) ─────────────────────────

  const isInSoinsSpace = computed(() => route.path.startsWith('/soins'));
  const pageTitle = computed(() => (isInSoinsSpace.value ? 'Mes patients' : 'Patients'));
  const routeNames = computed(() =>
    isInSoinsSpace.value
      ? { detail: 'soins-patient-detail', create: 'soins-patient-create' }
      : { detail: 'admin-patient-detail', create: 'admin-patient-create' },
  );

  // ─── Gating (Option A — verbes de permission nommés) ────────────────────────

  const canCreate = computed(() => authStore.hasPermission('PATIENT_CREATE'));
  const canEdit = computed(() => authStore.hasPermission('PATIENT_EDIT'));
  const canArchive = computed(() => authStore.hasPermission('ADMIN_FULL'));

  // ─── Filtres locaux (pilotent le store) ─────────────────────────────────────

  const searchQuery = ref('');
  const selectedEntityId = ref<number | null>(null);
  const selectedStatus = ref<PatientStatus | null>(null);
  const selectedGirMin = ref<number | null>(null);
  const selectedGirMax = ref<number | null>(null);

  const entityOptions = ref<{ value: number | null; label: string }[]>([
    { value: null, label: 'Toutes les entités' },
  ]);

  // ─── État dérivé du store ───────────────────────────────────────────────────

  const patients = computed(() => patientStore.visiblePatients);
  const isLoading = computed(() => patientStore.isLoading);
  const isLoadingMore = computed(() => patientStore.isLoadingMore);
  const hasMore = computed(() => patientStore.hasMore);
  const error = computed(() => patientStore.error);
  const totalPatients = computed(() => patientStore.pagination.total);

  /** Patients serveur restant à charger (volume brut, hors masquage client). */
  const remainingCount = computed(
    () => patientStore.pagination.total - patientStore.patients.length,
  );

  // ─── Helpers d'affichage ────────────────────────────────────────────────────

  /** Initiales pour l'avatar. */
  function getInitials(patient: PatientSummary): string {
    const first = patient.first_name?.[0] ?? '';
    const last = patient.last_name?.[0] ?? '';
    return `${first}${last}`.toUpperCase() || '?';
  }

  /** Nom complet « NOM Prénom ». */
  function getFullName(patient: PatientSummary): string {
    const parts = [patient.last_name, patient.first_name].filter(Boolean);
    return parts.join(' ') || 'Patient sans nom';
  }

  /** Âge formaté (« N ans ») — calcul délégué au helper consolidé. */
  function getAge(patient: PatientSummary): string {
    const age = computeAge(patient.birth_date);
    return age !== null ? `${age} ans` : '';
  }

  /** Date de naissance formatée (tiret « — » si absente). */
  function formatBirthDate(patient: PatientSummary): string {
    return formatDate(patient.birth_date, { emptyValue: '—' });
  }

  /** Classe Tailwind de la pastille GIR, dérivée du niveau de dépendance. */
  function getGirClass(gir?: number): string {
    switch (getGirLevel(gir)) {
      case 'severe':
        return 'bg-red-100 text-red-700';
      case 'moderate':
        return 'bg-amber-100 text-amber-700';
      case 'light':
        return 'bg-emerald-100 text-emerald-700';
      default:
        return 'bg-slate-100 text-slate-500';
    }
  }

  /**
   * Liseré gauche (border-l-4) de la card — encode la sévérité GIR : la pile
   * devient une carte de chaleur scannable de la charge en dépendance.
   * Patient sans GIR → liseré neutre.
   */
  function getCardAccentClass(gir?: number): string {
    switch (getGirLevel(gir)) {
      case 'severe':
        return 'border-l-red-400';
      case 'moderate':
        return 'border-l-amber-400';
      case 'light':
        return 'border-l-emerald-400';
      default:
        return 'border-l-slate-300';
    }
  }

  // ─── Tooltips de gating (règle masquer-vs-griser) ───────────────────────────

  const createTooltip = computed(() =>
    canCreate.value ? 'Créer un nouveau patient' : 'Création non autorisée',
  );

  const editTooltip = computed(() =>
    canEdit.value ? 'Modifier le dossier' : 'Modification non autorisée',
  );

  /** Le toggle archiver/réactiver n'a pas de sens pour un patient décédé. */
  function isArchivable(patient: PatientSummary): boolean {
    return patient.status !== 'DECEASED';
  }

  function archiveTooltip(patient: PatientSummary): string {
    if (!canArchive.value) return 'Archivage non autorisé';
    if (patient.status === 'DECEASED') return 'Patient décédé';
    return patient.status === 'ACTIVE' ? 'Archiver le patient' : 'Réactiver le patient';
  }

  // ─── Navigation (espace-aware) ──────────────────────────────────────────────

  function goToDetail(patient: PatientSummary): void {
    router.push({ name: routeNames.value.detail, params: { id: patient.id } });
  }

  function goToCreate(): void {
    router.push({ name: routeNames.value.create });
  }

  // ─── Actions CRUD ───────────────────────────────────────────────────────────

  /** Archiver / Réactiver — le store recharge depuis la page 1 après mutation. */
  async function toggleStatus(patient: PatientSummary): Promise<void> {
    if (patient.status === 'ACTIVE') {
      await patientStore.updatePatient(patient.id, { status: 'ARCHIVED' });
    } else if (patient.status === 'ARCHIVED' || patient.status === 'INACTIVE') {
      await patientStore.updatePatient(patient.id, { status: 'ACTIVE' });
    }
  }

  /** Réinitialise filtres locaux + store. */
  function resetAllFilters(): void {
    patientStore.resetFilters();
    searchQuery.value = '';
    selectedEntityId.value = null;
    selectedStatus.value = null;
    selectedGirMin.value = null;
    selectedGirMax.value = null;
  }

  // ─── Watchers de filtres → store ────────────────────────────────────────────

  const debouncedSearch = useDebounceFn(() => {
    patientStore.setFilters({ search: searchQuery.value });
  }, 300);

  watch(searchQuery, () => debouncedSearch());
  watch(selectedEntityId, (v) => patientStore.setFilters({ entity_id: v }));
  watch(selectedStatus, (v) => patientStore.setFilters({ status: v }));
  watch(selectedGirMin, (v) => patientStore.setFilters({ gir_min: v }));
  watch(selectedGirMax, (v) => patientStore.setFilters({ gir_max: v }));

  // ─── Lifecycle ──────────────────────────────────────────────────────────────

  onMounted(async () => {
    // Recharge depuis la page 1 (réinitialise la pile « Voir plus »).
    patientStore.refresh();

    // Chargement dynamique des entités pour le filtre.
    try {
      const entities: EntityResponse[] = await entityService.list();
      entityOptions.value = [
        { value: null, label: 'Toutes les entités' },
        ...entities.map((e) => ({ value: e.id, label: e.name })),
      ];
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[PatientsPage] Erreur chargement entités:', err);
      }
    }
  });
</script>

<template>
  <div class="space-y-5">
    <!-- ─── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ pageTitle }}</h1>
        <p class="text-slate-500 mt-1">
          {{ totalPatients }} patient{{ totalPatients !== 1 ? 's' : '' }}
          enregistré{{ totalPatients !== 1 ? 's' : '' }}
        </p>
      </div>
      <span v-tooltip.left="createTooltip" class="inline-flex">
        <Button
          :disabled="!canCreate"
          label="Nouveau patient"
          icon="pi pi-user-plus"
          @click="goToCreate"
        />
      </span>
    </div>

    <!-- ─── Filtres ────────────────────────────────────────────────────────── -->
    <PatientFilters
      v-model:search="searchQuery"
      v-model:entityId="selectedEntityId"
      v-model:status="selectedStatus"
      v-model:girMin="selectedGirMin"
      v-model:girMax="selectedGirMax"
      :entityOptions="entityOptions"
      :hasActiveFilters="patientStore.hasActiveFilters"
      @reset="resetAllFilters"
    />

    <!-- ─── Loading initial ────────────────────────────────────────────────── -->
    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <i class="pi pi-spin pi-spinner text-3xl text-blue-500"></i>
    </div>

    <!-- ─── Erreur ─────────────────────────────────────────────────────────── -->
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
        @click="patientStore.refresh()"
      />
    </div>

    <!-- ─── Empty state ────────────────────────────────────────────────────── -->
    <div
      v-else-if="!patients.length"
      class="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3"
    >
      <i class="pi pi-users text-4xl text-slate-300"></i>
      <h3 class="text-lg font-semibold text-slate-700">Aucun patient trouvé</h3>
      <p class="text-sm text-slate-500 max-w-md mx-auto">
        {{
          patientStore.hasActiveFilters
            ? 'Aucun patient ne correspond aux filtres. Modifiez-les ou réinitialisez la recherche.'
            : 'Aucun patient enregistré pour le moment.'
        }}
      </p>
    </div>

    <!-- ─── Stack de cards ─────────────────────────────────────────────────── -->
    <template v-else>
      <article
        v-for="patient in patients"
        :key="patient.id"
        :class="['patient-card', getCardAccentClass(patient.current_gir)]"
        @click="goToDetail(patient)"
      >
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <!-- Identité -->
          <div class="flex items-center gap-3 min-w-0">
            <div
              :class="
                patient.status === 'ACTIVE'
                  ? 'bg-blue-50 text-blue-600'
                  : 'bg-slate-100 text-slate-400'
              "
              class="w-11 h-11 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold"
            >
              {{ getInitials(patient) }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <p class="font-semibold text-slate-800 truncate">
                  {{ getFullName(patient) }}
                </p>
                <Tag
                  :value="PATIENT_STATUS_LABELS[patient.status]"
                  :severity="PATIENT_STATUS_SEVERITY[patient.status]"
                />
              </div>
              <p class="text-sm text-slate-400">
                {{ formatBirthDate(patient) }}
                <span v-if="getAge(patient)"> · {{ getAge(patient) }}</span>
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1.5">
            <span
              v-if="patient.current_gir"
              :class="getGirClass(patient.current_gir)"
              class="text-xs font-semibold px-2.5 py-1 rounded-full mr-1"
            >
              GIR {{ patient.current_gir }}
            </span>

            <span v-tooltip.top="editTooltip" class="inline-flex" @click.stop>
              <Button
                :disabled="!canEdit"
                icon="pi pi-pencil"
                severity="secondary"
                variant="text"
                size="small"
                rounded
                @click="goToDetail(patient)"
              />
            </span>

            <span v-tooltip.top="archiveTooltip(patient)" class="inline-flex" @click.stop>
              <Button
                :icon="patient.status === 'ACTIVE' ? 'pi pi-inbox' : 'pi pi-check-circle'"
                :severity="patient.status === 'ACTIVE' ? 'danger' : 'success'"
                :disabled="!canArchive || !isArchivable(patient)"
                variant="text"
                size="small"
                rounded
                @click="toggleStatus(patient)"
              />
            </span>

            <i class="pi pi-chevron-right text-slate-300 ml-1"></i>
          </div>
        </div>
      </article>

      <!-- ─── Voir plus ──────────────────────────────────────────────────── -->
      <div v-if="hasMore" class="flex justify-center pt-2">
        <Button
          :loading="isLoadingMore"
          icon="pi pi-chevron-down"
          severity="secondary"
          variant="outlined"
          @click="patientStore.loadMore()"
        >
          <span class="ml-1">
            Voir plus ({{ remainingCount }} restant{{ remainingCount !== 1 ? 's' : '' }})
          </span>
        </Button>
      </div>
    </template>
  </div>
</template>

<style scoped>
  .patient-card {
    background: white;
    border: 1px solid #e2e8f0; /* slate-200 */
    border-left-width: 4px;
    border-radius: 0.75rem;
    padding: 0.875rem 1.25rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .patient-card:hover {
    border-color: #cbd5e1; /* slate-300 */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transform: translateY(-1px);
  }
  .patient-card:active {
    transform: translateY(0);
  }
</style>