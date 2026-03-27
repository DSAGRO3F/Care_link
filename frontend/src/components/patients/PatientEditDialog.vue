<script setup lang="ts">
  /**
   * PatientEditDialog.vue — Panel latéral d'édition patient
   *
   * Pattern SlidePanel identique à StructureOverview.vue :
   *   - Overlay fixe + panel glissant depuis la droite
   *   - Formulaire scrollable (pas de wizard)
   *   - 3 fieldsets : Identité, Coordonnées, Rattachement
   *
   * 🆕 20/03/2026 — Création
   *
   * Destination : src/components/patients/PatientEditDialog.vue
   */
  import { ref, watch, computed } from 'vue';
  import { useToast } from 'primevue/usetoast';

  // PrimeVue
  import InputText from 'primevue/inputtext';
  import DatePicker from 'primevue/datepicker';
  import Button from 'primevue/button';
  import Divider from 'primevue/divider';

  // Lucide
  import { X, Pencil, IdCard, MapPin, Building2, Lock, Info } from 'lucide-vue-next';

  // Components
  import EntitySelector from '@/components/entities/EntitySelector.vue';

  // Store & types
  import { usePatientStore } from '@/stores';
  import type { PatientResponse, PatientUpdate } from '@/types';

  // =============================================================================
  // PROPS & EMITS
  // =============================================================================

  interface Props {
    visible: boolean;
    patient: PatientResponse | null;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    'update:visible': [value: boolean];
    saved: [patient: PatientResponse];
  }>();

  const toast = useToast();
  const patientStore = usePatientStore();

  // =============================================================================
  // STATE
  // =============================================================================

  const form = ref({
    first_name: '',
    last_name: '',
    birth_date: '',
    nir: '',
    ins: '',
    addressLine: '',
    addressPostalCode: '',
    addressCity: '',
    phone: '',
    email: '',
    entity_id: 0,
  });

  const birthDateValue = ref<Date | null>(null);
  const isSaving = ref(false);
  const validationErrors = ref<Record<string, string>>({});

  // =============================================================================
  // COMPUTED
  // =============================================================================

  const fullName = computed(() => {
    if (!props.patient) return '';
    return [props.patient.last_name, props.patient.first_name].filter(Boolean).join(' ');
  });

  const hasChanges = computed(() => {
    if (!props.patient) return false;
    const p = props.patient;
    const f = form.value;

    const currentAddress = buildAddress();

    return (
      f.first_name !== (p.first_name ?? '') ||
      f.last_name !== (p.last_name ?? '') ||
      f.birth_date !== (p.birth_date ?? '') ||
      f.nir !== (p.nir ?? '') ||
      f.ins !== (p.ins ?? '') ||
      currentAddress !== (p.address ?? '') ||
      f.phone !== (p.phone ?? '') ||
      f.email !== (p.email ?? '') ||
      f.entity_id !== (p.entity_id ?? 0)
    );
  });

  // =============================================================================
  // HELPERS
  // =============================================================================

  /**
   * Parse une adresse "14 rue des Essais, 24100 BERGERAC"
   * en { line, postalCode, city }
   */
  function parseAddress(address?: string): { line: string; postalCode: string; city: string } {
    if (!address) return { line: '', postalCode: '', city: '' };

    const parts = address.split(',').map((s) => s.trim());
    const line = parts[0] ?? '';

    if (parts.length > 1) {
      const cityPart = parts.slice(1).join(', ').trim();
      const match = cityPart.match(/^(\d{5})\s+(.+)$/);
      if (match) {
        return { line, postalCode: match[1], city: match[2] };
      }
      return { line, postalCode: '', city: cityPart };
    }

    return { line, postalCode: '', city: '' };
  }

  function buildAddress(): string {
    const parts = [
      form.value.addressLine,
      [form.value.addressPostalCode, form.value.addressCity].filter(Boolean).join(' '),
    ].filter(Boolean);
    return parts.join(', ');
  }

  /**
   * Pré-remplit le formulaire depuis les données patient
   */
  function populateForm(patient: PatientResponse) {
    const addr = parseAddress(patient.address);

    form.value = {
      first_name: patient.first_name ?? '',
      last_name: patient.last_name ?? '',
      birth_date: patient.birth_date ?? '',
      nir: patient.nir ?? '',
      ins: patient.ins ?? '',
      addressLine: addr.line,
      addressPostalCode: addr.postalCode,
      addressCity: addr.city,
      phone: patient.phone ?? '',
      email: patient.email ?? '',
      entity_id: patient.entity_id ?? 0,
    };

    // Sync DatePicker
    if (patient.birth_date) {
      birthDateValue.value = new Date(patient.birth_date);
    } else {
      birthDateValue.value = null;
    }

    validationErrors.value = {};
  }

  // =============================================================================
  // WATCH — Pré-remplissage à l'ouverture
  // =============================================================================

  watch(
    () => props.visible,
    (isVisible) => {
      if (isVisible && props.patient) {
        populateForm(props.patient);
      }
    },
  );

  // =============================================================================
  // METHODS
  // =============================================================================

  function onBirthDateChange(date: Date | Date[] | (Date | null)[] | null | undefined) {
    const d = Array.isArray(date) ? date[0] : date;
    birthDateValue.value = d ?? null;
    form.value.birth_date = d ? d.toISOString().split('T')[0] : '';
  }

  function onEntitySelect(entityId: number | null) {
    form.value.entity_id = entityId ?? 0;
  }

  function close() {
    emit('update:visible', false);
  }

  async function save() {
    if (!props.patient) return;

    // Validation
    validationErrors.value = {};
    if (!form.value.last_name.trim()) {
      validationErrors.value.last_name = 'Le nom est obligatoire';
    }
    if (!form.value.first_name.trim()) {
      validationErrors.value.first_name = 'Le prénom est obligatoire';
    }
    if (!form.value.entity_id || form.value.entity_id === 0) {
      validationErrors.value.entity_id = "L'entité de rattachement est obligatoire";
    }
    if (Object.keys(validationErrors.value).length > 0) return;

    isSaving.value = true;

    const payload: PatientUpdate = {
      first_name: form.value.first_name || undefined,
      last_name: form.value.last_name || undefined,
      birth_date: form.value.birth_date || undefined,
      nir: form.value.nir || undefined,
      ins: form.value.ins || undefined,
      address: buildAddress() || undefined,
      phone: form.value.phone || undefined,
      email: form.value.email || undefined,
    };

    try {
      const result = await patientStore.updatePatient(props.patient.id, payload);

      if (result) {
        toast.add({
          severity: 'success',
          summary: 'Patient modifié',
          detail: `Le dossier de ${form.value.last_name} ${form.value.first_name} a été mis à jour.`,
          life: 4000,
        });
        emit('saved', result);
        close();
      } else {
        toast.add({
          severity: 'error',
          summary: 'Erreur de modification',
          detail: patientStore.error || 'Impossible de modifier le patient.',
          life: 6000,
        });
      }
    } finally {
      isSaving.value = false;
    }
  }
</script>

<template>
  <Transition name="slide-panel">
    <div v-if="visible" class="fixed inset-0 z-50 flex">
      <!-- Overlay -->
      <div class="flex-1 bg-black/20 backdrop-blur-[2px]" @click="close" />

      <!-- Panel -->
      <div class="w-full max-w-lg bg-white shadow-2xl flex flex-col border-l border-slate-200">
        <!-- ─── HEADER ─── -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <div
              class="w-9 h-9 rounded-xl flex items-center justify-center"
              style="background: #f0fdfa; color: #0d9488"
            >
              <Pencil :size="18" :stroke-width="1.8" />
            </div>
            <div>
              <h2 class="text-base font-semibold text-slate-800">Modifier le patient</h2>
              <p class="text-xs text-slate-400 mt-0.5">{{ fullName }}</p>
            </div>
          </div>
          <button
            class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            @click="close"
          >
            <X :size="18" :stroke-width="1.8" />
          </button>
        </div>

        <!-- ─── BODY (scrollable) ─── -->
        <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          <!-- FIELDSET 1 — Identité -->
          <fieldset>
            <legend class="fieldset-legend">
              <IdCard :size="15" :stroke-width="1.8" />
              Identité
            </legend>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
              <!-- Nom -->
              <div class="field-group">
                <label class="field-label-edit">
                  Nom de famille <span class="text-red-500">*</span>
                </label>
                <InputText
                  v-model="form.last_name"
                  :class="{ 'p-invalid': validationErrors.last_name }"
                  placeholder="DUPONT"
                  class="w-full"
                />
                <small v-if="validationErrors.last_name" class="text-red-500">
                  {{ validationErrors.last_name }}
                </small>
              </div>

              <!-- Prénom -->
              <div class="field-group">
                <label class="field-label-edit"> Prénom <span class="text-red-500">*</span> </label>
                <InputText
                  v-model="form.first_name"
                  :class="{ 'p-invalid': validationErrors.first_name }"
                  placeholder="Jean"
                  class="w-full"
                />
                <small v-if="validationErrors.first_name" class="text-red-500">
                  {{ validationErrors.first_name }}
                </small>
              </div>

              <!-- Date de naissance -->
              <div class="field-group">
                <label class="field-label-edit">Date de naissance</label>
                <DatePicker
                  :modelValue="birthDateValue"
                  :maxDate="new Date()"
                  dateFormat="dd/mm/yy"
                  placeholder="JJ/MM/AAAA"
                  appendTo="body"
                  class="w-full"
                  showIcon
                  @update:modelValue="onBirthDateChange"
                />
              </div>

              <!-- spacer -->
              <div></div>

              <!-- NIR -->
              <div class="field-group">
                <label class="field-label-edit">
                  NIR
                  <span class="info-tooltip-trigger">
                    <Info :size="13" :stroke-width="1.8" />
                    <span class="info-tooltip">
                      Numéro de sécurité sociale — 15 chiffres. Sera chiffré en base (AES-256-GCM).
                    </span>
                  </span>
                </label>
                <InputText
                  v-model="form.nir"
                  placeholder="1 85 01 75 108 042 36"
                  maxlength="15"
                  class="w-full"
                />
              </div>

              <!-- INS -->
              <div class="field-group">
                <label class="field-label-edit">
                  INS
                  <span class="info-tooltip-trigger">
                    <Info :size="13" :stroke-width="1.8" />
                    <span class="info-tooltip">
                      Numéro carte vitale délivré par l'Assurance Maladie — identifiant unique du
                      patient dans le système de santé français. Sera chiffré en base.
                    </span>
                  </span>
                </label>
                <InputText v-model="form.ins" placeholder="Identifiant INS" class="w-full" />
              </div>
            </div>
          </fieldset>

          <Divider />

          <!-- FIELDSET 2 — Coordonnées -->
          <fieldset>
            <legend class="fieldset-legend">
              <MapPin :size="15" :stroke-width="1.8" />
              Coordonnées
            </legend>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
              <!-- Adresse — N° et rue -->
              <div class="field-group sm:col-span-2">
                <label class="field-label-edit">N° et nom de rue</label>
                <InputText
                  v-model="form.addressLine"
                  placeholder="14 rue des Essais"
                  class="w-full"
                />
              </div>

              <!-- Code postal -->
              <div class="field-group">
                <label class="field-label-edit">Code postal</label>
                <InputText
                  v-model="form.addressPostalCode"
                  placeholder="24100"
                  maxlength="5"
                  class="w-full"
                />
              </div>

              <!-- Ville -->
              <div class="field-group">
                <label class="field-label-edit">Ville</label>
                <InputText v-model="form.addressCity" placeholder="BERGERAC" class="w-full" />
              </div>

              <!-- Téléphone -->
              <div class="field-group">
                <label class="field-label-edit">Téléphone</label>
                <InputText v-model="form.phone" placeholder="06 12 34 56 78" class="w-full" />
              </div>

              <!-- Email -->
              <div class="field-group">
                <label class="field-label-edit">Email</label>
                <InputText
                  v-model="form.email"
                  type="email"
                  placeholder="patient@email.com"
                  class="w-full"
                />
              </div>
            </div>
          </fieldset>

          <Divider />

          <!-- FIELDSET 3 — Rattachement -->
          <fieldset>
            <legend class="fieldset-legend">
              <Building2 :size="15" :stroke-width="1.8" />
              Rattachement
            </legend>

            <div class="mt-3">
              <label class="field-label-edit">
                Entité de rattachement <span class="text-red-500">*</span>
              </label>
              <div class="border border-slate-200 rounded-lg p-3 mt-1.5">
                <EntitySelector
                  :modelValue="form.entity_id || null"
                  @update:modelValue="onEntitySelect"
                />
              </div>
              <small v-if="validationErrors.entity_id" class="text-red-500 mt-1 block">
                {{ validationErrors.entity_id }}
              </small>
            </div>
          </fieldset>

          <!-- Bandeau sécurité -->
          <div class="security-banner">
            <Lock :size="14" :stroke-width="1.8" />
            <span>Données chiffrées (AES-256-GCM) — conformité RGPD/HDS</span>
          </div>
        </div>

        <!-- ─── FOOTER ─── -->
        <div
          class="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50"
        >
          <p v-if="hasChanges" class="text-xs text-amber-600 font-medium">
            Modifications non enregistrées
          </p>
          <div v-else></div>

          <div class="flex items-center gap-2">
            <Button
              :disabled="isSaving"
              label="Annuler"
              severity="secondary"
              variant="text"
              size="small"
              @click="close"
            />
            <Button
              :loading="isSaving"
              :disabled="!hasChanges"
              label="Enregistrer"
              icon="pi pi-check"
              size="small"
              class="save-btn"
              @click="save"
            />
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
  /* ═══════════════════════════════════════════════════════
   SLIDE PANEL TRANSITIONS
   ═══════════════════════════════════════════════════════ */
  .slide-panel-enter-active {
    transition: opacity 0.25s ease;
  }
  .slide-panel-enter-active > div:last-child {
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .slide-panel-leave-active {
    transition: opacity 0.2s ease;
  }
  .slide-panel-leave-active > div:last-child {
    transition: transform 0.2s ease;
  }
  .slide-panel-enter-from {
    opacity: 0;
  }
  .slide-panel-enter-from > div:last-child {
    transform: translateX(100%);
  }
  .slide-panel-leave-to {
    opacity: 0;
  }
  .slide-panel-leave-to > div:last-child {
    transform: translateX(100%);
  }

  /* ═══════════════════════════════════════════════════════
   FIELDSET & FORM
   ═══════════════════════════════════════════════════════ */
  fieldset {
    border: none;
    padding: 0;
    margin: 0;
  }

  .fieldset-legend {
    @apply flex items-center gap-2 text-sm font-semibold text-slate-700;
    color: #0d9488;
  }

  .field-group {
    @apply flex flex-col gap-1;
  }

  .field-label-edit {
    @apply text-sm font-medium text-slate-600 flex items-center gap-1.5;
  }

  /* ═══════════════════════════════════════════════════════
   INFO TOOLTIP (NIR / INS)
   ═══════════════════════════════════════════════════════ */
  .info-tooltip-trigger {
    @apply relative inline-flex items-center text-slate-400 cursor-help;
  }
  .info-tooltip-trigger:hover {
    @apply text-slate-600;
  }
  .info-tooltip {
    @apply absolute z-50 hidden text-xs text-slate-600 leading-relaxed rounded-xl p-3;
    width: 18rem;
    top: 50%;
    left: calc(100% + 0.75rem);
    transform: translateY(-50%);
    background: white;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    pointer-events: none;
  }
  .info-tooltip::after {
    content: '';
    position: absolute;
    top: 50%;
    right: 100%;
    transform: translateY(-50%);
    border: 6px solid transparent;
    border-right-color: white;
  }
  .info-tooltip-trigger:hover .info-tooltip {
    display: block;
  }

  /* ═══════════════════════════════════════════════════════
   SECURITY BANNER
   ═══════════════════════════════════════════════════════ */
  .security-banner {
    @apply flex items-center gap-2 text-xs text-slate-400 p-3 rounded-lg;
    background: #f8fafc;
    border: 1px solid #f1f5f9;
  }

  /* ═══════════════════════════════════════════════════════
   SAVE BUTTON — teal
   ═══════════════════════════════════════════════════════ */
  .save-btn {
    background: #0d9488 !important;
    border-color: #0d9488 !important;
  }
  .save-btn:hover:not(:disabled) {
    background: #0f766e !important;
    border-color: #0f766e !important;
  }
  .save-btn:disabled {
    opacity: 0.5;
  }
</style>
