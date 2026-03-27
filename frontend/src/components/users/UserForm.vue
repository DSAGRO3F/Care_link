<script setup lang="ts">
  /**
   * UserForm.vue — Formulaire user réutilisable (création et édition)
   *
   * 🔄 S5 — Refonte majeure :
   *   - Sélecteur de profession groupé par catégorie (radio-group accordéon)
   *     remplace le dropdown plat (constat #11)
   *   - RPPS conditionnel : visible uniquement si requires_rpps=true (constat #15)
   *   - Prop `professionGroups` remplace `professions` (constat #11)
   *
   * Usage :
   *   <UserForm
   *     v-model="formData"
   *     mode="create"
   *     :profession-groups="professionGroups"
   *   />
   *
   * Destination : src/components/users/UserForm.vue
   */
  import { ref, computed } from 'vue';
  import InputText from 'primevue/inputtext';
  import Password from 'primevue/password';
  import Checkbox from 'primevue/checkbox';
  import Divider from 'primevue/divider';
  import type { ProfessionGroup } from '@/types';

  // ─── Props ───────────────────────────────────────────────────────────────────

  interface FormData {
    first_name: string;
    last_name: string;
    email: string;
    password?: string;
    password_confirm?: string;
    rpps: string;
    profession_id: number | null;
    is_admin: boolean;
  }

  interface Props {
    /** Données du formulaire (v-model) */
    modelValue: FormData;
    /** Mode du formulaire */
    mode: 'create' | 'edit';
    /** 🔄 S5 — Professions groupées par catégorie (remplace professions) */
    professionGroups?: ProfessionGroup[];
    /** Chargement des professions en cours */
    loadingProfessions?: boolean;
    /** Désactiver le formulaire */
    disabled?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    professionGroups: () => [],
    loadingProfessions: false,
    disabled: false,
  });

  const emit = defineEmits<{
    (e: 'update:modelValue', value: FormData): void;
  }>();

  // ─── Computed ────────────────────────────────────────────────────────────────

  const form = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val),
  });

  const passwordMatch = computed(() => {
    if (props.mode !== 'create') return null;
    if (!form.value.password_confirm) return null;
    return form.value.password === form.value.password_confirm;
  });

  /**
   * 🆕 S5 — Détermine si la profession sélectionnée requiert un RPPS.
   * Parcourt tous les groupes pour trouver la profession courante.
   */
  const selectedProfessionRequiresRpps = computed(() => {
    if (!props.modelValue.profession_id) return false;
    for (const group of props.professionGroups) {
      const prof = group.professions.find((p) => p.id === props.modelValue.profession_id);
      if (prof) return prof.requires_rpps;
    }
    return false;
  });

  // ─── Accordéon catégories ────────────────────────────────────────────────────

  /** Catégories dépliées (toutes ouvertes par défaut) */
  const expandedCategories = ref<string[]>(props.professionGroups.map((g) => g.category));

  function toggleCategory(category: string) {
    const idx = expandedCategories.value.indexOf(category);
    if (idx === -1) {
      expandedCategories.value.push(category);
    } else {
      expandedCategories.value.splice(idx, 1);
    }
  }

  function isCategoryExpanded(category: string): boolean {
    return expandedCategories.value.includes(category);
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  function update<K extends keyof FormData>(key: K, value: FormData[K] | undefined) {
    emit('update:modelValue', { ...props.modelValue, [key]: value });
  }

  /**
   * 🆕 S5 — Sélectionne une profession et déplie sa catégorie.
   * Si la nouvelle profession ne requiert pas RPPS, vide le champ RPPS.
   */
  function selectProfession(professionId: number | null) {
    const updates: Partial<FormData> = { profession_id: professionId };

    // Si la profession sélectionnée ne requiert pas RPPS → vider le champ
    if (professionId) {
      for (const group of props.professionGroups) {
        const prof = group.professions.find((p) => p.id === professionId);
        if (prof && !prof.requires_rpps) {
          updates.rpps = '';
          break;
        }
      }
    } else {
      // "Aucune profession" → vider le RPPS
      updates.rpps = '';
    }

    emit('update:modelValue', { ...props.modelValue, ...updates });
  }
</script>

<template>
  <div class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Nom -->
      <div>
        <label class="block text-sm font-medium text-slate-600 mb-2">Nom *</label>
        <InputText
          :modelValue="form.last_name"
          :disabled="disabled"
          placeholder="Dupont"
          class="w-full"
          @update:modelValue="update('last_name', $event)"
        />
      </div>

      <!-- Prénom -->
      <div>
        <label class="block text-sm font-medium text-slate-600 mb-2">Prénom *</label>
        <InputText
          :modelValue="form.first_name"
          :disabled="disabled"
          placeholder="Marie"
          class="w-full"
          @update:modelValue="update('first_name', $event)"
        />
      </div>

      <!-- Email -->
      <div>
        <label class="block text-sm font-medium text-slate-600 mb-2">Email *</label>
        <InputText
          :modelValue="form.email"
          :disabled="disabled"
          type="email"
          placeholder="m.dupont@structure.fr"
          class="w-full"
          @update:modelValue="update('email', $event)"
        />
      </div>

      <!-- Spacer pour alignement grid avant profession (full-width) -->
      <div class="hidden md:block"></div>

      <!-- ═══ Profession — sélecteur groupé par catégorie (🔄 S5) ═══ -->
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-slate-600 mb-3">Profession</label>

        <!-- Loading -->
        <div v-if="loadingProfessions" class="flex items-center gap-2 py-4">
          <i class="pi pi-spin pi-spinner text-blue-500"></i>
          <span class="text-sm text-slate-400">Chargement des professions…</span>
        </div>

        <!-- Sélecteur groupé -->
        <div v-else class="space-y-3">
          <div
            v-for="group in professionGroups"
            :key="group.category"
            class="border border-slate-200 rounded-xl overflow-hidden"
          >
            <!-- En-tête catégorie (accordéon) -->
            <button
              type="button"
              class="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
              @click="toggleCategory(group.category)"
            >
              <span class="text-sm font-semibold text-slate-600">
                {{ group.label }}
              </span>
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-400">{{ group.professions.length }}</span>
                <i
                  :class="isCategoryExpanded(group.category) ? 'pi-chevron-up' : 'pi-chevron-down'"
                  class="pi text-xs text-slate-400 transition-transform duration-200"
                ></i>
              </div>
            </button>

            <!-- Professions de la catégorie -->
            <div
              v-show="isCategoryExpanded(group.category)"
              class="px-4 py-2 grid grid-cols-1 sm:grid-cols-2 gap-1.5"
            >
              <button
                v-for="prof in group.professions"
                :key="prof.id"
                :class="
                  form.profession_id === prof.id
                    ? 'bg-blue-50 border border-blue-300 text-blue-800 font-medium'
                    : 'hover:bg-slate-50 text-slate-700 border border-transparent'
                "
                :disabled="disabled"
                type="button"
                class="flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-all"
                @click="selectProfession(prof.id)"
              >
                <!-- Radio indicator -->
                <div
                  :class="
                    form.profession_id === prof.id
                      ? 'border-blue-500 bg-blue-500'
                      : 'border-slate-300'
                  "
                  class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
                >
                  <div
                    v-if="form.profession_id === prof.id"
                    class="w-1.5 h-1.5 rounded-full bg-white"
                  ></div>
                </div>
                <span>{{ prof.name }}</span>
                <span v-if="prof.code" class="text-xs text-slate-400">({{ prof.code }})</span>
              </button>
            </div>
          </div>

          <!-- Option "Aucune profession" -->
          <button
            :class="
              !form.profession_id
                ? 'bg-slate-100 border-slate-300 font-medium'
                : 'border-slate-200 hover:bg-slate-50 text-slate-500'
            "
            :disabled="disabled"
            type="button"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm transition-all w-full text-left"
            @click="selectProfession(null)"
          >
            <div
              :class="!form.profession_id ? 'border-slate-500 bg-slate-500' : 'border-slate-300'"
              class="w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0"
            >
              <div v-if="!form.profession_id" class="w-1.5 h-1.5 rounded-full bg-white"></div>
            </div>
            <span>Aucune profession spécifique</span>
          </button>
        </div>
      </div>

      <!-- ═══ RPPS — conditionnel (🔄 S5, constat #15) ═══ -->
      <div v-if="selectedProfessionRequiresRpps">
        <label class="block text-sm font-medium text-slate-600 mb-2">
          N° RPPS <span class="text-red-500">*</span>
        </label>
        <InputText
          :modelValue="form.rpps"
          :disabled="disabled"
          placeholder="12345678901"
          class="w-full font-mono"
          maxlength="11"
          @update:modelValue="update('rpps', $event)"
        />
      </div>

      <!-- Spacer si RPPS visible (alignement grid) -->
      <div v-if="selectedProfessionRequiresRpps" class="hidden md:block"></div>

      <!-- Mot de passe (création uniquement) -->
      <template v-if="mode === 'create'">
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-2">Mot de passe *</label>
          <Password
            :modelValue="form.password"
            :feedback="true"
            :inputClass="'w-full'"
            :disabled="disabled"
            placeholder="Minimum 8 caractères"
            class="w-full"
            toggleMask
            @update:modelValue="update('password', $event)"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-600 mb-2"
            >Confirmer le mot de passe *</label
          >
          <Password
            :modelValue="form.password_confirm"
            :feedback="false"
            :inputClass="'w-full'"
            :disabled="disabled"
            placeholder="Retapez le mot de passe"
            class="w-full"
            toggleMask
            @update:modelValue="update('password_confirm', $event)"
          />
          <p v-if="passwordMatch === false" class="text-red-500 text-xs mt-1">
            Les mots de passe ne correspondent pas
          </p>
          <p v-else-if="passwordMatch === true" class="text-emerald-500 text-xs mt-1">
            <i class="pi pi-check text-xs mr-1"></i>Mots de passe identiques
          </p>
        </div>
      </template>
    </div>

    <!-- Option admin -->
    <Divider />
    <div class="flex items-center gap-3">
      <Checkbox
        :modelValue="form.is_admin"
        :binary="true"
        :disabled="disabled"
        inputId="user-form-is-admin"
        @update:modelValue="update('is_admin', $event)"
      />
      <label for="user-form-is-admin" class="text-sm text-slate-600 cursor-pointer">
        Ce professionnel est aussi <strong>administrateur</strong> de la structure
      </label>
    </div>
  </div>
</template>