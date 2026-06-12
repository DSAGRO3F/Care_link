/** * CareLink — CoordinationCatalogPage * Chemin :
frontend/src/pages/admin/catalog/CoordinationCatalogPage.vue * * Rôle : page orchestratrice de la
vue coordination consolidée (Phase 3B). * Assemble le banner, la toolbar (recherche + chips
domaine), * et l'accordéon domaine → catégorie → CoordinationPrestationCard. * Lecture seule
cross-entités pour le coordinateur. */
<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Page header -->
    <div class="border-b border-slate-200 bg-white px-8 py-6">
      <div class="flex items-center gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-teal-50 to-teal-100 text-teal-600"
        >
          <component :is="NetworkIcon" class="h-5 w-5" />
        </div>
        <div>
          <h1 class="text-2xl font-extrabold text-slate-800">Catalogue Consolidé</h1>
          <p class="text-sm text-slate-500">Vue transversale de l'offre de soins du groupement</p>
        </div>
      </div>
    </div>

    <!-- Page body -->
    <div class="mx-auto max-w-[1600px] px-8 py-6">
      <!-- Loading state -->
      <div v-if="store.loading" class="flex items-center justify-center py-20">
        <div class="text-center">
          <div
            class="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-teal-500"
          />
          <p class="text-sm text-slate-500">Chargement du catalogue consolidé…</p>
        </div>
      </div>

      <!-- Error state -->
      <div
        v-else-if="store.error"
        class="rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center"
      >
        <p class="text-sm font-medium text-red-600">{{ store.error }}</p>
        <button
          class="mt-3 rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-200"
          @click="store.loadConsolidated()"
        >
          Réessayer
        </button>
      </div>

      <!-- Loaded state -->
      <template v-else-if="store.summary">
        <!-- Banner -->
        <CoordinationBanner :summary="store.summary" class="mb-6" />

        <!-- Toolbar: search + domain chips -->
        <div class="mb-6 flex flex-wrap items-center gap-3">
          <!-- Search -->
          <div class="relative min-w-[240px] max-w-[400px] flex-1">
            <component
              :is="SearchIcon"
              class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
            />
            <input
              :value="store.searchQuery"
              type="text"
              placeholder="Rechercher une prestation, un code…"
              class="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-700 transition-colors focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/10"
              @input="store.setSearchQuery(($event.target as HTMLInputElement).value)"
            />
          </div>

          <!-- Domain filter chips -->
          <button
            :class="[chipBase, store.activeDomainFilter === null ? chipActive : chipInactive]"
            @click="store.setDomainFilter(null)"
          >
            Tous
            <span
              :class="[countBase, store.activeDomainFilter === null ? countActive : countInactive]"
            >
              {{ store.totalActivePrestations }}
            </span>
          </button>
          <button
            v-for="domain in DOMAIN_ORDER"
            :key="domain"
            :class="[chipBase, store.activeDomainFilter === domain ? chipActive : chipInactive]"
            @click="store.setDomainFilter(domain)"
          >
            {{ DOMAIN_LABELS[domain] }}
            <span
              :class="[
                countBase,
                store.activeDomainFilter === domain ? countActive : countInactive,
              ]"
            >
              {{ store.domainCounts[domain] ?? 0 }}
            </span>
          </button>
        </div>

        <!-- Empty filtered state -->
        <div
          v-if="store.domainGroups.length === 0"
          class="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center"
        >
          <p class="text-sm text-slate-500">Aucune prestation ne correspond à votre recherche.</p>
          <button
            class="mt-3 text-sm font-semibold text-teal-600 hover:text-teal-700"
            @click="store.resetFilters()"
          >
            Réinitialiser les filtres
          </button>
        </div>

        <!-- Domain → Category → Prestation accordion -->
        <div v-for="domainGroup in store.domainGroups" :key="domainGroup.domain" class="mb-8">
          <!-- Domain header -->
          <div class="mb-3 flex items-center gap-3 border-b-2 border-slate-100 pb-2.5">
            <div
              :class="[
                domainGroup.colors.icon,
                'flex h-8 w-8 items-center justify-center rounded-lg',
              ]"
            >
              <component :is="domainIcon" class="h-4 w-4" />
            </div>
            <span class="text-base font-bold text-slate-800">
              {{ domainGroup.label }}
            </span>
            <span class="text-sm text-slate-400">
              {{ domainGroup.prestationCount }} prestation{{
                domainGroup.prestationCount > 1 ? 's' : ''
              }}
              · {{ domainGroup.totalOffers }} offre{{ domainGroup.totalOffers > 1 ? 's' : '' }}
            </span>
          </div>

          <!-- Category sub-sections -->
          <div v-for="catGroup in domainGroup.categories" :key="catGroup.category" class="mb-4">
            <div class="mb-2 flex items-center gap-2">
              <span class="text-sm">{{ catGroup.icon }}</span>
              <span class="text-sm font-semibold text-slate-600">
                {{ catGroup.label }}
              </span>
              <span class="text-xs text-slate-400"> ({{ catGroup.prestationCount }}) </span>
            </div>

            <!-- Prestation cards -->
            <div class="flex flex-col gap-3">
              <CoordinationPrestationCard
                v-for="prestation in catGroup.prestations"
                :key="prestation.template_id"
                :prestation="prestation"
                @select="onSelectOffer"
              />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { onMounted } from 'vue';

  import {
    Network as NetworkIcon,
    Search as SearchIcon,
    Activity as domainIcon,
  } from 'lucide-vue-next';

  import CoordinationBanner from '@/components/catalog/CoordinationBanner.vue';
  import CoordinationPrestationCard from '@/components/catalog/CoordinationPrestationCard.vue';
  import { useCoordinationCatalogStore } from '@/stores';
  import type { ConsolidatedEntityOffer } from '@/types';
  import { DOMAIN_LABELS, DOMAIN_ORDER } from '@/types';

  const store = useCoordinationCatalogStore();

  // =========================================================================
  // CHIP STYLES (classes Tailwind réutilisées dans le template)
  // =========================================================================

  const chipBase =
    'inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors cursor-pointer border';
  const chipActive = 'bg-teal-50 border-teal-300 text-teal-700 font-semibold';
  const chipInactive =
    'bg-white border-slate-200 text-slate-600 hover:border-teal-300 hover:text-teal-600';
  const countBase =
    'inline-flex items-center justify-center min-w-[1.25rem] h-5 rounded-full px-1 text-[0.6875rem] font-bold';
  const countActive = 'bg-teal-100 text-teal-700';
  const countInactive = 'bg-slate-100 text-slate-500';

  // =========================================================================
  // LIFECYCLE
  // =========================================================================

  onMounted(() => {
    store.loadConsolidated();
  });

  // =========================================================================
  // HANDLERS
  // =========================================================================

  /**
   * Callback sélection d'une offre — prépare Phase 4 (plan d'aide).
   * Pour l'instant, log en DEV uniquement.
   */
  function onSelectOffer(offer: ConsolidatedEntityOffer): void {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[CoordinationCatalog] Offre sélectionnée:', offer);
    }
  }
</script>
