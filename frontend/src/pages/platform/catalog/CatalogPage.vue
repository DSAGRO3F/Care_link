<script setup lang="ts">
  /**
   * CatalogPage — Page Catalogue Admin CareLink (super-admin).
   *
   * Espace : Platform → /platform/catalog
   * Pattern : accordéon v3 (domaines → catégories → cards services).
   * CRUD : création/édition via drawer latéral, désactivation via action hover.
   *
   * Phase 3 ajoutera une page séparée dans pages/admin/catalog/ avec mode='admin'.
   */

  import { onMounted, ref } from 'vue';

  import { BookOpen, Download, Plus } from 'lucide-vue-next';
  import { useConfirm } from 'primevue/useconfirm';
  import ConfirmDialog from 'primevue/confirmdialog';
  import { useToast } from 'primevue/usetoast';

  import CatalogDomainSection from '@/components/catalog/CatalogDomainSection.vue';
  import CatalogServiceDrawer from '@/components/catalog/CatalogServiceDrawer.vue';
  import CatalogToolbar from '@/components/catalog/CatalogToolbar.vue';
  import { useCatalogStore } from '@/stores';
  import type { ServiceTemplateSummary } from '@/types';

  const store = useCatalogStore();
  const confirm = useConfirm();
  const toast = useToast();

  // =========================================================================
  // DRAWER STATE
  // =========================================================================

  const drawerVisible = ref(false);
  const editingService = ref<ServiceTemplateSummary | null>(null);

  function openCreateDrawer(): void {
    editingService.value = null;
    drawerVisible.value = true;
  }

  function openEditDrawer(service: ServiceTemplateSummary): void {
    editingService.value = service;
    drawerVisible.value = true;
  }

  // =========================================================================
  // ACTIONS
  // =========================================================================

  function handleDeactivate(service: ServiceTemplateSummary): void {
    confirm.require({
      group: 'catalogDeactivate',
      header: 'Désactiver le service',
      message: `Voulez-vous désactiver « ${service.name} » (${service.code}) ? Il restera visible mais ne pourra plus être utilisé dans les plans d'aide.`,
      acceptLabel: 'Désactiver',
      rejectLabel: 'Annuler',
      accept: async () => {
        try {
          await store.deactivateTemplate(service.id);
          toast.add({
            severity: 'success',
            summary: 'Service désactivé',
            detail: `${service.name} a été désactivé.`,
            life: 3000,
          });
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : 'Erreur lors de la désactivation';
          toast.add({ severity: 'error', summary: 'Erreur', detail: message, life: 5000 });
        }
      },
    });
  }

  async function handleReactivate(service: ServiceTemplateSummary): Promise<void> {
    try {
      await store.reactivateTemplate(service.id);
      toast.add({
        severity: 'success',
        summary: 'Service réactivé',
        detail: `${service.name} est de nouveau actif.`,
        life: 3000,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erreur lors de la réactivation';
      toast.add({ severity: 'error', summary: 'Erreur', detail: message, life: 5000 });
    }
  }

  // =========================================================================
  // LIFECYCLE
  // =========================================================================

  onMounted(async () => {
    await store.fetchAll();
  });
</script>

<template>
  <div>
    <!-- ConfirmDialog pour désactivation -->
    <ConfirmDialog group="catalogDeactivate">
      <template #icon>
        <div class="flex items-center justify-center w-10 h-10 rounded-full bg-red-50">
          <BookOpen :size="20" :stroke-width="1.8" class="text-red-600" />
        </div>
      </template>
    </ConfirmDialog>

    <!-- PAGE HEADER -->
    <div class="bg-white border-b border-slate-200 px-8 py-6">
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3.5">
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br from-teal-50 to-teal-100 text-teal-600"
          >
            <BookOpen :size="22" :stroke-width="2" />
          </div>
          <div>
            <h1 class="text-2xl font-extrabold text-slate-800 leading-tight">
              Catalogue de Services
            </h1>
            <p class="text-sm text-slate-500 mt-0.5">
              Catalogue national des prestations médico-sociales
            </p>
          </div>
        </div>
        <div class="flex gap-2 items-center">
          <button
            class="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-600 text-[0.8125rem] font-semibold hover:bg-slate-50 hover:border-slate-300 transition"
          >
            <Download :size="14" :stroke-width="2" />
            Exporter
          </button>
          <button
            class="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-teal-500 text-white text-[0.8125rem] font-semibold hover:bg-teal-600 hover:-translate-y-px hover:shadow-md transition"
            @click="openCreateDrawer"
          >
            <Plus :size="14" :stroke-width="2" />
            Nouveau service
          </button>
        </div>
      </div>
    </div>

    <!-- PAGE BODY -->
    <div class="px-8 py-6 max-w-[1400px]">
      <!-- Toolbar -->
      <CatalogToolbar
        :search-query="store.searchQuery"
        :active-domain="store.activeDomainFilter"
        :domain-counts="store.domainCounts"
        :total-count="store.totalCount"
        :total-active="store.totalActive"
        :total-inactive="store.totalInactive"
        @update:search-query="store.setSearchQuery"
        @update:active-domain="store.setDomainFilter"
      />

      <!-- Loading -->
      <div v-if="store.loading" class="flex items-center justify-center py-16">
        <div class="text-sm text-slate-400">Chargement du catalogue...</div>
      </div>

      <!-- Error -->
      <div v-else-if="store.error" class="text-center py-16">
        <div class="text-sm text-red-500 mb-2">{{ store.error }}</div>
        <button
          class="text-sm text-teal-600 hover:text-teal-700 font-medium"
          @click="store.fetchAll()"
        >
          Réessayer
        </button>
      </div>

      <!-- Empty state -->
      <div v-else-if="store.domainGroups.length === 0 && !store.loading" class="text-center py-16">
        <BookOpen :size="48" :stroke-width="1.5" class="mx-auto text-slate-300 mb-4" />
        <div class="text-sm text-slate-400">
          {{
            store.searchQuery
              ? 'Aucun service ne correspond à votre recherche'
              : 'Aucun service dans le catalogue'
          }}
        </div>
      </div>

      <!-- Domain sections -->
      <template v-else>
        <CatalogDomainSection
          v-for="domainGroup in store.domainGroups"
          :key="domainGroup.domain"
          :group="domainGroup"
          mode="platform"
          @edit="openEditDrawer"
          @deactivate="handleDeactivate"
          @reactivate="handleReactivate"
        />
      </template>
    </div>

    <!-- Drawer create/edit -->
    <CatalogServiceDrawer
      v-model:visible="drawerVisible"
      :edit-service="editingService"
      @saved="store.fetchAll()"
    />
  </div>
</template>
