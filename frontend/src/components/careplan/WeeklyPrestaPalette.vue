/** * CareLink — WeeklyPrestaPalette * Chemin :
frontend/src/components/careplan/WeeklyPrestaPalette.vue * * Rôle : panneau latéral gauche de la
semaine type (F3). * Affiche les services draft du Bloc 1 groupés par domaine, * chaque carte est
draggable (source de drag = draftIndex). * Badge compteur de placements par service. * Filtre texte
sur nom / code / profession. * Double-clic → emit vers le parent pour ouvrir le popover récurrence.
*/
<template>
  <div class="flex h-full flex-col border-r border-slate-200 bg-white">
    <!-- Header -->
    <div class="border-b border-slate-100 px-3 py-3">
      <h3 class="text-xs font-bold uppercase tracking-wide text-slate-700">
        Prestations du Bloc 1
      </h3>
      <p class="mt-0.5 text-[0.6875rem] text-slate-400">
        Glissez vers la grille · Double-clic = récurrence
      </p>
    </div>

    <!-- Search -->
    <div class="px-3 py-2">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Filtrer les prestations…"
        class="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-700 transition-colors placeholder:text-slate-400 focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400/20"
      />
    </div>

    <!-- Services list -->
    <div class="flex-1 overflow-y-auto px-2 pb-2">
      <!-- Empty state -->
      <div v-if="services.length === 0" class="flex flex-col items-center px-4 py-8 text-center">
        <p class="text-xs text-slate-400">Aucune prestation sélectionnée au Bloc 1</p>
      </div>

      <!-- Grouped by domain -->
      <div v-for="group in filteredGroups" :key="group.domain" class="mb-2">
        <div class="mb-1 flex items-center gap-1.5 px-1 pt-1">
          <span
            :class="['inline-block h-[7px] w-[7px] rounded-full', domainDotClass(group.domain)]"
            aria-hidden="true"
          />
          <span class="text-[0.625rem] font-bold uppercase tracking-wide text-slate-400">
            {{ domainLabel(group.domain) }} ({{ group.items.length }})
          </span>
        </div>

        <div
          v-for="item in group.items"
          :key="item.index"
          class="group mb-1 cursor-grab rounded-lg border border-slate-200 bg-white px-2.5 py-2 transition-all hover:-translate-y-px hover:border-teal-300 hover:shadow-sm active:cursor-grabbing"
          draggable="true"
          @dragstart="onDragStart($event, item.index)"
          @dragend="onDragEnd"
          @dblclick="$emit('dblclickService', item.index)"
        >
          <!-- Row 1: dot + name + badge -->
          <div class="flex items-center gap-1.5">
            <span
              :class="[
                'inline-block h-1.5 w-1.5 shrink-0 rounded-full',
                domainDotClass(group.domain),
              ]"
              aria-hidden="true"
            />
            <span class="flex-1 truncate text-xs font-semibold text-slate-700">
              {{ item.draft._display_service_name }}
            </span>
            <span
              :class="[
                'flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[0.5625rem] font-bold',
                item.placementCount > 0 ? 'bg-teal-500 text-white' : 'bg-slate-200 text-slate-400',
              ]"
            >
              {{ item.placementCount }}
            </span>
          </div>

          <!-- Row 2: meta -->
          <div class="mt-0.5 flex gap-2 text-[0.625rem] text-slate-400">
            <span>{{ item.draft.duration_minutes }} min</span>
            <span v-if="item.draft._display_profession_name">
              · {{ item.draft._display_profession_name }}
            </span>
          </div>
        </div>
      </div>

      <!-- No results after filter -->
      <div
        v-if="filteredGroups.length === 0 && services.length > 0"
        class="px-4 py-6 text-center text-xs text-slate-400"
      >
        Aucune prestation ne correspond.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  import type { CarePlanServiceDraft, WeeklyPlacement } from '@/types';
  import { DOMAIN_LABELS } from '@/types';

  // =========================================================================
  // PROPS & EMITS
  // =========================================================================

  const props = defineProps<{
    services: CarePlanServiceDraft[];
    placements: WeeklyPlacement[];
  }>();

  defineEmits<{
    dblclickService: [draftIndex: number];
  }>();

  // =========================================================================
  // SEARCH
  // =========================================================================

  const searchQuery = ref('');

  // =========================================================================
  // DOMAIN HELPERS
  // =========================================================================

  /** Label du domaine pour l'affichage */
  function domainLabel(domain: string): string {
    return (DOMAIN_LABELS as Record<string, string>)[domain] ?? domain;
  }

  /** Classe Tailwind du dot de domaine */
  function domainDotClass(domain: string): string {
    const map: Record<string, string> = {
      SANTE: 'bg-blue-500',
      AUTONOMIE: 'bg-violet-500',
      PARTICIPATION_SOCIALE: 'bg-orange-500',
    };
    return map[domain] ?? 'bg-slate-400';
  }

  // =========================================================================
  // COMPUTED — items enrichis et groupés
  // =========================================================================

  interface PaletteItem {
    index: number;
    draft: CarePlanServiceDraft;
    placementCount: number;
    searchable: string;
  }

  interface PaletteGroup {
    domain: string;
    items: PaletteItem[];
  }

  /** Items enrichis avec placement count et searchable string */
  const enrichedItems = computed<PaletteItem[]>(() =>
    props.services.map((draft, index) => ({
      index,
      draft,
      placementCount: props.placements.filter((p) => p.draftIndex === index).length,
      searchable: [
        draft._display_service_name,
        draft._display_service_code,
        draft._display_profession_name ?? '',
        draft._display_entity_name ?? '',
      ]
        .join(' ')
        .toLowerCase(),
    })),
  );

  /** Items filtrés par la recherche textuelle puis groupés par domaine */
  const filteredGroups = computed<PaletteGroup[]>(() => {
    const query = searchQuery.value.toLowerCase().trim();
    const filtered = query
      ? enrichedItems.value.filter((item) => item.searchable.includes(query))
      : enrichedItems.value;

    // Groupement par domaine avec ordre stable
    const domainOrder = ['SANTE', 'AUTONOMIE', 'PARTICIPATION_SOCIALE'];
    const groups = new Map<string, PaletteItem[]>();

    filtered.forEach((item) => {
      const domain = item.draft._display_domain ?? 'SANTE';
      if (!groups.has(domain)) groups.set(domain, []);
      groups.get(domain)!.push(item);
    });

    // Tri par domainOrder, puis domaines inconnus à la fin
    return domainOrder
      .filter((d) => groups.has(d))
      .map((d) => ({ domain: d, items: groups.get(d)! }))
      .concat(
        [...groups.entries()]
          .filter(([d]) => !domainOrder.includes(d))
          .map(([d, items]) => ({ domain: d, items })),
      );
  });

  // =========================================================================
  // DRAG
  // =========================================================================

  function onDragStart(event: DragEvent, draftIndex: number): void {
    if (!event.dataTransfer) return;
    event.dataTransfer.setData('application/x-draft-index', String(draftIndex));
    event.dataTransfer.effectAllowed = 'copy';
  }

  function onDragEnd(): void {
    // Cleanup si nécessaire (animation, etc.)
  }
</script>
