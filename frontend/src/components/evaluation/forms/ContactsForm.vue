<!--
  CareLink - ContactsForm
  Chemin : frontend/src/components/evaluation/forms/ContactsForm.vue

  Rôle : Formulaire de saisie « Contacts » — section 2/10 du wizard évaluation.
         Gère un nombre variable de contacts (0 à N).
         Chaque contact est présenté en carte résumé repliable (clic → déploiement).
         Deux profils de champs selon typeContact :
           · « Cercle d'aide et de soin » → champs professionnels (RPPS, structure, MSSanté)
           · « Entourage » / « Autre »    → champs relationnels (natureLien)
         Le toggle « Aucun contact connu » marque la section 'complete' sans contact.

  Pattern wizard : identique à UsagerForm.vue
    - Props      : patient (non utilisé ici) + initialData (brouillon)
    - Emits      : update:data + update:status
    - onMounted  : loadFromBrouillon → émission initiale
    - watch      : émission à chaque changement
-->
<template>
  <div class="contacts-form">
    <!-- ============================================================= -->
    <!-- BANDEAU "AUCUN CONTACT CONNU"                                  -->
    <!-- ============================================================= -->
    <div
      :class="{ 'contacts-no-contact-banner--active': noContact }"
      class="contacts-no-contact-banner"
    >
      <Checkbox v-model="noContact" :binary="true" input-id="no-contact" />
      <label for="no-contact" class="contacts-no-contact-banner__label">
        Ce patient n'a aucun contact connu
      </label>
      <span v-if="noContact" class="contacts-no-contact-banner__hint">
        <CheckCircle2 :size="14" :stroke-width="2" />
        Section marquée comme complète
      </span>
    </div>

    <!-- ============================================================= -->
    <!-- FIELDSET PRINCIPAL                                             -->
    <!-- ============================================================= -->
    <fieldset
      :class="{ 'contacts-fieldset--disabled': noContact }"
      class="form-fieldset form-fieldset--violet"
    >
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--violet">
          <BookUser :size="15" :stroke-width="1.8" />
        </span>
        Cercle d'aide
        <span class="contacts-count-badge">
          {{ contacts.length }}&nbsp;contact{{ contacts.length !== 1 ? 's' : '' }}
        </span>
      </legend>

      <!-- ── État vide ─────────────────────────────────────────────── -->
      <div v-if="contacts.length === 0 && !noContact" class="contacts-empty-state">
        <Users :size="40" :stroke-width="1.2" class="contacts-empty-state__icon" />
        <p class="contacts-empty-state__text">Aucun contact ajouté pour ce patient.</p>
        <button class="contacts-add-btn contacts-add-btn--center" @click="addContact">
          <Plus :size="15" :stroke-width="2" />
          Ajouter un premier contact
        </button>
      </div>

      <!-- ── Liste des cartes ───────────────────────────────────────── -->
      <TransitionGroup tag="div" name="contact-list" class="contacts-list">
        <div
          v-for="contact in contacts"
          :key="contact.id"
          :class="{ 'contact-card--expanded': isExpanded(contact.id) }"
          class="contact-card"
        >
          <!-- En-tête résumé (toujours visible, cliquable) -->
          <div
            :aria-expanded="isExpanded(contact.id)"
            class="contact-card__header"
            role="button"
            @click="toggleExpand(contact.id)"
          >
            <div :class="['contact-card__avatar', avatarClass(contact.typeContact)]">
              {{ getInitials(contact) }}
            </div>

            <div class="contact-card__summary">
              <span class="contact-card__name">
                {{ contactDisplayName(contact) }}
              </span>
              <span class="contact-card__meta">
                {{ contact.role || contact.natureLien || '—' }}
                <span v-if="contact.structure" class="contact-card__structure">
                  · {{ contact.structure }}
                </span>
              </span>
            </div>

            <div class="contact-card__badges">
              <span
                v-if="contact.personneConfiance"
                class="contact-card__badge contact-card__badge--confiance"
                title="Personne de confiance désignée"
              >
                <ShieldCheck :size="11" :stroke-width="2" />
                Confiance
              </span>
              <span
                v-if="contact.responsableLegal"
                class="contact-card__badge contact-card__badge--legal"
                title="Responsable légal"
              >
                <Scale :size="11" :stroke-width="2" />
                Légal
              </span>
              <span :class="['contact-card__badge', typeBadgeClass(contact.typeContact)]">
                {{ typeContactLabel(contact.typeContact) }}
              </span>
            </div>

            <ChevronDown
              :size="16"
              :stroke-width="2"
              :class="[
                'contact-card__chevron',
                { 'contact-card__chevron--open': isExpanded(contact.id) },
              ]"
            />
            <button
              class="contact-card__delete"
              title="Supprimer ce contact"
              @click.stop="removeContact(contact.id)"
            >
              <Trash2 :size="14" :stroke-width="2" />
            </button>
          </div>

          <!-- Corps dépliable -->
          <Transition name="contact-expand">
            <div v-if="isExpanded(contact.id)" class="contact-card__body">
              <!-- ── Identité ───────────────────────────────────────── -->
              <fieldset class="contact-card__sub-fieldset">
                <legend class="contact-card__sub-legend">
                  <span class="form-legend-icon form-legend-icon--blue">
                    <UserCircle :size="13" :stroke-width="1.8" />
                  </span>
                  Identité
                </legend>

                <div class="form-grid-2">
                  <div class="form-group">
                    <label :for="`type-${contact.id}`" class="form-label form-label--required">
                      Type de contact
                    </label>
                    <Select
                      :id="`type-${contact.id}`"
                      v-model="contact.typeContact"
                      :options="typeContactOptions"
                      option-label="label"
                      option-value="value"
                      placeholder="Sélectionner..."
                      class="w-full"
                    />
                  </div>
                  <div class="form-group">
                    <label :for="`civilite-${contact.id}`" class="form-label">Civilité</label>
                    <Select
                      :id="`civilite-${contact.id}`"
                      v-model="contact.civilite"
                      :options="civiliteOptions"
                      option-label="label"
                      option-value="value"
                      placeholder="Sélectionner..."
                      class="w-full"
                    />
                  </div>
                </div>

                <div class="form-grid-2">
                  <div class="form-group">
                    <label :for="`nom-${contact.id}`" class="form-label form-label--required">
                      Nom utilisé
                    </label>
                    <InputText
                      :id="`nom-${contact.id}`"
                      v-model="contact.nomUtilise"
                      class="w-full"
                      placeholder="Nom"
                    />
                  </div>
                  <div class="form-group">
                    <label :for="`prenom-${contact.id}`" class="form-label">Prénom</label>
                    <InputText
                      :id="`prenom-${contact.id}`"
                      v-model="contact.prenomUtilise"
                      class="w-full"
                      placeholder="Prénom"
                    />
                  </div>
                </div>
              </fieldset>

              <!-- ── Champs professionnels (Cercle d'aide) ──────────── -->
              <template v-if="isProfessional(contact.typeContact)">
                <fieldset class="contact-card__sub-fieldset">
                  <legend class="contact-card__sub-legend">
                    <span class="form-legend-icon form-legend-icon--teal">
                      <Stethoscope :size="13" :stroke-width="1.8" />
                    </span>
                    Informations professionnelles
                  </legend>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label :for="`titre-${contact.id}`" class="form-label">Titre</label>
                      <InputText
                        :id="`titre-${contact.id}`"
                        v-model="contact.titre"
                        class="w-full"
                        placeholder="ex : Docteur, Infirmier..."
                      />
                    </div>
                    <div class="form-group">
                      <label :for="`role-${contact.id}`" class="form-label">Rôle dans l'aide</label>
                      <AutoComplete
                        :id="`role-${contact.id}`"
                        v-model="contact.role"
                        :suggestions="filteredRoles"
                        placeholder="Sélectionner ou saisir..."
                        class="w-full"
                        dropdown
                        @complete="searchRoles"
                      />
                    </div>
                  </div>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label :for="`rpps-${contact.id}`" class="form-label">N° RPPS</label>
                      <InputMask
                        :id="`rpps-${contact.id}`"
                        v-model="contact.numRpps"
                        :unmask="true"
                        :autoClear="false"
                        mask="99999999999"
                        class="w-full"
                        placeholder="Numéro RPPS (11 chiffres)"
                      />
                    </div>
                    <div class="form-group">
                      <label :for="`finess-${contact.id}`" class="form-label">FINESS ET</label>
                      <InputText
                        :id="`finess-${contact.id}`"
                        v-model="contact.finessET"
                        class="w-full"
                        placeholder="N° FINESS établissement"
                      />
                    </div>
                  </div>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label :for="`structure-${contact.id}`" class="form-label">Structure</label>
                      <InputText
                        :id="`structure-${contact.id}`"
                        v-model="contact.structure"
                        class="w-full"
                        placeholder="Nom de la structure"
                      />
                    </div>
                    <div class="form-group">
                      <label :for="`type-structure-${contact.id}`" class="form-label">
                        Type de structure
                      </label>
                      <Select
                        :id="`type-structure-${contact.id}`"
                        v-model="contact.typeStructure"
                        :options="typeStructureOptions"
                        option-label="label"
                        option-value="value"
                        placeholder="Sélectionner..."
                        class="w-full"
                      />
                    </div>
                  </div>
                </fieldset>
              </template>

              <!-- ── Champs relationnels (Entourage / Autre) ─────────── -->
              <template v-else>
                <fieldset class="contact-card__sub-fieldset">
                  <legend class="contact-card__sub-legend">
                    <span class="form-legend-icon form-legend-icon--pink">
                      <Heart :size="13" :stroke-width="1.8" />
                    </span>
                    Lien avec le patient
                  </legend>

                  <div class="form-grid-2">
                    <div class="form-group">
                      <label :for="`lien-${contact.id}`" class="form-label">Nature du lien</label>
                      <InputText
                        :id="`lien-${contact.id}`"
                        v-model="contact.natureLien"
                        class="w-full"
                        placeholder="ex : Conjoint, Enfant, Ami(e)..."
                      />
                    </div>
                    <!-- Cellule droite vide pour maintenir la grille -->
                    <div class="form-group" />
                  </div>
                </fieldset>
              </template>

              <!-- ── Coordonnées (tous types) ───────────────────────── -->
              <fieldset class="contact-card__sub-fieldset">
                <legend class="contact-card__sub-legend">
                  <span class="form-legend-icon form-legend-icon--emerald">
                    <Phone :size="13" :stroke-width="1.8" />
                  </span>
                  Coordonnées
                </legend>

                <div class="form-grid-2">
                  <div class="form-group">
                    <label :for="`mobile-${contact.id}`" class="form-label">
                      Téléphone mobile
                    </label>
                    <InputMask
                      :id="`mobile-${contact.id}`"
                      v-model="contact.mobile"
                      :unmask="true"
                      :autoClear="false"
                      mask="99 99 99 99 99"
                      class="w-full"
                      placeholder="06 00 00 00 00"
                    />
                  </div>
                  <div class="form-group">
                    <label :for="`mail-pro-${contact.id}`" class="form-label">Email</label>
                    <InputText
                      :id="`mail-pro-${contact.id}`"
                      v-model="contact.mailPro"
                      type="email"
                      class="w-full"
                      placeholder="prenom.nom@mail.com"
                    />
                  </div>
                </div>

                <!-- MSSanté : professionnel uniquement -->
                <div v-if="isProfessional(contact.typeContact)" class="form-grid-2">
                  <div class="form-group">
                    <label :for="`mssante-${contact.id}`" class="form-label">
                      MSSanté
                      <span class="contacts-mssante-hint">messagerie sécurisée</span>
                    </label>
                    <InputText
                      :id="`mssante-${contact.id}`"
                      v-model="contact.mailMSSANTE"
                      class="w-full"
                      placeholder="rpps@mssante.fr"
                    />
                  </div>
                  <div class="form-group" />
                </div>
              </fieldset>

              <!-- ── Statuts légaux (tous types) ────────────────────── -->
              <fieldset class="contact-card__sub-fieldset">
                <legend class="contact-card__sub-legend">
                  <span class="form-legend-icon form-legend-icon--amber">
                    <Scale :size="13" :stroke-width="1.8" />
                  </span>
                  Statuts légaux
                </legend>

                <!-- Personne de confiance -->
                <div class="contacts-legal-row">
                  <div class="contacts-legal-item">
                    <Checkbox
                      v-model="contact.personneConfiance"
                      :input-id="`confiance-${contact.id}`"
                      :binary="true"
                    />
                    <label :for="`confiance-${contact.id}`" class="contacts-legal-item__label">
                      Personne de confiance
                    </label>
                  </div>
                  <div v-if="contact.personneConfiance" class="form-group contacts-legal-date">
                    <label :for="`date-confiance-${contact.id}`" class="form-label">
                      Date de désignation
                    </label>
                    <InputText
                      :id="`date-confiance-${contact.id}`"
                      v-model="contact.dateDesignationPersonneConfiance"
                      class="w-full"
                      placeholder="JJ/MM/AAAA"
                    />
                  </div>
                </div>

                <!-- Responsable légal -->
                <div class="contacts-legal-row">
                  <div class="contacts-legal-item">
                    <Checkbox
                      v-model="contact.responsableLegal"
                      :input-id="`legal-${contact.id}`"
                      :binary="true"
                    />
                    <label :for="`legal-${contact.id}`" class="contacts-legal-item__label">
                      Responsable légal
                    </label>
                  </div>
                  <div v-if="contact.responsableLegal" class="form-group contacts-legal-date">
                    <label :for="`date-legal-${contact.id}`" class="form-label">
                      Date de désignation
                    </label>
                    <InputText
                      :id="`date-legal-${contact.id}`"
                      v-model="contact.dateDesignationResponsableLegal"
                      class="w-full"
                      placeholder="JJ/MM/AAAA"
                    />
                  </div>
                </div>
              </fieldset>
            </div>
          </Transition>
        </div>
      </TransitionGroup>

      <!-- ── Bouton ajouter (si au moins 1 contact existant) ─────────── -->
      <button v-if="contacts.length > 0 && !noContact" class="contacts-add-btn" @click="addContact">
        <Plus :size="15" :stroke-width="2" />
        Ajouter un contact
      </button>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - ContactsForm
   * Chemin : frontend/src/components/evaluation/forms/ContactsForm.vue
   */
  import { ref, computed, watch, onMounted } from 'vue';
  import InputText from 'primevue/inputtext';
  import InputMask from 'primevue/inputmask';
  import Select from 'primevue/select';
  import AutoComplete from 'primevue/autocomplete';
  import Checkbox from 'primevue/checkbox';
  import {
    BookUser,
    UserCircle,
    Phone,
    Stethoscope,
    Heart,
    Scale,
    ShieldCheck,
    Users,
    Plus,
    Trash2,
    ChevronDown,
    CheckCircle2,
  } from 'lucide-vue-next';

  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import type { PatientResponse } from '@/types';

  // ── Types ──────────────────────────────────────────────────────────────

  interface ContactItem {
    id: string;
    typeContact: string;
    civilite: string;
    nomUtilise: string;
    prenomUtilise: string;
    mobile: string;
    mailPro: string;
    mailMSSANTE: string;
    // Professionnel (Cercle d'aide)
    titre: string;
    role: string;
    numRpps: string;
    structure: string;
    typeStructure: string;
    finessET: string;
    // Relationnel (Entourage / Autre)
    natureLien: string;
    // Statuts légaux (tous types)
    personneConfiance: boolean;
    dateDesignationPersonneConfiance: string;
    responsableLegal: boolean;
    dateDesignationResponsableLegal: string;
  }

  // ── Props / Emits ──────────────────────────────────────────────────────

  interface Props {
    patient: PatientResponse | null;
    initialData?: WizardSectionData;
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

  const typeContactOptions = [
    { label: "Cercle d'aide et de soin", value: "Cercle d'aide et de soin" },
    { label: 'Entourage', value: 'Entourage' },
    { label: 'Autre', value: 'Autre' },
  ];

  const ROLE_PRO_SUGGESTIONS = [
    'Médecin traitant',
    'Médecin spécialiste',
    'Infirmier',
    'Kinésithérapeute',
    'Orthophoniste',
    'Aide-soignant',
    'Auxiliaire de vie',
    'Pharmacien',
    'Accompagnement social/médico-social au soin',
    'Responsable de secteur',
    'Autre professionnel',
  ];

  const filteredRoles = ref<string[]>([]);

  function searchRoles(event: { query: string }) {
    const q = event.query.toLowerCase();
    filteredRoles.value = q
      ? ROLE_PRO_SUGGESTIONS.filter((r) => r.toLowerCase().includes(q))
      : [...ROLE_PRO_SUGGESTIONS];
  }

  const typeStructureOptions = [
    { label: 'SSIAD', value: 'SSIAD' },
    { label: 'SAAD', value: 'SAAD' },
    { label: 'EHPAD', value: 'EHPAD' },
    { label: 'Réseaux / DAC / CRT / CPTS', value: 'Réseaux / DAC / CRT / CPTS' },
    { label: 'Cabinet médical', value: 'Cabinet médical' },
    { label: 'Hôpital / Clinique', value: 'Hôpital / Clinique' },
    { label: 'Autre', value: 'Autre' },
  ];

  // ── État ───────────────────────────────────────────────────────────────

  /** Tableau des contacts à géométrie variable */
  const contacts = ref<ContactItem[]>([]);

  /** Aucun contact connu → section marquée complète sans contact */
  const noContact = ref(false);

  /** IDs des cartes actuellement dépliées */
  const expandedIds = ref<Set<string>>(new Set());

  // ── Gestion des IDs ────────────────────────────────────────────────────

  let _idCounter = 0;

  function newId(): string {
    return `contact-${++_idCounter}`;
  }

  // ── Usines ─────────────────────────────────────────────────────────────

  function createEmptyContact(): ContactItem {
    return {
      id: newId(),
      typeContact: "Cercle d'aide et de soin",
      civilite: '',
      nomUtilise: '',
      prenomUtilise: '',
      mobile: '',
      mailPro: '',
      mailMSSANTE: '',
      titre: '',
      role: '',
      numRpps: '',
      structure: '',
      typeStructure: '',
      finessET: '',
      natureLien: '',
      personneConfiance: false,
      dateDesignationPersonneConfiance: '',
      responsableLegal: false,
      dateDesignationResponsableLegal: '',
    };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- JSON hydration: 20+ champs avec fallback, narrowing verbeux pour gain marginal
  function contactFromJson(c: Record<string, any>): ContactItem {
    return {
      id: newId(),
      typeContact: c.typeContact || "Cercle d'aide et de soin",
      civilite: c.civilite || c.personnePhysique?.civilite || '',
      nomUtilise: c.nomUtilise || c.personnePhysique?.nomUtilise || '',
      prenomUtilise: c.prenomUtilise || c.personnePhysique?.prenomUtilise || '',
      mobile: c.mobile || c.contactInfosPersonnels?.mobile || '',
      mailPro: c.mailPro || c.contactInfosPersonnels?.mailPro || '',
      mailMSSANTE: c.mailMSSANTE || c.contactInfosPersonnels?.mailMSSANTE || '',
      titre: c.titre || '',
      role: c.role || '',
      numRpps: c.numRpps || '',
      structure: c.structure || '',
      typeStructure: c.typeStructure || '',
      finessET: c.finessET || '',
      natureLien: c.natureLien || '',
      personneConfiance: c.personneConfiance || false,
      dateDesignationPersonneConfiance: c.dateDesignationPersonneConfiance || '',
      responsableLegal: c.responsableLegal || false,
      dateDesignationResponsableLegal: c.dateDesignationResponsableLegal || '',
    };
  }

  // ── Actions ────────────────────────────────────────────────────────────

  function addContact() {
    const c = createEmptyContact();
    contacts.value.push(c);
    expandedIds.value.add(c.id); // Nouveau contact → déployé d'emblée
  }

  function removeContact(id: string) {
    contacts.value = contacts.value.filter((c) => c.id !== id);
    expandedIds.value.delete(id);
  }

  function toggleExpand(id: string) {
    if (expandedIds.value.has(id)) {
      expandedIds.value.delete(id);
    } else {
      expandedIds.value.add(id);
    }
    // Déclenche la réactivité sur le Set (Vue 3 ne détecte pas .add/.delete nativement)
    expandedIds.value = new Set(expandedIds.value);
  }

  function isExpanded(id: string): boolean {
    return expandedIds.value.has(id);
  }

  // ── Helpers affichage ──────────────────────────────────────────────────

  function getInitials(contact: ContactItem): string {
    const n = (contact.nomUtilise || '').charAt(0).toUpperCase();
    const p = (contact.prenomUtilise || '').charAt(0).toUpperCase();
    if (n && p) return n + p;
    return n || p || '?';
  }

  function contactDisplayName(contact: ContactItem): string {
    if (contact.nomUtilise && contact.prenomUtilise) {
      return `${contact.nomUtilise} ${contact.prenomUtilise}`;
    }
    return contact.nomUtilise || contact.prenomUtilise || 'Nouveau contact';
  }

  function isProfessional(typeContact: string): boolean {
    return typeContact === "Cercle d'aide et de soin";
  }

  function avatarClass(typeContact: string): string {
    switch (typeContact) {
      case "Cercle d'aide et de soin":
        return 'contact-card__avatar--pro';
      case 'Entourage':
        return 'contact-card__avatar--family';
      default:
        return 'contact-card__avatar--other';
    }
  }

  function typeBadgeClass(typeContact: string): string {
    switch (typeContact) {
      case "Cercle d'aide et de soin":
        return 'contact-card__badge--pro';
      case 'Entourage':
        return 'contact-card__badge--family';
      default:
        return 'contact-card__badge--other';
    }
  }

  function typeContactLabel(typeContact: string): string {
    switch (typeContact) {
      case "Cercle d'aide et de soin":
        return 'Professionnel';
      case 'Entourage':
        return 'Entourage';
      default:
        return 'Autre';
    }
  }

  // ── Calcul du statut de la section ─────────────────────────────────────

  const sectionStatus = computed<SectionStatus>(() => {
    // Aucun contact confirmé explicitement → section complète
    if (noContact.value) return 'complete';

    // Aucun contact et absence non confirmée → vide
    if (contacts.value.length === 0) return 'empty';

    // Au moins un contact : complet si tous ont un nom, partiel sinon
    const allHaveName = contacts.value.every(
      (c) => c.nomUtilise.trim() !== '' || c.prenomUtilise.trim() !== '',
    );
    return allHaveName ? 'complete' : 'partial';
  });

  // ── Sérialisation ──────────────────────────────────────────────────────

  function serializeFormData(): WizardSectionData {
    return {
      noContact: noContact.value,
      contacts: contacts.value.map(({ id: _id, ...rest }) => rest),
    };
  }

  // ── Chargement depuis brouillon ────────────────────────────────────────

  function loadFromBrouillon(): boolean {
    const d = props.initialData;
    if (!d || Object.keys(d).length === 0) return false;

    if (d.noContact) {
      noContact.value = true;
    }

    if (Array.isArray(d.contacts) && d.contacts.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- type propagé depuis contactFromJson
      contacts.value = d.contacts.map((c: Record<string, any>) => contactFromJson(c));
      // Brouillon rechargé → toutes les cartes repliées (vue résumé)
    }

    return true;
  }

  // ── Watchers ───────────────────────────────────────────────────────────

  watch(
    [contacts, noContact],
    () => {
      emit('update:data', serializeFormData());
      emit('update:status', sectionStatus.value);
    },
    { deep: true },
  );

  // ── Montage ────────────────────────────────────────────────────────────

  onMounted(() => {
    loadFromBrouillon();

    // Émission initiale
    emit('update:data', serializeFormData());
    emit('update:status', sectionStatus.value);
  });
</script>

<style scoped>
  /*
 * ContactsForm — styles spécifiques au composant.
 * Styles partagés (.form-fieldset, .form-grid-2, .form-group, etc.) dans main.css.
 * Pattern evaluation : @apply Tailwind dans <style scoped>.
 */

  .contacts-form {
    @apply space-y-7;
  }

  /* ── Bandeau "Aucun contact" ──────────────────────────────────────────── */

  .contacts-no-contact-banner {
    @apply flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50;
    @apply transition-colors duration-200;
  }

  .contacts-no-contact-banner--active {
    @apply border-amber-200 bg-amber-50;
  }

  .contacts-no-contact-banner__label {
    @apply text-sm font-medium text-slate-700 cursor-pointer select-none;
  }

  .contacts-no-contact-banner__hint {
    @apply ml-auto flex items-center gap-1.5 text-xs font-medium text-emerald-600;
  }

  /* ── Fieldset désactivé ───────────────────────────────────────────────── */

  .contacts-fieldset--disabled {
    @apply opacity-40 pointer-events-none select-none;
  }

  /* ── Badge compteur dans la légende ──────────────────────────────────── */

  .contacts-count-badge {
    @apply ml-2 inline-flex items-center px-2 py-0.5 rounded-full
         text-xs font-medium bg-slate-100 text-slate-500;
  }

  /* ── État vide ───────────────────────────────────────────────────────── */

  .contacts-empty-state {
    @apply flex flex-col items-center gap-3 py-10 text-center;
  }

  .contacts-empty-state__icon {
    @apply text-slate-300;
  }

  .contacts-empty-state__text {
    @apply text-sm text-slate-400;
  }

  /* ── Bouton ajouter ──────────────────────────────────────────────────── */

  .contacts-add-btn {
    @apply mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
         border border-dashed border-slate-300 text-sm font-medium text-slate-500
         bg-white hover:border-teal-400 hover:text-teal-600 hover:bg-teal-50
         transition-colors duration-150 cursor-pointer;
  }

  .contacts-add-btn--center {
    @apply mt-0;
  }

  /* ── Liste avec animation ────────────────────────────────────────────── */

  .contacts-list {
    @apply flex flex-col gap-3;
  }

  /* TransitionGroup */
  .contact-list-enter-active {
    transition:
      opacity 0.25s ease,
      transform 0.25s ease;
  }
  .contact-list-leave-active {
    transition:
      opacity 0.2s ease,
      transform 0.2s ease;
  }
  .contact-list-enter-from {
    opacity: 0;
    transform: translateY(-10px);
  }
  .contact-list-leave-to {
    opacity: 0;
    transform: translateX(10px);
  }

  /* ── Carte contact ────────────────────────────────────────────────────── */

  .contact-card {
    @apply rounded-xl border border-slate-200 bg-white overflow-hidden
         shadow-sm transition-shadow duration-150;
  }

  .contact-card--expanded {
    @apply shadow-md border-slate-300;
  }

  /* En-tête */
  .contact-card__header {
    @apply flex items-center gap-3 px-4 py-3 cursor-pointer
         hover:bg-slate-50 transition-colors duration-150;
  }

  /* Avatar initiales */
  .contact-card__avatar {
    @apply flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
         text-sm font-semibold;
  }

  .contact-card__avatar--pro {
    @apply bg-teal-100 text-teal-700;
  }

  .contact-card__avatar--family {
    @apply bg-violet-100 text-violet-700;
  }

  .contact-card__avatar--other {
    @apply bg-slate-100 text-slate-600;
  }

  /* Résumé nom + meta */
  .contact-card__summary {
    @apply flex-1 min-w-0 flex flex-col;
  }

  .contact-card__name {
    @apply text-sm font-semibold text-slate-800 truncate;
  }

  .contact-card__meta {
    @apply text-xs text-slate-500 truncate;
  }

  .contact-card__structure {
    @apply text-slate-400;
  }

  /* Badges */
  .contact-card__badges {
    @apply flex items-center gap-1.5 flex-shrink-0;
  }

  .contact-card__badge {
    @apply inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium;
  }

  .contact-card__badge--confiance {
    @apply bg-emerald-50 text-emerald-700 border border-emerald-200;
  }

  .contact-card__badge--legal {
    @apply bg-amber-50 text-amber-700 border border-amber-200;
  }

  .contact-card__badge--pro {
    @apply bg-teal-50 text-teal-700;
  }

  .contact-card__badge--family {
    @apply bg-violet-50 text-violet-700;
  }

  .contact-card__badge--other {
    @apply bg-slate-100 text-slate-500;
  }

  /* Chevron */
  .contact-card__chevron {
    @apply flex-shrink-0 text-slate-400 transition-transform duration-200;
  }

  .contact-card__chevron--open {
    @apply rotate-180;
  }

  /* Bouton supprimer */
  .contact-card__delete {
    @apply flex-shrink-0 p-1.5 rounded-lg text-slate-400
         hover:text-red-500 hover:bg-red-50 transition-colors duration-150;
  }

  /* Corps dépliable */
  .contact-card__body {
    @apply px-4 pb-4 pt-2 border-t border-slate-100 space-y-4;
  }

  /* Transition déploiement carte */
  .contact-expand-enter-active {
    transition:
      opacity 0.2s ease,
      transform 0.2s ease;
  }
  .contact-expand-leave-active {
    transition: opacity 0.15s ease;
  }
  .contact-expand-enter-from {
    opacity: 0;
    transform: translateY(-6px);
  }
  .contact-expand-leave-to {
    opacity: 0;
  }

  /* ── Sub-fieldsets dans le corps ─────────────────────────────────────── */

  .contact-card__sub-fieldset {
    @apply rounded-lg border border-slate-100 bg-slate-50 px-3 pb-3 pt-0;
  }

  .contact-card__sub-legend {
    @apply flex items-center gap-2 px-1 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-0;
    /* Réutilise form-legend-icon (main.css) avec icône plus petite */
  }

  .contact-card__sub-legend .form-legend-icon {
    @apply w-6 h-6; /* Override : plus petit que les légendes de section */
  }

  /* ── Coordonnées : hint MSSanté ──────────────────────────────────────── */

  .contacts-mssante-hint {
    @apply ml-1 text-xs font-normal text-slate-400;
  }

  /* ── Statuts légaux ──────────────────────────────────────────────────── */

  .contacts-legal-row {
    @apply flex flex-col gap-2 py-2 first:pt-1;
  }

  .contacts-legal-row + .contacts-legal-row {
    @apply border-t border-slate-200;
  }

  .contacts-legal-item {
    @apply flex items-center gap-2;
  }

  .contacts-legal-item__label {
    @apply text-sm text-slate-700 cursor-pointer select-none;
  }

  .contacts-legal-date {
    @apply pl-6 max-w-xs;
  }
</style>