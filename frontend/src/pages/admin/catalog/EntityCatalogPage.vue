<script setup lang="ts">
  /**
   * EntityCatalogPage — Page catalogue Admin Tenant (Phase 3A).
   *
   * Orchestre le catalogue pour une entité : bannière entité avec compteurs,
   * toolbar recherche/filtres, accordéon domaine→catégorie→services fusionnés,
   * toggle activation, personnalisation inline, toast feedback.
   *
   * Résolution entityId :
   * - Charge les entités du tenant via entityService.admin
   * - Si une seule entité → sélection automatique
   * - Si plusieurs → sélecteur compact en bandeau
   *
   * 🆕 v5.28 — Phase 3A.
   */

  import { computed, onMounted, ref, watch } from 'vue';

  import { Building2, Globe } from 'lucide-vue-next';
  import Select from 'primevue/select';
  import { useToast } from 'primevue/usetoast';

  import CatalogDomainSection from '@/components/catalog/CatalogDomainSection.vue';
  import CatalogToolbar from '@/components/catalog/CatalogToolbar.vue';
  import { entityService } from '@/services';
  import { useEntityCatalogStore } from '@/stores';
  import type { MergedEntityService } from '@/types';

  // =========================================================================
  // STORE & TOAST
  // =========================================================================

  const store = useEntityCatalogStore();
  const toast = useToast();

  // =========================================================================
  // ENTITY SELECTION
  // =========================================================================

  interface EntityOption {
    id: number;
    name: string;
    type: string;
  }

  const entities = ref<EntityOption[]>([]);
  const selectedEntityId = ref<number | null>(null);
  const entitiesLoading = ref(false);

  const hasMultipleEntities = computed(() => entities.value.length > 1);

  /** Charge les entités du tenant courant */
  async function loadEntities(): Promise<void> {
    entitiesLoading.value = true;
    try {
      const response = await entityService.list();
      entities.value = response.map((e: { id: number; name: string; entity_type?: string }) => ({
        id: e.id,
        name: e.name,
        type: e.entity_type ?? '',
      }));

      // Sélection automatique si une seule entité
      if (entities.value.length === 1) {
        selectedEntityId.value = entities.value[0].id;
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erreur chargement entités';
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: message,
        life: 5000,
      });
    } finally {
      entitiesLoading.value = false;
    }
  }

  /** Quand l'entité sélectionnée change, charger son catalogue */
  watch(selectedEntityId, async (newId) => {
    if (newId) {
      try {
        await store.loadCatalog(newId);
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Erreur',
          detail: 'Impossible de charger le catalogue de cette entité',
          life: 5000,
        });
      }
    }
  });

  // =========================================================================
  // ENTITÉ SÉLECTIONNÉE
  // =========================================================================

  const selectedEntity = computed(
    () => entities.value.find((e) => e.id === selectedEntityId.value) ?? null,
  );

  // =========================================================================
  // ACTIONS — Toggle & Save
  // =========================================================================

  async function onToggle(merged: MergedEntityService): Promise<void> {
    try {
      await store.toggleService(merged);
      toast.add({
        severity: merged.isActivated ? 'warn' : 'success',
        summary: merged.isActivated ? 'Service désactivé' : 'Service activé',
        detail: merged.template.name,
        life: 3000,
      });
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: `Impossible de modifier ${merged.template.name}`,
        life: 5000,
      });
    }
  }

  async function onSave(
    merged: MergedEntityService,
    fields: { price_euros: number | null; custom_duration_minutes: number | null },
  ): Promise<void> {
    if (!merged.entityService) return;

    try {
      await store.updateCustomization(merged.entityService.id, fields);
      toast.add({
        severity: 'success',
        summary: 'Enregistré',
        detail: `${merged.template.name} — personnalisation sauvegardée`,
        life: 3000,
      });
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: `Impossible de sauvegarder ${merged.template.name}`,
        life: 5000,
      });
    }
  }

  // =========================================================================
  // LIFECYCLE
  // =========================================================================

  onMounted(() => {
    loadEntities();
  });
</script>

<template>
  <div>
    <!-- Page header -->
    <div class="bg-white border-b border-slate-200 px-6 py-5">
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3.5">
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br from-teal-50 to-teal-100 text-teal-600 shrink-0"
          >
            <Globe :size="22" :stroke-width="2" />
          </div>
          <div>
            <h1 class="text-2xl font-extrabold text-slate-800 leading-tight">
              Catalogue de prestations
            </h1>
            <p class="text-sm text-slate-500 mt-0.5">
              Activez et personnalisez les prestations proposées par votre entité
            </p>
          </div>
        </div>

        <!-- Sélecteur entité (si multi-entités) -->
        <div v-if="hasMultipleEntities" class="shrink-0">
          <Select
            v-model="selectedEntityId"
            :options="entities"
            option-label="name"
            option-value="id"
            placeholder="Sélectionner une entité..."
            class="w-64"
          />
        </div>
      </div>
    </div>

    <!-- Page body -->
    <div class="px-6 py-5 max-w-[1400px]">
      <!-- État : chargement entités -->
      <div v-if="entitiesLoading" class="text-center py-16 text-slate-400">
        <div
          class="animate-spin w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full mx-auto mb-3"
        />
        Chargement...
      </div>

      <!-- État : aucune entité sélectionnée (multi-entités) -->
      <div v-else-if="!selectedEntityId && hasMultipleEntities" class="text-center py-16">
        <Building2 :size="48" :stroke-width="1.5" class="mx-auto text-slate-300 mb-4" />
        <p class="text-lg font-semibold text-slate-600">Sélectionnez une entité</p>
        <p class="text-sm text-slate-400 mt-1">
          Choisissez l'entité dont vous souhaitez configurer le catalogue
        </p>
      </div>

      <!-- État : aucune entité trouvée -->
      <div v-else-if="entities.length === 0 && !entitiesLoading" class="text-center py-16">
        <Building2 :size="48" :stroke-width="1.5" class="mx-auto text-slate-300 mb-4" />
        <p class="text-lg font-semibold text-slate-600">Aucune entité trouvée</p>
        <p class="text-sm text-slate-400 mt-1">
          Contactez votre administrateur pour être rattaché à une entité
        </p>
      </div>

      <!-- État : catalogue chargé -->
      <template v-else-if="selectedEntityId">
        <!-- Bannière entité -->
        <div
          class="bg-gradient-to-r from-teal-700 to-teal-800 text-white rounded-2xl px-6 py-5 mb-6 flex items-center justify-between gap-4"
        >
          <div class="flex items-center gap-3">
            <div class="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center">
              <Building2 :size="22" :stroke-width="2" class="text-white" />
            </div>
            <div>
              <div class="text-lg font-bold">
                {{ selectedEntity?.name }}
              </div>
              <div class="text-sm text-teal-200">
                {{ selectedEntity?.type }}
              </div>
            </div>
          </div>
          <div class="flex gap-8">
            <div class="text-center">
              <div class="text-3xl font-extrabold">{{ store.activatedCount }}</div>
              <div class="text-[0.6875rem] text-teal-300 uppercase tracking-wide">Activées</div>
            </div>
            <div class="text-center">
              <div class="text-3xl font-extrabold">{{ store.nationalCount }}</div>
              <div class="text-[0.6875rem] text-teal-300 uppercase tracking-wide">Disponibles</div>
            </div>
          </div>
        </div>

        <!-- Chargement catalogue -->
        <div v-if="store.loading" class="text-center py-16 text-slate-400">
          <div
            class="animate-spin w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full mx-auto mb-3"
          />
          Chargement du catalogue...
        </div>

        <!-- Erreur -->
        <div v-else-if="store.error" class="text-center py-16">
          <p class="text-red-500 font-semibold">{{ store.error }}</p>
          <button
            class="mt-3 px-4 py-2 rounded-xl bg-teal-500 text-white font-semibold text-sm hover:bg-teal-600 transition"
            @click="store.loadCatalog(selectedEntityId!)"
          >
            Réessayer
          </button>
        </div>

        <!-- Catalogue -->
        <template v-else>
          <!-- Toolbar -->
          <CatalogToolbar
            :search-query="store.searchQuery"
            :active-domain="store.activeDomainFilter"
            :domain-counts="store.domainCounts"
            :total-count="store.nationalCount"
            :total-active="store.activatedCount"
            :total-inactive="store.nationalCount - store.activatedCount"
            mode="admin"
            @update:search-query="store.setSearchQuery"
            @update:active-domain="store.setDomainFilter"
          />

          <!-- Accordéon domaine → catégorie → services -->
          <CatalogDomainSection
            v-for="group in store.domainGroups"
            :key="group.domain"
            :group="group"
            mode="admin"
            @toggle="onToggle"
            @save="onSave"
          />

          <!-- Aucun résultat après filtrage -->
          <div
            v-if="store.domainGroups.length === 0 && !store.loading"
            class="text-center py-12 text-slate-400"
          >
            <p class="text-sm">Aucune prestation ne correspond à votre recherche</p>
            <button
              class="mt-2 text-teal-600 text-sm font-semibold hover:underline"
              @click="store.resetFilters()"
            >
              Réinitialiser les filtres
            </button>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
