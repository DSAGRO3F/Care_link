<script setup lang="ts">
  /**
   * PatientIdentityBanner — Bandeau d'identitovigilance patient.
   *
   * Composant standalone affiché en haut des pages où l'utilisateur manipule
   * un dossier patient (création de plan d'aide, édition, etc.). Concept
   * d'identitovigilance standard du médico-social : réduire le risque
   * d'erreur d'identification en exposant en permanence les discriminants
   * (nom + prénom + date de naissance + adresse).
   *
   * Convention RGPD : le NIR n'est JAMAIS affiché dans ce bandeau.
   *
   * Props : patient — contrat minimal structurel (7 champs d'identitovigilance
   * réellement lus). Champs optionnels ET nullables (`?: T | null`) pour
   * accepter structurellement les deux styles de miroir du codebase :
   * `PatientResponse` (champs `?:`, surensemble, page plan d'aide) comme
   * `PatientIdentity` (champs `| null`, sous-ensemble minimisé, portail
   * valideur). Évite de coupler ce composant générique à un type de module.
   */
  import { computed } from 'vue';

  interface Props {
    patient: {
      first_name?: string | null;
      last_name?: string | null;
      birth_date?: string | null;
      address?: string | null;
      postal_code?: string | null;
      city?: string | null;
      current_gir?: number | null;
    };
  }

  const props = defineProps<Props>();

  // =============================================================================
  // COMPUTED — formatage affichage
  // =============================================================================

  /** Nom complet en MAJUSCULES + Prénom (convention identitovigilance). */
  const fullName = computed(() => {
    const last = props.patient.last_name?.toUpperCase() ?? '';
    const first = props.patient.first_name ?? '';
    const composed = `${last} ${first}`.trim();
    return composed || 'Patient sans nom';
  });

  /** Initiales pour l'avatar (prénom + nom). */
  const initials = computed(() => {
    const first = props.patient.first_name?.[0] ?? '';
    const last = props.patient.last_name?.[0] ?? '';
    const composed = `${first}${last}`.toUpperCase();
    return composed || '?';
  });

  /** Date de naissance formatée fr-FR (JJ/MM/AAAA). */
  const formattedBirthDate = computed(() => {
    if (!props.patient.birth_date) return null;
    const date = new Date(props.patient.birth_date);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  });

  /** Âge calculé en années révolues. */
  const age = computed(() => {
    if (!props.patient.birth_date) return null;
    const birth = new Date(props.patient.birth_date);
    if (Number.isNaN(birth.getTime())) return null;
    const today = new Date();
    let years = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      years--;
    }
    return years >= 0 ? years : null;
  });

  /** Adresse complète sur une ligne (rue — code postal ville). */
  const fullAddress = computed(() => {
    const parts: string[] = [];
    if (props.patient.address) parts.push(props.patient.address);
    const cityLine = [props.patient.postal_code, props.patient.city].filter(Boolean).join(' ');
    if (cityLine) parts.push(cityLine);
    return parts.length > 0 ? parts.join(' — ') : null;
  });

  /** Badge GIR avec coloration sémantique sobre (palette atténuée). */
  const girBadge = computed(() => {
    const gir = props.patient.current_gir;
    if (gir === undefined || gir === null) {
      return {
        label: 'GIR non évalué',
        classes: 'bg-slate-100 text-slate-600 border-slate-200',
      };
    }
    let classes: string;
    if (gir <= 2) {
      // Forte dépendance
      classes = 'bg-rose-50 text-rose-700 border-rose-200';
    } else if (gir <= 4) {
      // Dépendance modérée
      classes = 'bg-amber-50 text-amber-700 border-amber-200';
    } else {
      // Autonomie préservée
      classes = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    return {
      label: `GIR ${gir}`,
      classes,
    };
  });
</script>

<template>
  <section
    class="patient-identity-banner flex items-center gap-4 rounded-lg border border-slate-200 bg-white px-5 py-4 shadow-sm"
    aria-label="Identité du patient"
  >
    <!-- Avatar initiales -->
    <div
      class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-teal-50 text-base font-semibold text-teal-700 ring-1 ring-teal-100"
      aria-hidden="true"
    >
      {{ initials }}
    </div>

    <!-- Bloc identité principal -->
    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 class="truncate text-base font-semibold text-slate-900">
          {{ fullName }}
        </h2>
        <span v-if="formattedBirthDate" class="text-sm text-slate-600">
          Né(e) le {{ formattedBirthDate }}
          <span v-if="age !== null" class="text-slate-400">· {{ age }} ans</span>
        </span>
      </div>
      <p v-if="fullAddress" class="mt-0.5 flex items-center gap-1 truncate text-xs text-slate-500">
        <i class="pi pi-map-marker text-xs" aria-hidden="true" />
        <span class="truncate">{{ fullAddress }}</span>
      </p>
    </div>

    <!-- Badge GIR -->
    <div class="shrink-0">
      <span
        :class="[
          'inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium',
          girBadge.classes,
        ]"
      >
        {{ girBadge.label }}
      </span>
    </div>
  </section>
</template>
