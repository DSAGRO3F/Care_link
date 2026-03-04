/**
 * Store Pinia pour l'état de l'interface utilisateur
 * Sidebar, modales, thème, breakpoints
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUiStore = defineStore('ui', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================
  
  /** Sidebar ouverte (desktop) */
  const sidebarOpen = ref(true)
  
  /** Menu mobile ouvert */
  const mobileMenuOpen = ref(false)
  
  /** Largeur de la fenêtre */
  const windowWidth = ref(window.innerWidth)
  
  /** Thème sombre activé */
  const darkMode = ref(false)

  // ===========================================================================
  // GETTERS
  // ===========================================================================
  
  /** Est-on sur mobile ? (<768px) */
  const isMobile = computed(() => windowWidth.value < 768)
  
  /** Est-on sur tablette ? (768-1024px) */
  const isTablet = computed(() => windowWidth.value >= 768 && windowWidth.value < 1024)
  
  /** Est-on sur desktop ? (>=1024px) */
  const isDesktop = computed(() => windowWidth.value >= 1024)
  
  /** Breakpoint actuel */
  const breakpoint = computed(() => {
    if (windowWidth.value < 640) return 'xs'
    if (windowWidth.value < 768) return 'sm'
    if (windowWidth.value < 1024) return 'md'
    if (windowWidth.value < 1280) return 'lg'
    return 'xl'
  })

  // ===========================================================================
  // ACTIONS
  // ===========================================================================
  
  /** Initialiser les listeners de resize */
  function initialize() {
    window.addEventListener('resize', handleResize)
    
    // Charger le thème depuis localStorage
    const savedDarkMode = localStorage.getItem('carelink_dark_mode')
    if (savedDarkMode === 'true') {
      setDarkMode(true)
    }
  }

  /** Nettoyer les listeners */
  function cleanup() {
    window.removeEventListener('resize', handleResize)
  }

  /** Handler resize */
  function handleResize() {
    windowWidth.value = window.innerWidth
    
    // Fermer le menu mobile si on passe en desktop
    if (isDesktop.value) {
      mobileMenuOpen.value = false
    }
  }

  /** Toggle sidebar desktop */
  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  /** Toggle menu mobile */
  function toggleMobileMenu() {
    mobileMenuOpen.value = !mobileMenuOpen.value
  }

  /** Fermer le menu mobile */
  function closeMobileMenu() {
    mobileMenuOpen.value = false
  }

  /** Activer/désactiver le mode sombre */
  function setDarkMode(value: boolean) {
    darkMode.value = value
    localStorage.setItem('carelink_dark_mode', String(value))
    
    // Appliquer la classe sur le document
    if (value) {
      document.documentElement.classList.add('dark-mode')
    } else {
      document.documentElement.classList.remove('dark-mode')
    }
  }

  /** Toggle mode sombre */
  function toggleDarkMode() {
    setDarkMode(!darkMode.value)
  }

  // ===========================================================================
  // RETURN
  // ===========================================================================
  
  return {
    // State
    sidebarOpen,
    mobileMenuOpen,
    windowWidth,
    darkMode,
    
    // Getters
    isMobile,
    isTablet,
    isDesktop,
    breakpoint,
    
    // Actions
    initialize,
    cleanup,
    toggleSidebar,
    toggleMobileMenu,
    closeMobileMenu,
    setDarkMode,
    toggleDarkMode,
  }
})
