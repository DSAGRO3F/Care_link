<script setup lang="ts">
  /**
   * EntityTreeNode — Nœud récursif de l'arborescence
   *
   * v6 — Refonte card racine style prototype :
   *   - Thème teal (prototype) au lieu de violet
   *   - Info-grid responsive avec pastilles colorées (adresse, FINESS, SIRET, etc.)
   *   - Badges identité (type, Active, Entité racine)
   *   - Icône pi-sitemap conservée (arborescence)
   *   - Nouvelles props : tenantCode, childCount, totalUsers
   *   - Cards enfants et arborescence inchangés
   *
   * Destination : src/components/entities/EntityTreeNode.vue
   */
  import { computed, ref } from 'vue';
  import {
    ROOT_ENTITY_TYPES,
    EntityTypeShortLabels,
    EntityTypeIcons,
    EntityTypeColors,
    EntityTypePlatformColors,
    type EntityResponse,
  } from '@/types';

  // Récursion : le composant s'importe lui-même
  import EntityTreeNode from './EntityTreeNode.vue';

  // =============================================================================
  // TYPES
  // =============================================================================

  export interface TreeNode extends EntityResponse {
    _children: TreeNode[];
  }

  // =============================================================================
  // PROPS & EMITS
  // =============================================================================

  interface Props {
    node: TreeNode;
    depth?: number;
    dark?: boolean;
    readonly?: boolean;
    selectedId?: number | null;
    expandedIds: Set<number>;
    isLast?: boolean;
    /** Code structure du tenant (affiché dans la grille racine) */
    tenantCode?: string;
    /** Nombre total d'entités rattachées (hors racine) */
    childCount?: number;
    /** Nombre total de professionnels rattachés */
    totalUsers?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    depth: 0,
    dark: false,
    readonly: false,
    selectedId: null,
    isLast: false,
    tenantCode: '',
    childCount: 0,
    totalUsers: 0,
  });

  const emit = defineEmits<{
    select: [entity: EntityResponse];
    create: [parentId: number];
    edit: [entity: EntityResponse];
    delete: [entity: EntityResponse];
    toggle: [id: number];
  }>();

  // =============================================================================
  // COMPUTED
  // =============================================================================

  const isRoot = computed(() => ROOT_ENTITY_TYPES.includes(props.node.entity_type));
  const hasChildren = computed(() => props.node._children.length > 0);
  const isExpanded = computed(() => props.expandedIds.has(props.node.id));
  const isSelected = computed(() => props.selectedId === props.node.id);

  const colors = computed(() =>
    props.dark
      ? EntityTypePlatformColors[props.node.entity_type]
      : EntityTypeColors[props.node.entity_type],
  );

  const patientsCount = computed(() => props.node.patients_count || 0);
  const usersCount = computed(() => props.node.users_count || 0);

  const hovered = ref(false);
  const codeCopied = ref(false);

  // Copie du code structure dans le presse-papier
  async function copyTenantCode() {
    if (!props.tenantCode) return;
    try {
      await navigator.clipboard.writeText(props.tenantCode);
      codeCopied.value = true;
      setTimeout(() => {
        codeCopied.value = false;
      }, 2000);
    } catch {
      // Fallback pour les navigateurs restrictifs
      const el = document.createElement('textarea');
      el.value = props.tenantCode;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      codeCopied.value = true;
      setTimeout(() => {
        codeCopied.value = false;
      }, 2000);
    }
  }

  // Adresse formatée pour la racine
  const formattedAddress = computed(() => {
    const parts: string[] = [];
    if (props.node.address_line1) parts.push(props.node.address_line1);
    const cityPart = [props.node.postal_code, props.node.city].filter(Boolean).join(' ');
    if (cityPart) parts.push(cityPart);
    return parts.join(', ');
  });
</script>

<template>
  <div class="entity-tree-node">
    <!-- ═══════════════════════════════════════════════════════════════
         RACINE — Card hero style prototype (thème teal)
         ═══════════════════════════════════════════════════════════════ -->
    <div
      v-if="isRoot"
      :class="[
        isSelected
          ? dark
            ? 'bg-teal-500/15 ring-1 ring-teal-500/40'
            : 'root-card-selected'
          : dark
            ? 'bg-slate-800 ring-1 ring-slate-700 hover:ring-slate-600'
            : 'root-card',
      ]"
      class="group relative rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden"
      @click="emit('select', node)"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
    >
      <!-- Accent top bar — signature teal du prototype -->
      <div
        :class="dark ? 'bg-teal-500' : 'root-top-bar'"
        class="absolute top-0 left-0 right-0 h-[3px]"
      ></div>

      <!-- ─── HERO SECTION ─── -->
      <div class="p-5 pt-6">
        <div class="flex items-start justify-between">
          <div class="flex items-start gap-4">
            <!-- Icône racine — gradient teal, pi-sitemap conservé -->
            <div class="root-icon flex-shrink-0">
              <i class="pi pi-sitemap text-xl text-white"></i>
            </div>

            <div>
              <!-- Nom de l'entité -->
              <h3
                :class="dark ? 'text-white' : 'text-slate-900'"
                class="text-lg font-bold leading-tight"
              >
                {{ node.name }}
              </h3>

              <!-- Badges -->
              <div class="flex flex-wrap items-center gap-1.5 mt-2">
                <span
                  :class="dark ? 'bg-teal-500/20 text-teal-300' : 'bg-teal-50 text-teal-700'"
                  class="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full"
                >
                  {{ EntityTypeShortLabels[node.entity_type] }}
                </span>
                <span
                  v-if="node.is_active"
                  :class="
                    dark ? 'bg-emerald-500/20 text-emerald-300' : 'bg-emerald-50 text-emerald-700'
                  "
                  class="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full"
                >
                  <span
                    :class="dark ? 'bg-emerald-400' : 'bg-emerald-500'"
                    class="w-[5px] h-[5px] rounded-full"
                  ></span>
                  Active
                </span>
                <span
                  v-if="!node.is_active"
                  class="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-600"
                >
                  Inactive
                </span>
                <span
                  :class="dark ? 'bg-slate-700 text-slate-300' : 'bg-slate-100 text-slate-600'"
                  class="inline-flex items-center text-[11px] font-semibold px-2.5 py-1 rounded-full"
                >
                  Entité racine
                </span>
              </div>
            </div>
          </div>

          <!-- Actions racine (hover) -->
          <div
            v-if="!readonly"
            class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <button
              v-if="hasChildren"
              :class="
                dark
                  ? 'text-slate-400 hover:text-white hover:bg-slate-700'
                  : 'text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100'
              "
              :title="isExpanded ? 'Replier' : 'Déplier'"
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              @click.stop="emit('toggle', node.id)"
            >
              <i :class="isExpanded ? 'pi-chevron-up' : 'pi-chevron-down'" class="pi text-sm"></i>
            </button>
            <button
              :class="
                dark
                  ? 'text-emerald-400/70 hover:text-emerald-300 hover:bg-emerald-500/20'
                  : 'text-emerald-500/70 hover:text-emerald-600 hover:bg-emerald-50'
              "
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              title="Ajouter une entité membre"
              @click.stop="emit('create', node.id)"
            >
              <i class="pi pi-plus text-sm"></i>
            </button>
            <button
              :class="
                dark
                  ? 'text-amber-400/60 hover:text-amber-300 hover:bg-amber-500/20'
                  : 'text-amber-500/60 hover:text-amber-600 hover:bg-amber-50'
              "
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              title="Modifier"
              @click.stop="emit('edit', node)"
            >
              <i class="pi pi-pencil text-xs"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- ─── INFO GRID — Grille d'informations style prototype ─── -->
      <div :class="dark ? 'border-slate-700' : 'border-slate-100'" class="info-grid border-t">
        <!-- 1. Code structure (avec bouton copier) -->
        <div class="info-item">
          <div :class="dark ? 'bg-amber-500/15' : 'bg-amber-50'" class="info-icon">
            <i :class="dark ? 'text-amber-400' : 'text-amber-600'" class="pi pi-key"></i>
          </div>
          <div class="min-w-0 flex-1">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              Code structure
            </div>
            <div class="flex items-center gap-2">
              <span
                :class="dark ? 'text-amber-300' : 'text-amber-700'"
                class="info-value font-mono font-bold truncate"
              >
                {{ tenantCode || '—' }}
              </span>
              <button
                v-if="tenantCode"
                :class="
                  codeCopied
                    ? dark
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-emerald-100 text-emerald-600'
                    : dark
                      ? 'text-slate-500 hover:text-amber-400 hover:bg-amber-500/10'
                      : 'text-slate-400 hover:text-amber-600 hover:bg-amber-50'
                "
                :title="codeCopied ? 'Copié !' : 'Copier le code'"
                class="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center transition-all duration-200"
                @click.stop="copyTenantCode"
              >
                <i :class="codeCopied ? 'pi-check' : 'pi-copy'" class="pi text-xs"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- 2. Adresse -->
        <div class="info-item">
          <div :class="dark ? 'bg-blue-500/15' : 'bg-blue-50'" class="info-icon">
            <i :class="dark ? 'text-blue-400' : 'text-blue-600'" class="pi pi-map-marker"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              Adresse
            </div>
            <div :class="dark ? 'text-slate-200' : 'text-slate-700'" class="info-value truncate">
              {{ formattedAddress || '—' }}
            </div>
          </div>
        </div>

        <!-- 3. FINESS géo -->
        <div class="info-item">
          <div :class="dark ? 'bg-teal-500/15' : 'bg-teal-50'" class="info-icon">
            <i :class="dark ? 'text-teal-400' : 'text-teal-600'" class="pi pi-id-card"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              FINESS géo.
            </div>
            <div
              :class="dark ? 'text-slate-200' : 'text-slate-700'"
              class="info-value font-mono truncate"
            >
              {{ node.finess_geo || '—' }}
            </div>
          </div>
        </div>

        <!-- 4. Téléphone -->
        <div class="info-item">
          <div :class="dark ? 'bg-slate-700' : 'bg-slate-100'" class="info-icon">
            <i :class="dark ? 'text-slate-400' : 'text-slate-500'" class="pi pi-phone"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              Téléphone
            </div>
            <div :class="dark ? 'text-slate-200' : 'text-slate-700'" class="info-value truncate">
              {{ node.phone || '—' }}
            </div>
          </div>
        </div>

        <!-- 5. SIRET -->
        <div class="info-item">
          <div :class="dark ? 'bg-violet-500/15' : 'bg-violet-50'" class="info-icon">
            <i :class="dark ? 'text-violet-400' : 'text-violet-600'" class="pi pi-building"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">SIRET</div>
            <div
              :class="dark ? 'text-slate-200' : 'text-slate-700'"
              class="info-value font-mono truncate"
            >
              {{ node.siret || '—' }}
            </div>
          </div>
        </div>

        <!-- 6. Email -->
        <div class="info-item">
          <div :class="dark ? 'bg-blue-500/15' : 'bg-blue-50'" class="info-icon">
            <i :class="dark ? 'text-blue-400' : 'text-blue-600'" class="pi pi-envelope"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">Email</div>
            <div :class="dark ? 'text-slate-200' : 'text-slate-700'" class="info-value truncate">
              {{ node.email || '—' }}
            </div>
          </div>
        </div>

        <!-- 7. Entités rattachées -->
        <div class="info-item">
          <div :class="dark ? 'bg-sky-500/15' : 'bg-sky-50'" class="info-icon">
            <i :class="dark ? 'text-sky-400' : 'text-sky-600'" class="pi pi-sitemap"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              Entités rattachées
            </div>
            <div
              :class="dark ? 'text-slate-200' : 'text-slate-700'"
              class="info-value font-semibold"
            >
              {{ childCount }}
            </div>
          </div>
        </div>

        <!-- 8. Professionnels rattachés -->
        <div class="info-item">
          <div :class="dark ? 'bg-indigo-500/15' : 'bg-indigo-50'" class="info-icon">
            <i :class="dark ? 'text-indigo-400' : 'text-indigo-600'" class="pi pi-users"></i>
          </div>
          <div class="min-w-0">
            <div :class="dark ? 'text-slate-500' : 'text-slate-400'" class="info-label">
              Professionnels
            </div>
            <div
              :class="dark ? 'text-slate-200' : 'text-slate-700'"
              class="info-value font-semibold"
            >
              {{ totalUsers }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
         ENFANT — Carte standard avec connecteurs visuels
         ═══════════════════════════════════════════════════════════════ -->
    <div v-else class="flex">
      <!-- Zone connecteur avec courbes fluides -->
      <div class="relative flex-shrink-0" style="width: 56px">
        <!-- Segment vertical : du haut → début de la courbe -->
        <div
          :class="dark ? 'bg-slate-600' : 'tree-connector-line'"
          :style="{ height: 'calc(50% - 16px)' }"
          class="absolute left-0 top-0 w-[2px]"
        ></div>

        <!-- Courbe fluide (quart de cercle reliant vertical → horizontal) -->
        <div
          :class="dark ? 'border-slate-600' : 'tree-connector-curve'"
          class="absolute left-0 rounded-bl-[16px] tree-curve-piece"
          style="top: calc(50% - 16px); width: 16px; height: 16px"
        ></div>

        <!-- Segment horizontal : de la fin de la courbe → bord de la carte -->
        <div
          :class="dark ? 'bg-slate-600' : 'tree-connector-line'"
          class="absolute h-[2px] right-0"
          style="top: 50%; left: 16px; transform: translateY(-1px)"
        ></div>

        <!-- Continuation verticale (si pas dernier frère) -->
        <div
          v-if="!isLast"
          :class="dark ? 'bg-slate-600' : 'tree-connector-line'"
          class="absolute left-0 w-[2px] bottom-0"
          style="top: 50%"
        ></div>
      </div>

      <!-- Carte enfant -->
      <div
        :class="[
          isSelected
            ? dark
              ? 'bg-violet-500/15 border-violet-500/40'
              : 'bg-violet-50/60 border-violet-300 shadow-sm shadow-violet-100'
            : dark
              ? 'bg-slate-800 border-slate-700 hover:border-slate-600'
              : 'bg-white border-zinc-200 shadow-sm hover:border-violet-200 hover:shadow-md',
        ]"
        class="group flex-1 rounded-xl p-4 my-2 transition-all duration-200 border cursor-pointer"
        @click="emit('select', node)"
        @mouseenter="hovered = true"
        @mouseleave="hovered = false"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-start gap-3">
            <div
              :class="[colors.bg, colors.border]"
              class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 border"
            >
              <i :class="EntityTypeIcons[node.entity_type]" class="text-base"></i>
            </div>

            <div>
              <div class="flex items-center gap-2 mb-0.5">
                <span
                  :class="[colors.bg, colors.text, colors.border]"
                  class="text-xs font-semibold px-2 py-0.5 rounded-full border"
                >
                  {{ EntityTypeShortLabels[node.entity_type] }}
                </span>
                <span
                  v-if="!node.is_active"
                  class="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 border border-red-200"
                >
                  Inactif
                </span>
              </div>

              <h4 :class="dark ? 'text-white' : 'text-zinc-800'" class="font-semibold">
                {{ node.name }}
              </h4>

              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
                <span
                  v-if="node.city"
                  :class="dark ? 'text-slate-400' : 'text-zinc-500'"
                  class="text-xs flex items-center gap-1"
                >
                  <i class="pi pi-map-marker" style="font-size: 0.65rem"></i>
                  {{ node.postal_code ? node.postal_code + ' ' : '' }}{{ node.city }}
                </span>
                <span
                  v-if="node.finess_geo"
                  :class="dark ? 'text-slate-600' : 'text-zinc-300'"
                  class="text-xs font-mono"
                >
                  ET {{ node.finess_geo }}
                </span>
                <span
                  v-if="node.siret"
                  :class="dark ? 'text-slate-600' : 'text-zinc-300'"
                  class="text-xs font-mono"
                >
                  SIRET {{ node.siret }}
                </span>
              </div>

              <!-- Stats enfant -->
              <div
                v-if="patientsCount > 0 || usersCount > 0"
                class="flex items-center gap-3 mt-1.5"
              >
                <span
                  v-if="patientsCount > 0"
                  :class="
                    dark ? 'bg-emerald-500/15 text-emerald-400' : 'bg-emerald-50 text-emerald-600'
                  "
                  class="text-[11px] px-2 py-0.5 rounded-md"
                >
                  {{ patientsCount }} patients
                </span>
                <span
                  v-if="usersCount > 0"
                  :class="dark ? 'bg-sky-500/15 text-sky-400' : 'bg-sky-50 text-sky-600'"
                  class="text-[11px] px-2 py-0.5 rounded-md"
                >
                  {{ usersCount }} pros
                </span>
              </div>
            </div>
          </div>

          <!-- Actions enfant (hover) -->
          <div
            v-if="!readonly"
            class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <button
              v-if="hasChildren"
              :class="
                dark
                  ? 'text-slate-400 hover:text-white hover:bg-slate-700'
                  : 'text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100'
              "
              :title="isExpanded ? 'Replier' : 'Déplier'"
              class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
              @click.stop="emit('toggle', node.id)"
            >
              <i :class="isExpanded ? 'pi-chevron-up' : 'pi-chevron-down'" class="pi text-xs"></i>
            </button>
            <button
              :class="
                dark
                  ? 'text-emerald-400/60 hover:text-emerald-300 hover:bg-emerald-500/20'
                  : 'text-emerald-500/60 hover:text-emerald-600 hover:bg-emerald-50'
              "
              class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
              title="Ajouter une sous-entité"
              @click.stop="emit('create', node.id)"
            >
              <i class="pi pi-plus text-xs"></i>
            </button>
            <button
              :class="
                dark
                  ? 'text-amber-400/60 hover:text-amber-300 hover:bg-amber-500/20'
                  : 'text-amber-500/60 hover:text-amber-600 hover:bg-amber-50'
              "
              class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
              title="Modifier"
              @click.stop="emit('edit', node)"
            >
              <i class="pi pi-pencil text-xs"></i>
            </button>
            <button
              v-if="!isRoot"
              :class="
                dark
                  ? 'text-red-400/60 hover:text-red-300 hover:bg-red-500/20'
                  : 'text-red-500/60 hover:text-red-600 hover:bg-red-50'
              "
              class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
              title="Supprimer"
              @click.stop="emit('delete', node)"
            >
              <i class="pi pi-trash text-xs"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
         ENFANTS — Conteneur récursif avec connecteur vertical
         ═══════════════════════════════════════════════════════════════ -->
    <Transition name="tree-expand">
      <div
        v-if="isExpanded && hasChildren"
        :class="isRoot ? 'ml-16' : 'ml-[56px]'"
        class="relative"
      >
        <!-- Continuation de la ligne verticale du parent (quand pas dernier frère) -->
        <div
          v-if="!isRoot && !isLast"
          :class="dark ? 'bg-slate-600' : 'tree-connector-line'"
          class="absolute top-0 bottom-0 w-[2px]"
          style="left: -56px"
        ></div>

        <!-- Nœuds enfants récursifs (chaque enfant dessine son propre segment vertical) -->
        <EntityTreeNode
          v-for="(child, index) in node._children"
          :key="child.id"
          :node="child"
          :depth="depth + 1"
          :dark="dark"
          :readonly="readonly"
          :selected-id="selectedId"
          :expanded-ids="expandedIds"
          :is-last="index === node._children.length - 1"
          :tenant-code="tenantCode"
          :child-count="childCount"
          :total-users="totalUsers"
          @select="(e) => emit('select', e)"
          @create="(pid) => emit('create', pid)"
          @edit="(e) => emit('edit', e)"
          @delete="(e) => emit('delete', e)"
          @toggle="(id) => emit('toggle', id)"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
  /* ═══════════════════════════════════════════════════════
   CARTE RACINE — Traitement premium teal (style prototype)
   ═══════════════════════════════════════════════════════ */

  /* État normal */
  .root-card {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.03) 0%, rgba(255, 255, 255, 1) 60%);
    border: 1.5px solid rgba(20, 184, 166, 0.2);
    box-shadow:
      0 1px 3px rgba(20, 184, 166, 0.06),
      0 4px 12px rgba(20, 184, 166, 0.03);
  }
  .root-card:hover {
    border-color: rgba(20, 184, 166, 0.35);
    box-shadow:
      0 2px 8px rgba(20, 184, 166, 0.1),
      0 8px 24px rgba(20, 184, 166, 0.05);
  }

  /* État sélectionné */
  .root-card-selected {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.06) 0%, rgba(255, 255, 255, 1) 60%);
    border: 1.5px solid rgba(20, 184, 166, 0.4);
    box-shadow:
      0 0 0 3px rgba(20, 184, 166, 0.08),
      0 2px 8px rgba(20, 184, 166, 0.1);
  }

  /* Accent top bar gradient */
  .root-top-bar {
    background: linear-gradient(90deg, #14b8a6, #0d9488);
  }

  /* Icône racine — gradient teal avec ombre */
  .root-icon {
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #14b8a6, #0d9488);
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.25);
    flex-shrink: 0;
  }

  /* ═══════════════════════════════════════════════════════
   INFO GRID — Grille responsive style prototype
   ═══════════════════════════════════════════════════════ */

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    padding: 1.25rem 1.5rem;
  }

  .info-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .info-icon {
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 0.625rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8125rem;
    flex-shrink: 0;
  }

  .info-label {
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1.2;
  }

  .info-value {
    font-size: 0.8125rem;
    font-weight: 500;
    line-height: 1.3;
  }

  /* ═══════════════════════════════════════════════════════
   CONNECTEURS ARBORESCENCE — Courbes fluides
   ═══════════════════════════════════════════════════════ */

  .tree-connector-line {
    background: rgba(20, 184, 166, 0.35);
  }

  .tree-connector-curve {
    border-color: rgba(20, 184, 166, 0.35);
  }

  .tree-curve-piece {
    border-left-width: 2px;
    border-left-style: solid;
    border-bottom-width: 2px;
    border-bottom-style: solid;
    border-top: none;
    border-right: none;
  }

  /* ═══════════════════════════════════════════════════════
   TRANSITIONS
   ═══════════════════════════════════════════════════════ */

  .tree-expand-enter-active,
  .tree-expand-leave-active {
    transition: all 0.25s ease;
    overflow: hidden;
  }

  .tree-expand-enter-from,
  .tree-expand-leave-to {
    opacity: 0;
    transform: translateY(-6px);
  }

  /* ═══════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════ */

  @media (max-width: 640px) {
    .info-grid {
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      padding: 1rem;
    }
  }
</style>
