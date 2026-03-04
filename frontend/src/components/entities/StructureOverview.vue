<script setup lang="ts">
/**
 * StructureOverview — Vue complète de l'organisation d'un tenant
 *
 * v3.1 — Sprint 6 : Support mode admin complet
 *   - canDeletePanelEntity : protège la racine contre la suppression en mode admin
 *   - EntitiesPage.vue wrapper créé (pages/admin/entities/)
 *   - L'admin client a le CRUD complet SAUF création/suppression de la racine
 *
 * v3 — Améliorations arborescence :
 *   - Étape 0 : Re-parentage orphelins avec dialog de confirmation
 *   - Étape 2 : Types niveau 3 (ANTENNE, BUREAU, AGENCE) avec typeOptions filtré par profondeur
 *   - Étape 3 : Héritage SIRET (Option A : affichage parent, pas de stockage en base)
 *   - Légende enrichie avec les types niveau 3
 *   - Bandeau rattachement affiche le parent direct (pas seulement la racine)
 *   - Panneau VIEW affiche le SIRET hérité pour les sous-entités
 *
 * v2 — Simplification UI :
 *   - Card "Arborescence" supprimé (EntityTreeView directement)
 *   - Boutons "Nouvelle entité" supprimés (doublon avec "+" sur carte racine)
 *   - "Tout ouvrir/fermer" déporté dans la carte racine (EntityTreeNode)
 *
 * Modes d'utilisation :
 *
 *   SuperAdmin (embedded dans TenantDetailPage) :
 *     <StructureOverview :tenant-id="42" :dark="true" tenant-name="..." :embedded="true" />
 *     → Header + stats masqués (la page parente les affiche)
 *     → canManageRoot = true
 *
 *   SuperAdmin (standalone, ex: onglet) :
 *     <StructureOverview :tenant-id="42" :dark="true" tenant-name="..." />
 *     → Header + stats affichés
 *
 *   Admin (standalone, EntitiesPage — Sprint 6) :
 *     <StructureOverview />
 *     → Header + stats affichés, thème light
 *     → canManageRoot = false, canDeletePanelEntity protège la racine
 *
 * Fonctionnalités :
 *   ✓ Arborescence EntityTreeView avec CRUD complet
 *   ✓ Panel latéral 3 modes : view (lecture), create, edit
 *   ✓ Clic entité → panneau détail lecture → bouton Modifier
 *   ✓ Validation robuste : email regex, SIRET 14, FINESS 9
 *   ✓ Champ address (texte libre)
 *   ✓ Fieldsets Identification / Coordonnées
 *   ✓ canManageRoot pour SuperAdmin
 *   ✓ API abstraction SuperAdmin (platform) / Admin (tenant)
 *   ✓ Dialog confirmation suppression
 *   ✓ Dual theme dark/light
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'

// PrimeVue
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'

// Composants enfants
import EntityTreeView from './EntityTreeView.vue'

// Services
import { entityService, getErrorMessage } from '@/services'

// Types
import {
  EntityType,
  ROOT_ENTITY_TYPES,
  CHILD_ENTITY_TYPES,
  SUB_ENTITY_TYPES,
  EntityTypeLabels,
  EntityTypeShortLabels,
  EntityTypeDarkColors,
  EntityTypeColors,
  type EntityResponse,
  type EntityCreate,
  type EntityUpdate,
} from '@/types/entity'

// =============================================================================
// PROPS
// =============================================================================

interface Props {
  tenantId?: number
  dark?: boolean
  tenantName?: string
  /** Données du tenant pour auto-créer l'entité racine si absente */
  tenantData?: {
    name: string
    legal_name?: string
    tenant_type?: string
    siret?: string
    address_line1?: string
    postal_code?: string
    city?: string
    country_id?: number
  } | null
  /** Mode embedded : masque le header et les stats (fournis par le parent) */
  embedded?: boolean
  /** Code structure du tenant (affiché dans le card racine) */
  tenantCode?: string
}

const props = withDefaults(defineProps<Props>(), {
  tenantId: undefined,
  dark: false,
  tenantName: '',
  tenantData: null,
  embedded: false,
  tenantCode: '',
})

const toast = useToast()

// =============================================================================
// STATE
// =============================================================================

const entities = ref<EntityResponse[]>([])
const loading = ref(false)
const selectedEntity = ref<EntityResponse | null>(null)

// Panel — 3 modes : view (lecture), create, edit
const panelVisible = ref(false)
const panelMode = ref<'view' | 'create' | 'edit'>('view')
const panelParentId = ref<number | null>(null)
const panelEntity = ref<EntityResponse | null>(null)
const panelSubmitting = ref(false)

// Formulaire (address = champ unique côté Entity backend)
const form = ref({
  name: '',
  entity_type: null as EntityType | null,
  finess_geo: '',
  finess_juridique: '',
  siret: '',
  address: '',
  postal_code: '',
  city: '',
  email: '',
  phone: '',
})

// Erreurs de validation
const errors = ref<Record<string, string>>({})

// Recherche entreprise (API gouv)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searchLoading = ref(false)
const showSearchResults = ref(false)
const searchTimeout = ref<ReturnType<typeof setTimeout> | null>(null)
const searchFilled = ref(false) // true quand une entreprise a été sélectionnée
// Suppression
const deleteDialogVisible = ref(false)
const entityToDelete = ref<EntityResponse | null>(null)
const deleteSubmitting = ref(false)

// Re-parentage orphelins
const orphanDialogVisible = ref(false)
const orphanCount = ref(0)
const orphanRootName = ref('')
const orphanResolve = ref<((confirmed: boolean) => void) | null>(null)

// Héritage SIRET (Option A : affichage seul, pas de stockage)
const siretInherited = ref(false)
const parentSiret = ref('')

// =============================================================================
// MODE — Platform (SuperAdmin) vs Tenant (Admin)
// =============================================================================

const isPlatform = computed(() => !!props.tenantId)
const canManageRoot = computed(() => isPlatform.value)

// =============================================================================
// API — Abstraction SuperAdmin / Admin
// =============================================================================

async function fetchEntities() {
  loading.value = true
  try {
    entities.value = isPlatform.value
      ? await entityService.platform.list(props.tenantId!)
      : await entityService.list()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Erreur de chargement',
      detail: getErrorMessage(err),
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}

async function apiCreate(data: EntityCreate): Promise<EntityResponse> {
  return isPlatform.value
    ? entityService.platform.create(props.tenantId!, data)
    : entityService.create(data)
}

async function apiUpdate(entityId: number, data: EntityUpdate): Promise<EntityResponse> {
  return isPlatform.value
    ? entityService.platform.update(props.tenantId!, entityId, data)
    : entityService.update(entityId, data)
}

async function apiDelete(entityId: number): Promise<void> {
  return isPlatform.value
    ? entityService.platform.delete(props.tenantId!, entityId)
    : entityService.delete(entityId)
}

/**
 * Auto-crée l'entité racine depuis les données du tenant si elle n'existe pas,
 * puis re-parente les entités orphelines vers cette racine.
 *
 * Analogie : quand un immeuble (tenant) existe au cadastre mais que l'organigramme
 * interne (entities) n'a pas encore de hall d'entrée, on le crée automatiquement
 * et on y rattache les bureaux qui flottaient sans étage.
 */
async function ensureRootEntity() {
  if (!props.tenantData?.tenant_type || !canManageRoot.value) return

  // Mapper le tenant_type vers EntityType (seuls les types connus du frontend)
  const tenantType = props.tenantData.tenant_type as EntityType
  if (!Object.values(EntityType).includes(tenantType)) return

  // Vérifier si une entité racine (sans parent) du même type existe déjà
  const rootExists = entities.value.some(
    (e) => (e.parent_id === null || e.parent_id === undefined)
      && e.entity_type === tenantType
  )
  if (rootExists) return

  try {
    // 1. Créer l'entité racine depuis les données du tenant
    const rootData: EntityCreate = {
      name: props.tenantData.name,
      entity_type: tenantType,
      country_id: props.tenantData.country_id || 1,
      ...(props.tenantData.siret && { siret: props.tenantData.siret }),
      ...(props.tenantData.address_line1 && { address: props.tenantData.address_line1 }),
      ...(props.tenantData.postal_code && { postal_code: props.tenantData.postal_code }),
      ...(props.tenantData.city && { city: props.tenantData.city }),
    }
    const newRoot = await apiCreate(rootData)

    // 2. Re-parenter les entités orphelines (parent_id null mais pas la racine)
    const orphans = entities.value.filter(
      (e) => (e.parent_id === null || e.parent_id === undefined)
    )
    for (const orphan of orphans) {
      try {
        await apiUpdate(orphan.id, { parent_id: newRoot.id })
      } catch {
        // Si le backend refuse le re-parentage, on continue silencieusement
      }
    }

    // 3. Recharger l'arbre complet
    await fetchEntities()

    toast.add({
      severity: 'info',
      summary: 'Structure initialisée',
      detail: `Entité racine « ${newRoot.name} » créée depuis les données du tenant`,
      life: 5000,
    })
  } catch (err) {
    // Échec silencieux — l'utilisateur peut toujours créer la racine manuellement
    if (import.meta.env.DEV) console.warn('[StructureOverview] ensureRootEntity failed:', err)
  }
}

// =============================================================================
// HELPERS — Profondeur d'un nœud dans l'arbre
// =============================================================================

/**
 * Calcule la profondeur d'une entité dans l'arbre (0 = racine, 1 = enfant direct...).
 * Utile pour déterminer les types autorisés et l'héritage SIRET.
 */
function getNodeDepth(entityId: number | null): number {
  if (!entityId) return -1
  let depth = 0
  let current = entities.value.find(e => e.id === entityId)
  while (current?.parent_id) {
    depth++
    current = entities.value.find(e => e.id === current!.parent_id)
    if (!current) break
  }
  return depth
}

/**
 * Retourne le SIRET hérité d'un parent (en remontant l'arbre si nécessaire).
 */
function getInheritedSiret(parentId: number | null): string {
  if (!parentId) return ''
  let current = entities.value.find(e => e.id === parentId)
  while (current) {
    if (current.siret) return current.siret
    if (!current.parent_id) break
    current = entities.value.find(e => e.id === current!.parent_id)
  }
  return ''
}

// =============================================================================
// RE-PARENTAGE — Corrige les entités orphelines (parent_id null)
// =============================================================================

/**
 * Détecte les entités orphelines (parent_id null mais pas de type racine)
 * et propose de les rattacher automatiquement à la racine existante.
 *
 * Analogie : des bureaux qui flottent dans le vide sans être rattachés
 * à un étage de l'immeuble — on les raccroche au hall d'entrée.
 */
async function reParentOrphans() {
  if (!canManageRoot.value) return

  // Trouver la racine
  const root = entities.value.find(
    (e) => (e.parent_id === null || e.parent_id === undefined)
      && ROOT_ENTITY_TYPES.includes(e.entity_type)
  )
  if (!root) return

  // Trouver les orphelins (parent_id null mais pas la racine)
  const orphans = entities.value.filter(
    (e) => (e.parent_id === null || e.parent_id === undefined)
      && e.id !== root.id
  )
  if (orphans.length === 0) return

  // Demander confirmation à l'utilisateur
  const confirmed = await askOrphanConfirmation(orphans.length, root.name)
  if (!confirmed) return

  // Re-parenter
  let reparented = 0
  for (const orphan of orphans) {
    try {
      await apiUpdate(orphan.id, { parent_id: root.id })
      reparented++
    } catch {
      if (import.meta.env.DEV) console.warn(`[StructureOverview] Failed to reparent entity ${orphan.id}`)
    }
  }

  if (reparented > 0) {
    await fetchEntities()
    toast.add({
      severity: 'success',
      summary: 'Structure corrigée',
      detail: `${reparented} entité${reparented > 1 ? 's' : ''} rattachée${reparented > 1 ? 's' : ''} à ${root.name}`,
      life: 4000,
    })
  }
}

/** Affiche le dialog de confirmation et retourne une Promise<boolean> */
function askOrphanConfirmation(count: number, rootName: string): Promise<boolean> {
  orphanCount.value = count
  orphanRootName.value = rootName
  orphanDialogVisible.value = true

  return new Promise((resolve) => {
    orphanResolve.value = resolve
  })
}

function confirmOrphans() {
  orphanDialogVisible.value = false
  orphanResolve.value?.(true)
  orphanResolve.value = null
}

function cancelOrphans() {
  orphanDialogVisible.value = false
  orphanResolve.value?.(false)
  orphanResolve.value = null
}

// =============================================================================
// STATS CONSOLIDÉES
// =============================================================================

const totalEntities = computed(() => entities.value.length)

const totalPatients = computed(() =>
  entities.value.reduce((sum, e) => sum + (e.patients_count || 0), 0)
)

const totalUsers = computed(() =>
  entities.value.reduce((sum, e) => sum + (e.users_count || 0), 0)
)

// La racine = l'entité sans parent (position dans l'arbre), pas un type spécifique
const rootEntity = computed(() =>
  entities.value.find((e) => e.parent_id === null || e.parent_id === undefined)
)

const childCount = computed(() =>
  entities.value.filter((e) => e.parent_id !== null && e.parent_id !== undefined).length
)

const ratioLabel = computed(() => {
  if (totalUsers.value === 0) return '—'
  return (totalPatients.value / totalUsers.value).toFixed(1)
})

// =============================================================================
// PANEL — Ouverture / Fermeture
// =============================================================================

/** Ouvre le panneau en mode lecture (clic sur une entité) */
function openView(entity: EntityResponse) {
  panelMode.value = 'view'
  panelEntity.value = entity
  selectedEntity.value = entity
  panelVisible.value = true
}

/** Ouvre le panneau en mode création */
function openCreate(parentId: number | null) {
  panelMode.value = 'create'
  panelParentId.value = parentId
  panelEntity.value = null
  resetForm()

  // Héritage SIRET (Option A) : si le parent est de profondeur >= 1,
  // on affiche le SIRET du parent en lecture seule mais on ne l'enverra PAS au backend.
  // L'entité de niveau 3 n'a pas de SIRET propre (null en base), elle l'hérite de son parent.
  if (parentId) {
    const depth = getNodeDepth(parentId)
    if (depth >= 1) {
      const inherited = getInheritedSiret(parentId)
      if (inherited) {
        parentSiret.value = inherited
        siretInherited.value = true
        form.value.siret = inherited  // Affichage seul — sera exclu du payload
      }
    }
  }

  panelVisible.value = true
}

/** Ouvre le panneau en mode édition */
function openEdit(entity: EntityResponse) {
  panelMode.value = 'edit'
  panelEntity.value = entity
  panelParentId.value = entity.parent_id
  form.value = {
    name: entity.name,
    entity_type: entity.entity_type,
    finess_geo: entity.finess_geo || '',
    finess_juridique: entity.finess_juridique || '',
    siret: entity.siret || '',
    address: entity.address || entity.address_line1 || '',
    postal_code: entity.postal_code || '',
    city: entity.city || '',
    email: entity.email || '',
    phone: entity.phone || '',
  }
  errors.value = {}
  panelVisible.value = true
}

/** Bascule du mode view → edit */
function switchToEdit() {
  if (panelEntity.value) {
    openEdit(panelEntity.value)
  }
}

function closePanel() {
  panelVisible.value = false
  panelEntity.value = null
  selectedEntity.value = null
  resetForm()
}

function resetForm() {
  form.value = {
    name: '',
    entity_type: null,
    finess_geo: '',
    finess_juridique: '',
    siret: '',
    address: '',
    postal_code: '',
    city: '',
    email: '',
    phone: '',
  }
  errors.value = {}
  // Reset recherche entreprise
  searchQuery.value = ''
  searchResults.value = []
  showSearchResults.value = false
  searchFilled.value = false
  // Reset héritage SIRET
  siretInherited.value = false
  parentSiret.value = ''
}

// =============================================================================
// RECHERCHE ENTREPRISE — API annuaire-entreprises.data.gouv.fr
// =============================================================================

function onSearchInput() {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)

  const q = searchQuery.value.trim()
  if (q.length < 3) {
    searchResults.value = []
    showSearchResults.value = false
    return
  }

  searchLoading.value = true
  searchTimeout.value = setTimeout(async () => {
    try {
      const url = `https://recherche-entreprises.api.gouv.fr/search?q=${encodeURIComponent(q)}&per_page=6`
      const response = await fetch(url)
      const data = await response.json()
      searchResults.value = data.results || []
      showSearchResults.value = searchResults.value.length > 0
    } catch (err) {
      console.warn('[API Entreprises] Erreur:', err)
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }, 350)
}

function selectEntreprise(result: any) {
  const siege = result.siege || {}
  form.value.name = result.nom_complet || result.nom_raison_sociale || ''
  form.value.siret = siege.siret || ''
  form.value.address = formatAddress(siege)
  form.value.postal_code = siege.code_postal || ''
  form.value.city = siege.libelle_commune || ''

  // Fermer le dropdown et marquer comme rempli
  showSearchResults.value = false
  searchQuery.value = result.nom_complet || result.nom_raison_sociale || ''
  searchFilled.value = true
}

/** Construit l'adresse à partir des champs du siège */
function formatAddress(siege: any): string {
  const parts: string[] = []
  if (siege.numero_voie) parts.push(siege.numero_voie)
  if (siege.type_voie) parts.push(siege.type_voie)
  if (siege.libelle_voie) parts.push(siege.libelle_voie)
  return parts.join(' ') || siege.adresse || ''
}

/** Réinitialise la recherche pour permettre une nouvelle saisie */
function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  showSearchResults.value = false
  searchFilled.value = false
}

// Dropdown Type — filtré par profondeur du parent
const typeOptions = computed(() => {
  // Édition → type verrouillé
  if (panelMode.value === 'edit') {
    return form.value.entity_type
      ? [{ value: form.value.entity_type, label: EntityTypeLabels[form.value.entity_type] }]
      : []
  }

  // Déterminer la profondeur du parent pour restreindre les types autorisés
  const parentDepth = getNodeDepth(panelParentId.value)

  // Parent de profondeur >= 1 (SSIAD, SAAD…) → sous-entités uniquement
  if (parentDepth >= 1) {
    return SUB_ENTITY_TYPES.map((t) => ({ value: t, label: EntityTypeLabels[t] }))
  }

  // SuperAdmin → tous les types racine + enfants
  if (canManageRoot.value) {
    return [...ROOT_ENTITY_TYPES, ...CHILD_ENTITY_TYPES]
      .map((t) => ({ value: t, label: EntityTypeLabels[t] }))
  }

  // Admin tenant → uniquement les types enfants
  return CHILD_ENTITY_TYPES.map((t) => ({ value: t, label: EntityTypeLabels[t] }))
})

// =============================================================================
// VALIDATION — email regex, SIRET 14, FINESS 9
// =============================================================================

function validate(): boolean {
  const errs: Record<string, string> = {}

  if (!form.value.name.trim() || form.value.name.trim().length < 2) {
    errs.name = 'Le nom est requis (2 caractères minimum)'
  }

  if (!form.value.entity_type && panelMode.value === 'create') {
    errs.entity_type = 'Le type de structure est requis'
  }

  if (form.value.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    errs.email = 'Format email invalide'
  }

  if (form.value.siret) {
    const siretClean = form.value.siret.replace(/\s/g, '')
    if (!/^\d{14}$/.test(siretClean)) {
      errs.siret = 'Le SIRET doit contenir exactement 14 chiffres'
    }
  }

  if (form.value.finess_geo && !/^\d{9}$/.test(form.value.finess_geo.trim())) {
    errs.finess_geo = 'Le FINESS doit contenir 9 chiffres'
  }

  if (form.value.finess_juridique && !/^\d{9}$/.test(form.value.finess_juridique.trim())) {
    errs.finess_juridique = 'Le FINESS doit contenir 9 chiffres'
  }

  errors.value = errs
  return Object.keys(errs).length === 0
}

const isFormValid = computed(() =>
  form.value.name.trim().length >= 2 && form.value.entity_type !== null
)

// =============================================================================
// PANEL — Soumission Create / Edit
// =============================================================================

async function handlePanelSubmit() {
  if (panelSubmitting.value) return
  if (!validate()) return

  panelSubmitting.value = true

  try {
    const siretClean = form.value.siret.replace(/\s/g, '').trim()

    if (panelMode.value === 'create') {
      // Option A : si SIRET hérité, on ne l'envoie PAS au backend (restera null en base)
      const shouldSendSiret = !siretInherited.value && siretClean

      const data: EntityCreate = {
        name: form.value.name.trim(),
        entity_type: form.value.entity_type!,
        parent_id: panelParentId.value || undefined,
        country_id: 1, // France par défaut
        ...(form.value.finess_geo.trim() && { finess_geo: form.value.finess_geo.trim() }),
        ...(form.value.finess_juridique.trim() && { finess_juridique: form.value.finess_juridique.trim() }),
        ...(shouldSendSiret && { siret: siretClean }),
        ...(form.value.address.trim() && { address: form.value.address.trim() }),
        ...(form.value.postal_code.trim() && { postal_code: form.value.postal_code.trim() }),
        ...(form.value.city.trim() && { city: form.value.city.trim() }),
        ...(form.value.email.trim() && { email: form.value.email.trim() }),
        ...(form.value.phone.trim() && { phone: form.value.phone.trim() }),
      }
      await apiCreate(data)
      toast.add({
        severity: 'success',
        summary: 'Entité créée',
        detail: `${EntityTypeShortLabels[data.entity_type]} — ${data.name}`,
        life: 3000,
      })
    } else {
      const data: EntityUpdate = {
        name: form.value.name.trim(),
        finess_geo: form.value.finess_geo.trim() || null,
        finess_juridique: form.value.finess_juridique.trim() || null,
        siret: siretClean || null,
        address: form.value.address.trim() || null,
        postal_code: form.value.postal_code.trim() || null,
        city: form.value.city.trim() || null,
        email: form.value.email.trim() || null,
        phone: form.value.phone.trim() || null,
      }
      await apiUpdate(panelEntity.value!.id, data)
      toast.add({
        severity: 'success',
        summary: 'Entité modifiée',
        detail: form.value.name,
        life: 3000,
      })
    }

    closePanel()
    await fetchEntities()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: panelMode.value === 'create' ? 'Erreur de création' : 'Erreur de modification',
      detail: getErrorMessage(err),
      life: 5000,
    })
  } finally {
    panelSubmitting.value = false
  }
}

// =============================================================================
// SUPPRESSION
// =============================================================================

function confirmDelete(entity: EntityResponse) {
  entityToDelete.value = entity
  deleteDialogVisible.value = true
}

async function handleDelete() {
  if (!entityToDelete.value || deleteSubmitting.value) return
  deleteSubmitting.value = true

  try {
    await apiDelete(entityToDelete.value.id)
    toast.add({
      severity: 'success',
      summary: 'Entité supprimée',
      detail: entityToDelete.value.name,
      life: 3000,
    })
    if (selectedEntity.value?.id === entityToDelete.value.id) {
      selectedEntity.value = null
    }
    deleteDialogVisible.value = false
    entityToDelete.value = null
    await fetchEntities()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Erreur de suppression',
      detail: getErrorMessage(err),
      life: 5000,
    })
  } finally {
    deleteSubmitting.value = false
  }
}

// =============================================================================
// HELPERS — Panneau View (lecture)
// =============================================================================

/** Entité parente de l'entité affichée */
const viewParentEntity = computed(() => {
  if (!panelEntity.value?.parent_id) return null
  return entities.value.find((e) => e.id === panelEntity.value!.parent_id) || null
})

/** Nombre d'enfants directs */
const viewChildrenCount = computed(() => {
  if (!panelEntity.value) return 0
  return entities.value.filter((e) => e.parent_id === panelEntity.value!.id).length
})

/** Compte récursif de tous les descendants d'une entité */
function countDescendants(entityId: number): number {
  const directChildren = entities.value.filter((e) => e.parent_id === entityId)
  let count = directChildren.length
  for (const child of directChildren) {
    count += countDescendants(child.id)
  }
  return count
}

/** Nombre total de descendants de l'entité à supprimer */
const deleteDescendantsCount = computed(() => {
  if (!entityToDelete.value) return 0
  return countDescendants(entityToDelete.value.id)
})

/** Noms des enfants directs de l'entité à supprimer (pour le warning) */
const deleteChildrenNames = computed(() => {
  if (!entityToDelete.value) return []
  return entities.value
    .filter((e) => e.parent_id === entityToDelete.value!.id)
    .map((e) => `${EntityTypeShortLabels[e.entity_type]} — ${e.name}`)
})

/**
 * L'entité affichée dans le panneau peut-elle être supprimée ?
 * - SuperAdmin (isPlatform) : peut tout supprimer
 * - Admin client : peut supprimer tout SAUF la racine
 *   (la racine est créée par le SuperAdmin, le syndic ne démolit pas l'immeuble)
 */
const canDeletePanelEntity = computed(() => {
  if (!panelEntity.value) return false
  if (isPlatform.value) return true
  // Admin : l'entité a un parent → ce n'est pas la racine → suppression autorisée
  return panelEntity.value.parent_id !== null && panelEntity.value.parent_id !== undefined
})

/** Supprimer depuis le panel view : ferme le panel puis ouvre la confirmation */
function confirmDeleteFromPanel() {
  if (!panelEntity.value) return
  const entity = panelEntity.value
  closePanel()
  // nextTick pour laisser la transition du panel se terminer
  setTimeout(() => {
    confirmDelete(entity)
  }, 100)
}

/** Couleurs du badge type */
function entityTypeColorClasses(type: EntityType) {
  return props.dark ? EntityTypeDarkColors[type] : EntityTypeColors[type]
}

// =============================================================================
// LIFECYCLE
// =============================================================================

onMounted(async () => {
  await fetchEntities()
  await ensureRootEntity()
  await reParentOrphans()
})

// Fermer le dropdown recherche si clic en dehors
function onClickOutsideSearch(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.search-dropdown-container')) {
    showSearchResults.value = false
  }
}
onMounted(() => document.addEventListener('click', onClickOutsideSearch))
onUnmounted(() => document.removeEventListener('click', onClickOutsideSearch))

watch(() => props.tenantId, () => {
  if (props.tenantId) fetchEntities()
})

// =============================================================================
// THEME HELPERS
// =============================================================================

const labelClass = computed(() => props.dark ? 'text-slate-300' : 'text-zinc-600')
const labelSmallClass = computed(() => props.dark ? 'text-slate-400' : 'text-zinc-500')
const fieldsetLegendClass = computed(() => props.dark ? 'text-slate-400' : 'text-zinc-400')
const inputClass = computed(() =>
  props.dark ? 'w-full bg-slate-900 border-slate-700 text-white placeholder-slate-500' : 'w-full'
)
</script>

<template>
  <div class="structure-overview">

    <!-- ═════════════════════════════════════════════════════════════════
         HEADER (masqué en mode embedded)
         ═════════════════════════════════════════════════════════════════ -->
    <div v-if="!embedded" class="mb-6">
      <h2
        class="text-xl font-bold"
        :class="dark ? 'text-white' : 'text-zinc-800'"
      >
        Organisation
      </h2>
      <p class="text-sm mt-0.5" :class="dark ? 'text-slate-400' : 'text-zinc-500'">
        Structure et entités{{ tenantName ? ` — ${tenantName}` : '' }}
      </p>
    </div>

    <!-- ═════════════════════════════════════════════════════════════════
         STATS CONSOLIDÉES (masquées en mode embedded)
         ═════════════════════════════════════════════════════════════════ -->
    <div v-if="!embedded" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">

      <!-- Entités -->
      <div
        class="rounded-xl p-4 border transition-colors"
        :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-zinc-100 shadow-sm'"
      >
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="dark ? 'bg-blue-500/20' : 'bg-blue-50'">
            <i class="pi pi-sitemap text-sm" :class="dark ? 'text-blue-400' : 'text-blue-500'"></i>
          </div>
          <div>
            <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-white' : 'text-zinc-800'">{{ totalEntities }}</p>
            <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">
              Entités
              <span v-if="childCount > 0" class="opacity-70">({{ childCount }} membre{{ childCount > 1 ? 's' : '' }})</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Patients -->
      <div
        class="rounded-xl p-4 border transition-colors"
        :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-zinc-100 shadow-sm'"
      >
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="dark ? 'bg-emerald-500/20' : 'bg-emerald-50'">
            <i class="pi pi-users text-sm" :class="dark ? 'text-emerald-400' : 'text-emerald-500'"></i>
          </div>
          <div>
            <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-white' : 'text-zinc-800'">{{ totalPatients }}</p>
            <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Patients</p>
          </div>
        </div>
      </div>

      <!-- Professionnels -->
      <div
        class="rounded-xl p-4 border transition-colors"
        :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-zinc-100 shadow-sm'"
      >
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="dark ? 'bg-sky-500/20' : 'bg-sky-50'">
            <i class="pi pi-briefcase text-sm" :class="dark ? 'text-sky-400' : 'text-sky-500'"></i>
          </div>
          <div>
            <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-white' : 'text-zinc-800'">{{ totalUsers }}</p>
            <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Professionnels</p>
          </div>
        </div>
      </div>

      <!-- Ratio -->
      <div
        class="rounded-xl p-4 border transition-colors"
        :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-zinc-100 shadow-sm'"
      >
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="dark ? 'bg-violet-500/20' : 'bg-violet-50'">
            <i class="pi pi-chart-bar text-sm" :class="dark ? 'text-violet-400' : 'text-violet-500'"></i>
          </div>
          <div>
            <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-white' : 'text-zinc-800'">{{ ratioLabel }}</p>
            <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Patients / pro</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═════════════════════════════════════════════════════════════════
         ARBORESCENCE — EntityTreeView directement (sans card wrapper)
         Le "Tout ouvrir/fermer" et le "+" sont dans la carte racine (EntityTreeNode)
         ═════════════════════════════════════════════════════════════════ -->
    <EntityTreeView
      :entities="entities"
      :dark="dark"
      :selected-id="selectedEntity?.id || null"
      :tenant-code="tenantCode"
      :child-count="childCount"
      :total-users="totalUsers"
      @select="openView"
      @create="openCreate"
      @edit="openEdit"
      @delete="confirmDelete"
    />

    <!-- Légende -->
    <div
      class="mt-4 px-4 py-3 rounded-xl border flex items-center gap-4 flex-wrap"
      :class="dark ? 'bg-slate-800/40 border-slate-700' : 'bg-white border-zinc-100'"
    >
      <span class="text-[10px] font-semibold uppercase tracking-wider" :class="dark ? 'text-slate-600' : 'text-zinc-300'">
        Légende
      </span>
      <div
        v-for="type in [EntityType.GCSMS, EntityType.GTSMS, EntityType.SSIAD, EntityType.SAAD, EntityType.SPASAD, EntityType.EHPAD, EntityType.ANTENNE, EntityType.BUREAU, EntityType.AGENCE]"
        :key="type"
        class="flex items-center gap-1.5"
      >
        <div
          class="w-2 h-2 rounded-full border"
          :class="[
            dark ? EntityTypeDarkColors[type].bg : EntityTypeColors[type].bg,
            dark ? EntityTypeDarkColors[type].border : EntityTypeColors[type].border,
          ]"
        ></div>
        <span class="text-xs" :class="dark ? 'text-slate-400' : 'text-zinc-500'">
          {{ EntityTypeShortLabels[type] }}
        </span>
      </div>
    </div>

    <!-- ═════════════════════════════════════════════════════════════════
         PANNEAU LATÉRAL — VIEW / CREATE / EDIT
         ═════════════════════════════════════════════════════════════════ -->
    <Transition name="slide-panel">
      <div v-if="panelVisible" class="fixed inset-0 z-50 flex">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="closePanel"></div>

        <!-- Panel -->
        <div
          class="relative ml-auto w-full max-w-md h-full flex flex-col shadow-2xl"
          :class="dark ? 'bg-slate-900 border-l border-slate-700' : 'bg-white border-l border-zinc-200'"
        >
          <!-- ═══════════════════════════════════════════════
               HEADER du panneau
               ═══════════════════════════════════════════════ -->
          <div
            class="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
            :class="dark ? 'border-slate-700' : 'border-zinc-100'"
          >
            <div class="flex items-center gap-3">
              <div
                class="w-9 h-9 rounded-lg flex items-center justify-center"
                :class="
                  panelMode === 'view'
                    ? (dark ? 'bg-blue-500/20' : 'bg-blue-50')
                    : (dark ? 'bg-violet-500/20' : 'bg-blue-50')
                "
              >
                <i
                  :class="
                    panelMode === 'view' ? 'pi pi-eye' :
                    panelMode === 'create' ? 'pi pi-plus' : 'pi pi-pencil'
                  "
                  class="text-sm"
                  :style="{
                    color: panelMode === 'view'
                      ? (dark ? '#60a5fa' : '#3b82f6')
                      : (dark ? '#a78bfa' : '#3b82f6')
                  }"
                ></i>
              </div>
              <div>
                <h3 class="text-lg font-semibold" :class="dark ? 'text-white' : 'text-zinc-800'">
                  {{ panelMode === 'view' ? 'Détail entité' : panelMode === 'create' ? 'Nouvelle entité' : 'Modifier l\'entité' }}
                </h3>
                <p class="text-xs mt-0.5" :class="dark ? 'text-slate-500' : 'text-zinc-400'">
                  {{ panelMode === 'create' ? 'Remplissez les informations' : panelEntity?.name }}
                </p>
              </div>
            </div>
            <button
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              :class="dark ? 'text-slate-400 hover:text-white hover:bg-slate-700' : 'text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100'"
              @click="closePanel"
            >
              <i class="pi pi-times"></i>
            </button>
          </div>

          <!-- ═══════════════════════════════════════════════
               BODY — Mode VIEW (lecture)
               ═══════════════════════════════════════════════ -->
          <div v-if="panelMode === 'view' && panelEntity" class="flex-1 overflow-y-auto px-6 py-5">

            <!-- Badge type + statut -->
            <div class="flex items-center gap-2 mb-5">
              <span
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
                :class="[entityTypeColorClasses(panelEntity.entity_type).bg, entityTypeColorClasses(panelEntity.entity_type).border, entityTypeColorClasses(panelEntity.entity_type).text]"
              >
                {{ EntityTypeShortLabels[panelEntity.entity_type] }}
              </span>
              <span
                v-if="!panelEntity.is_active"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30"
              >
                Inactif
              </span>
            </div>

            <!-- Nom -->
            <h4 class="text-lg font-bold mb-4" :class="dark ? 'text-white' : 'text-zinc-800'">
              {{ panelEntity.name }}
            </h4>

            <!-- Identification -->
            <fieldset class="mb-6">
              <legend class="text-xs font-semibold uppercase tracking-wider mb-3" :class="fieldsetLegendClass">
                Identification
              </legend>
              <dl class="space-y-2.5">
                <div>
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Type de structure</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">{{ EntityTypeLabels[panelEntity.entity_type] }}</dd>
                </div>
                <div v-if="panelEntity.finess_juridique">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">FINESS Juridique (EJ)</dt>
                  <dd class="text-sm font-mono" :class="dark ? 'text-white' : 'text-zinc-700'">{{ panelEntity.finess_juridique }}</dd>
                </div>
                <div v-if="panelEntity.finess_geo">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">FINESS Géographique (ET)</dt>
                  <dd class="text-sm font-mono" :class="dark ? 'text-white' : 'text-zinc-700'">{{ panelEntity.finess_geo }}</dd>
                </div>
                <div v-if="panelEntity.siret">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">SIRET</dt>
                  <dd class="text-sm font-mono" :class="dark ? 'text-white' : 'text-zinc-700'">{{ panelEntity.siret }}</dd>
                </div>
                <div v-else-if="panelEntity.parent_id && getInheritedSiret(panelEntity.parent_id)">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">
                    SIRET
                    <span class="text-emerald-500 ml-1">(hérité)</span>
                  </dt>
                  <dd class="text-sm font-mono" :class="dark ? 'text-white/60' : 'text-zinc-500'">
                    {{ getInheritedSiret(panelEntity.parent_id) }}
                  </dd>
                </div>
              </dl>
            </fieldset>

            <!-- Coordonnées -->
            <fieldset class="mb-6">
              <legend class="text-xs font-semibold uppercase tracking-wider mb-3" :class="fieldsetLegendClass">
                Coordonnées
              </legend>
              <dl class="space-y-2.5">
                <div v-if="panelEntity.address || panelEntity.city">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Adresse</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">
                    <span v-if="panelEntity.address">{{ panelEntity.address }}<br></span>
                    <span v-if="panelEntity.postal_code || panelEntity.city">{{ panelEntity.postal_code }} {{ panelEntity.city }}</span>
                  </dd>
                </div>
                <div v-if="panelEntity.email">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Email</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">
                    <i class="pi pi-envelope text-xs mr-1.5" :class="dark ? 'text-slate-500' : 'text-zinc-400'"></i>{{ panelEntity.email }}
                  </dd>
                </div>
                <div v-if="panelEntity.phone">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Téléphone</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">
                    <i class="pi pi-phone text-xs mr-1.5" :class="dark ? 'text-slate-500' : 'text-zinc-400'"></i>{{ panelEntity.phone }}
                  </dd>
                </div>
                <div v-if="!panelEntity.address && !panelEntity.city && !panelEntity.email && !panelEntity.phone">
                  <p class="text-sm italic" :class="dark ? 'text-slate-600' : 'text-zinc-400'">
                    Aucune coordonnée renseignée
                  </p>
                </div>
              </dl>
            </fieldset>

            <!-- Rattachement -->
            <fieldset class="mb-6">
              <legend class="text-xs font-semibold uppercase tracking-wider mb-3" :class="fieldsetLegendClass">
                Rattachement
              </legend>
              <dl class="space-y-2.5">
                <div v-if="viewParentEntity">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Rattachée à</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">
                    <i class="pi pi-arrow-up text-xs mr-1.5" :class="dark ? 'text-slate-500' : 'text-zinc-400'"></i>
                    {{ viewParentEntity.name }}
                    <span class="text-xs ml-1" :class="dark ? 'text-slate-500' : 'text-zinc-400'">
                      ({{ EntityTypeShortLabels[viewParentEntity.entity_type] }})
                    </span>
                  </dd>
                </div>
                <div v-else>
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Niveau</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">Entité racine</dd>
                </div>
                <div v-if="viewChildrenCount > 0">
                  <dt class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Entités rattachées</dt>
                  <dd class="text-sm" :class="dark ? 'text-white' : 'text-zinc-700'">
                    {{ viewChildrenCount }} entité{{ viewChildrenCount > 1 ? 's' : '' }}
                  </dd>
                </div>
              </dl>
            </fieldset>

            <!-- Stats -->
            <fieldset>
              <legend class="text-xs font-semibold uppercase tracking-wider mb-3" :class="fieldsetLegendClass">
                Activité
              </legend>
              <div class="grid grid-cols-2 gap-3">
                <div
                  class="rounded-lg p-3 border"
                  :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-zinc-50 border-zinc-100'"
                >
                  <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-emerald-400' : 'text-emerald-600'">
                    {{ (panelEntity as any).patients_count || 0 }}
                  </p>
                  <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Patients</p>
                </div>
                <div
                  class="rounded-lg p-3 border"
                  :class="dark ? 'bg-slate-800/60 border-slate-700' : 'bg-zinc-50 border-zinc-100'"
                >
                  <p class="text-lg font-bold tabular-nums" :class="dark ? 'text-sky-400' : 'text-sky-600'">
                    {{ (panelEntity as any).users_count || 0 }}
                  </p>
                  <p class="text-[11px]" :class="dark ? 'text-slate-500' : 'text-zinc-400'">Professionnels</p>
                </div>
              </div>
            </fieldset>
          </div>

          <!-- ═══════════════════════════════════════════════
               BODY — Mode CREATE / EDIT (formulaire)
               ═══════════════════════════════════════════════ -->
          <div v-else-if="panelMode === 'create' || panelMode === 'edit'" class="flex-1 overflow-y-auto px-6 py-5">

            <!-- Bandeau rattachement auto -->
            <Message
              v-if="panelMode === 'create' && panelParentId"
              severity="info"
              :closable="false"
              class="text-sm mb-5"
            >
              <span>
                Rattachée automatiquement à
                <strong>{{ entities.find(e => e.id === panelParentId)?.name || rootEntity?.name }}</strong>
              </span>
            </Message>

            <!-- ═══════ RECHERCHE ENTREPRISE (create only) ═══════ -->
            <div v-if="panelMode === 'create'" class="mb-6">
              <div
                class="rounded-xl p-4 border"
                :class="dark ? 'bg-violet-500/10 border-violet-500/20' : 'bg-violet-50/60 border-violet-200'"
              >
                <div class="flex items-center gap-2 mb-3">
                  <i
                    class="pi pi-search text-sm"
                    :class="dark ? 'text-violet-400' : 'text-violet-500'"
                  ></i>
                  <span
                    class="text-xs font-semibold uppercase tracking-wider"
                    :class="dark ? 'text-violet-400' : 'text-violet-600'"
                  >
                    Recherche automatique
                  </span>
                </div>
                <p class="text-xs mb-3" :class="dark ? 'text-slate-400' : 'text-zinc-500'">
                  Saisissez le SIRET ou le nom de la structure pour pré-remplir le formulaire.
                </p>

                <div class="relative search-dropdown-container">
                  <div class="flex gap-2">
                    <div class="relative flex-1">
                      <InputText
                        v-model="searchQuery"
                        :placeholder="searchFilled ? '' : 'SIRET ou nom de la structure…'"
                        :class="inputClass"
                        class="w-full !pr-8"
                        :disabled="searchFilled"
                        @input="onSearchInput"
                        @focus="searchResults.length > 0 && (showSearchResults = true)"
                      />
                      <!-- Spinner dans le champ -->
                      <i
                        v-if="searchLoading"
                        class="pi pi-spinner pi-spin absolute right-3 top-1/2 -translate-y-1/2 text-xs"
                        :class="dark ? 'text-slate-500' : 'text-zinc-400'"
                      ></i>
                    </div>
                    <!-- Bouton reset si une entreprise est sélectionnée -->
                    <button
                      v-if="searchFilled"
                      class="px-3 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5"
                      :class="dark
                        ? 'text-slate-400 hover:text-white bg-slate-700 hover:bg-slate-600'
                        : 'text-zinc-500 hover:text-zinc-700 bg-zinc-100 hover:bg-zinc-200'"
                      title="Nouvelle recherche"
                      @click="clearSearch"
                    >
                      <i class="pi pi-refresh text-xs"></i>
                      Changer
                    </button>
                  </div>

                  <!-- Dropdown résultats -->
                  <Transition name="dropdown-fade">
                    <div
                      v-if="showSearchResults"
                      class="absolute z-50 left-0 right-0 mt-1 rounded-xl border shadow-xl overflow-hidden"
                      :class="dark ? 'bg-slate-800 border-slate-700' : 'bg-white border-zinc-200 shadow-zinc-200/50'"
                    >
                      <button
                        v-for="(result, idx) in searchResults"
                        :key="idx"
                        class="w-full text-left px-4 py-3 transition-colors border-b last:border-b-0"
                        :class="dark
                          ? 'border-slate-700 hover:bg-slate-700/50'
                          : 'border-zinc-100 hover:bg-violet-50/50'"
                        @click="selectEntreprise(result)"
                      >
                        <div class="flex items-start justify-between gap-3">
                          <div class="min-w-0">
                            <p
                              class="text-sm font-medium truncate"
                              :class="dark ? 'text-white' : 'text-zinc-800'"
                            >
                              {{ result.nom_complet || result.nom_raison_sociale }}
                            </p>
                            <p
                              class="text-xs mt-0.5 truncate"
                              :class="dark ? 'text-slate-400' : 'text-zinc-500'"
                            >
                              <template v-if="result.siege?.code_postal">
                                {{ result.siege.code_postal }}
                                {{ result.siege.libelle_commune }}
                              </template>
                              <template v-if="result.siege?.code_postal && result.siege?.siret">
                                —
                              </template>
                              <template v-if="result.siege?.siret">
                                <span class="font-mono">{{ result.siege.siret }}</span>
                              </template>
                            </p>
                          </div>
                          <span
                            v-if="result.nature_juridique"
                            class="text-[10px] px-1.5 py-0.5 rounded flex-shrink-0"
                            :class="dark ? 'bg-slate-700 text-slate-400' : 'bg-zinc-100 text-zinc-400'"
                          >
                            {{ result.nature_juridique }}
                          </span>
                        </div>
                      </button>

                      <!-- Aucun résultat -->
                      <div
                        v-if="searchResults.length === 0 && !searchLoading"
                        class="px-4 py-3 text-center"
                      >
                        <p class="text-xs" :class="dark ? 'text-slate-500' : 'text-zinc-400'">
                          Aucune entreprise trouvée
                        </p>
                      </div>
                    </div>
                  </Transition>
                </div>

                <!-- Confirmation de sélection -->
                <Transition name="dropdown-fade">
                  <div
                    v-if="searchFilled"
                    class="mt-3 flex items-center gap-2 text-xs"
                    :class="dark ? 'text-emerald-400' : 'text-emerald-600'"
                  >
                    <i class="pi pi-check-circle text-sm"></i>
                    <span>Champs pré-remplis — vérifiez et complétez si nécessaire.</span>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- ═══════ FIELDSET IDENTIFICATION ═══════ -->
            <fieldset class="mb-6">
              <legend
                class="text-xs font-semibold uppercase tracking-wider mb-4"
                :class="fieldsetLegendClass"
              >
                Identification
              </legend>

              <div class="space-y-4">
                <!-- Code structure (lecture seule — racine uniquement) -->
                <div v-if="panelMode === 'edit' && panelEntity && !panelEntity.parent_id && tenantCode">
                  <label class="block text-sm font-medium mb-1.5" :class="labelClass">
                    Code structure
                  </label>
                  <div
                    class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm border font-mono font-bold"
                    :class="dark
                      ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                      : 'bg-amber-50 border-amber-200 text-amber-700'"
                  >
                    <i class="pi pi-key text-xs" :class="dark ? 'text-amber-400' : 'text-amber-500'"></i>
                    {{ tenantCode }}
                    <span
                      class="ml-auto text-[10px] font-sans font-medium px-1.5 py-0.5 rounded"
                      :class="dark ? 'bg-slate-700 text-slate-400' : 'bg-slate-100 text-slate-400'"
                    >
                      non modifiable
                    </span>
                  </div>
                  <small class="text-xs mt-1 block" :class="dark ? 'text-slate-500' : 'text-slate-400'">
                    Code communiqué aux utilisateurs pour se connecter
                  </small>
                </div>

                <!-- Type (create only) -->
                <div v-if="panelMode === 'create'">
                  <label class="block text-sm font-medium mb-1.5" :class="labelClass">
                    Type de structure <span class="text-red-500">*</span>
                  </label>
                  <Dropdown
                    v-model="form.entity_type"
                    :options="typeOptions"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Sélectionner un type"
                    :class="[inputClass, { 'p-invalid': errors.entity_type }]"
                    panelClass="entity-type-panel"
                    appendTo="body"
                  />
                  <small v-if="errors.entity_type" class="text-red-500 text-xs mt-1 block">
                    {{ errors.entity_type }}
                  </small>
                </div>

                <!-- Type (edit — lecture seule, texte simple sans chevron) -->
                <div v-else>
                  <label class="block text-sm font-medium mb-1.5" :class="labelClass">
                    Type de structure
                  </label>
                  <div
                    class="px-3 py-2.5 rounded-lg text-sm border"
                    :class="dark
                      ? 'bg-slate-800/50 border-slate-700 text-slate-300'
                      : 'bg-slate-50 border-slate-200 text-slate-600'"
                  >
                    {{ form.entity_type ? EntityTypeLabels[form.entity_type] : '—' }}
                  </div>
                </div>

                <!-- Nom -->
                <div>
                  <label class="block text-sm font-medium mb-1.5" :class="labelClass">
                    Nom <span class="text-red-500">*</span>
                  </label>
                  <InputText
                    v-model="form.name"
                    placeholder="Ex : SSIAD de Paris Nord"
                    :class="[inputClass, { 'p-invalid': errors.name }]"
                  />
                  <small v-if="errors.name" class="text-red-500 text-xs mt-1 block">
                    {{ errors.name }}
                  </small>
                </div>

                <!-- FINESS -->
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      FINESS Juridique (EJ)
                    </label>
                    <InputText
                      v-model="form.finess_juridique"
                      placeholder="9 chiffres"
                      maxlength="9"
                      :class="[inputClass, 'font-mono text-sm', { 'p-invalid': errors.finess_juridique }]"
                    />
                    <small v-if="errors.finess_juridique" class="text-red-500 text-xs mt-1 block">
                      {{ errors.finess_juridique }}
                    </small>
                  </div>
                  <div>
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      FINESS Géographique (ET)
                    </label>
                    <InputText
                      v-model="form.finess_geo"
                      placeholder="9 chiffres"
                      maxlength="9"
                      :class="[inputClass, 'font-mono text-sm', { 'p-invalid': errors.finess_geo }]"
                    />
                    <small v-if="errors.finess_geo" class="text-red-500 text-xs mt-1 block">
                      {{ errors.finess_geo }}
                    </small>
                  </div>
                </div>

                <!-- SIRET -->
                <div>
                  <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                    SIRET
                    <span v-if="siretInherited" class="text-emerald-500 font-normal ml-1">
                      (hérité de l'entité parente)
                    </span>
                  </label>
                  <InputText
                    v-model="form.siret"
                    placeholder="14 chiffres"
                    :disabled="siretInherited"
                    :class="[
                      inputClass,
                      'font-mono text-sm',
                      { 'p-invalid': errors.siret },
                      siretInherited ? 'opacity-60 cursor-not-allowed' : '',
                    ]"
                  />
                  <small v-if="siretInherited" class="text-emerald-600 text-xs mt-1 block">
                    <i class="pi pi-lock text-[10px] mr-1"></i>
                    Même établissement juridique — le SIRET n'est pas dupliqué en base
                  </small>
                  <small v-else-if="errors.siret" class="text-red-500 text-xs mt-1 block">
                    {{ errors.siret }}
                  </small>
                </div>
              </div>
            </fieldset>

            <!-- ═══════ FIELDSET COORDONNÉES ═══════ -->
            <fieldset>
              <legend
                class="text-xs font-semibold uppercase tracking-wider mb-4"
                :class="fieldsetLegendClass"
              >
                Coordonnées
              </legend>

              <div class="space-y-4">
                <!-- Adresse -->
                <div>
                  <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                    Adresse
                  </label>
                  <Textarea
                    v-model="form.address"
                    placeholder="Numéro, rue, complément..."
                    :class="inputClass"
                    rows="2"
                    autoResize
                  />
                </div>

                <!-- CP + Ville -->
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      Code postal
                    </label>
                    <InputText v-model="form.postal_code" placeholder="75000" :class="inputClass" />
                  </div>
                  <div class="col-span-2">
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      Ville
                    </label>
                    <InputText v-model="form.city" placeholder="Paris" :class="inputClass" />
                  </div>
                </div>

                <!-- Email + Téléphone -->
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      Email
                    </label>
                    <InputText
                      v-model="form.email"
                      type="email"
                      placeholder="contact@structure.fr"
                      :class="[inputClass, { 'p-invalid': errors.email }]"
                    />
                    <small v-if="errors.email" class="text-red-500 text-xs mt-1 block">
                      {{ errors.email }}
                    </small>
                  </div>
                  <div>
                    <label class="block text-xs font-medium mb-1.5" :class="labelSmallClass">
                      Téléphone
                    </label>
                    <InputText v-model="form.phone" placeholder="01 23 45 67 89" :class="inputClass" />
                  </div>
                </div>
              </div>
            </fieldset>
          </div>

          <!-- ═══════════════════════════════════════════════
               FOOTER
               ═══════════════════════════════════════════════ -->
          <div
            class="flex items-center justify-end gap-3 px-6 py-4 border-t flex-shrink-0"
            :class="dark ? 'border-slate-700' : 'border-zinc-100'"
          >
            <!-- Mode VIEW : Supprimer | Fermer + Modifier -->
            <template v-if="panelMode === 'view'">
              <div class="flex items-center justify-between w-full">
                <!-- Gauche : Supprimer (masqué pour la racine en mode admin) -->
                <Button
                  v-if="canDeletePanelEntity"
                  label="Supprimer"
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  size="small"
                  @click="confirmDeleteFromPanel"
                />
                <div v-else />
                <!-- Droite : Fermer + Modifier -->
                <div class="flex items-center gap-3">
                  <Button
                    label="Fermer"
                    severity="secondary"
                    text
                    size="small"
                    @click="closePanel"
                  />
                  <Button
                    label="Modifier"
                    icon="pi pi-pencil"
                    severity="secondary"
                    outlined
                    size="small"
                    @click="switchToEdit"
                  />
                </div>
              </div>
            </template>

            <!-- Mode CREATE / EDIT : Annuler + Sauvegarder -->
            <template v-else>
              <Button
                label="Annuler"
                severity="secondary"
                text
                size="small"
                @click="closePanel"
              />
              <Button
                :label="panelMode === 'create' ? 'Créer l\'entité' : 'Enregistrer'"
                :icon="panelMode === 'create' ? 'pi pi-plus' : 'pi pi-check'"
                size="small"
                :loading="panelSubmitting"
                :disabled="!isFormValid || panelSubmitting"
                @click="handlePanelSubmit"
              />
            </template>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ═════════════════════════════════════════════════════════════════
         DIALOG SUPPRESSION
         ═════════════════════════════════════════════════════════════════ -->
    <Dialog
      v-model:visible="deleteDialogVisible"
      modal
      header="Confirmer la suppression"
      :style="{ width: '480px' }"
      :closable="!deleteSubmitting"
    >
      <div class="flex items-start gap-3 py-2">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
          :class="deleteDescendantsCount > 0 ? 'bg-red-500/20' : 'bg-red-100'"
        >
          <i class="pi pi-exclamation-triangle text-red-500"></i>
        </div>
        <div>
          <p class="text-sm text-zinc-700">
            Supprimer <strong>{{ entityToDelete?.name }}</strong> de l'organisation ?
          </p>

          <!-- Warning cascade si entité avec enfants -->
          <template v-if="deleteDescendantsCount > 0">
            <div class="mt-3 p-3 rounded-lg bg-red-50 border border-red-200">
              <p class="text-xs font-semibold text-red-700 mb-1.5">
                <i class="pi pi-exclamation-circle mr-1"></i>
                Suppression en cascade
              </p>
              <p class="text-xs text-red-600">
                Cette entité est une structure principale à laquelle
                {{ deleteDescendantsCount === 1 ? 'est rattachée' : 'sont rattachées' }}
                <strong>{{ deleteDescendantsCount }} entité{{ deleteDescendantsCount > 1 ? 's' : '' }}</strong>.
                La suppression entraînera la suppression de toutes les entités rattachées :
              </p>
              <ul class="mt-2 space-y-0.5">
                <li
                  v-for="(name, index) in deleteChildrenNames"
                  :key="index"
                  class="text-xs text-red-600 flex items-center gap-1.5"
                >
                  <i class="pi pi-minus text-[8px] text-red-400"></i>
                  {{ name }}
                </li>
              </ul>
            </div>
            <p class="text-xs text-zinc-500 mt-2">
              Les patients et professionnels associés à ces entités devront être réaffectés.
            </p>
          </template>

          <!-- Message simple si pas d'enfants -->
          <p v-else class="text-xs text-zinc-400 mt-1.5">
            Cette entité sera retirée de l'arborescence. Les données associées
            (patients, professionnels) devront être réaffectées.
          </p>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-2">
          <Button
            label="Annuler"
            severity="secondary"
            text
            size="small"
            :disabled="deleteSubmitting"
            @click="deleteDialogVisible = false"
          />
          <Button
            :label="deleteDescendantsCount > 0 ? 'Supprimer tout' : 'Supprimer'"
            severity="danger"
            size="small"
            icon="pi pi-trash"
            :loading="deleteSubmitting"
            @click="handleDelete"
          />
        </div>
      </template>
    </Dialog>

    <!-- ═════════════════════════════════════════════════════════════════
         DIALOG RE-PARENTAGE ORPHELINS
         ═════════════════════════════════════════════════════════════════ -->
    <Dialog
      v-model:visible="orphanDialogVisible"
      modal
      header="Structure à corriger"
      :style="{ width: '460px' }"
      :closable="true"
      @hide="cancelOrphans"
    >
      <div class="flex items-start gap-3 py-2">
        <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-amber-100">
          <i class="pi pi-exclamation-triangle text-amber-500"></i>
        </div>
        <div>
          <p class="text-sm text-zinc-700">
            <strong>{{ orphanCount }} entité{{ orphanCount > 1 ? 's' : '' }}</strong>
            {{ orphanCount > 1 ? 'ne sont pas rattachées' : 'n\'est pas rattachée' }}
            à la structure racine.
          </p>
          <p class="text-xs text-zinc-500 mt-2">
            Souhaitez-vous rattacher automatiquement
            {{ orphanCount > 1 ? 'ces entités' : 'cette entité' }}
            à <strong>{{ orphanRootName }}</strong> ?
          </p>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-end gap-2">
          <Button
            label="Plus tard"
            severity="secondary"
            text
            size="small"
            @click="cancelOrphans"
          />
          <Button
            label="Rattacher"
            icon="pi pi-link"
            size="small"
            @click="confirmOrphans"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
/* ── Fieldset reset ── */
fieldset {
  border: none;
  padding: 0;
  margin: 0;
}

/* ── Dropdown search results ── */
.dropdown-fade-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-fade-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
