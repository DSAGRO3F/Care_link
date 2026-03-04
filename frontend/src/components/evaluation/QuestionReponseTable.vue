<template>
  <!--
    CareLink - Tableau Question/Réponse réutilisable
    À placer dans : frontend/src/components/evaluation/QuestionReponseTable.vue
  -->
  <div class="qr-table">
    <!-- Titre de section optionnel -->
    <div v-if="title" class="qr-section-header">
      <i v-if="icon" :class="icon" class="mr-2"></i>
      <span class="font-semibold">{{ title }}</span>
    </div>

    <!-- Tableau des Q/R -->
    <div class="qr-content">
      <div 
        v-for="(item, index) in items" 
        :key="index"
        class="qr-row"
        :class="{ 'qr-row-alt': index % 2 === 1 }"
      >
        <div class="qr-question">
          <i v-if="item.icon" :class="item.icon" class="mr-2 text-slate-400"></i>
          {{ item.question }}
        </div>
        <div class="qr-reponse">
          <!-- Slot pour contenu personnalisé -->
          <slot :name="`item-${index}`" :item="item">
            <!-- Affichage par défaut selon le type -->
            <template v-if="item.type === 'tag'">
              <Tag :value="item.reponse" :severity="item.severity || 'info'" />
            </template>
            <template v-else-if="item.type === 'boolean'">
              <i 
                :class="item.reponse ? 'pi pi-check-circle text-green-500' : 'pi pi-times-circle text-red-400'"
              ></i>
              <span class="ml-2">{{ item.reponse ? 'Oui' : 'Non' }}</span>
            </template>
            <template v-else-if="item.type === 'date'">
              <i class="pi pi-calendar mr-2 text-slate-400"></i>
              {{ item.reponse }}
            </template>
            <template v-else-if="item.type === 'list' && Array.isArray(item.reponse)">
              <div class="flex flex-wrap gap-1">
                <Tag 
                  v-for="(val, i) in item.reponse" 
                  :key="i" 
                  :value="val" 
                  severity="secondary"
                  class="text-xs"
                />
              </div>
            </template>
            <template v-else-if="item.type === 'multiline'">
              <div class="whitespace-pre-line">{{ item.reponse }}</div>
            </template>
            <template v-else>
              <!-- Texte simple -->
              <span :class="{ 'text-slate-400 italic': !item.reponse }">
                {{ item.reponse || 'Non renseigné' }}
              </span>
            </template>
          </slot>
        </div>
      </div>
    </div>

    <!-- Message si vide -->
    <div v-if="!items || items.length === 0" class="qr-empty">
      <i class="pi pi-info-circle mr-2"></i>
      {{ emptyMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import Tag from 'primevue/tag'

export interface QRItem {
  question: string
  reponse: string | boolean | string[] | null
  type?: 'text' | 'tag' | 'boolean' | 'date' | 'list' | 'multiline'
  severity?: 'success' | 'info' | 'warning' | 'danger' | 'secondary'
  icon?: string
}

interface Props {
  items: QRItem[]
  title?: string
  icon?: string
  emptyMessage?: string
}

withDefaults(defineProps<Props>(), {
  emptyMessage: 'Aucune information disponible'
})
</script>

<style scoped>
.qr-table {
  @apply rounded-lg overflow-hidden border border-slate-200;
}

.qr-section-header {
  @apply px-4 py-3 bg-slate-50 border-b border-slate-200 text-slate-700 flex items-center;
}

.qr-content {
  @apply divide-y divide-slate-100;
}

.qr-row {
  @apply flex flex-col sm:flex-row;
}

.qr-row-alt {
  @apply bg-slate-50/50;
}

.qr-question {
  @apply px-4 py-3 text-sm text-slate-600 font-medium sm:w-2/5 flex items-start;
}

.qr-reponse {
  @apply px-4 py-3 text-sm text-slate-900 sm:w-3/5 flex items-center flex-wrap;
}

.qr-empty {
  @apply px-4 py-6 text-center text-slate-400 text-sm;
}

/* Responsive */
@media (max-width: 640px) {
  .qr-question {
    @apply pb-1 font-semibold;
  }
  .qr-reponse {
    @apply pt-1 pb-3;
  }
}
</style>
