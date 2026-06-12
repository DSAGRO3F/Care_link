/** * CareLink — CoordinationPrestationCard * Chemin :
frontend/src/components/catalog/CoordinationPrestationCard.vue * * Rôle : card accordéon d'une
prestation consolidée. Affiche le header * (code, nom, tags, badge entités, chevron animé) et le
body expansible * (liste d'offres entités via CoordinationEntityOffer + compare strip). * Transition
CSS max-height (même pattern que l'accordéon Phase 2). */
<template>
  <div
    :class="[
      'group overflow-hidden rounded-lg border bg-white transition-all',
      expanded
        ? 'border-slate-300 shadow-md'
        : 'border-slate-200 hover:border-slate-300 hover:shadow-md',
    ]"
  >
    <!-- ===== HEADER (cliquable) ===== -->
    <div
      :class="[
        'flex cursor-pointer select-none items-center gap-3 px-4 py-3.5 transition-colors',
        expanded ? 'border-b border-teal-100 bg-teal-50' : 'hover:bg-slate-50',
      ]"
      @click="expanded = !expanded"
    >
      <!-- Category icon -->
      <div
        :class="[
          domainColors.icon,
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm',
        ]"
      >
        {{ categoryIcon }}
      </div>

      <!-- Info: code + name + meta -->
      <div class="min-w-0 flex-1">
        <div class="flex items-baseline gap-2">
          <span
            class="shrink-0 rounded bg-teal-50 px-1.5 py-0.5 font-mono text-[0.6875rem] font-semibold tracking-wide text-teal-600"
          >
            {{ prestation.code }}
          </span>
          <span class="truncate text-[0.9375rem] font-bold text-slate-800">
            {{ prestation.name }}
          </span>
        </div>
        <div class="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-400">
          <span v-if="prestation.required_profession_name">
            {{ prestation.required_profession_name }}
          </span>
          <span v-if="prestation.default_duration_minutes">
            {{ prestation.default_duration_minutes }} min (réf.)
          </span>
          <span
            v-if="prestation.requires_prescription"
            class="rounded-full bg-blue-50 px-1.5 py-0.5 text-[0.625rem] font-semibold text-blue-600"
          >
            Ordonnance
          </span>
          <span
            v-if="prestation.is_medical_act"
            class="rounded-full bg-rose-50 px-1.5 py-0.5 text-[0.625rem] font-semibold text-rose-600"
          >
            Acte médical
          </span>
          <span
            v-if="prestation.apa_eligible"
            class="rounded-full bg-amber-50 px-1.5 py-0.5 text-[0.625rem] font-semibold text-amber-600"
          >
            APA
          </span>
        </div>
      </div>

      <!-- Availability badge -->
      <div class="flex shrink-0 items-center gap-1.5">
        <span
          v-if="prestation.offer_count > 0"
          class="rounded-full bg-emerald-50 px-2 py-0.5 text-[0.6875rem] font-semibold text-emerald-600"
        >
          {{ prestation.offer_count }} entité{{ prestation.offer_count > 1 ? 's' : '' }}
        </span>
        <span
          v-else
          class="rounded-full bg-slate-100 px-2 py-0.5 text-[0.6875rem] font-semibold text-slate-400"
        >
          Aucune offre
        </span>
      </div>

      <!-- Chevron -->
      <component
        :is="ChevronDownIcon"
        :class="[
          'h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200',
          expanded ? 'rotate-180 text-teal-600' : '',
        ]"
      />
    </div>

    <!-- ===== BODY (expandable) ===== -->
    <div
      :class="[
        'overflow-hidden transition-[max-height] duration-300 ease-in-out',
        expanded ? 'max-h-[800px]' : 'max-h-0',
      ]"
    >
      <!-- Entity offers -->
      <CoordinationEntityOffer
        v-for="offer in prestation.offers"
        :key="offer.entity_id"
        :offer="offer"
        :is-best-tarif="isBestTarifForEntity(offer.entity_name)"
        @select="$emit('select', $event)"
      />

      <!-- Compare strip -->
      <div
        v-if="prestation.best_tarif && prestation.offer_count > 1"
        class="flex items-center gap-2 border-t border-slate-200 bg-slate-50 px-5 py-2 text-xs text-slate-500"
      >
        <span>💡</span>
        <span class="font-bold text-teal-600">
          Meilleur tarif : {{ prestation.best_tarif.entity_name }} ({{
            prestation.best_tarif.value.toFixed(2)
          }}
          €)
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  import { ChevronDown as ChevronDownIcon } from 'lucide-vue-next';

  import CoordinationEntityOffer from './CoordinationEntityOffer.vue';
  import type { ConsolidatedEntityOffer, ConsolidatedPrestation } from '@/types';
  import { CATEGORY_ICONS, DOMAIN_COLORS } from '@/types';

  const props = defineProps<{
    prestation: ConsolidatedPrestation;
  }>();

  defineEmits<{
    select: [offer: ConsolidatedEntityOffer];
  }>();

  /** État accordéon */
  const expanded = ref(false);

  /** Icône catégorie (emoji) */
  const categoryIcon = computed(() => {
    return CATEGORY_ICONS[props.prestation.category] ?? '📋';
  });

  /** Couleurs du domaine pour l'icône */
  const domainColors = computed(() => {
    return (
      DOMAIN_COLORS[props.prestation.domain] ?? {
        bg: 'bg-slate-50',
        text: 'text-slate-600',
        icon: 'bg-slate-50 text-slate-600',
        border: 'border-slate-200',
      }
    );
  });

  /** Vérifie si une entité est celle du meilleur tarif */
  function isBestTarifForEntity(entityName: string): boolean {
    return props.prestation.best_tarif?.entity_name === entityName;
  }
</script>
