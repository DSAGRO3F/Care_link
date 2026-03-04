<template>
  <!--
    CareLink - Navigation hiérarchique pour les évaluations
    À placer dans : frontend/src/components/evaluation/SectionNavigator.vue
  -->
  <div class="section-navigator">
    <!-- Breadcrumb -->
    <div class="nav-breadcrumb">
      <template v-for="(item, index) in breadcrumb" :key="item.key">
        <button
          v-if="index < breadcrumb.length - 1"
          class="breadcrumb-item breadcrumb-link"
          @click="onBreadcrumbClick(item)"
        >
          <i v-if="index === 0" class="pi pi-home mr-1"></i>
          <span>{{ item.label }}</span>
        </button>
        <span v-else class="breadcrumb-item breadcrumb-current">
          {{ item.label }}
        </span>
        <i 
          v-if="index < breadcrumb.length - 1" 
          class="pi pi-chevron-right breadcrumb-separator"
        ></i>
      </template>
    </div>

    <!-- Bouton retour (si pas à la racine) -->
    <div v-if="showBackButton" class="nav-back">
      <Button
        icon="pi pi-arrow-left"
        label="Retour"
        severity="secondary"
        text
        size="small"
        @click="onBack"
      />
    </div>

    <!-- Liste des sections/sous-sections -->
    <div class="nav-sections">
      <!-- Mode: Sections principales -->
      <template v-if="mode === 'sections'">
        <div
          v-for="section in sections"
          :key="section.key"
          class="section-card"
          @click="onSectionClick(section)"
        >
          <div class="section-icon">
            <i :class="section.icon"></i>
          </div>
          <div class="section-info">
            <div class="section-label">{{ section.label }}</div>
            <div v-if="section.childCount" class="section-count">
              {{ section.childCount }} élément{{ section.childCount > 1 ? 's' : '' }}
            </div>
          </div>
          <div class="section-arrow">
            <i :class="section.hasChildren ? 'pi pi-chevron-right' : 'pi pi-eye'"></i>
          </div>
        </div>
      </template>

      <!-- Mode: Sous-sections -->
      <template v-else-if="mode === 'subsections'">
        <div
          v-for="sub in subSections"
          :key="sub.key"
          class="subsection-card"
          @click="onSubSectionClick(sub)"
        >
          <div class="subsection-bullet"></div>
          <div class="subsection-label">{{ sub.label }}</div>
          <div class="subsection-arrow">
            <i class="pi pi-chevron-right"></i>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'

export interface BreadcrumbItem {
  label: string
  key: string | null
  isRoot: boolean
}

export interface SectionItem {
  key: string
  label: string
  icon: string
  hasChildren: boolean
  childCount?: number
}

export interface SubSectionItem {
  key: string
  label: string
  parentKey?: string
}

interface Props {
  breadcrumb: BreadcrumbItem[]
  sections?: SectionItem[]
  subSections?: SubSectionItem[]
  mode: 'sections' | 'subsections'
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'navigate', item: BreadcrumbItem): void
  (e: 'select-section', section: SectionItem): void
  (e: 'select-subsection', subSection: SubSectionItem): void
  (e: 'back'): void
}>()

const showBackButton = computed(() => {
  return props.breadcrumb.length > 1
})

function onBreadcrumbClick(item: BreadcrumbItem) {
  emit('navigate', item)
}

function onSectionClick(section: SectionItem) {
  emit('select-section', section)
}

function onSubSectionClick(subSection: SubSectionItem) {
  emit('select-subsection', subSection)
}

function onBack() {
  emit('back')
}
</script>

<style scoped>
.section-navigator {
  @apply flex flex-col gap-4;
}

/* Breadcrumb */
.nav-breadcrumb {
  @apply flex items-center flex-wrap gap-1 px-2 py-2 bg-slate-50 rounded-lg text-sm;
}

.breadcrumb-item {
  @apply px-2 py-1 rounded;
}

.breadcrumb-link {
  @apply text-primary-600 hover:bg-primary-50 cursor-pointer transition-colors;
  background: none;
  border: none;
  font: inherit;
}

.breadcrumb-current {
  @apply text-slate-700 font-medium;
}

.breadcrumb-separator {
  @apply text-slate-300 text-xs mx-1;
}

/* Bouton retour */
.nav-back {
  @apply -mt-2;
}

/* Sections principales */
.nav-sections {
  @apply flex flex-col gap-2;
}

.section-card {
  @apply flex items-center gap-4 p-4 bg-white border border-slate-200 rounded-xl
         cursor-pointer transition-all hover:border-primary-300 hover:shadow-sm;
}

.section-icon {
  @apply w-10 h-10 rounded-lg bg-primary-50 text-primary-600
         flex items-center justify-center text-lg;
}

.section-info {
  @apply flex-1;
}

.section-label {
  @apply font-medium text-slate-800;
}

.section-count {
  @apply text-xs text-slate-400 mt-0.5;
}

.section-arrow {
  @apply text-slate-300;
}

.section-card:hover .section-arrow {
  @apply text-primary-500;
}

/* Sous-sections */
.subsection-card {
  @apply flex items-center gap-3 px-4 py-3 bg-white border border-slate-100 rounded-lg
         cursor-pointer transition-all hover:border-primary-200 hover:bg-primary-50/30;
}

.subsection-bullet {
  @apply w-2 h-2 rounded-full bg-primary-400;
}

.subsection-label {
  @apply flex-1 text-slate-700;
}

.subsection-arrow {
  @apply text-slate-300 text-sm;
}

.subsection-card:hover .subsection-arrow {
  @apply text-primary-500;
}
</style>