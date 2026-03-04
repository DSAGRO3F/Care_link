/**
 * Store Pinia pour l'espace Admin Client
 * Gère l'état global de la gestion des utilisateurs ET des patients
 *
 * Responsabilités :
 *   - Users    : liste paginée, filtres, CRUD (Sprint 2-5)
 *   - Patients : liste paginée, filtres, CRUD (Sprint 7)
 *
 * Pattern calqué sur platform.store.ts (PlatformStore)
 *
 * ⚠️ DETTE TECHNIQUE (identifiée audit 25/02/2026)
 * Ce store combine Users et Patients dans un seul fichier (~620 lignes).
 * Les deux sections sont structurellement identiques (state, getters, CRUD,
 * filtres, pagination). Ce pattern ne doit PAS être reproduit pour l'espace
 * soins.
 *
 * Refactoring envisagé (post-MVP) :
 *   Option A — Un store par domaine : users.store.ts, patients.store.ts
 *   Option B — Un composable factory useCrudStore() qui génère le
 *             boilerplate (state, getters, actions CRUD, filtres, pagination)
 *             à partir d'un service et de types génériques.
 *
 * Pour l'espace soins, privilégier l'option A (stores séparés) en attendant
 * d'avoir assez de recul pour concevoir le factory (option B).
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { userService } from '@/services/user.service'
import { patientService } from '@/services/patient.service'
import type {
  UserSummary,
  UserResponse,
  UserList,
  UserCreate,
  UserUpdate,
  UserQueryParams,
} from '@/types/user'
import type {
  PatientSummary,
  PatientResponse,
  PatientList,
  PatientCreate,
  PatientUpdate,
  PatientQueryParams,
  PatientStatus,
} from '@/types/patient'

export const useAdminStore = defineStore('admin', () => {
  // ═══════════════════════════════════════════════════════════════════════════
  // ██  SECTION USERS (Sprint 2-5 — inchangé)
  // ═══════════════════════════════════════════════════════════════════════════

  // ===========================================================================
  // STATE — Users
  // ===========================================================================

  /** Liste des utilisateurs (paginée, brute — telle que retournée par l'API) */
  const users = ref<UserSummary[]>([])

  /** Utilisateur actuellement sélectionné (version complète) */
  const currentUser = ref<UserResponse | null>(null)

  /** Pagination Users */
  const pagination = ref({
    page: 1,
    size: 20,
    total: 0,
    pages: 0,
  })

  /** Filtres de recherche Users */
  const filters = ref({
    search: '',
    entity_id: null as number | null,
    role: null as string | null,
    profession_id: null as number | null,
    is_active: null as boolean | null,
  })

  /** État de chargement Users */
  const isLoading = ref(false)
  const isLoadingUser = ref(false)
  const isSaving = ref(false)

  /** Erreur éventuelle */
  const error = ref<string | null>(null)

  // ===========================================================================
  // GETTERS — Users
  // ===========================================================================

  /** Nombre total d'utilisateurs */
  const totalUsers = computed(() => pagination.value.total)

  /** Y a-t-il des filtres actifs ? */
  const hasActiveFilters = computed(() => {
    return (
      filters.value.search !== '' ||
      filters.value.entity_id !== null ||
      filters.value.role !== null ||
      filters.value.profession_id !== null ||
      filters.value.is_active !== null
    )
  })

  /**
   * Utilisateurs visibles dans la liste — logique métier de filtrage par défaut :
   * Si aucun filtre is_active n'est actif, on masque les inactifs
   */
  const visibleUsers = computed(() => {
    if (filters.value.is_active !== null) {
      return users.value
    }
    return users.value.filter((u) => u.is_active)
  })

  /**
   * Nombre d'utilisateurs visibles
   */
  const visibleTotal = computed(() => {
    if (filters.value.is_active !== null) {
      return pagination.value.total
    }
    const inactiveCount = users.value.filter((u) => !u.is_active).length
    return pagination.value.total - inactiveCount
  })

  // ===========================================================================
  // ACTIONS — Users : Lecture
  // ===========================================================================

  async function fetchUsers() {
    isLoading.value = true
    error.value = null

    try {
      const params: UserQueryParams = {
        page: pagination.value.page,
        size: pagination.value.size,
      }

      if (filters.value.search) params.search = filters.value.search
      if (filters.value.entity_id !== null) params.entity_id = filters.value.entity_id
      if (filters.value.role) params.role = filters.value.role
      if (filters.value.profession_id !== null) params.profession_id = filters.value.profession_id
      if (filters.value.is_active !== null) params.is_active = filters.value.is_active

      const result: UserList = await userService.list(params)

      users.value = result.items
      pagination.value = {
        page: result.page,
        size: result.size,
        total: result.total,
        pages: result.pages,
      }
    } catch (err) {
      error.value = 'Erreur lors du chargement des professionnels'
      console.error('[AdminStore] fetchUsers error:', err)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUser(userId: number) {
    isLoadingUser.value = true
    error.value = null

    try {
      currentUser.value = await userService.get(userId)
    } catch (err) {
      error.value = 'Erreur lors du chargement du professionnel'
      console.error('[AdminStore] fetchUser error:', err)
    } finally {
      isLoadingUser.value = false
    }
  }

  // ===========================================================================
  // ACTIONS — Users : Écriture
  // ===========================================================================

  async function createUser(data: UserCreate): Promise<UserResponse | null> {
    isSaving.value = true
    error.value = null

    try {
      const newUser = await userService.create(data)
      await fetchUsers()
      return newUser
    } catch (err) {
      error.value = 'Erreur lors de la création du professionnel'
      console.error('[AdminStore] createUser error:', err)
      return null
    } finally {
      isSaving.value = false
    }
  }

  async function updateUser(
    userId: number,
    data: UserUpdate
  ): Promise<UserResponse | null> {
    isSaving.value = true
    error.value = null

    try {
      const updated = await userService.update(userId, data)

      if (currentUser.value?.id === userId) {
        currentUser.value = updated
      }

      await fetchUsers()
      return updated
    } catch (err) {
      error.value = 'Erreur lors de la modification du professionnel'
      console.error('[AdminStore] updateUser error:', err)
      return null
    } finally {
      isSaving.value = false
    }
  }

  async function deleteUser(userId: number): Promise<boolean> {
    isSaving.value = true
    error.value = null

    try {
      await userService.delete(userId)

      if (currentUser.value?.id === userId) {
        currentUser.value = null
      }

      await fetchUsers()
      return true
    } catch (err) {
      error.value = 'Erreur lors de la désactivation du professionnel'
      console.error('[AdminStore] deleteUser error:', err)
      return false
    } finally {
      isSaving.value = false
    }
  }

  // ===========================================================================
  // ACTIONS — Users : Rôles
  // ===========================================================================

  async function addRole(userId: number, roleId: number): Promise<boolean> {
    error.value = null

    try {
      await userService.roles.add(userId, roleId)
      if (currentUser.value?.id === userId) {
        await fetchUser(userId)
      }
      return true
    } catch (err) {
      error.value = 'Erreur lors de l\'assignation du rôle'
      console.error('[AdminStore] addRole error:', err)
      return false
    }
  }

  async function removeRole(userId: number, roleId: number): Promise<boolean> {
    error.value = null

    try {
      await userService.roles.remove(userId, roleId)
      if (currentUser.value?.id === userId) {
        await fetchUser(userId)
      }
      return true
    } catch (err) {
      error.value = 'Erreur lors du retrait du rôle'
      console.error('[AdminStore] removeRole error:', err)
      return false
    }
  }

  // ===========================================================================
  // ACTIONS — Users : Filtres et pagination
  // ===========================================================================

  /**
  * Pattern fire-and-forget : ces actions lancent fetchUsers() sans await.
  * C'est intentionnel — les composants réagissent aux ref() réactives
  * (isLoading, users, error) plutôt qu'au retour de la Promise.
  */

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.page = 1
    fetchUsers()
  }

  function setPage(page: number) {
    pagination.value.page = page
    fetchUsers()
  }

  function resetFilters() {
    filters.value = {
      search: '',
      entity_id: null,
      role: null,
      profession_id: null,
      is_active: null,
    }
    pagination.value.page = 1
    fetchUsers()
  }

  function refresh() {
    fetchUsers()
  }

  function clearCurrentUser() {
    currentUser.value = null
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ██  SECTION PATIENTS (Sprint 7)
  // ═══════════════════════════════════════════════════════════════════════════

  // ===========================================================================
  // STATE — Patients
  // ===========================================================================

  /** Liste des patients (paginée, brute — telle que retournée par l'API) */
  const patients = ref<PatientSummary[]>([])

  /** Patient actuellement sélectionné (version complète) */
  const currentPatient = ref<PatientResponse | null>(null)

  /** Pagination Patients */
  const patientPagination = ref({
    page: 1,
    size: 20,
    total: 0,
    pages: 0,
  })

  /** Filtres de recherche Patients */
  const patientFilters = ref({
    search: '',
    entity_id: null as number | null,
    status: null as PatientStatus | null,
    gir_min: null as number | null,
    gir_max: null as number | null,
  })

  /** État de chargement Patients */
  const isLoadingPatients = ref(false)
  const isLoadingPatient = ref(false)
  const isSavingPatient = ref(false)

  /** Erreur Patients (séparée de l'erreur Users pour indépendance) */
  const patientError = ref<string | null>(null)

  // ===========================================================================
  // GETTERS — Patients
  // ===========================================================================

  /** Nombre total de patients */
  const totalPatients = computed(() => patientPagination.value.total)

  /** Y a-t-il des filtres patients actifs ? */
  const hasActivePatientFilters = computed(() => {
    return (
      patientFilters.value.search !== '' ||
      patientFilters.value.entity_id !== null ||
      patientFilters.value.status !== null ||
      patientFilters.value.gir_min !== null ||
      patientFilters.value.gir_max !== null
    )
  })

  /**
   * Patients visibles dans la liste — logique métier :
   * Par défaut on exclut les archivés et décédés de la vue liste,
   * sauf si un filtre de statut est explicitement sélectionné.
   */
  const visiblePatients = computed(() => {
    if (patientFilters.value.status !== null) {
      return patients.value
    }
    return patients.value.filter(
      (p) => p.status !== 'ARCHIVED' && p.status !== 'DECEASED'
    )
  })

  /**
   * Nombre de patients visibles
   */
  const visiblePatientTotal = computed(() => {
    if (patientFilters.value.status !== null) {
      return patientPagination.value.total
    }
    const hiddenCount = patients.value.filter(
      (p) => p.status === 'ARCHIVED' || p.status === 'DECEASED'
    ).length
    return patientPagination.value.total - hiddenCount
  })

  // ===========================================================================
  // ACTIONS — Patients : Lecture
  // ===========================================================================

  /**
   * Charge la liste des patients avec pagination et filtres
   */
  async function fetchPatients() {
    isLoadingPatients.value = true
    patientError.value = null

    try {
      const params: PatientQueryParams = {
        page: patientPagination.value.page,
        size: patientPagination.value.size,
      }

      if (patientFilters.value.search) params.search = patientFilters.value.search
      if (patientFilters.value.entity_id !== null) params.entity_id = patientFilters.value.entity_id
      if (patientFilters.value.status !== null) params.status = patientFilters.value.status
      if (patientFilters.value.gir_min !== null) params.gir_min = patientFilters.value.gir_min
      if (patientFilters.value.gir_max !== null) params.gir_max = patientFilters.value.gir_max

      const result: PatientList = await patientService.getAll(params)

      patients.value = result.items
      patientPagination.value = {
        page: result.page,
        size: result.size,
        total: result.total,
        pages: result.pages,
      }
    } catch (err) {
      patientError.value = 'Erreur lors du chargement des patients'
      console.error('[AdminStore] fetchPatients error:', err)
    } finally {
      isLoadingPatients.value = false
    }
  }

  /**
   * Charge un patient par son ID (version complète)
   */
  async function fetchPatient(patientId: number) {
    isLoadingPatient.value = true
    patientError.value = null

    try {
      currentPatient.value = await patientService.getById(patientId)
    } catch (err) {
      patientError.value = 'Erreur lors du chargement du patient'
      console.error('[AdminStore] fetchPatient error:', err)
    } finally {
      isLoadingPatient.value = false
    }
  }

  // ===========================================================================
  // ACTIONS — Patients : Écriture
  // ===========================================================================

  /**
   * Crée un nouveau patient et rafraîchit la liste
   */
  async function createPatient(data: PatientCreate): Promise<PatientResponse | null> {
    isSavingPatient.value = true
    patientError.value = null

    try {
      const newPatient = await patientService.create(data)
      await fetchPatients()
      return newPatient
    } catch (err) {
      patientError.value = 'Erreur lors de la création du patient'
      console.error('[AdminStore] createPatient error:', err)
      return null
    } finally {
      isSavingPatient.value = false
    }
  }

  /**
   * Met à jour un patient et rafraîchit
   */
  async function updatePatient(
    patientId: number,
    data: PatientUpdate
  ): Promise<PatientResponse | null> {
    isSavingPatient.value = true
    patientError.value = null

    try {
      const updated = await patientService.update(patientId, data)

      if (currentPatient.value?.id === patientId) {
        currentPatient.value = updated
      }

      await fetchPatients()
      return updated
    } catch (err) {
      patientError.value = 'Erreur lors de la modification du patient'
      console.error('[AdminStore] updatePatient error:', err)
      return null
    } finally {
      isSavingPatient.value = false
    }
  }

  /**
   * Archive un patient (soft delete) et rafraîchit
   */
  async function deletePatient(patientId: number): Promise<boolean> {
    isSavingPatient.value = true
    patientError.value = null

    try {
      await patientService.delete(patientId)

      if (currentPatient.value?.id === patientId) {
        currentPatient.value = null
      }

      await fetchPatients()
      return true
    } catch (err) {
      patientError.value = 'Erreur lors de l\'archivage du patient'
      console.error('[AdminStore] deletePatient error:', err)
      return false
    } finally {
      isSavingPatient.value = false
    }
  }

  // ===========================================================================
  // ACTIONS — Patients : Filtres et pagination
  // ===========================================================================

  /**
  * Pattern fire-and-forget : ces actions lancent fetchUsers() sans await.
  * C'est intentionnel — les composants réagissent aux ref() réactives
  * (isLoading, users, error) plutôt qu'au retour de la Promise.
  */

  function setPatientFilters(newFilters: Partial<typeof patientFilters.value>) {
    patientFilters.value = { ...patientFilters.value, ...newFilters }
    patientPagination.value.page = 1
    fetchPatients()
  }

  function setPatientPage(page: number) {
    patientPagination.value.page = page
    fetchPatients()
  }

  function resetPatientFilters() {
    patientFilters.value = {
      search: '',
      entity_id: null,
      status: null,
      gir_min: null,
      gir_max: null,
    }
    patientPagination.value.page = 1
    fetchPatients()
  }

  function refreshPatients() {
    fetchPatients()
  }

  function clearCurrentPatient() {
    currentPatient.value = null
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ██  RETURN
  // ═══════════════════════════════════════════════════════════════════════════

  return {
    // ── Users — State ──
    users,
    currentUser,
    pagination,
    filters,
    isLoading,
    isLoadingUser,
    isSaving,
    error,

    // ── Users — Getters ──
    totalUsers,
    hasActiveFilters,
    visibleUsers,
    visibleTotal,

    // ── Users — Actions ──
    fetchUsers,
    fetchUser,
    createUser,
    updateUser,
    deleteUser,
    addRole,
    removeRole,
    setFilters,
    setPage,
    resetFilters,
    refresh,
    clearCurrentUser,

    // ── Patients — State ──
    patients,
    currentPatient,
    patientPagination,
    patientFilters,
    isLoadingPatients,
    isLoadingPatient,
    isSavingPatient,
    patientError,

    // ── Patients — Getters ──
    totalPatients,
    hasActivePatientFilters,
    visiblePatients,
    visiblePatientTotal,

    // ── Patients — Actions ──
    fetchPatients,
    fetchPatient,
    createPatient,
    updatePatient,
    deletePatient,
    setPatientFilters,
    setPatientPage,
    resetPatientFilters,
    refreshPatients,
    clearCurrentPatient,
  }
})