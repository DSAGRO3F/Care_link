/**
 * Store Pinia pour l'authentification
 * Gère l'état de connexion, les tokens JWT, l'utilisateur courant
 *
 * 🔧 S4.1-A : Debounce guards sur loginWithCredentials, changePassword, handlePSCCallback
 * 🔧 S4.1-B : fetchCurrentUser() ne fait plus logout() — seul initialize() décide
 * 🔧 S4.1-C : Écoute 'auth:tokens-refreshed' pour synchroniser Pinia après refresh intercepteur
 * 🔧 S4.1-D : refreshToken exposé dans le return du store
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authService } from '@/services';
import type { AuthenticatedUser, LoginResponse } from '@/types';

export const useAuthStore = defineStore('auth', () => {
  // ===========================================================================
  // STATE
  // ===========================================================================

  const user = ref<AuthenticatedUser | null>(null);
  const accessToken = ref<string | null>(null);
  const refreshToken = ref<string | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const tenantCode = ref<string | null>(null);

  // ===========================================================================
  // GETTERS
  // ===========================================================================

  /** L'utilisateur est-il connecté ? */
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value);

  /** L'utilisateur est-il admin ? */
  const isAdmin = computed(() => user.value?.is_admin ?? false);

  /** Rôles de l'utilisateur */
  const userRoles = computed(() => user.value?.roles ?? []);

  /** ID du tenant courant */
  const currentTenantId = computed(() => user.value?.tenant_id);

  /** Nom complet de l'utilisateur */
  const fullName = computed(() => user.value?.full_name ?? '');

  /** Forcer chgt. mot de passe après 1ère auth. */
  const mustChangePassword = computed(() => user.value?.must_change_password ?? false);

  // ===========================================================================
  // 🔧 S4.1-C : Synchronisation tokens après refresh intercepteur
  // ===========================================================================

  /**
   * L'intercepteur Axios (api.ts) dispatch un CustomEvent après un refresh
   * réussi. On écoute cet événement pour synchroniser l'état Pinia avec
   * les nouveaux tokens déjà stockés dans localStorage.
   */
  if (typeof window !== 'undefined') {
    window.addEventListener('auth:tokens-refreshed', ((event: CustomEvent) => {
      accessToken.value = event.detail.accessToken;
      refreshToken.value = event.detail.refreshToken;
    }) as EventListener);
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  /** Connexion email/mot de passe */
  async function loginWithCredentials(tenantCode_: string, email: string, password: string) {
    // 🔧 S4.1-A : Debounce — ignorer si déjà en cours
    if (isLoading.value) return;

    isLoading.value = true;
    error.value = null;

    try {
      const response = await authService.login({ tenant_code: tenantCode_, email, password });
      handleLoginSuccess(response);
      // 🆕 Stocker le tenant_code pour l'afficher dans les pages admin
      tenantCode.value = tenantCode_;
      localStorage.setItem('tenant_code', tenantCode_);
      return response;
    } catch (err) {
      error.value = 'Identifiants invalides';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /** Forcer cht. mot de passe après 1ère auth */
  async function changePassword(currentPassword: string, newPassword: string) {
    // 🔧 S4.1-A : Debounce
    if (isLoading.value) return;

    isLoading.value = true;
    error.value = null;
    try {
      const response = await authService.changePassword(currentPassword, newPassword);
      handleLoginSuccess(response);
      return response;
    } catch (err) {
      error.value = 'Erreur lors du changement de mot de passe';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /** Redirection vers PSC pour authentification */
  async function loginWithPSC(redirectAfter?: string) {
    try {
      const { authorization_url } = await authService.getPSCLoginUrl(redirectAfter);
      window.location.href = authorization_url;
    } catch (err) {
      error.value = 'Impossible de se connecter à Pro Santé Connect';
      throw err;
    }
  }

  /** Traitement du callback PSC */
  async function handlePSCCallback(code: string, state: string) {
    // 🔧 S4.1-A : Debounce
    if (isLoading.value) return;

    isLoading.value = true;
    error.value = null;

    try {
      const response = await authService.pscCallback(code, state);
      handleLoginSuccess(response);
      return response;
    } catch (err) {
      error.value = "Erreur lors de l'authentification PSC";
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /** Traitement du login réussi - stocke user et tokens */
  function handleLoginSuccess(response: LoginResponse) {
    user.value = response.user;
    accessToken.value = response.tokens.access_token;
    refreshToken.value = response.tokens.refresh_token;

    // Persistance localStorage
    localStorage.setItem('access_token', response.tokens.access_token);
    localStorage.setItem('refresh_token', response.tokens.refresh_token);
  }

  /** Renouveler les tokens */
  async function refreshTokens() {
    if (!refreshToken.value) {
      throw new Error('Pas de refresh token');
    }

    const tokens = await authService.refresh(refreshToken.value);
    accessToken.value = tokens.access_token;
    refreshToken.value = tokens.refresh_token;

    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);

    return tokens;
  }

  /**
   * Récupérer l'utilisateur courant.
   *
   * 🔧 S4.1-B : Ne fait plus logout() en cas d'erreur.
   * Raison : l'intercepteur Axios gère le refresh automatiquement sur 401.
   * Si une erreur réseau transitoire survient, on ne veut pas perdre la session.
   * C'est initialize() qui décide de logout() si fetchCurrentUser échoue.
   */
  async function fetchCurrentUser() {
    if (!accessToken.value) return null;

    try {
      user.value = await authService.getMe();
      return user.value;
    } catch {
      // 🔧 S4.1-B : On retourne null sans logout()
      // L'intercepteur a déjà tenté le refresh si c'était un 401.
      // Si c'est une erreur transitoire, la session reste intacte.
      user.value = null;
      return null;
    }
  }

  /** Déconnexion */
  function logout() {
    user.value = null;
    accessToken.value = null;
    refreshToken.value = null;
    tenantCode.value = null;
    error.value = null;

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('tenant_code');
  }

  /**
   * Initialisation au démarrage - restaure la session.
   *
   * 🔧 S4.1-B : Si fetchCurrentUser() échoue (même après refresh intercepteur),
   * on appelle logout() pour nettoyer proprement.
   * Avant ce fix, fetchCurrentUser faisait un logout() interne sur TOUTE erreur
   * (y compris réseau transitoire), ce qui causait des déconnexions intempestives.
   */
  async function initialize() {
    accessToken.value = localStorage.getItem('access_token');
    refreshToken.value = localStorage.getItem('refresh_token');
    tenantCode.value = localStorage.getItem('tenant_code');

    if (accessToken.value) {
      const result = await fetchCurrentUser();
      if (!result) {
        // L'intercepteur a tenté le refresh si c'était un 401.
        // Si on arrive ici sans user, la session est irrécupérable → nettoyage.
        logout();
      }
    }
  }

  /** Vérifier si l'utilisateur a un rôle spécifique */
  function hasRole(role: string): boolean {
    return userRoles.value.includes(role);
  }

  /** Vérifier si l'utilisateur a au moins un des rôles */
  function hasAnyRole(roles: string[]): boolean {
    return roles.some((role) => userRoles.value.includes(role));
  }

  // ===========================================================================
  // RETURN
  // ===========================================================================

  return {
    // State
    user,
    accessToken,
    refreshToken, // 🔧 S4.1-D : exposé (était manquant)
    tenantCode,
    isLoading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    userRoles,
    currentTenantId,
    fullName,
    mustChangePassword,

    // Actions
    loginWithCredentials,
    loginWithPSC,
    handlePSCCallback,
    refreshTokens,
    fetchCurrentUser,
    logout,
    initialize,
    hasRole,
    hasAnyRole,
    changePassword,
  };
});
