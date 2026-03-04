/**
 * Point d'entrée principal de l'application CareLink
 * Configure et monte l'application Vue avec tous ses plugins
 *
 * PrimeVue 4 — Migration vague A (04/03/2026)
 * La configuration Aura/preset était déjà v4. Seul package.json a été mis à jour.
 * Composants renommés dans les templates (vague C/D) : Dropdown→Select, TabView→Tabs
 *
 * PrimeVue 4 — Thème teal CareLink (04/03/2026)
 * definePreset remplace la palette primaire bleue d'Aura par le teal #0d9488 de CareLink.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Composant racine
import App from './App.vue'

// Router
import router from './router'

// PrimeVue et son thème
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'

// Styles globaux
import './assets/styles/main.css'

// =============================================================================
// THÈME CARELINK — Palette primaire teal (04/03/2026)
// Remplace le bleu Aura par défaut par le teal #0d9488 de CareLink.
// Tous les composants PrimeVue (Button, Tabs, focus rings, paginator...)
// héritent automatiquement de cette palette sans override CSS manuel.
// Les espaces Admin et Platform conservent leurs accents propres via leurs
// layouts (slate/teal et violet/indigo) — ce thème est le socle commun.
// =============================================================================
const CareTheme = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '{teal.50}',
      100: '{teal.100}',
      200: '{teal.200}',
      300: '{teal.300}',
      400: '{teal.400}',
      500: '{teal.500}',
      600: '{teal.600}',
      700: '{teal.700}',
      800: '{teal.800}',
      900: '{teal.900}',
      950: '{teal.950}',
    }
  }
})

// Création de l'application Vue
const app = createApp(App)

import Tooltip from 'primevue/tooltip'
app.directive('tooltip', Tooltip)

// =============================================================================
// PLUGINS
// =============================================================================

// Pinia - Gestion d'état (stores)
const pinia = createPinia()
app.use(pinia)

// Vue Router - Navigation
app.use(router)

// PrimeVue - Composants UI
app.use(PrimeVue, {
  theme: {
    preset: CareTheme,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark-mode',
      cssLayer: false,
    },
  },
  // Localisation française
  locale: {
    startsWith: 'Commence par',
    contains: 'Contient',
    notContains: 'Ne contient pas',
    endsWith: 'Se termine par',
    equals: 'Égal à',
    notEquals: 'Différent de',
    noFilter: 'Aucun filtre',
    lt: 'Inférieur à',
    lte: 'Inférieur ou égal à',
    gt: 'Supérieur à',
    gte: 'Supérieur ou égal à',
    dateIs: 'Date égale à',
    dateIsNot: 'Date différente de',
    dateBefore: 'Date avant',
    dateAfter: 'Date après',
    clear: 'Effacer',
    apply: 'Appliquer',
    matchAll: 'Correspond à tous',
    matchAny: 'Correspond à au moins un',
    addRule: 'Ajouter une règle',
    removeRule: 'Supprimer la règle',
    accept: 'Oui',
    reject: 'Non',
    choose: 'Choisir',
    upload: 'Téléverser',
    cancel: 'Annuler',
    dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
    dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
    dayNamesMin: ['Di', 'Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa'],
    monthNames: ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'],
    monthNamesShort: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'],
    today: "Aujourd'hui",
    weekHeader: 'Sem',
    firstDayOfWeek: 1,
    dateFormat: 'dd/mm/yy',
    weak: 'Faible',
    medium: 'Moyen',
    strong: 'Fort',
    passwordPrompt: 'Entrez un mot de passe',
    emptyFilterMessage: 'Aucun résultat trouvé',
    emptyMessage: 'Aucune option disponible',
  },
})

// Services PrimeVue pour les toasts et confirmations
app.use(ToastService)
app.use(ConfirmationService)

// =============================================================================
// INITIALISATION
// =============================================================================

// Initialiser les stores au démarrage
import { useAuthStore } from './stores/auth.store'

// Fonction d'initialisation asynchrone
async function initializeApp() {
  const authStore = useAuthStore()

  // Restaurer la session depuis localStorage si elle existe
  await authStore.initialize()

  // Monter l'application
  app.mount('#app')
}

// Lancer l'initialisation
initializeApp()