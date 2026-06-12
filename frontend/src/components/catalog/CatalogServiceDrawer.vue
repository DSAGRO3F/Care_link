<script setup lang="ts">
  /**
   * CatalogServiceDrawer — Panneau latéral pour créer / modifier un service.
   *
   * Utilise la transition CSS slide-panel de main.css.
   * Convention #69 : pas de ConfirmDialog ici (pas d'action irréversible).
   *
   * Champs : code, nom, domaine, catégorie (filtré par domaine),
   * description, durée, profession, toggles (ordonnance, acte médical, APA).
   */

  import { computed, ref, watch } from 'vue';

  import { Check, X } from 'lucide-vue-next';
  import { useToast } from 'primevue/usetoast';

  import type {
    ServiceCategory,
    ServiceDomain,
    ServiceTemplateCreate,
    ServiceTemplateSummary,
    ServiceTemplateUpdate,
  } from '@/types';
  import { CATEGORY_LABELS, DOMAIN_CATEGORY_MAP, DOMAIN_LABELS, DOMAIN_ORDER } from '@/types';
  import { useCatalogStore } from '@/stores';

  const props = defineProps<{
    visible: boolean;
    editService?: ServiceTemplateSummary | null;
  }>();

  const emit = defineEmits<{
    'update:visible': [value: boolean];
    saved: [];
  }>();

  const toast = useToast();
  const store = useCatalogStore();
  const saving = ref(false);

  const isEdit = computed(() => !!props.editService);
  const title = computed(() => (isEdit.value ? 'Modifier le service' : 'Nouveau service'));

  // =========================================================================
  // FORM STATE
  // =========================================================================

  const form = ref({
    code: '',
    name: '',
    domain: '' as ServiceDomain | '',
    category: '' as ServiceCategory | '',
    description: '',
    default_duration_minutes: 30,
    required_profession_id: null as number | null,
    requires_prescription: false,
    is_medical_act: false,
    apa_eligible: true,
  });

  /** Catégories filtrées par domaine sélectionné */
  const availableCategories = computed(() => {
    if (!form.value.domain) return [];
    return DOMAIN_CATEGORY_MAP[form.value.domain as ServiceDomain] || [];
  });

  /** Reset catégorie si le domaine change et que la catégorie n'est plus valide */
  watch(
    () => form.value.domain,
    (newDomain) => {
      if (newDomain) {
        const validCats = DOMAIN_CATEGORY_MAP[newDomain as ServiceDomain] || [];
        if (!validCats.includes(form.value.category as ServiceCategory)) {
          form.value.category = '';
        }
      }
    },
  );

  /** Préremplir le formulaire quand on passe en mode édition */
  watch(
    () => props.editService,
    (service) => {
      if (service) {
        form.value = {
          code: service.code,
          name: service.name,
          domain: service.domain,
          category: service.category,
          description: '',
          default_duration_minutes: service.default_duration_minutes,
          required_profession_id: null,
          requires_prescription: service.requires_prescription,
          is_medical_act: service.is_medical_act,
          apa_eligible: service.apa_eligible,
        };
      } else {
        resetForm();
      }
    },
  );

  function resetForm(): void {
    form.value = {
      code: '',
      name: '',
      domain: '',
      category: '',
      description: '',
      default_duration_minutes: 30,
      required_profession_id: null,
      requires_prescription: false,
      is_medical_act: false,
      apa_eligible: true,
    };
  }

  function close(): void {
    emit('update:visible', false);
    resetForm();
  }

  // =========================================================================
  // VALIDATION
  // =========================================================================

  const canSubmit = computed(() => {
    return (
      form.value.code.trim().length > 0 &&
      form.value.name.trim().length > 0 &&
      form.value.domain !== '' &&
      form.value.category !== '' &&
      form.value.default_duration_minutes >= 5 &&
      !saving.value
    );
  });

  // =========================================================================
  // SUBMIT
  // =========================================================================

  async function handleSubmit(): Promise<void> {
    if (!canSubmit.value) return;

    saving.value = true;
    try {
      if (isEdit.value && props.editService) {
        const payload: ServiceTemplateUpdate = {
          name: form.value.name,
          domain: form.value.domain as ServiceDomain,
          category: form.value.category as ServiceCategory,
          description: form.value.description || undefined,
          default_duration_minutes: form.value.default_duration_minutes,
          requires_prescription: form.value.requires_prescription,
          is_medical_act: form.value.is_medical_act,
          apa_eligible: form.value.apa_eligible,
        };
        await store.updateTemplate(props.editService.id, payload);
        toast.add({
          severity: 'success',
          summary: 'Service modifié',
          detail: `${form.value.name} a été mis à jour.`,
          life: 3000,
        });
      } else {
        const payload: ServiceTemplateCreate = {
          code: form.value.code.trim().toUpperCase().replace(/\s+/g, '_'),
          name: form.value.name.trim(),
          domain: form.value.domain as ServiceDomain,
          category: form.value.category as ServiceCategory,
          description: form.value.description || undefined,
          default_duration_minutes: form.value.default_duration_minutes,
          requires_prescription: form.value.requires_prescription,
          is_medical_act: form.value.is_medical_act,
          apa_eligible: form.value.apa_eligible,
        };
        await store.createTemplate(payload);
        toast.add({
          severity: 'success',
          summary: 'Service créé',
          detail: `${form.value.name} a été ajouté au catalogue.`,
          life: 3000,
        });
      }

      emit('saved');
      close();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erreur lors de la sauvegarde';
      toast.add({ severity: 'error', summary: 'Erreur', detail: message, life: 5000 });
    } finally {
      saving.value = false;
    }
  }
</script>

<template>
  <!-- Overlay -->
  <Transition name="slide-panel">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex justify-end"
      @click.self="close"
    >
      <!-- Drawer -->
      <div class="w-[520px] max-w-[90vw] h-full bg-white shadow-2xl flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <span class="text-lg font-bold text-slate-800">{{ title }}</span>
          <button
            class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
            @click="close"
          >
            <X :size="18" :stroke-width="2" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <!-- Code -->
          <div class="form-group">
            <label class="form-label form-label--required">Code unique</label>
            <input
              v-model="form.code"
              :disabled="isEdit"
              type="text"
              class="p-inputtext w-full font-mono tracking-wide"
              placeholder="ex : TOILETTE_COMPLETE"
            />
            <div class="text-xs text-slate-400 mt-1">
              Identifiant unique en majuscules, sans espaces
            </div>
          </div>

          <!-- Nom -->
          <div class="form-group">
            <label class="form-label form-label--required">Nom du service</label>
            <input
              v-model="form.name"
              type="text"
              class="p-inputtext w-full"
              placeholder="ex : Toilette complète"
            />
          </div>

          <!-- Domaine + Catégorie -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-group">
              <label class="form-label form-label--required">Domaine</label>
              <select v-model="form.domain" class="p-inputtext w-full">
                <option value="">Sélectionner...</option>
                <option v-for="d in DOMAIN_ORDER" :key="d" :value="d">
                  {{ DOMAIN_LABELS[d] }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label form-label--required">Catégorie</label>
              <select v-model="form.category" :disabled="!form.domain" class="p-inputtext w-full">
                <option value="">Sélectionner...</option>
                <option v-for="c in availableCategories" :key="c" :value="c">
                  {{ CATEGORY_LABELS[c] }}
                </option>
              </select>
            </div>
          </div>

          <!-- Description -->
          <div class="form-group">
            <label class="form-label">Description</label>
            <textarea
              v-model="form.description"
              class="p-inputtext w-full min-h-[4rem] resize-y"
              placeholder="Description détaillée du service..."
            />
          </div>

          <!-- Durée -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-group">
              <label class="form-label form-label--required">Durée standard (min)</label>
              <input
                v-model.number="form.default_duration_minutes"
                type="number"
                class="p-inputtext w-full"
                min="5"
                max="480"
                placeholder="30"
              />
            </div>
          </div>

          <!-- Toggles -->
          <div class="mt-4">
            <label class="form-label mb-3">Caractéristiques</label>

            <div class="flex items-center justify-between py-2.5 border-b border-slate-100">
              <div>
                <div class="text-sm text-slate-600">Nécessite une ordonnance</div>
                <div class="text-xs text-slate-400 mt-0.5">
                  Ce service requiert une prescription médicale préalable
                </div>
              </div>
              <label class="relative inline-block w-10 h-[1.375rem] cursor-pointer">
                <input v-model="form.requires_prescription" type="checkbox" class="sr-only peer" />
                <span
                  class="absolute inset-0 rounded-full bg-slate-200 peer-checked:bg-teal-500 transition-colors"
                />
                <span
                  class="absolute top-[3px] left-[3px] w-4 h-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-[1.125rem]"
                />
              </label>
            </div>

            <div class="flex items-center justify-between py-2.5 border-b border-slate-100">
              <div>
                <div class="text-sm text-slate-600">Acte médical / paramédical</div>
                <div class="text-xs text-slate-400 mt-0.5">
                  Acte relevant de la compétence exclusive d'un professionnel de santé
                </div>
              </div>
              <label class="relative inline-block w-10 h-[1.375rem] cursor-pointer">
                <input v-model="form.is_medical_act" type="checkbox" class="sr-only peer" />
                <span
                  class="absolute inset-0 rounded-full bg-slate-200 peer-checked:bg-teal-500 transition-colors"
                />
                <span
                  class="absolute top-[3px] left-[3px] w-4 h-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-[1.125rem]"
                />
              </label>
            </div>

            <div class="flex items-center justify-between py-2.5">
              <div>
                <div class="text-sm text-slate-600">Éligible APA</div>
                <div class="text-xs text-slate-400 mt-0.5">
                  Facturable au titre de l'Allocation Personnalisée d'Autonomie
                </div>
              </div>
              <label class="relative inline-block w-10 h-[1.375rem] cursor-pointer">
                <input v-model="form.apa_eligible" type="checkbox" class="sr-only peer" />
                <span
                  class="absolute inset-0 rounded-full bg-slate-200 peer-checked:bg-teal-500 transition-colors"
                />
                <span
                  class="absolute top-[3px] left-[3px] w-4 h-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-[1.125rem]"
                />
              </label>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex gap-2 justify-end px-6 py-4 border-t border-slate-100">
          <button
            class="px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-600 bg-white hover:bg-slate-50 transition"
            @click="close"
          >
            Annuler
          </button>
          <button
            :disabled="!canSubmit"
            class="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-teal-500 hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition inline-flex items-center gap-2"
            @click="handleSubmit"
          >
            <Check :size="14" :stroke-width="2" />
            {{ isEdit ? 'Enregistrer' : 'Créer le service' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>
