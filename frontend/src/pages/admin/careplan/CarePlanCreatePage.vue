/** * CareLink — CarePlanCreatePage * Chemin :
frontend/src/pages/admin/careplan/CarePlanCreatePage.vue * * Rôle : page de création d'un plan
d'aide (Phase 4 — F2). * Layout : header + formulaire métadonnées + split panel * - Gauche :
catalogue consolidé Phase 3B (accordéon réutilisé) * - Droite : SelectedServicesPanel (panier) * *
Le @select des composants Phase 3B alimente le panier draft du store. * La sauvegarde appelle POST
/care-plans avec les services. */
<template>
  <div class="min-h-screen bg-slate-50">
    <Toast position="top-right" />
    <!-- ===== PAGE HEADER ===== -->
    <div class="border-b border-slate-200 bg-white px-8 py-5">
      <div class="flex items-center gap-3">
        <button
          class="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50"
          @click="router.back()"
        >
          ←
        </button>
        <div>
          <h1 class="text-xl font-extrabold text-slate-800">{{ pageTitle }}</h1>
          <p class="text-sm text-slate-500">{{ pageSubtitle }}</p>
        </div>
      </div>
    </div>

    <!-- ===== FORM: Plan metadata ===== -->
    <div class="mx-auto max-w-[1600px] px-8 py-5">
      <!-- Bandeau identitovigilance (affiché dès qu'un patient est chargé) -->
      <Transition name="patient-banner" mode="out-in">
        <div v-if="currentPatient && !isLoadingPatient" class="mb-4">
          <PatientIdentityBanner :patient="currentPatient" />

          <!-- Chip provenance : "Suite évaluation du JJ/MM/AAAA" -->
          <button
            v-if="evaluationInfo"
            type="button"
            class="mt-2 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
            @click="onBackToEvaluation"
          >
            <i class="pi pi-history text-xs" aria-hidden="true" />
            <span>
              Suite évaluation
              <template v-if="evaluationInfo.dateFormatted">
                du {{ evaluationInfo.dateFormatted }}
              </template>
            </span>
            <i class="pi pi-arrow-right text-xs opacity-60" aria-hidden="true" />
          </button>
        </div>
      </Transition>

      <!-- ===== F6.5 — BANDEAU PARENT (mode révision uniquement) ===== -->
      <div
        v-if="isReviseMode && parentPlan"
        class="mb-4 flex items-start gap-3 rounded-xl border border-teal-200 bg-teal-50/50 px-4 py-3"
      >
        <i class="pi pi-history mt-0.5 text-base text-teal-600" aria-hidden="true" />

        <div class="min-w-0 flex-1">
          <!-- Ligne 1 : libellé + n° + statut -->
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-bold uppercase tracking-wide text-teal-700">
              Révision du plan
            </span>
            <span
              class="rounded-full bg-white px-2 py-0.5 text-[0.625rem] font-semibold text-slate-600 ring-1 ring-slate-200"
            >
              #{{ parentPlan.id }}
            </span>
            <span
              class="rounded-full bg-white px-2 py-0.5 text-[0.625rem] font-semibold text-slate-600 ring-1 ring-slate-200"
            >
              {{ PLAN_STATUS_LABELS[parentPlan.status] ?? parentPlan.status }}
            </span>
          </div>

          <!-- Ligne 2 : titre -->
          <div class="mt-1 text-sm font-semibold text-slate-800">
            {{ parentPlan.title }}
          </div>

          <!-- Ligne 3 : période -->
          <div class="mt-0.5 text-xs text-slate-500">
            Période : du {{ formatShortDate(parentPlan.start_date) }}
            <template v-if="parentPlan.end_date">
              au {{ formatShortDate(parentPlan.end_date) }}
            </template>
            <template v-else>
              — sans fin programmée
            </template>
          </div>
        </div>

        <!-- Lien fiche détail -->
        <router-link
          v-if="parentPlanLinkTo"
          :to="parentPlanLinkTo"
          class="inline-flex shrink-0 items-center gap-1 rounded-lg border border-teal-200 bg-white px-3 py-1.5 text-xs font-semibold text-teal-700 transition-colors hover:bg-teal-100"
        >
          Voir la fiche
          <i class="pi pi-arrow-right text-[0.625rem]" aria-hidden="true" />
        </router-link>
      </div>

      <div class="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <h2 class="mb-4 text-sm font-bold uppercase tracking-wide text-slate-500">
          Informations du plan
        </h2>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <!-- Titre -->
          <div class="lg:col-span-2">
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Titre du plan * </label>
            <input
              v-model="form.title"
              type="text"
              placeholder="Ex : Plan d'aide Mme Dupont"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
            />
          </div>

          <!-- Patient -->
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Patient * </label>
            <Select
              v-model="form.patient_id"
              :options="patientOptions"
              :filter="true"
              :loading="patientStore.isLoadingAllForDropdown"
              :disabled="patientStore.isLoadingAllForDropdown"
              option-label="label"
              option-value="value"
              filter-placeholder="Rechercher un patient…"
              placeholder="Sélectionner un patient"
              class="w-full"
            >
              <template #option="slotProps">
                <div class="flex flex-col leading-tight">
                  <span class="text-sm font-semibold text-slate-800">
                    {{ (slotProps.option as PatientOption).label }}
                  </span>
                  <span
                    v-if="(slotProps.option as PatientOption).birthDateFormatted"
                    class="text-xs text-slate-400"
                  >
                    Né(e) le {{ (slotProps.option as PatientOption).birthDateFormatted }}
                  </span>
                </div>
              </template>
              <template #empty>
                <span class="text-sm text-slate-400">Aucun patient trouvé</span>
              </template>
            </Select>
          </div>

          <!-- Entité -->
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Entité * </label>
            <Select
              v-model="form.entity_id"
              :options="entityOptions"
              :loading="entityStore.loading"
              :disabled="entityStore.loading"
              option-label="label"
              option-value="value"
              placeholder="Sélectionner une entité"
              class="w-full"
            >
              <template #option="slotProps">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center gap-2 min-w-0">
                    <span
                      :class="[
                        'inline-block h-2 w-2 shrink-0 rounded-full',
                        EntityTypeColors[(slotProps.option as EntityOption).entityType]?.bg ??
                          'bg-slate-400',
                      ]"
                      aria-hidden="true"
                    />
                    <span class="truncate text-sm font-medium text-slate-800">
                      {{ (slotProps.option as EntityOption).label }}
                    </span>
                  </div>
                  <span class="shrink-0 text-xs text-slate-400">
                    {{ (slotProps.option as EntityOption).typeLabel }}
                  </span>
                </div>
              </template>
              <template #empty>
                <span class="text-sm text-slate-400">Aucune entité trouvée</span>
              </template>
            </Select>
          </div>

          <!-- Date début -->
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Date de début * </label>
            <input
              v-model="form.start_date"
              type="date"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
            />
          </div>

          <!-- Date fin -->
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Date de fin </label>
            <input
              v-model="form.end_date"
              type="date"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
            />
          </div>

          <!-- Budget alloué -->
          <div>
            <label class="mb-1 block text-xs font-semibold text-slate-600">
              Budget mensuel alloué (€)
            </label>
            <input
              v-model.number="form.budget_allocated"
              type="number"
              min="0"
              step="0.01"
              placeholder="Ex : 1200"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
            />
          </div>

          <!-- Notes -->
          <div class="lg:col-span-2">
            <label class="mb-1 block text-xs font-semibold text-slate-600"> Notes </label>
            <input
              v-model="form.notes"
              type="text"
              placeholder="Observations, contexte…"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
            />
          </div>
        </div>
      </div>

      <!-- ===== STEPPER : Prestations → Semaine type ===== -->
      <div class="mb-6 flex items-center justify-center gap-2">
        <button
          :class="[
            'flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold transition-colors',
            currentStep === 1
              ? 'bg-teal-500 text-white'
              : 'bg-teal-50 text-teal-600 hover:bg-teal-100',
          ]"
          type="button"
          @click="currentStep = 1"
        >
          <span
            :class="[
              'flex h-5 w-5 items-center justify-center rounded-full text-[0.625rem] font-bold',
              currentStep === 1 ? 'bg-white/20' : 'bg-teal-100',
            ]"
          >
            {{ currentStep > 1 ? '✓' : '1' }}
          </span>
          Prestations
        </button>
        <span class="text-slate-300">›</span>
        <button
          :class="[
            'flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold transition-colors',
            currentStep === 2
              ? 'bg-teal-500 text-white'
              : carePlanStore.draftServicesCount > 0
                ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                : 'cursor-not-allowed bg-slate-100 text-slate-400',
          ]"
          :disabled="carePlanStore.draftServicesCount === 0"
          type="button"
          @click="goToStep2"
        >
          <span
            :class="[
              'flex h-5 w-5 items-center justify-center rounded-full text-[0.625rem] font-bold',
              currentStep === 2 ? 'bg-white/20' : 'bg-slate-200',
            ]"
          >
            2
          </span>
          Semaine type
        </button>
      </div>

      <!-- ===== ÉTAPE 1 : Sélection des prestations (Bloc 1) ===== -->
      <div v-if="currentStep === 1" class="flex gap-6">
        <!-- LEFT: Catalogue consolidé (Phase 3B components) -->
        <div class="min-w-0 flex-1">
          <!-- Loading -->
          <div v-if="catalogStore.loading" class="flex items-center justify-center py-16">
            <div class="text-center">
              <div
                class="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-teal-500"
              />
              <p class="text-sm text-slate-500">Chargement du catalogue…</p>
            </div>
          </div>

          <!-- Error -->
          <div
            v-else-if="catalogStore.error"
            class="rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center"
          >
            <p class="text-sm font-medium text-red-600">{{ catalogStore.error }}</p>
            <button
              class="mt-3 rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-200"
              @click="catalogStore.loadConsolidated()"
            >
              Réessayer
            </button>
          </div>

          <!-- Loaded: search + accordion -->
          <template v-else-if="catalogStore.summary">
            <!-- Sous-titre identitaire du catalogue -->
            <div class="mb-3 flex items-center gap-2">
              <h3 class="text-sm font-bold uppercase tracking-wide text-slate-500">
                Catalogue consolidé
              </h3>
              <i
                v-tooltip.top="{
                  value:
                    'Offre consolidée de toutes les entités de votre GCSMS/GTSMS. Les prestations affichées ici sont celles que votre structure sait proposer — à vous de choisir celles adaptées au patient.',
                  pt: {
                    root: { class: 'carelink-catalog-tooltip' },
                  },
                }"
                class="pi pi-info-circle cursor-help text-xs text-slate-400 transition-colors hover:text-teal-500"
                aria-hidden="true"
              />
            </div>

            <!-- Search bar -->
            <div class="mb-4">
              <input
                :value="catalogStore.searchQuery"
                type="text"
                placeholder="Rechercher une prestation, un code…"
                class="w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
                @input="catalogStore.setSearchQuery(($event.target as HTMLInputElement).value)"
              />
            </div>

            <!-- Domain filter chips -->
            <div class="mb-4 flex flex-wrap gap-2">
              <button
                :class="[
                  chipBase,
                  catalogStore.activeDomainFilter === null ? chipActive : chipInactive,
                ]"
                @click="catalogStore.setDomainFilter(null)"
              >
                Tous ({{ catalogStore.totalActivePrestations }})
              </button>
              <button
                v-for="domain in DOMAIN_ORDER"
                :key="domain"
                :class="[
                  chipBase,
                  catalogStore.activeDomainFilter === domain ? chipActive : chipInactive,
                ]"
                @click="catalogStore.setDomainFilter(domain)"
              >
                {{ DOMAIN_LABELS[domain] }}
                ({{ catalogStore.domainCounts[domain] ?? 0 }})
              </button>
            </div>

            <!-- Empty state -->
            <div
              v-if="catalogStore.domainGroups.length === 0"
              class="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center"
            >
              <p class="text-sm text-slate-500">Aucune prestation trouvée.</p>
              <button
                class="mt-3 text-sm font-semibold text-teal-600"
                @click="catalogStore.resetFilters()"
              >
                Réinitialiser
              </button>
            </div>

            <!-- Domain → Category → PrestationCard (accordéon) -->
            <div
              v-for="domainGroup in catalogStore.domainGroups"
              :key="domainGroup.domain"
              class="mb-5"
            >
              <!-- Domain header -->
              <div class="mb-2 flex items-center gap-2 border-b border-slate-100 pb-2">
                <span class="text-sm font-bold text-slate-700">
                  {{ domainGroup.label }}
                </span>
                <span class="text-xs text-slate-400">
                  {{ domainGroup.prestationCount }} prestation{{
                    domainGroup.prestationCount > 1 ? 's' : ''
                  }}
                </span>
              </div>

              <!-- Category sections (accordéon : une seule ouverte à la fois) -->
              <div
                v-for="catGroup in domainGroup.categories"
                :key="catGroup.category"
                :class="[
                  'catalog-accordion-item mb-1.5 overflow-hidden rounded-xl border transition-colors',
                  openCategoryKey === `${domainGroup.domain}::${catGroup.category}`
                    ? 'border-teal-200 bg-white'
                    : 'border-slate-100 bg-white hover:border-slate-200',
                ]"
              >
                <!-- Category header (clickable) -->
                <button
                  type="button"
                  class="flex w-full items-center justify-between px-4 py-3 text-left transition-colors"
                  @click="toggleCategory(domainGroup.domain, catGroup.category)"
                >
                  <div class="flex items-center gap-2">
                    <span class="text-sm">{{ catGroup.icon }}</span>
                    <span class="text-xs font-semibold text-slate-700">
                      {{ catGroup.label }}
                    </span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span
                      class="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[0.625rem] font-medium text-slate-500"
                    >
                      {{ catGroup.prestationCount }}
                    </span>
                    <i
                      :class="[
                        'pi pi-chevron-right text-[0.625rem] text-slate-400 transition-transform duration-200',
                        openCategoryKey === `${domainGroup.domain}::${catGroup.category}`
                          ? 'rotate-90'
                          : '',
                      ]"
                      aria-hidden="true"
                    />
                  </div>
                </button>

                <!-- Category body (collapsible) -->
                <div
                  :class="[
                    'catalog-accordion-body',
                    openCategoryKey === `${domainGroup.domain}::${catGroup.category}`
                      ? 'is-open'
                      : '',
                  ]"
                >
                  <div class="flex flex-col gap-2 px-4 pb-3">
                    <CoordinationPrestationCard
                      v-for="prestation in catGroup.prestations"
                      :key="prestation.template_id"
                      :prestation="prestation"
                      @select="(offer) => onSelectOffer(offer, prestation)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- RIGHT: Panier (sticky) -->
        <div class="w-[340px] shrink-0">
          <div class="sticky top-4">
            <SelectedServicesPanel
              :services="carePlanStore.draftServices"
              :total-hours-week="carePlanStore.draftTotalHoursWeek"
              :budget-weekly="carePlanStore.draftBudgetWeekly"
              :budget-allocated="form.budget_allocated ?? 0"
              @remove="carePlanStore.removeDraftService"
              @update="carePlanStore.updateDraftService"
            />

            <!-- Navigation vers étape 2 (remplace le bouton sauvegarder — flux linéaire Option A) -->
            <button
              :disabled="carePlanStore.draftServicesCount === 0"
              :class="[
                'mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition-colors',
                carePlanStore.draftServicesCount > 0
                  ? 'bg-teal-500 text-white hover:bg-teal-600'
                  : 'cursor-not-allowed bg-slate-200 text-slate-400',
              ]"
              type="button"
              @click="goToStep2"
            >
              📅 Construire la semaine type →
            </button>

            <p
              v-if="carePlanStore.draftServicesCount === 0"
              class="mt-2 text-center text-xs text-slate-400"
            >
              Ajoutez au moins une prestation pour continuer
            </p>
          </div>
        </div>
      </div>

      <!-- ===== ÉTAPE 2 : Semaine type (F3) ===== -->
      <div v-else-if="currentStep === 2">
        <div class="flex" style="height: calc(100vh - 22rem)">
          <!-- LEFT: Palette prestations -->
          <div class="w-[260px] shrink-0 overflow-hidden">
            <WeeklyPrestaPalette
              :services="carePlanStore.draftServices"
              :placements="carePlanStore.weeklyPlacements"
              @dblclick-service="onDblClickPresta"
            />
          </div>

          <!-- RIGHT: Week grid -->
          <div class="flex flex-1 flex-col overflow-hidden">
            <div class="flex-1 overflow-auto p-3">
              <div class="grid grid-cols-7 gap-2">
                <WeeklyDayCard
                  v-for="(dayName, dayIdx) in WEEK_DAYS"
                  :key="dayIdx"
                  :day="dayIdx"
                  :day-name="dayName"
                  :placements="carePlanStore.weeklyPlacements.filter((p) => p.day === dayIdx)"
                  :drafts="carePlanStore.draftServices"
                  @drop="
                    (draftIdx: number, periodKey: string) =>
                      onWeeklyDrop(dayIdx, draftIdx, periodKey)
                  "
                  @remove-placement="carePlanStore.removePlacement"
                  @update-placement-time="carePlanStore.updatePlacementTime"
                />
              </div>
            </div>

            <!-- Bottom bar -->
            <div
              class="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-2.5 shadow-[0_-2px_8px_rgba(0,0,0,0.03)]"
            >
              <div class="flex gap-5 text-[0.8125rem] text-slate-500">
                <span>
                  Placées :
                  <strong class="font-bold text-slate-800">{{
                    carePlanStore.placementsCount
                  }}</strong>
                </span>
                <span>
                  Heures / sem :
                  <strong class="font-bold text-slate-800">{{
                    carePlanStore.totalPlacedHoursFormatted
                  }}</strong>
                </span>
                <span>
                  Doublons :
                  <strong
                    :class="carePlanStore.doublonCount > 0 ? 'text-red-500' : 'text-emerald-500'"
                    class="font-bold"
                  >
                    {{ carePlanStore.doublonCount }}
                  </strong>
                </span>
              </div>
              <div class="flex gap-2">
                <button
                  class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
                  type="button"
                  @click="carePlanStore.clearPlacements()"
                >
                  Réinitialiser
                </button>
                <button
                  class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
                  type="button"
                  @click="currentStep = 1"
                >
                  ← Prestations
                </button>
                <!-- F6.6 UX — icône info de réassurance (mode révision uniquement) -->
                <span
                  v-if="isReviseMode"
                  class="flex h-9 w-9 cursor-help items-center justify-center text-base text-teal-400 transition-colors hover:text-teal-600"
                  title="Modifiable jusqu'à étape soumission"
                  aria-label="Modifiable jusqu'à étape soumission"
                >
                  <i class="pi pi-info-circle"></i>
                </span>
                <button
                  :disabled="!canSave || carePlanStore.saving || carePlanStore.doublonCount > 0"
                  :class="[
                    'rounded-lg px-5 py-2 text-sm font-bold transition-colors',
                    canSave && carePlanStore.doublonCount === 0
                      ? 'bg-teal-500 text-white hover:bg-teal-600'
                      : 'cursor-not-allowed bg-slate-200 text-slate-400',
                  ]"
                  type="button"
                  @click="onSave"
                >
                  {{ carePlanStore.saving ? 'Enregistrement…' : '💾 Enregistrer le plan' }}
                </button>

              </div>
            </div>
            <!-- Error message -->
            <p v-if="carePlanStore.error" class="text-xs font-medium text-red-500">
                {{ carePlanStore.error }}
            </p>
          </div>
        </div>
      </div>

        <!-- Recurrence Popover -->
        <RecurrencePopover
          :visible="popoverVisible"
          :draft="popoverDraft"
          :draft-index="popoverDraftIndex"
          :period="popoverPeriod"
          :initial-start-time="popoverStartTime"
          :initial-day="popoverDay"
          :pos-x="popoverX"
          :pos-y="popoverY"
          @close="popoverVisible = false"
          @apply="onRecurrenceApply"
        />
    </div>
  </div>

</template>

<script setup lang="ts">
  import { computed, watchEffect, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';

  import Select from 'primevue/select';
  import Toast from 'primevue/toast';
  import { useToast } from 'primevue/usetoast';

  import CoordinationPrestationCard from '@/components/catalog/CoordinationPrestationCard.vue';
  import RecurrencePopover from '@/components/careplan/RecurrencePopover.vue';
  import SelectedServicesPanel from '@/components/careplan/SelectedServicesPanel.vue';
  import PatientIdentityBanner from '@/components/careplan/PatientIdentityBanner.vue';
  import WeeklyDayCard from '@/components/careplan/WeeklyDayCard.vue';
  import WeeklyPrestaPalette from '@/components/careplan/WeeklyPrestaPalette.vue';
  import { carePlanService, patientService } from '@/services';
  import {
    useCarePlanStore,
    useCoordinationCatalogStore,
    useEntityStore,
    usePatientStore,
  } from '@/stores';
  import type { EntityOption } from '@/stores';
  import type {
    CarePlanResponse, // F6.5 — typage ref parentPlan
    CarePlanServiceDraft,
    CarePlanServiceResponse, // F6.3 — typage paramètre helper mapResponsesToDrafts
    ConsolidatedEntityOffer,
    ConsolidatedPrestation,
    FrequencyType, // F6.3 — cast Response.frequency_type (string) → enum
    PatientSummary,
    ServicePriority, // F6.3 — cast Response.priority (string) → enum
  } from '@/types';
  import { DOMAIN_LABELS, DOMAIN_ORDER, EntityTypeColors, PLAN_STATUS_LABELS, WEEK_DAYS } from '@/types';

  const route = useRoute();
  const router = useRouter();
  const carePlanStore = useCarePlanStore();
  const catalogStore = useCoordinationCatalogStore();
  const entityStore = useEntityStore();
  const patientStore = usePatientStore();
  const toast = useToast();

  /** Détecte l'espace courant pour adapter les navigations. */
  const isInSoinsSpace = computed(() => route.path.startsWith('/soins'));

  /**
   * Mode wizard révision (B28b, décision 38 plan / 38 cadrage — option B
   * mode unifié). True quand la page est ouverte avec ?revise_from=N pour
   * éditer un DRAFT-révision existant. False = mode création ex nihilo.
   */
  const isReviseMode = computed(() => route.query.revise_from !== undefined);

  /**
   * ID du DRAFT-révision à hydrater quand isReviseMode est true.
   * NULL en mode création ex nihilo ou si le param est mal formé.
   */
  const revisedDraftId = computed<number | null>(() => {
    if (!isReviseMode.value) return null;
    const id = Number(route.query.revise_from);
    return Number.isInteger(id) && id > 0 ? id : null;
  });

/**
   * 🆕 v5.55 (B59) — Titre H1 dynamique selon le mode wizard.
   *
   * Mode création ex nihilo → "Nouveau plan d'aide"
   * Mode révision (?revise_from=N) → "Réviser le plan d'aide"
   *
   * Volontairement texte fixe (pas de référence à parentPlan.id) pour éviter
   * un flicker durant le chargement asynchrone du bandeau parent. Le bandeau
   * F6.5 contextuel juste en dessous fournit déjà l'info précise (#ID + titre
   * + période du parent).
   */
  const pageTitle = computed(() =>
    isReviseMode.value ? "Réviser le plan d'aide" : "Nouveau plan d'aide",
  );

  /**
   * 🆕 v5.55 (B59) — Sous-titre H1 dynamique.
   */
  const pageSubtitle = computed(() =>
    isReviseMode.value
      ? 'Ajustez les prestations et la semaine type du brouillon de révision'
      : 'Sélectionnez les prestations et configurez le plan',
  );

  /**
   * 🆕 v5.55 (B59) — Synchronise le breadcrumb top-left (AppHeader) avec le mode.
   *
   * `route.meta.title` est défini statiquement dans le routeur (admin.ts/soins.ts).
   * On le surcharge ici pour refléter le mode wizard. AppHeader consomme
   * `route.meta.title` via un computed réactif → l'update se propage automatiquement.
   *
   * `watchEffect` immédiat (vs `watch immediate`) couvre aussi le cas du mount
   * direct sur l'URL `?revise_from=N` (navigation entrante depuis F8).
   */
  watchEffect(() => {
    route.meta.title = isReviseMode.value
      ? "Réviser un plan d'aide"
      : "Nouveau plan d'aide";
  });

  /**
   * F6.5 — Plan parent chargé pour le bandeau contextuel mode révision.
   *
   * Chargement direct via carePlanService.get() (pas via le store) pour ne
   * pas écraser `carePlanStore.currentPlan` qui reste le DRAFT-révision en
   * cours d'édition. Le bandeau n'a besoin que des champs CarePlanResponse
   * (titre, statut, dates) — les services du parent sont ignorés.
   *
   * NULL en mode création ex nihilo, en cas d'échec de chargement, ou avant
   * la fin de l'hydratation onMounted.
   */
  const parentPlan = ref<CarePlanResponse | null>(null);

  /**
   * F6.5 — Lien vers la fiche détail du plan parent (espace-aware).
   * NULL si parentPlan absent — guard côté template.
   */
  const parentPlanLinkTo = computed<string | null>(() => {
    if (parentPlan.value === null) return null;
    const prefix = isInSoinsSpace.value ? '/soins' : '/admin';
    return `${prefix}/care-plans/${parentPlan.value.id}`;
  });

  // =========================================================================
  // HELPERS — RÉVISION (filtrage notes audit B28)
  // =========================================================================

  /**
   * Pattern d'audit B28 (cohérent avec convention #118 mode consultation) :
   * `[RÉVISION B28[a-z]? YYYY-MM-DDThh:mm:ss.fff+TZ] ... motif: XXX[\n|]Commentaire: YYY`
   *
   * La regex retire :
   *  1. La ligne d'audit complète `[RÉVISION B28x ...]` + son contenu (motif, etc.)
   *  2. Le séparateur : soit `\n`, soit position avant `Commentaire: ` (lookahead),
   *     soit fin de string — robuste aux deux formats DB possibles.
   *  3. Le préfixe `Commentaire: ` éventuel restant.
   *
   * Le commentaire IDEC est préservé pour édition naturelle dans le textarea.
   *
   * Utilisé exclusivement à l'hydratation `form.notes` en mode révision (F6.2).
   * IMPORTANT : la note d'audit reste intacte côté DB. F6.6 (save) devra la
   * reconstruire au save (cf. dette tracée plan_phase4 + frontend_spec).
   */
  const REVISION_AUDIT_PREFIX =
    /^\[RÉVISION B28[a-z]? \d{4}-\d{2}-\d{2}T[^\]]+\][^\n]*?(?:\n|(?=Commentaire: )|$)(?:Commentaire: )?/;

  function filterRevisionAuditFromNotes(rawNotes: string): string {
    return rawNotes.replace(REVISION_AUDIT_PREFIX, '').trim();
  }

  /**
   * F6.3 — Mappe une liste de CarePlanServiceResponse vers CarePlanServiceDraft.
   *
   * Reconstitue les champs _display_* depuis :
   *   - Les champs déjà enrichis par le backend dans Response :
   *     service_name, service_code, entity_name, effective_tarif
   *   - Le catalogue consolidé pour les champs absents de Response :
   *     required_profession_name, domain (résolus via l'index template_id → ConsolidatedPrestation)
   *
   * Edge case : si une prestation n'est pas trouvée dans le catalogue (template
   * désactivé/supprimé entre la création du plan parent et la révision), les
   * champs catalogue valent `null` et les champs Response font foi (`name ?? ''`).
   *
   * Les casts `as FrequencyType` / `as ServicePriority` sont nécessaires car
   * Response porte ces enums comme `string` (sérialisation Pydantic),
   * Draft les porte comme enums TypeScript (CarePlanServiceCreate hérité).
   *
   * @param responses Services du plan (DRAFT cloné côté backend en mode révision)
   * @param prestationIndex Index template_id → ConsolidatedPrestation depuis catalogStore
   * @returns Liste des drafts prête pour `carePlanStore.hydrateDraftServices()`
   */
  function mapResponsesToDrafts(
    responses: CarePlanServiceResponse[],
    prestationIndex: Map<number, ConsolidatedPrestation>,
  ): CarePlanServiceDraft[] {
    return responses.map((r) => {
      const prestation = prestationIndex.get(r.service_template_id);
      return {
        // Champs API (CarePlanServiceCreate)
        service_template_id: r.service_template_id,
        entity_service_id: r.entity_service_id,
        quantity_per_week: r.quantity_per_week,
        frequency_type: r.frequency_type as FrequencyType,
        frequency_days: r.frequency_days,
        preferred_time_start: r.preferred_time_start,
        preferred_time_end: r.preferred_time_end,
        duration_minutes: r.duration_minutes,
        priority: r.priority as ServicePriority,
        special_instructions: r.special_instructions,
        // Champs display (frontend-only, reconstitués depuis Response + catalogue)
        _display_service_name: r.service_name ?? prestation?.name ?? '',
        _display_service_code: r.service_code ?? prestation?.code ?? '',
        _display_entity_name: r.entity_name,
        _display_tarif: r.effective_tarif,
        _display_profession_name: prestation?.required_profession_name ?? null,
      _display_domain: prestation?.domain ?? null,
    };
  });
}

/**
 * F6.6 — Extrait la ligne d'audit B28 d'une note brute.
 *
 * Retourne la ligne complète `[RÉVISION B28x ...] motif: XXX` (sans `\n` final
 * ni préfixe `Commentaire: ...` qui suit), ou `null` si aucune ligne d'audit.
 *
 * Utilisé au save mode édition pour préserver l'audit trail intact :
 * `form.notes` ne contient que le commentaire IDEC édité (filtré par
 * filterRevisionAuditFromNotes au F6.2), donc il faut re-préfixer avec
 * la ligne audit avant d'envoyer le payload `updatePlan`.
 *
 * Inverse fonctionnel de filterRevisionAuditFromNotes : ce qui est extrait
 * ici est exactement ce qui était retiré là-bas (modulo le `Commentaire: `).
 */
function extractRevisionAuditLine(rawNotes: string): string | null {
  const match = rawNotes.match(
    /^\[RÉVISION B28[a-z]? \d{4}-\d{2}-\d{2}T[^\]]+\][^\n]*?(?=\n|Commentaire: |$)/,
  );
  return match ? match[0] : null;
}

/**
 * F6.6 — Reconstruit le champ `notes` au save mode édition révision.
 *
 * Concatène l'audit line + commentaire IDEC en respectant le format
 * canonique avec `\n` séparateur + préfixe `Commentaire: `.
 *
 * Si le commentaire IDEC est vide, retourne juste l'audit line (la note
 * minimale qu'on s'engage à préserver en DB pour traçabilité B28).
 */
function reconstructNotesWithAudit(
  auditLine: string,
  editedComment: string,
): string {
  if (!editedComment) return auditLine;
  return `${auditLine}\nCommentaire: ${editedComment}`;
}

  // =========================================================================
  // FORM STATE
  // =========================================================================

  const form = reactive({
    title: '',
    patient_id: null as number | null,
    entity_id: null as number | null,
    start_date: '',
    end_date: '',
    budget_allocated: null as number | null,
    notes: '',
    source_evaluation_id: null as number | null, // F6.2 — coffre commun (option C)
    gir_at_creation: null as number | null, // F6.2 — coffre commun (option C)
  });

  // =========================================================================
  // DROPDOWN OPTIONS
  // =========================================================================

  /** Option structurée pour le Select patient (identitovigilance : date de naissance en discriminant). */
  interface PatientOption {
    value: number;
    label: string;
    firstName: string;
    lastName: string;
    birthDate: string | null;
    birthDateFormatted: string;
  }

  /**
   * Options patients pour le Select : exclut archivés/décédés (cohérent avec
   * visiblePatients du store), label "NOM Prénom" formaté pour l'identitovigilance,
   * discriminant date de naissance dans le slot option. Tri A→Z insensible
   * à la casse et aux accents.
   */
  const patientOptions = computed<PatientOption[]>(() => {
    return patientStore.allPatientsLight
      .filter((p: PatientSummary) => p.status !== 'ARCHIVED' && p.status !== 'DECEASED')
      .map((p: PatientSummary) => {
        const last = (p.last_name ?? '').toUpperCase();
        const first = p.first_name ?? '';
        const label = `${last} ${first}`.trim() || `Patient #${p.id}`;
        return {
          value: p.id,
          label,
          firstName: first,
          lastName: last,
          birthDate: p.birth_date ?? null,
          birthDateFormatted: formatShortDate(p.birth_date ?? null),
        };
      })
      .sort((a, b) => a.label.localeCompare(b.label, 'fr', { sensitivity: 'base' }));
  });

  /** Options entités déjà prêtes via le store dédié (computed, tri inclus). */
  const entityOptions = computed<EntityOption[]>(() => entityStore.entityOptions);

  // =========================================================================
  // PATIENT BANNER — chargement réactif du patient complet
  // =========================================================================

  /** Patient complet chargé pour le bandeau d'identitovigilance. */
  const currentPatient = computed(() => patientStore.currentPatient);
  const isLoadingPatient = computed(() => patientStore.isLoadingPatient);

  /**
   * Watch sur form.patient_id : déclenche fetchPatient à chaque changement
   * pour alimenter le bandeau d'identitovigilance.
   *
   * Auto-fill entité : si le patient chargé a un entity_id et que le Select
   * entité est encore vide, on pré-remplit automatiquement. Le coordinateur
   * peut toujours changer manuellement — le Select reste éditable.
   */
  watch(
    () => form.patient_id,
    async (newId) => {
      if (newId !== null && newId > 0) {
        await patientStore.fetchPatient(newId);

        // Auto-fill entity si vide et si le patient a un rattachement connu
        const loadedPatient = patientStore.currentPatient;
        if (loadedPatient?.entity_id && form.entity_id === null) {
          form.entity_id = loadedPatient.entity_id;
        }
      } else {
        patientStore.clearCurrentPatient();
      }
    },
  );

  // =========================================================================
  // PROVENANCE — ?from_evaluation
  // =========================================================================

  /** Info affichée dans le chip de provenance (null = pas de provenance). */
  const evaluationInfo = ref<{ id: number; dateFormatted: string; girScore: number | null } | null>(
    null,
  );

  /** Retour vers l'évaluation de provenance. */
  function onBackToEvaluation(): void {
    if (!form.patient_id || !evaluationInfo.value) return;
    router
      .push({
        name: isInSoinsSpace.value ? 'soins-patient-detail' : 'admin-patient-detail',
        params: { id: form.patient_id },
        query: { evaluation: evaluationInfo.value.id },
      })
      .catch(() => {
        router.back();
      });
  }

  // =========================================================================
  // HELPERS
  // =========================================================================

  /** Format date court fr-FR (JJ/MM/AAAA) — défensif contre les dates invalides. */
  function formatShortDate(iso: string | null): string {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  // =========================================================================
  // CHIP STYLES
  // =========================================================================

  const chipBase =
    'rounded-full border px-3 py-1 text-xs font-medium transition-colors cursor-pointer';
  const chipActive = 'bg-teal-50 border-teal-300 text-teal-700 font-semibold';
  const chipInactive = 'bg-white border-slate-200 text-slate-500 hover:border-teal-300';

  // =========================================================================
  // ACCORDION CATALOGUE — une seule catégorie ouverte à la fois
  // =========================================================================

  /**
   * Clé de la catégorie actuellement dépliée (format "domain::category").
   * null = toutes repliées. Une seule ouverte à la fois (comportement accordéon).
   */
  const openCategoryKey = ref<string | null>(null);

  /** Toggle accordéon : clic sur une catégorie ouverte la ferme, clic sur une autre la switch. */
  function toggleCategory(domain: string, category: string): void {
    const key = `${domain}::${category}`;
    openCategoryKey.value = openCategoryKey.value === key ? null : key;
  }

  /** Reset catégorie ouverte quand on change de filtre domaine (évite un stale state). */
  watch(
    () => catalogStore.activeDomainFilter,
    () => {
      openCategoryKey.value = null;
    },
  );

  // =========================================================================
  // COMPUTED
  // =========================================================================

  // =========================================================================
  // STEPPER — Navigation Bloc 1 ↔ Bloc 2
  // =========================================================================

  /** Étape courante : 1 = Sélection prestations, 2 = Semaine type */
  const currentStep = ref(1);

  /** Passage à l'étape 2 (semaine type) — nécessite au moins 1 prestation */
  function goToStep2(): void {
    if (carePlanStore.draftServicesCount > 0) {
      currentStep.value = 2;
    }
  }

  // =========================================================================
  // POPOVER RÉCURRENCE (F3) — état + handlers
  // =========================================================================

  const popoverVisible = ref(false);
  const popoverDraftIndex = ref(0);
  const popoverPeriod = ref('matin');
  const popoverStartTime = ref('08:00');
  const popoverDay = ref<number | null>(null);
  const popoverX = ref(300);
  const popoverY = ref(200);

  /** Popover dummy draft pour le v-bind initial (évite undefined) */
  const popoverDraft = computed(() => {
    return (
      carePlanStore.draftServices[popoverDraftIndex.value] ?? {
        service_template_id: 0,
        quantity_per_week: 1,
        frequency_type: 'WEEKLY' as const,
        duration_minutes: 30,
        _display_service_name: '',
        _display_service_code: '',
        _display_entity_name: null,
        _display_tarif: null,
        _display_profession_name: null,
        _display_domain: null,
      }
    );
  });

  /**
   * Drop d'une prestation sur un jour/période → ouvre le popover récurrence.
   * L'heure est auto-stackée via le store.
   */
  function onWeeklyDrop(dayIdx: number, draftIndex: number, periodKey: string): void {
    popoverDraftIndex.value = draftIndex;
    popoverPeriod.value = periodKey;
    popoverStartTime.value = carePlanStore.getAutoStackedTime(dayIdx, periodKey);
    popoverDay.value = dayIdx;
    // Position au centre de l'écran
    popoverX.value = Math.round(window.innerWidth / 2 - 150);
    popoverY.value = Math.round(window.innerHeight / 2 - 150);
    popoverVisible.value = true;
  }

  /** Double-clic sur une prestation dans la palette → popover avec jours weekdays */
  function onDblClickPresta(draftIndex: number): void {
    popoverDraftIndex.value = draftIndex;
    popoverPeriod.value = 'matin';
    popoverStartTime.value = '08:00';
    popoverDay.value = null; // null → pré-coche Lun-Ven
    popoverX.value = Math.round(window.innerWidth / 2 - 150);
    popoverY.value = Math.round(window.innerHeight / 2 - 150);
    popoverVisible.value = true;
  }

  /** Applique la récurrence depuis le popover */
  function onRecurrenceApply(
    draftIndex: number,
    days: number[],
    period: string,
    startTime: string,
    duration: number,
  ): void {
    carePlanStore.applyRecurrence(draftIndex, days, period, startTime, duration);
    popoverVisible.value = false;
  }

  // =========================================================================
  // COMPUTED — Validation
  // =========================================================================

  const canSave = computed(() => {
    return (
      form.title.trim().length > 0 &&
      form.patient_id !== null &&
      form.patient_id > 0 &&
      form.entity_id !== null &&
      form.entity_id > 0 &&
      form.start_date !== '' &&
      carePlanStore.draftServicesCount > 0
    );
  });

  // =========================================================================
  // LIFECYCLE
  // =========================================================================

  onMounted(async () => {
    // Vider le panier au montage (fresh start — ex nihilo OU révision avant hydratation F6.3)
    carePlanStore.clearDraft();

    // Chargements parallèles communs : dropdowns + catalogue consolidé si pas en cache
    const loadPromises: Promise<unknown>[] = [
      patientStore.fetchAllForDropdown(),
      entityStore.load(),
    ];
    if (!catalogStore.data) {
      loadPromises.push(catalogStore.loadConsolidated());
    }

    // Aiguillage mode révision (B28b F6.1, décision 38 mode unifié) :
    // ?revise_from=N → charger le DRAFT-révision en parallèle, le pré-remplissage
    // depuis query params est sauté (le DRAFT cloné porte déjà toutes ses données).
    if (isReviseMode.value && revisedDraftId.value !== null) {
      loadPromises.push(carePlanStore.loadPlan(revisedDraftId.value));
      await Promise.all(loadPromises);

      // F6.2 — Hydratation form depuis currentPlan (9 champs scalaires).
      // IMPORTANT : entity_id AVANT patient_id pour que le guard `=== null`
      // du watch ligne ~704 protège contre l'auto-fill malveillant qui
      // écraserait l'entité héritée du plan parent par l'entity_id actuel
      // du patient (potentiellement modifiée depuis la création du plan).
      const draft = carePlanStore.currentPlan;
      if (draft !== null) {
        // F6.2 — Hydratation form depuis currentPlan (9 champs scalaires)
        form.title = draft.title;
        form.start_date = draft.start_date;
        form.end_date = draft.end_date ?? '';
        form.budget_allocated = draft.budget_allocated ?? null;
        form.notes = filterRevisionAuditFromNotes(draft.notes ?? ''); // F6.2 + filtre audit B28 (dette F6.6 : reconstruire au save)
        form.gir_at_creation = draft.gir_at_creation ?? null;
        form.source_evaluation_id = draft.source_evaluation_id ?? null;
        form.entity_id = draft.entity_id; // AVANT patient_id (cf. note ci-dessus)
        form.patient_id = draft.patient_id; // Trigger watch ligne ~704 → fetchPatient → bandeau peuplé

        // F6.3 — Hydratation draftServices[] depuis currentPlan.services
        // Le catalogue est garanti chargé à ce point (loadPromises l'inclut si data était null).
        if (draft.services.length > 0 && catalogStore.data !== null) {
          const prestationIndex = new Map<number, ConsolidatedPrestation>();
          for (const p of catalogStore.data.prestations) {
            prestationIndex.set(p.template_id, p);
          }
          const drafts = mapResponsesToDrafts(draft.services, prestationIndex);
          carePlanStore.hydrateDraftServices(drafts);
        }

        // F6.4 — Reconstruction weeklyPlacements[] depuis services
      // Pour chaque service hydraté, on projette N placements (un par jour de
      // frequency_days). Décalage -1 (convention backend ISO 1=Lun…7=Dim →
      // convention frontend 0=Lun…6=Dim, cohérent avec syncDraftsFromPlacements
      // ligne ~655 qui applique le décalage inverse +1 au save).
      draft.services.forEach((service, draftIndex) => {
        if (
          service.frequency_days === null ||
          service.frequency_days.length === 0 ||
          service.preferred_time_start === null
        ) {
          // Service sans placement programmé (ON_DEMAND, etc.) → skip,
          // restera dans le panier sans placement dans la grille.
          return;
        }
        const startTime = service.preferred_time_start.substring(0, 5); // 'HH:MM:SS' → 'HH:MM'
        const period = carePlanStore.periodFromStartTime(startTime);
        const days = service.frequency_days.map((d) => d - 1); // ISO → frontend
        carePlanStore.applyRecurrence(
          draftIndex,
          days,
          period,
          startTime,
          service.duration_minutes,
        );
      });

      // F6.5 — Bandeau parent : charge le plan parent via le service direct
      // pour ne pas écraser carePlanStore.currentPlan (qui reste le DRAFT).
      // Échec silencieux : si le parent n'est pas accessible (droits, suppression
      // ultérieure, etc.), parentPlan reste null et le bandeau ne s'affiche pas.
      // UX dégradée mais non bloquante — l'IDEC (coordinateur) peut toujours réviser.
      if (draft.supersedes_plan_id !== null) {
        try {
          parentPlan.value = await carePlanService.get(draft.supersedes_plan_id);
          } catch {
            parentPlan.value = null;
        }
      }

    }
    return;
    }

    // Mode création ex nihilo : pré-remplissage depuis les query params
    await Promise.all(loadPromises);

    const query = route.query;

    if (query.patient_id) {
      const pid = Number(query.patient_id);
      if (Number.isInteger(pid) && pid > 0) {
        form.patient_id = pid;
        // Le watch déclenchera fetchPatient → alimente le bandeau
      }
    }

    if (query.entity_id) {
      const eid = Number(query.entity_id);
      if (Number.isInteger(eid) && eid > 0) {
        form.entity_id = eid;
      }
    }

    // Provenance : chip informatif + lien retour — non bloquant si échec
    if (query.from_evaluation && form.patient_id !== null) {
      const evalId = Number(query.from_evaluation);
      if (Number.isInteger(evalId) && evalId > 0) {
        try {
          const evaluation = await patientService.getEvaluation(form.patient_id, evalId);
          evaluationInfo.value = {
            id: evalId,
            dateFormatted: formatShortDate(evaluation.created_at ?? null),
            girScore: evaluation.gir_score ?? null,
          };
          // F6.2 — Synchronisation form (source unique pour le payload submit).
          // evaluationInfo reste pour le chip UI (porte dateFormatted non-payload).
          form.source_evaluation_id = evalId;
          form.gir_at_creation = evaluation.gir_score ?? null;
        } catch {
          // Chip silencieusement masqué si l'évaluation est inaccessible
          evaluationInfo.value = null;
        }
      }
    }
  });

  // =========================================================================
  // HANDLERS
  // =========================================================================

  /**
   * Sélection d'une offre depuis le catalogue → ajout au panier draft.
   * La closure dans le template donne accès à la prestation parente.
   */
  function onSelectOffer(offer: ConsolidatedEntityOffer, prestation: ConsolidatedPrestation): void {
    const draft: CarePlanServiceDraft = {
      // Champs API (CarePlanServiceCreate)
      service_template_id: prestation.template_id,
      entity_service_id: null, // Non disponible dans le catalogue consolidé
      quantity_per_week: 1,
      frequency_type: 'WEEKLY',
      duration_minutes: offer.custom_duree ?? prestation.default_duration_minutes ?? 30,
      priority: 'MEDIUM',
      // Champs display (frontend-only)
      _display_service_name: prestation.name,
      _display_service_code: prestation.code,
      _display_entity_name: offer.entity_name,
      _display_tarif: offer.custom_tarif,
      _display_profession_name: prestation.required_profession_name,
      _display_domain: prestation.domain ?? null,
    };

    carePlanStore.addDraftService(draft);
  }

  /**
   * Sauvegarde du plan — construit le payload et appelle l'API.
   * Les champs _display_* sont exclus automatiquement par le backend
   * (Pydantic ignore les champs inconnus par défaut).
   */
  async function onSave(): Promise<void> {
  if (!canSave.value) return;

  // Synchroniser les placements F3 → enrichir les drafts avec frequency_days, preferred_time_*
  carePlanStore.syncDraftsFromPlacements();

  // Construire le payload services à partir des drafts (commun aux 2 modes,
  // les champs _display_* sont automatiquement filtrés par Pydantic backend)
  const services = carePlanStore.draftServices.map((draft: CarePlanServiceDraft) => ({
    service_template_id: draft.service_template_id,
    entity_service_id: draft.entity_service_id ?? undefined,
    quantity_per_week: draft.quantity_per_week,
    frequency_type: draft.frequency_type,
    frequency_days: draft.frequency_days ?? undefined,
    preferred_time_start: draft.preferred_time_start ?? undefined,
    preferred_time_end: draft.preferred_time_end ?? undefined,
    duration_minutes: draft.duration_minutes,
    priority: draft.priority ?? 'MEDIUM',
    special_instructions: draft.special_instructions ?? undefined,
  }));

  try {
    if (isReviseMode.value && revisedDraftId.value !== null) {
      // ====================================================================
      // F6.6 — MODE ÉDITION RÉVISION
      // ====================================================================
      // Sauvegarde 2-temps : replaceServices (panier+grille) + updatePlan
      // (champs scalaires). Le plan reste DRAFT — pas de transition de
      // status, la submission se fait depuis la page détail via le bouton
      // "Soumettre pour validation" déjà existant.

      // Reconstruction notes audit B28 (dette F6.6 tracée en F6.2) :
      // form.notes a été filtré au F6.2 (n'a plus la ligne audit), il faut
      // la re-préfixer pour préserver l'audit trail intact en DB.
      const originalNotes = carePlanStore.currentPlan?.notes ?? '';
      const auditLine = extractRevisionAuditLine(originalNotes);
      const editedComment = form.notes.trim();
      const finalNotes: string | undefined = auditLine !== null
        ? reconstructNotesWithAudit(auditLine, editedComment)
        : (editedComment || undefined);

      const planId = revisedDraftId.value;

      // Étape 1/2 : remplacement complet des services (panier + grille)
      await carePlanStore.replaceServices(planId, { services });

      // Étape 2/2 : mise à jour des champs scalaires éditables
      await carePlanStore.updatePlan(planId, {
        title: form.title.trim(),
        start_date: form.start_date,
        end_date: form.end_date || undefined,
        budget_allocated: form.budget_allocated ?? undefined,
        notes: finalNotes,
      });

      toast.add({
        severity: 'success',
        summary: 'Révision enregistrée',
        detail: `La révision reste en brouillon — vous pourrez la modifier ou la soumettre pour validation depuis sa fiche.`,
        life: 5000,
      });
      carePlanStore.clearDraft();
      carePlanStore.clearPlacements();
      await router.push({
        name: isInSoinsSpace.value ? 'soins-care-plans-detail' : 'admin-care-plans-detail',
        params: { id: planId },
      });
    } else {
      // ====================================================================
      // MODE EX NIHILO (inchangé hors F6.2 lecture coffre commun)
      // ====================================================================
      const plan = await carePlanStore.createPlan({
        patient_id: form.patient_id!,
        entity_id: form.entity_id!,
        title: form.title.trim(),
        start_date: form.start_date,
        end_date: form.end_date || undefined,
        budget_allocated: form.budget_allocated ?? undefined,
        notes: form.notes || undefined,
        source_evaluation_id: form.source_evaluation_id ?? undefined,  // F6.2 — lecture coffre commun
        gir_at_creation: form.gir_at_creation ?? undefined,            // F6.2 — lecture coffre commun
        services,
      });

      toast.add({
        severity: 'success',
        summary: 'Plan enregistré',
        detail: `Le plan « ${form.title.trim()} » a été créé avec ${services.length} prestation${services.length > 1 ? 's' : ''}.`,
        life: 4000,
      });
      carePlanStore.clearDraft();
      carePlanStore.clearPlacements();
      await router.push({
        name: isInSoinsSpace.value ? 'soins-care-plans-detail' : 'admin-care-plans-detail',
        params: { id: plan.id },
      });
    }
  } catch {
    // Le store positionne carePlanStore.error — toast pour feedback immédiat
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: carePlanStore.error ?? 'Impossible d\'enregistrer le plan.',
      life: 5000,
    });
  }
}
</script>

<style scoped>
  /* Transition douce du bandeau d'identitovigilance : fade + slide-down 150ms */
  .patient-banner-enter-active,
  .patient-banner-leave-active {
    transition:
      opacity 150ms ease-out,
      transform 150ms ease-out;
  }

  .patient-banner-enter-from,
  .patient-banner-leave-to {
    opacity: 0;
    transform: translateY(-4px);
  }

  /* Accordéon catalogue : déploiement fluide des catégories */
  .catalog-accordion-body {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 250ms ease-out;
  }

  .catalog-accordion-body > div {
    overflow: hidden;
  }

  .catalog-accordion-body.is-open {
    grid-template-rows: 1fr;
  }

  /* Tooltip « Catalogue consolidé » — fond clair, style médical doux.
   :global() car PrimeVue render le tooltip dans un portal hors du composant. */
  :global(.carelink-catalog-tooltip.p-tooltip) {
    max-width: 320px;
  }

  :global(.carelink-catalog-tooltip .p-tooltip-text) {
    background: #fffefb;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 12px;
    line-height: 1.5;
    box-shadow: 0 2px 8px rgb(0 0 0 / 0.06);
  }

  :global(.carelink-catalog-tooltip .p-tooltip-arrow) {
    border-top-color: #e2e8f0;
  }
</style>
