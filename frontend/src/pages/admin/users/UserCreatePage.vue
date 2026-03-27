<script setup lang="ts">
  /**
   * UserCreatePage.vue — Création d'un professionnel de santé
   *
   * 🔄 S5 — Refonte wizard :
   *   - Étape 1 : utilise UserForm.vue (factorisation, constat #12)
   *   - Étape 1 : professions groupées par catégorie (constat #11)
   *   - Étape 1 : RPPS conditionnel via requires_rpps (constat #15)
   *   - Étape 3 : filtre les rôles obsolètes (constat #13)
   *   - Étape 3 : message info permissions profession (constat #14)
   *   - Validation : RPPS obligatoire si profession le requiert
   *
   * 🐛 FIX post-S5 :
   *   - identityForm : reactive() → ref() pour compatibilité v-model
   *     (reactive ne peut pas être remplacé par un nouvel objet émis par UserForm)
   *   - fetchProfessions : pagination complète (toutes les pages)
   *
   * Parcours en 3 étapes :
   *   1. Identité & Profession  — via UserForm (groupé par catégorie)
   *   2. Rattachement            — Sélection entité(s) via liste + type de contrat
   *   3. Responsabilités & Récap — Rôles fonctionnels uniquement + récapitulatif
   *
   * Flux de soumission :
   *   POST /users                     → crée l'utilisateur
   *   POST /users/{id}/entities       → rattache à l'entité sélectionnée
   *   POST /users/{id}/roles          → assigne chaque rôle coché
   *
   * Thème : Admin light (slate/blue)
   * Route : /admin/users/new
   * Layout : AdminLayout
   *
   * Destination : src/pages/admin/users/UserCreatePage.vue
   */
  import { ref, computed, onMounted } from 'vue';
  import { useRouter } from 'vue-router';
  import { useToast } from 'primevue/usetoast';

  // PrimeVue
  import Select from 'primevue/select';
  import Button from 'primevue/button';
  import Checkbox from 'primevue/checkbox';
  import Divider from 'primevue/divider';
  import Message from 'primevue/message';
  import Tag from 'primevue/tag';

  // 🔄 S5 — Composant factorisé (constat #12)
  import UserForm from '@/components/users/UserForm.vue';

  // Services
  import { api } from '@/services';
  import { userService, getErrorMessage } from '@/services';
  import { entityService } from '@/services';
  import type {
    UserCreate,
    UserEntityCreate,
    RoleResponse,
    ProfessionResponse,
    ContractType,
  } from '@/types';
  import type { ProfessionGroup } from '@/types';
  import {
    PROFESSION_CATEGORY_LABELS,
    PROFESSION_CATEGORY_ORDER,
    OBSOLETE_ROLE_NAMES,
  } from '@/types';
  import type { EntityResponse } from '@/types';
  import axios from 'axios';

  const router = useRouter();
  const toast = useToast();

  // =============================================================================
  // STATE
  // =============================================================================

  const currentStep = ref(0);
  const isSubmitting = ref(false);
  const submissionProgress = ref('');

  // 🔄 S5 — Labels mis à jour
  const steps = [
    { label: 'Identité & Profession', icon: 'pi pi-user' },
    { label: 'Rattachement', icon: 'pi pi-sitemap' },
    { label: 'Responsabilités', icon: 'pi pi-check-circle' },
  ];

  // ── Formulaire identité ─────────────────────────────────────────────────────
  // 🐛 FIX : ref() au lieu de reactive() pour compatibilité v-model avec UserForm.
  //    UserForm émet update:modelValue avec un NOUVEL objet → reactive ne peut pas
  //    être remplacé (const), ref si (via .value).

  const identityForm = ref({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    password_confirm: '',
    rpps: '',
    profession_id: null as number | null,
    is_admin: false,
  });

  // ── Rattachement entité ─────────────────────────────────────────────────────

  const selectedEntityId = ref<number | null>(null);
  const selectedEntity = ref<EntityResponse | null>(null);
  const contractType = ref<ContractType>('SALARIE');
  const entities = ref<EntityResponse[]>([]);
  const isLoadingEntities = ref(false);

  const contractTypeOptions = [
    { value: 'SALARIE', label: 'Salarié' },
    { value: 'LIBERAL', label: 'Libéral' },
    { value: 'VACATION', label: 'Vacataire' },
    { value: 'REMPLACEMENT', label: 'Remplacement' },
    { value: 'BENEVOLE', label: 'Bénévole' },
  ];

  // ── Rôles ───────────────────────────────────────────────────────────────────

  const availableRoles = ref<RoleResponse[]>([]);
  const selectedRoleIds = ref<number[]>([]);
  const isLoadingRoles = ref(false);

  // ── Professions ─────────────────────────────────────────────────────────────

  const professions = ref<ProfessionResponse[]>([]);
  const isLoadingProfessions = ref(false);

  /**
   * 🆕 S5 — Professions groupées par catégorie pour le sélecteur accordéon.
   * Filtre les professions inactives et trie par display_order.
   */
  const professionGroups = computed<ProfessionGroup[]>(() => {
    return PROFESSION_CATEGORY_ORDER.map((cat) => ({
      category: cat,
      label: PROFESSION_CATEGORY_LABELS[cat] || cat,
      professions: professions.value
        .filter((p) => p.category === cat && p.status === 'active')
        .sort((a, b) => a.display_order - b.display_order),
    })).filter((g) => g.professions.length > 0);
  });

  /**
   * 🆕 S5 — Rôles fonctionnels uniquement (filtre les rôles-professions obsolètes).
   * Résout le constat #13.
   */
  const functionalRoles = computed(() =>
    availableRoles.value.filter((r) => !OBSOLETE_ROLE_NAMES.includes(r.name)),
  );

  // =============================================================================
  // VALIDATION
  // =============================================================================

  /**
   * 🔄 S5 — Détermine si la profession sélectionnée requiert un RPPS.
   */
  const selectedProfessionRequiresRpps = computed(() => {
    if (!identityForm.value.profession_id) return false;
    const prof = professions.value.find((p) => p.id === identityForm.value.profession_id);
    return prof?.requires_rpps ?? false;
  });

  /**
   * 🔄 S5 — Validation étape 1 enrichie : RPPS obligatoire si profession le requiert.
   */
  const isStep1Valid = computed(() => {
    const f = identityForm.value;
    const baseValid =
      f.first_name.trim().length >= 2 &&
      f.last_name.trim().length >= 2 &&
      f.email.includes('@') &&
      f.password.length >= 8 &&
      f.password === f.password_confirm;

    // Si profession requiert RPPS, vérifier qu'il est rempli (11 chiffres)
    if (selectedProfessionRequiresRpps.value) {
      return baseValid && f.rpps.trim().length === 11;
    }
    return baseValid;
  });

  const canProceed = computed(() => {
    switch (currentStep.value) {
      case 0:
        return isStep1Valid.value;
      default:
        return true;
    }
  });

  // =============================================================================
  // CHARGEMENT DES DONNÉES
  // =============================================================================

  async function fetchEntities() {
    isLoadingEntities.value = true;
    try {
      entities.value = await entityService.list();
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[UserCreate] Erreur chargement entités:', err);
      }
    } finally {
      isLoadingEntities.value = false;
    }
  }

  async function fetchRoles() {
    isLoadingRoles.value = true;
    try {
      availableRoles.value = await userService.allRoles.list();
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[UserCreate] Erreur chargement rôles:', err);
      }
    } finally {
      isLoadingRoles.value = false;
    }
  }

  /**
   * 🐛 FIX : Charge TOUTES les pages de professions.
   * L'API pagine à 20 par défaut (27 professions → 2 pages).
   * Sans ça, la catégorie ADMINISTRATIF est absente.
   */
  async function fetchProfessions() {
    isLoadingProfessions.value = true;
    try {
      let allProfessions: ProfessionResponse[] = [];
      let page = 1;
      let totalPages = 1;

      do {
        const response = await api.get('/professions', { params: { page, size: 50 } });
        const data = response.data;
        const items = data.items ?? data;
        allProfessions = [...allProfessions, ...items];
        totalPages = data.pages ?? 1;
        page++;
      } while (page <= totalPages);

      professions.value = allProfessions;
    } catch (_err) {
      if (import.meta.env.DEV) {
        console.warn('[UserCreate] Professions non chargées (endpoint pas encore implémenté ?)');
      }
      professions.value = [];
    } finally {
      isLoadingProfessions.value = false;
    }
  }

  // =============================================================================
  // SÉLECTION ENTITÉ
  // =============================================================================

  function selectEntity(entity: EntityResponse) {
    selectedEntityId.value = entity.id;
    selectedEntity.value = entity;
  }

  function clearEntitySelection() {
    selectedEntityId.value = null;
    selectedEntity.value = null;
  }

  // =============================================================================
  // RÔLES
  // =============================================================================

  function toggleRole(roleId: number) {
    const idx = selectedRoleIds.value.indexOf(roleId);
    if (idx === -1) {
      selectedRoleIds.value.push(roleId);
    } else {
      selectedRoleIds.value.splice(idx, 1);
    }
  }

  function isRoleSelected(roleId: number): boolean {
    return selectedRoleIds.value.includes(roleId);
  }

  // =============================================================================
  // NAVIGATION
  // =============================================================================

  function nextStep() {
    if (canProceed.value && currentStep.value < 2) currentStep.value++;
  }

  function prevStep() {
    if (currentStep.value > 0) currentStep.value--;
  }

  function goToStep(index: number) {
    if (index <= currentStep.value) currentStep.value = index;
  }

  function handleCancel() {
    router.push({ name: 'admin-users' });
  }

  // =============================================================================
  // HELPERS
  // =============================================================================

  function getSelectedRoles(): RoleResponse[] {
    return availableRoles.value.filter((r) => selectedRoleIds.value.includes(r.id));
  }

  function getSelectedProfessionLabel(): string {
    if (!identityForm.value.profession_id) return 'Non spécifiée';
    const p = professions.value.find((p) => p.id === identityForm.value.profession_id);
    return p?.name ?? 'Non spécifiée';
  }

  // =============================================================================
  // SOUMISSION
  // =============================================================================

  async function handleSubmit() {
    if (isSubmitting.value) return;
    isSubmitting.value = true;

    try {
      // ── 1. Créer l'utilisateur ──────────────────────────────────────────
      submissionProgress.value = 'Création du professionnel…';

      const f = identityForm.value;
      const userData: UserCreate = {
        email: f.email.trim(),
        password: f.password,
        first_name: f.first_name.trim(),
        last_name: f.last_name.trim(),
        rpps: f.rpps.trim() || undefined,
        profession_id: f.profession_id || undefined,
        is_admin: f.is_admin,
      };

      const createdUser = await userService.create(userData);

      toast.add({
        severity: 'success',
        summary: 'Professionnel créé avec succès',
        detail: `${createdUser.first_name} ${createdUser.last_name} — ${getSelectedProfessionLabel()}`,
        life: 6000,
      });

      // ── 2. Rattacher à l'entité ─────────────────────────────────────────
      if (selectedEntityId.value) {
        submissionProgress.value = "Rattachement à l'entité…";
        try {
          const entityData: UserEntityCreate = {
            entity_id: selectedEntityId.value,
            is_primary: true,
            contract_type: contractType.value,
            start_date: new Date().toISOString().split('T')[0],
          };
          await userService.entities.attach(createdUser.id, entityData);
        } catch (err) {
          if (import.meta.env.DEV) {
            console.warn('[Submit] Erreur rattachement entité:', err);
          }
          toast.add({
            severity: 'warn',
            summary: 'Rattachement non effectué',
            detail: 'Le professionnel devra être rattaché manuellement.',
            life: 8000,
          });
        }
      }

      // ── 3. Assigner les rôles ───────────────────────────────────────────
      if (selectedRoleIds.value.length > 0) {
        submissionProgress.value = 'Assignation des rôles…';
        for (const roleId of selectedRoleIds.value) {
          try {
            await userService.roles.add(createdUser.id, roleId);
          } catch (err) {
            const roleName = availableRoles.value.find((r) => r.id === roleId)?.name ?? roleId;
            if (import.meta.env.DEV) {
              console.warn(`[Submit] Erreur rôle "${roleName}":`, err);
            }
            toast.add({
              severity: 'warn',
              summary: `Rôle non assigné : ${roleName}`,
              detail: getErrorMessage(err),
              life: 8000,
            });
          }
        }
      }

      // ── 4. Redirection ──────────────────────────────────────────────────
      submissionProgress.value = 'Redirection…';
      setTimeout(() => {
        router.push({ name: 'admin-user-detail', params: { id: createdUser.id } });
      }, 1000);
    } catch (error: unknown) {
      if (import.meta.env.DEV) {
        const debugDetail = axios.isAxiosError(error) ? error.response?.data : error;
        console.error('[Submit] Erreur globale:', debugDetail);
      }
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
      toast.add({
        severity: 'error',
        summary: 'Erreur de création',
        detail: detail || getErrorMessage(error),
        life: 8000,
      });
    } finally {
      isSubmitting.value = false;
      submissionProgress.value = '';
    }
  }

  // =============================================================================
  // LIFECYCLE
  // =============================================================================

  onMounted(() => {
    fetchEntities();
    fetchRoles();
    fetchProfessions();
  });
</script>

<template>
  <div class="max-w-4xl mx-auto pb-12">
    <!-- BREADCRUMB -->
    <nav class="flex items-center gap-2 text-sm mb-6">
      <router-link
        :to="{ name: 'admin-users' }"
        class="text-slate-400 hover:text-slate-700 transition-colors"
      >
        Professionnels
      </router-link>
      <i class="pi pi-chevron-right text-slate-300 text-xs"></i>
      <span class="text-slate-800 font-medium">Nouveau professionnel</span>
    </nav>

    <!-- HEADER -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-slate-800 mb-1">Nouveau professionnel de santé</h1>
      <p class="text-slate-500">
        Créez un compte, rattachez à une entité et assignez des responsabilités.
      </p>
    </div>

    <!-- STEPPER -->
    <div class="flex items-center justify-between mb-10 px-4">
      <template v-for="(step, idx) in steps" :key="idx">
        <button
          :class="idx <= currentStep ? 'cursor-pointer' : 'cursor-default'"
          class="flex flex-col items-center gap-2 group transition-all"
          @click="goToStep(idx)"
        >
          <div
            :class="
              idx < currentStep
                ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-500/20'
                : idx === currentStep
                  ? 'bg-blue-50 border-blue-400 text-blue-600 shadow-md ring-2 ring-blue-200'
                  : 'bg-slate-100 border-slate-300 text-slate-400'
            "
            class="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 border-2"
          >
            <i v-if="idx < currentStep" class="pi pi-check text-sm"></i>
            <i v-else :class="step.icon" class="text-sm"></i>
          </div>
          <span
            :class="idx <= currentStep ? 'text-slate-800' : 'text-slate-400'"
            class="text-xs font-medium tracking-wide transition-colors"
          >
            {{ step.label }}
          </span>
        </button>

        <div
          v-if="idx < steps.length - 1"
          :class="idx < currentStep ? 'bg-blue-500' : 'bg-slate-200'"
          class="flex-1 h-0.5 mx-3 mb-6 rounded-full transition-all duration-500"
        ></div>
      </template>
    </div>

    <!-- FORMULAIRE -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <!-- ═══ ÉTAPE 1 — IDENTITÉ & PROFESSION (🔄 S5 — utilise UserForm) ═══ -->
      <div v-show="currentStep === 0" class="p-8">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <i class="pi pi-user text-blue-500"></i>
          </div>
          <div>
            <h2 class="text-lg font-semibold text-slate-800">Identité & Profession</h2>
            <p class="text-sm text-slate-400">Informations personnelles et profession exercée</p>
          </div>
        </div>

        <!-- 🔄 S5 — Composant factorisé (constat #12) -->
        <!-- 🐛 FIX : v-model fonctionne maintenant car identityForm est un ref() -->
        <UserForm
          v-model="identityForm"
          :profession-groups="professionGroups"
          :loading-professions="isLoadingProfessions"
          mode="create"
        />
      </div>

      <!-- ═══ ÉTAPE 2 — RATTACHEMENT (INCHANGÉE) ═══ -->
      <div v-show="currentStep === 1" class="p-8">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <i class="pi pi-sitemap text-blue-500"></i>
          </div>
          <div>
            <h2 class="text-lg font-semibold text-slate-800">Rattachement à une entité</h2>
            <p class="text-sm text-slate-400">Sélectionnez l'entité principale du professionnel</p>
          </div>
        </div>

        <!-- Entité sélectionnée -->
        <div v-if="selectedEntity" class="mb-6">
          <div
            class="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl px-5 py-4"
          >
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <i class="pi pi-building text-blue-600"></i>
              </div>
              <div>
                <p class="font-medium text-slate-800">{{ selectedEntity.name }}</p>
                <p class="text-sm text-slate-500">
                  {{ selectedEntity.entity_type }}
                  <span v-if="selectedEntity.city"> · {{ selectedEntity.city }}</span>
                </p>
              </div>
            </div>
            <Button
              label="Changer"
              icon="pi pi-pencil"
              severity="secondary"
              variant="text"
              size="small"
              @click="clearEntitySelection"
            />
          </div>

          <div class="mt-4">
            <label class="block text-sm font-medium text-slate-600 mb-2">Type de contrat</label>
            <Select
              v-model="contractType"
              :options="contractTypeOptions"
              optionLabel="label"
              optionValue="value"
              class="w-full md:w-64"
            />
          </div>
        </div>

        <!-- Liste des entités -->
        <div v-else>
          <div v-if="isLoadingEntities" class="flex items-center justify-center py-12">
            <i class="pi pi-spin pi-spinner text-blue-500 text-2xl"></i>
          </div>

          <div v-else-if="entities.length === 0" class="text-center py-12">
            <div
              class="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3"
            >
              <i class="pi pi-sitemap text-2xl text-slate-400"></i>
            </div>
            <p class="text-slate-500">Aucune entité trouvée dans votre structure.</p>
            <p class="text-sm text-slate-400 mt-1">
              Créez d'abord des entités dans l'espace Structure.
            </p>
          </div>

          <div v-else class="space-y-2 max-h-80 overflow-y-auto pr-1">
            <button
              v-for="entity in entities"
              :key="entity.id"
              :class="
                selectedEntityId === entity.id
                  ? 'border-blue-400 bg-blue-50 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              "
              class="w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left"
              @click="selectEntity(entity)"
            >
              <div
                class="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center shrink-0"
              >
                <i class="pi pi-building text-slate-500"></i>
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-slate-800 text-sm truncate">{{ entity.name }}</p>
                <p class="text-xs text-slate-400">
                  {{ entity.entity_type }}
                  <span v-if="entity.city"> · {{ entity.city }}</span>
                </p>
              </div>
              <i v-if="selectedEntityId === entity.id" class="pi pi-check-circle text-blue-500"></i>
            </button>
          </div>

          <Message :closable="false" severity="info" class="mt-4">
            <template #default>
              <span class="text-sm"
                >Le rattachement est optionnel. Vous pourrez l'ajouter plus tard depuis le
                profil.</span
              >
            </template>
          </Message>
        </div>
      </div>

      <!-- ═══ ÉTAPE 3 — RESPONSABILITÉS & RÉCAP (🔄 S5) ═══ -->
      <div v-show="currentStep === 2" class="p-8">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <i class="pi pi-shield text-blue-500"></i>
          </div>
          <div>
            <!-- 🔄 S5 — Titre et description mis à jour -->
            <h2 class="text-lg font-semibold text-slate-800">Responsabilités & Récapitulatif</h2>
            <p class="text-sm text-slate-400">
              Responsabilités complémentaires dans CareLink (optionnel)
            </p>
          </div>
        </div>

        <!-- 🆕 S5 — Message info permissions profession (constat #14) -->
        <Message :closable="false" severity="info" class="mb-6">
          <template #default>
            <span class="text-sm">
              Les permissions de base sont déterminées par la profession
              <strong>{{ getSelectedProfessionLabel() }}</strong
              >. Les responsabilités ci-dessous ajoutent des accès supplémentaires.
            </span>
          </template>
        </Message>

        <!-- Rôles fonctionnels (🔄 S5 — filtrés, constat #13) -->
        <div class="mb-8">
          <h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Ce professionnel a-t-il des responsabilités supplémentaires ?
          </h3>

          <div v-if="isLoadingRoles" class="flex items-center gap-2 py-4">
            <i class="pi pi-spin pi-spinner text-blue-500"></i>
            <span class="text-sm text-slate-400">Chargement des rôles…</span>
          </div>

          <div v-else-if="functionalRoles.length === 0" class="py-4">
            <p class="text-slate-500 text-sm">Aucun rôle disponible.</p>
          </div>

          <!-- 🔄 S5 — v-for sur functionalRoles au lieu de availableRoles -->
          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <button
              v-for="role in functionalRoles"
              :key="role.id"
              :class="
                isRoleSelected(role.id)
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              "
              class="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left"
              @click="toggleRole(role.id)"
            >
              <Checkbox
                :modelValue="isRoleSelected(role.id)"
                :binary="true"
                @click.stop
                @update:modelValue="toggleRole(role.id)"
              />
              <div class="flex-1 min-w-0">
                <p class="font-medium text-slate-800 text-sm">{{ role.name }}</p>
                <p v-if="role.description" class="text-xs text-slate-400 truncate">
                  {{ role.description }}
                </p>
              </div>
              <Tag
                v-if="role.is_system_role"
                value="Système"
                severity="info"
                class="text-xs shrink-0"
              />
            </button>
          </div>
        </div>

        <Divider />

        <!-- Récapitulatif -->
        <h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
          Récapitulatif
        </h3>

        <div class="bg-slate-50 rounded-xl p-6 space-y-4">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p class="text-xs text-slate-400">Nom complet</p>
              <p class="font-medium text-slate-800">
                {{ identityForm.last_name }} {{ identityForm.first_name }}
              </p>
            </div>
            <div>
              <p class="text-xs text-slate-400">Email</p>
              <p class="text-slate-700">{{ identityForm.email }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400">Profession</p>
              <p class="text-slate-700">{{ getSelectedProfessionLabel() }}</p>
            </div>
            <!-- 🔄 S5 — RPPS affiché uniquement si rempli -->
            <div v-if="identityForm.rpps">
              <p class="text-xs text-slate-400">RPPS</p>
              <p class="text-slate-700 font-mono">{{ identityForm.rpps }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400">Administrateur</p>
              <p class="text-slate-700">{{ identityForm.is_admin ? 'Oui' : 'Non' }}</p>
            </div>
          </div>

          <Divider />

          <div>
            <p class="text-xs text-slate-400 mb-1">Entité de rattachement</p>
            <p v-if="selectedEntity" class="text-slate-700">
              <i class="pi pi-building text-xs mr-1"></i>
              {{ selectedEntity.name }} ({{ selectedEntity.entity_type }}) — contrat
              {{ contractType.toLowerCase() }}
            </p>
            <p v-else class="text-slate-400 italic">Aucun rattachement</p>
          </div>

          <Divider />

          <div>
            <!-- 🔄 S5 — Label mis à jour -->
            <p class="text-xs text-slate-400 mb-2">Responsabilités</p>
            <div v-if="getSelectedRoles().length > 0" class="flex flex-wrap gap-1.5">
              <Tag
                v-for="role in getSelectedRoles()"
                :key="role.id"
                :value="role.name"
                severity="info"
              />
            </div>
            <p v-else class="text-slate-400 italic">Aucune responsabilité supplémentaire</p>
          </div>
        </div>

        <!-- Progress soumission -->
        <div v-if="isSubmitting" class="mt-6">
          <div
            class="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-5 py-4"
          >
            <i class="pi pi-spin pi-spinner text-blue-500"></i>
            <span class="text-blue-700 text-sm font-medium">{{ submissionProgress }}</span>
          </div>
        </div>
      </div>

      <!-- FOOTER NAVIGATION -->
      <div
        class="flex items-center justify-between px-8 py-4 bg-slate-50 border-t border-slate-200"
      >
        <Button label="Annuler" severity="secondary" variant="text" @click="handleCancel" />
        <div class="flex items-center gap-3">
          <Button
            v-if="currentStep > 0"
            label="Précédent"
            severity="secondary"
            variant="outlined"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button
            v-if="currentStep < 2"
            :disabled="!canProceed"
            label="Suivant"
            icon="pi pi-arrow-right"
            iconPos="right"
            @click="nextStep"
          />
          <Button
            v-if="currentStep === 2"
            :loading="isSubmitting"
            :disabled="isSubmitting"
            label="Créer le professionnel"
            icon="pi pi-check"
            severity="success"
            @click="handleSubmit"
          />
        </div>
      </div>
    </div>
  </div>
</template>