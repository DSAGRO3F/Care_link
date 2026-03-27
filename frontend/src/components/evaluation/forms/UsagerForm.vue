<!--
  CareLink - UsagerForm
  Chemin : frontend/src/components/evaluation/forms/UsagerForm.vue

  Rôle : Formulaire de saisie « Usager » — première section du wizard.
         Se pré-remplit depuis les données patient existantes (déchiffrées),
         remonte son état (empty/partial/complete) vers le wizard,
         et sauvegarde ses données dans sectionStates.usager.data.

  Pattern de référence pour les 9 autres formulaires :
    - Props : patient (données déchiffrées) + initialData (brouillon existant)
    - Emits : update:data + update:status
    - onMounted : pré-remplissage → calcul statut → émission
    - watch(formData) : émission à chaque changement

  Style : pattern icon container inspiré de UserDetailPage.vue
          (w-8 h-8 rounded-xl bg-{color}-50 avec icône Lucide)
-->
<template>
  <div class="usager-form">
    <!-- ── Bandeau validation pré-submit ──────────────────────────────── -->
    <div v-if="submitAttempted && submitWarnings.length > 0" class="submit-warnings-banner">
      <AlertTriangle :size="16" :stroke-width="2" />
      <span>
        <strong>Champs recommandés avant soumission :</strong>
        {{ submitWarnings.join(', ') }}
      </span>
    </div>

    <!-- ============================================================= -->
    <!-- BLOC 1 — ÉTAT CIVIL                                           -->
    <!-- ============================================================= -->
    <fieldset class="form-fieldset form-fieldset--blue">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--blue">
          <UserCircle :size="15" :stroke-width="1.8" />
        </span>
        Informations d'état civil
      </legend>

      <div class="form-grid-2">
        <!-- Civilité -->
        <div class="form-group">
          <label for="civilite" class="form-label">Civilité</label>
          <Select
            id="civilite"
            v-model="form.civilite"
            :options="civiliteOptions"
            :class="{ 'p-invalid': submitAttempted && !form.civilite }"
            option-label="label"
            option-value="value"
            placeholder="Sélectionner..."
            class="w-full"
          />
          <small v-if="submitAttempted && !form.civilite" class="form-error">
            Civilité recommandée avant soumission
          </small>
        </div>

        <!-- Sexe -->
        <div class="form-group">
          <label for="sexe" class="form-label">Sexe</label>
          <Select
            id="sexe"
            v-model="form.sexe"
            :options="sexeOptions"
            :class="{ 'p-invalid': submitAttempted && !form.sexe }"
            option-label="label"
            option-value="value"
            placeholder="Sélectionner..."
            class="w-full"
          />
          <small v-if="submitAttempted && !form.sexe" class="form-error">
            Sexe recommandé avant soumission
          </small>
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Nom de famille -->
        <div class="form-group">
          <label for="nomFamille" class="form-label form-label--required"> Nom de famille </label>
          <InputText
            id="nomFamille"
            v-model="form.nomFamille"
            :class="{ 'p-invalid': validationErrors.nomFamille }"
            class="w-full"
            placeholder="Nom de famille"
          />
          <small v-if="validationErrors.nomFamille" class="form-error">
            Le nom de famille est requis
          </small>
        </div>

        <!-- Nom utilisé (si différent) -->
        <div class="form-group">
          <label for="nomUtilise" class="form-label">Nom utilisé</label>
          <InputText
            id="nomUtilise"
            v-model="form.nomUtilise"
            class="w-full"
            placeholder="Si différent du nom de famille"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Prénom utilisé -->
        <div class="form-group">
          <label for="prenomUtilise" class="form-label form-label--required">
            Prénom utilisé
          </label>
          <InputText
            id="prenomUtilise"
            v-model="form.prenomUtilise"
            :class="{ 'p-invalid': validationErrors.prenomUtilise }"
            class="w-full"
            placeholder="Prénom courant"
          />
          <small v-if="validationErrors.prenomUtilise" class="form-error">
            Le prénom est requis
          </small>
        </div>

        <!-- Prénoms acte de naissance -->
        <div class="form-group">
          <label for="prenomsActeNaissance" class="form-label"> Prénom(s) acte de naissance </label>
          <InputText
            id="prenomsActeNaissance"
            v-model="form.prenomsActeNaissance"
            class="w-full"
            placeholder="Tous les prénoms"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Date de naissance — 3 champs séparés + badge âge -->
        <div class="form-group">
          <label class="form-label form-label--required"> Date de naissance </label>
          <div class="birth-date-input">
            <input
              ref="dayRef"
              v-model="birthDay"
              :class="{ 'birth-date-input__field--invalid': validationErrors.dateNaissance }"
              type="text"
              inputmode="numeric"
              maxlength="2"
              placeholder="JJ"
              class="birth-date-input__field birth-date-input__field--short"
              @input="onBirthDayInput"
              @keydown="onBirthFieldKeydown($event, 'day')"
            />
            <span class="birth-date-input__sep">/</span>
            <input
              ref="monthRef"
              v-model="birthMonth"
              :class="{ 'birth-date-input__field--invalid': validationErrors.dateNaissance }"
              type="text"
              inputmode="numeric"
              maxlength="2"
              placeholder="MM"
              class="birth-date-input__field birth-date-input__field--short"
              @input="onBirthMonthInput"
              @keydown="onBirthFieldKeydown($event, 'month')"
            />
            <span class="birth-date-input__sep">/</span>
            <input
              ref="yearRef"
              v-model="birthYear"
              :class="{ 'birth-date-input__field--invalid': validationErrors.dateNaissance }"
              type="text"
              inputmode="numeric"
              maxlength="4"
              placeholder="AAAA"
              class="birth-date-input__field birth-date-input__field--year"
              @input="onBirthYearInput"
              @keydown="onBirthFieldKeydown($event, 'year')"
            />
            <span v-if="computedAge !== null" class="birth-date-input__age">
              {{ computedAge }} ans
            </span>
          </div>
          <small v-if="validationErrors.dateNaissance" class="form-error">
            La date de naissance est requise
          </small>
        </div>

        <!-- Situation familiale -->
        <div class="form-group">
          <label for="situationFamiliale" class="form-label"> Situation familiale </label>
          <Select
            id="situationFamiliale"
            v-model="form.situationFamiliale"
            :options="situationFamilialeOptions"
            option-label="label"
            option-value="value"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Code postal de naissance -->
        <div class="form-group">
          <label for="communeNaissanceCP" class="form-label"> Code postal de naissance </label>
          <InputText
            id="communeNaissanceCP"
            v-model="form.communeNaissanceCP"
            class="w-full"
            placeholder="ex: 75012"
            maxlength="5"
          />
        </div>

        <!-- Commune de naissance -->
        <div class="form-group">
          <label for="communeNaissanceLibelle" class="form-label"> Commune de naissance </label>
          <InputText
            id="communeNaissanceLibelle"
            v-model="form.communeNaissanceLibelle"
            class="w-full"
            placeholder="ex: Paris 12e Arrondissement"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Pays de naissance -->
        <div class="form-group">
          <label for="paysNaissance" class="form-label"> Pays de naissance </label>
          <InputText
            id="paysNaissance"
            v-model="form.paysNaissance"
            class="w-full"
            placeholder="ex: France"
          />
        </div>
      </div>

      <!-- NIR (Sécurité Sociale) -->
      <div class="form-grid-2">
        <div class="form-group">
          <label for="nir" class="form-label"> N° Sécurité Sociale (NIR) </label>
          <InputText
            id="nir"
            v-model="form.nir"
            class="w-full"
            placeholder="1 45 06 79 439 436 66"
          />
        </div>

        <!-- INS (si disponible) -->
        <div class="form-group">
          <label for="ins" class="form-label"> Identifiant National de Santé (INS) </label>
          <InputText id="ins" v-model="form.ins" class="w-full" placeholder="INS" />
        </div>
      </div>
    </fieldset>

    <!-- Séparateur État civil → Adresse -->
    <div class="bloc-separator">
      <div class="bloc-separator__dot"></div>
    </div>

    <!-- ============================================================= -->
    <!-- BLOC 2 — ADRESSE                                              -->
    <!-- ============================================================= -->
    <fieldset class="form-fieldset form-fieldset--amber">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--amber">
          <MapPin :size="15" :stroke-width="1.8" />
        </span>
        Adresse
      </legend>

      <div class="form-group">
        <label for="adresseLigne" class="form-label">N° et nom de rue</label>
        <InputText
          id="adresseLigne"
          v-model="form.adresseLigne"
          :class="{ 'p-invalid': submitAttempted && !form.adresseLigne?.trim() }"
          class="w-full"
          placeholder="Numéro et nom de voie"
        />
        <small v-if="submitAttempted && !form.adresseLigne?.trim()" class="form-error">
          L'adresse est requise
        </small>
      </div>

      <div class="form-group">
        <label for="adresseCommentaire" class="form-label"> Complément d'adresse / accès </label>
        <Textarea
          id="adresseCommentaire"
          v-model="form.adresseCommentaire"
          :auto-resize="true"
          class="w-full"
          rows="2"
          placeholder="Digicode, bâtiment, étage, instructions..."
        />
      </div>

      <div class="form-grid-2">
        <div class="form-group">
          <label for="codePostal" class="form-label">Code postal</label>
          <InputText
            id="codePostal"
            v-model="form.codePostal"
            :class="{ 'p-invalid': submitAttempted && !form.codePostal?.trim() }"
            class="w-full"
            placeholder="ex: 94100"
          />
          <small v-if="submitAttempted && !form.codePostal?.trim()" class="form-error">
            Le code postal est requis
          </small>
        </div>

        <div class="form-group">
          <label for="commune" class="form-label">Commune</label>
          <InputText
            id="commune"
            v-model="form.commune"
            :class="{ 'p-invalid': submitAttempted && !form.commune?.trim() }"
            class="w-full"
            placeholder="ex: Saint-Maur-des-Fossés"
          />
          <small v-if="submitAttempted && !form.commune?.trim()" class="form-error">
            La commune est requise
          </small>
        </div>
      </div>
    </fieldset>

    <!-- Séparateur Adresse → Contacts personnels -->
    <div class="bloc-separator">
      <div class="bloc-separator__dot"></div>
    </div>

    <!-- ============================================================= -->
    <!-- BLOC 3 — CONTACTS PERSONNELS                                  -->
    <!-- ============================================================= -->
    <fieldset class="form-fieldset form-fieldset--emerald">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--emerald">
          <Phone :size="15" :stroke-width="1.8" />
        </span>
        Contacts personnels
      </legend>

      <div class="form-grid-2">
        <div class="form-group">
          <label for="telMobile" class="form-label">Téléphone mobile</label>
          <InputMask
            id="telMobile"
            v-model="form.telMobile"
            :unmask="true"
            :autoClear="false"
            mask="99 99 99 99 99"
            class="w-full"
            placeholder="06 00 00 00 00"
          />
        </div>

        <div class="form-group">
          <label for="telDomicile" class="form-label">Téléphone domicile</label>
          <InputMask
            id="telDomicile"
            v-model="form.telDomicile"
            :unmask="true"
            :autoClear="false"
            mask="99 99 99 99 99"
            class="w-full"
            placeholder="01 00 00 00 00"
          />
        </div>
      </div>

      <div class="form-group">
        <label for="email" class="form-label">Adresse email</label>
        <InputText
          id="email"
          v-model="form.email"
          type="email"
          class="w-full"
          placeholder="prenom.nom@mail.com"
        />
      </div>
    </fieldset>

    <!-- ============================================================= -->
    <!-- BANDEAU PRÉ-REMPLISSAGE                                       -->
    <!-- ============================================================= -->
    <div v-if="prefillApplied" class="form-prefill-banner">
      <Info :size="16" :stroke-width="2" />
      <span>
        Les champs ont été pré-remplis depuis la fiche patient. Vous pouvez les compléter ou les
        modifier.
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - UsagerForm
   * Chemin : frontend/src/components/evaluation/forms/UsagerForm.vue
   *
   * Pattern de référence : chaque formulaire du wizard suit ce modèle.
   */
  import { ref, reactive, computed, watch, onMounted } from 'vue';
  import InputText from 'primevue/inputtext';
  import InputMask from 'primevue/inputmask';
  import Select from 'primevue/select';
  import Textarea from 'primevue/textarea';
  import { UserCircle, MapPin, Phone, Info, AlertTriangle } from 'lucide-vue-next';

  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import type { PatientResponse } from '@/types';

  // ── Props ──────────────────────────────────────────────────────────────

  interface Props {
    /** Données patient déchiffrées (depuis l'API) */
    patient: PatientResponse | null;
    /** Données existantes de la section (brouillon rechargé) */
    initialData?: WizardSectionData;
    /** Passe à true quand l'utilisateur clique "Soumettre" — active la validation visuelle */
    submitAttempted?: boolean;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'update:data', data: WizardSectionData): void;
    (e: 'update:status', status: SectionStatus): void;
  }>();

  // ── Options dropdowns ──────────────────────────────────────────────────

  const civiliteOptions = [
    { label: 'Monsieur', value: 'M' },
    { label: 'Madame', value: 'MME' },
  ];

  const sexeOptions = [
    { label: 'Masculin', value: 'M' },
    { label: 'Féminin', value: 'F' },
  ];

  const situationFamilialeOptions = [
    { label: 'Célibataire', value: 'celibataire' },
    { label: 'Marié(e)', value: 'marie' },
    { label: 'Pacsé(e)', value: 'pacse' },
    { label: 'Divorcé(e)', value: 'divorce' },
    { label: 'Séparé(e)', value: 'separe' },
    { label: 'Veuf/Veuve', value: 'veuf' },
    { label: 'Concubinage', value: 'concubinage' },
  ];

  // ── État du formulaire ─────────────────────────────────────────────────

  const form = reactive({
    // État civil
    civilite: '' as string,
    sexe: '' as string,
    nomFamille: '',
    nomUtilise: '',
    prenomUtilise: '',
    prenomsActeNaissance: '',
    dateNaissance: null as Date | null,
    situationFamiliale: '' as string,
    communeNaissanceCP: '',
    communeNaissanceLibelle: '',
    paysNaissance: '',
    nir: '',
    ins: '',

    // Adresse
    adresseLigne: '',
    adresseCommentaire: '',
    codePostal: '',
    commune: '',

    // Contacts personnels
    telMobile: '',
    telDomicile: '',
    email: '',
  });

  // ── Date de naissance — 3 champs séparés ───────────────────────────────

  const birthDay = ref('');
  const birthMonth = ref('');
  const birthYear = ref('');

  const dayRef = ref<HTMLInputElement | null>(null);
  const monthRef = ref<HTMLInputElement | null>(null);
  const yearRef = ref<HTMLInputElement | null>(null);

  /** Calcul de l'âge à partir des 3 champs */
  const computedAge = computed<number | null>(() => {
    const d = parseInt(birthDay.value, 10);
    const m = parseInt(birthMonth.value, 10);
    const y = parseInt(birthYear.value, 10);

    if (!d || !m || !y || birthYear.value.length < 4) return null;
    if (d < 1 || d > 31 || m < 1 || m > 12 || y < 1900 || y > new Date().getFullYear()) return null;

    const today = new Date();
    let age = today.getFullYear() - y;
    const monthDiff = today.getMonth() + 1 - m;
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < d)) {
      age--;
    }
    return age >= 0 ? age : null;
  });

  /** Synchronise les 3 champs → form.dateNaissance (Date) */
  function syncDateFromFields() {
    const d = parseInt(birthDay.value, 10);
    const m = parseInt(birthMonth.value, 10);
    const y = parseInt(birthYear.value, 10);

    if (
      d &&
      m &&
      y &&
      birthYear.value.length === 4 &&
      d >= 1 &&
      d <= 31 &&
      m >= 1 &&
      m <= 12 &&
      y >= 1900
    ) {
      const date = new Date(y, m - 1, d);
      if (!isNaN(date.getTime()) && date.getDate() === d) {
        form.dateNaissance = date;
        return;
      }
    }
    form.dateNaissance = null;
  }

  /** Peuple les 3 champs depuis un objet Date */
  function setFieldsFromDate(date: Date) {
    birthDay.value = String(date.getDate()).padStart(2, '0');
    birthMonth.value = String(date.getMonth() + 1).padStart(2, '0');
    birthYear.value = String(date.getFullYear());
  }

  /** Filtre les caractères non numériques */
  function sanitizeNumeric(val: string): string {
    return val.replace(/\D/g, '');
  }

  /** Auto-tab vers le champ suivant quand le champ courant est plein */
  function onBirthDayInput() {
    birthDay.value = sanitizeNumeric(birthDay.value);
    if (birthDay.value.length === 2) {
      monthRef.value?.focus();
    }
    syncDateFromFields();
  }

  function onBirthMonthInput() {
    birthMonth.value = sanitizeNumeric(birthMonth.value);
    if (birthMonth.value.length === 2) {
      yearRef.value?.focus();
    }
    syncDateFromFields();
  }

  function onBirthYearInput() {
    birthYear.value = sanitizeNumeric(birthYear.value);
    syncDateFromFields();
  }

  /** Backspace sur champ vide → retour au champ précédent */
  function onBirthFieldKeydown(event: KeyboardEvent, field: 'day' | 'month' | 'year') {
    if (event.key === 'Backspace') {
      if (field === 'month' && birthMonth.value === '') {
        dayRef.value?.focus();
      } else if (field === 'year' && birthYear.value === '') {
        monthRef.value?.focus();
      }
    }
  }

  // ── Validation manuelle (même pattern que PatientCreatePage) ────────────

  const validationErrors = computed(() => {
    const errors: Record<string, string> = {};
    if (!form.nomFamille.trim()) errors.nomFamille = 'Le nom de famille est requis';
    if (!form.prenomUtilise.trim()) errors.prenomUtilise = 'Le prénom est requis';
    if (!form.dateNaissance) errors.dateNaissance = 'La date de naissance est requise';
    return errors;
  });

  // ── Avertissements pré-submit (champs structurants identité + adresse) ───

  const submitWarnings = computed<string[]>(() => {
    const warnings: string[] = [];
    // État civil
    if (!form.civilite) warnings.push('Civilité');
    if (!form.sexe) warnings.push('Sexe');
    if (!form.nomFamille.trim()) warnings.push('Nom de famille');
    if (!form.prenomUtilise.trim()) warnings.push('Prénom');
    if (!form.dateNaissance) warnings.push('Date de naissance');
    // Adresse
    if (!form.adresseLigne?.trim()) warnings.push('N° et nom de rue');
    if (!form.codePostal?.trim()) warnings.push('Code postal');
    if (!form.commune?.trim()) warnings.push('Commune');
    return warnings;
  });

  // ── Indicateur de pré-remplissage ──────────────────────────────────────

  const prefillApplied = ref(false);

  // ── Pré-remplissage depuis les données patient ─────────────────────────

  function prefillFromPatient() {
    const p = props.patient;
    if (!p) return;

    let filled = false;

    // Nom
    if (p.last_name) {
      form.nomFamille = p.last_name;
      form.nomUtilise = p.last_name;
      filled = true;
    }

    // Prénom
    if (p.first_name) {
      form.prenomUtilise = p.first_name;
      form.prenomsActeNaissance = p.first_name;
      filled = true;
    }

    // Date de naissance
    if (p.birth_date) {
      try {
        const d = new Date(p.birth_date);
        if (!isNaN(d.getTime())) {
          form.dateNaissance = d;
          setFieldsFromDate(d);
          filled = true;
        }
      } catch {
        // Ignore parsing errors
      }
    }

    // NIR
    if (p.nir) {
      form.nir = p.nir;
      filled = true;
    }

    // INS
    if (p.ins) {
      form.ins = p.ins;
      filled = true;
    }

    // Adresse : le backend stocke une seule chaîne,
    // on la met dans le champ adresse ligne.
    // Si le patient a des données structurées, on les utilise.
    if (p.address) {
      form.adresseLigne = p.address;
      filled = true;
    }

    // Téléphone
    if (p.phone) {
      form.telMobile = p.phone;
      filled = true;
    }

    // Email
    if (p.email) {
      form.email = p.email;
      filled = true;
    }

    prefillApplied.value = filled;
  }

  // ── Chargement depuis un brouillon existant (prioritaire sur patient) ──

  function loadFromBrouillon() {
    const d = props.initialData;
    if (!d || Object.keys(d).length === 0) return false;

    // État civil
    if (d.civilite) form.civilite = d.civilite;
    if (d.sexe) form.sexe = d.sexe;
    if (d.nomFamille) form.nomFamille = d.nomFamille;
    if (d.nomUtilise) form.nomUtilise = d.nomUtilise;
    if (d.prenomUtilise) form.prenomUtilise = d.prenomUtilise;
    if (d.prenomsActeNaissance) form.prenomsActeNaissance = d.prenomsActeNaissance;
    if (d.dateNaissance) {
      try {
        const date = new Date(d.dateNaissance);
        if (!isNaN(date.getTime())) {
          form.dateNaissance = date;
          setFieldsFromDate(date);
        }
      } catch {
        /* ignore */
      }
    }
    if (d.situationFamiliale) form.situationFamiliale = d.situationFamiliale;
    if (d.communeNaissanceCP) form.communeNaissanceCP = d.communeNaissanceCP;
    if (d.communeNaissanceLibelle) form.communeNaissanceLibelle = d.communeNaissanceLibelle;
    // Rétrocompatibilité : ancien brouillon avec champ unique communeNaissance
    if (!d.communeNaissanceCP && !d.communeNaissanceLibelle && d.communeNaissance) {
      form.communeNaissanceLibelle = d.communeNaissance;
    }
    if (d.paysNaissance) form.paysNaissance = d.paysNaissance;
    if (d.nir) form.nir = d.nir;
    if (d.ins) form.ins = d.ins;

    // Adresse
    if (d.adresseLigne) form.adresseLigne = d.adresseLigne;
    if (d.adresseCommentaire) form.adresseCommentaire = d.adresseCommentaire;
    if (d.codePostal) form.codePostal = d.codePostal;
    if (d.commune) form.commune = d.commune;

    // Contacts
    if (d.telMobile) form.telMobile = d.telMobile;
    if (d.telDomicile) form.telDomicile = d.telDomicile;
    if (d.email) form.email = d.email;

    return true;
  }

  // ── Calcul du statut de la section ─────────────────────────────────────

  const sectionStatus = computed<SectionStatus>(() => {
    const hasName = !!form.nomFamille.trim();
    const hasPrenom = !!form.prenomUtilise.trim();
    const hasDate = !!form.dateNaissance;

    // Aucun champ requis rempli → vide
    if (!hasName && !hasPrenom && !hasDate) {
      // Vérifier s'il y a au moins un champ quelconque rempli
      const anyFilled = Object.entries(form).some(([key, val]) => {
        if (key === 'dateNaissance') return false;
        if (typeof val === 'string') return val.trim().length > 0;
        return !!val;
      });
      return anyFilled ? 'partial' : 'empty';
    }

    // Tous les champs requis remplis → complet
    if (hasName && hasPrenom && hasDate) return 'complete';

    // Sinon → partiel
    return 'partial';
  });

  // ── Sérialisation des données du formulaire ────────────────────────────

  function serializeFormData(): WizardSectionData {
    return {
      // État civil
      civilite: form.civilite || null,
      sexe: form.sexe || null,
      nomFamille: form.nomFamille,
      nomUtilise: form.nomUtilise || form.nomFamille,
      prenomUtilise: form.prenomUtilise,
      prenomsActeNaissance: form.prenomsActeNaissance || form.prenomUtilise,
      dateNaissance: form.dateNaissance ? form.dateNaissance.toISOString() : null,
      situationFamiliale: form.situationFamiliale || null,
      communeNaissanceCP: form.communeNaissanceCP || null,
      communeNaissanceLibelle: form.communeNaissanceLibelle || null,
      paysNaissance: form.paysNaissance || null,
      nir: form.nir || null,
      ins: form.ins || null,

      // Adresse
      adresseLigne: form.adresseLigne || null,
      adresseCommentaire: form.adresseCommentaire || null,
      codePostal: form.codePostal || null,
      commune: form.commune || null,

      // Contacts personnels
      telMobile: form.telMobile || null,
      telDomicile: form.telDomicile || null,
      email: form.email || null,
    };
  }

  // ── Watchers : émission vers le wizard à chaque changement ─────────────

  watch(
    () => ({ ...form }),
    () => {
      emit('update:data', serializeFormData());
      emit('update:status', sectionStatus.value);
    },
    { deep: true },
  );

  // ── Montage : pré-remplissage puis émission initiale ───────────────────

  onMounted(() => {
    // Priorité 1 : brouillon existant (données saisies précédemment)
    const hadBrouillon = loadFromBrouillon();

    // Priorité 2 : données patient (si pas de brouillon)
    if (!hadBrouillon) {
      prefillFromPatient();
    }

    // Émission initiale du statut et des données
    emit('update:data', serializeFormData());
    emit('update:status', sectionStatus.value);
  });
</script>

<style scoped>
  /*
 * Layout structurel uniquement (propre à UsagerForm).
 * Les styles partagés (.form-fieldset, .form-grid-2, .form-group,
 * .form-label, .form-error, .form-prefill-banner, .form-legend-icon,
 * .birth-date-input) vivent dans main.css conformément à la
 * convention #3 (FRONTEND_CONVENTIONS_16_03_2026.md).
 */
  .usager-form {
    @apply space-y-7;
  }

  /* Bandeau amber récapitulatif pré-submit */
  .submit-warnings-banner {
    @apply flex items-start gap-2 px-4 py-3 rounded-xl
         border border-amber-200 bg-amber-50 text-amber-800 text-sm;
  }
  .submit-warnings-banner strong {
    @apply font-semibold;
  }
  .submit-warnings-banner svg {
    @apply flex-shrink-0 mt-0.5 text-amber-500;
  }
</style>