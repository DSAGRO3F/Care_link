/**
 * CareLink - Utilitaires partagés des formateurs d'évaluation
 * Chemin : frontend/src/components/evaluation/formatters/utils.ts
 *
 * Fonctions extraites de ContactsSection, UsagerSection, DispositifsSection,
 * SanteBlocSection, PoaSection, PoaAutonomieSection pour éviter la duplication.
 */

/**
 * Formate un numéro de téléphone français (10 chiffres) en groupes de 2.
 * Ex: "0612345678" → "06 12 34 56 78"
 */
export function formatPhone(phone?: string): string {
  if (!phone) return '';
  const cleaned = phone.replace(/\D/g, '');
  return cleaned.length === 10 ? cleaned.replace(/(\d{2})(?=\d)/g, '$1 ').trim() : phone;
}

/**
 * Formate une date ISO en format français (JJ/MM/AAAA).
 */
export function formatDate(date?: string): string {
  if (!date) return '';
  try {
    return new Date(date).toLocaleDateString('fr-FR');
  } catch {
    return date;
  }
}

/**
 * Formate une date/heure ISO en format français (JJ/MM/AAAA HH:MM).
 */
export function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Retourne la classe CSS correspondant au niveau de préoccupation AGGIR.
 * Utilisé par PoaSection et PoaAutonomieSection.
 */
export function getPreoccLevel(level?: string): string {
  const l = level?.toLowerCase() || '';
  if (l.includes('élevé') && !l.includes('assez')) return 'high';
  if (l.includes('assez élevé')) return 'medium-high';
  if (l.includes('assez faible')) return 'medium-low';
  if (l.includes('faible')) return 'low';
  return 'medium';
}
