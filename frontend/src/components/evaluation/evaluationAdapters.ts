/**
 * CareLink - Adaptateurs format wizard → format EvalSchema
 * Chemin : frontend/src/components/evaluation/evaluationAdapters.ts
 *
 * Fonctions pures : transforment les données sérialisées par les formulaires
 * wizard (format plat/wrappé) vers le format EvalSchema nested attendu par
 * le JSON schema backend (evaluation_v1.json).
 *
 * Utilisé par :
 *   - SectionRenderer.vue (affichage relecture)
 *   - useEvaluationWizard.ts (sauvegarde submit)
 *
 * 🆕 S3.2 — 18/03/2026 : adaptUsager transmet nir + ins dans personnePhysique
 * 🆕 TEL — 21/03/2026 : sanitizePhone() strip espaces/tirets/points sur téléphones + RPPS
 * 🆕 TYPES — 23/03/2026 : 18 `any` → 0, interfaces wizard/EvalSchema locales
 * 🆕 RENAME — 23/03/2026 : Bachelard* → EvalSchema* + type guards (convention #56)
 * 🆕 PREFILL — 26/03/2026 : reverse adapters EvalSchema → wizard flat (reverseAdaptUsager, reverseAdaptContacts, reverseAdaptDispositifs)
 *
 * Chaque adaptateur détecte le format d'entrée : si les données sont déjà
 * au format EvalSchema, elles passent telles quelles → compatibilité ascendante.
 *
 * IMPORTANT : le JSON schema backend interdit les valeurs `null` pour les
 * champs string/object. Toujours utiliser `''` pour les strings absents
 * et `{ ligne: '', ... }` pour les objets absents.
 */

// ── Types Wizard (format plat, entrée formulaires) ────────────────────

/** Contact tel que sérialisé par ContactsForm.vue (format plat) */
interface WizardContactItem {
  typeContact?: string;
  civilite?: string;
  nomUtilise?: string;
  prenomUtilise?: string;
  dateNaissance?: string;
  adresse?: EvalSchemaAdresse;
  domicile?: string;
  mobile?: string;
  mailMSSANTE?: string;
  mailPro?: string;
  titre?: string;
  role?: string;
  numRpps?: string;
  structure?: string;
  typeStructure?: string;
  finessET?: string;
  natureLien?: string;
  personneConfiance?: boolean;
  dateDesignationPersonneConfiance?: string;
  responsableLegal?: boolean;
  dateDesignationResponsableLegal?: string;
}

/** Wrapper contacts wizard : { noContact, contacts[] } */
interface WizardContactsData {
  noContact?: boolean;
  contacts?: WizardContactItem[];
}

/** Usager tel que sérialisé par UsagerForm.vue (format plat) */
interface WizardUsagerData {
  civilite?: string;
  sexe?: string;
  nomFamille?: string;
  nomUtilise?: string;
  prenomUtilise?: string;
  prenomsActeNaissance?: string;
  dateNaissance?: string;
  communeNaissanceCP?: string;
  communeNaissanceLibelle?: string;
  communeNaissance?: string;
  paysNaissance?: string;
  situationFamiliale?: string;
  nir?: string;
  ins?: string;
  clientId?: string;
  adresseLigne?: string;
  adresseCommentaire?: string;
  codePostal?: string;
  commune?: string;
  telDomicile?: string;
  telMobile?: string;
  email?: string;
}

/** Item matériel wizard */
interface WizardMaterielItem {
  materiel?: string;
  statut?: string;
}

/** Wrapper matériels wizard : { noMateriel, items[] } */
interface WizardMaterielsData {
  noMateriel?: boolean;
  items?: WizardMaterielItem[];
}

/** Item dispositif wizard */
interface WizardDispositifItem {
  dispositif?: string;
  statut?: string;
  datePose?: string;
  dateControle?: string;
  dateRetrait?: string;
  notes?: string;
}

/** Wrapper dispositifs wizard : { noDispositif, items[] } */
interface WizardDispositifsData {
  noDispositif?: boolean;
  items?: WizardDispositifItem[];
}

// ── Types EvalSchema (format nested, conforme evaluation_v1.json) ─────

interface EvalSchemaAdresse {
  ligne: string;
  commentaire: string;
  codePostal: string;
  libelleCommune: string;
}

interface EvalSchemaContactPersonnePhysique {
  civilite?: string;
  nomUtilise: string;
  prenomUtilise: string;
  dateNaissance: string;
}

interface EvalSchemaContactInfos {
  domicile: string;
  mobile: string;
  mailMSSANTE: string;
  mailPro: string;
}

export interface EvalSchemaContact {
  typeContact: string;
  personnePhysique: EvalSchemaContactPersonnePhysique;
  adresse: EvalSchemaAdresse;
  contactInfosPersonnels: EvalSchemaContactInfos;
  titre: string;
  role: string;
  numRpps: string;
  structure: string;
  typeStructure: string;
  finessET: string;
  natureLien: string;
  personneConfiance: boolean;
  dateDesignationPersonneConfiance: string;
  responsableLegal: boolean;
  dateDesignationResponsableLegal: string;
}

interface EvalSchemaUsagerPersonnePhysique {
  civilite?: string;
  sexe?: string;
  nomFamille: string;
  nomUtilise: string;
  prenomUtilise: string;
  premierPrenomActeNaissance: string;
  prenomsActeNaissance: string;
  dateNaissance: string;
  communeNaissance: { codePostal: string; libelleCommune: string };
  paysNaissance: { libellePays: string };
  situationFamiliale: string;
  nir: string;
  ins: string;
}

export interface EvalSchemaUsager {
  "Informations d'état civil": {
    clientId: string;
    personnePhysique: EvalSchemaUsagerPersonnePhysique;
  };
  adresse: EvalSchemaAdresse;
  contactInfosPersonnels: {
    domicile: string;
    mobile: string;
    mail: string;
  };
}

interface EvalSchemaMaterielItem {
  materiel: string;
  statut: string;
}

export interface EvalSchemaMateriels {
  noMateriel: boolean;
  items: EvalSchemaMaterielItem[];
}

export interface EvalSchemaDispositif {
  dispositif: string;
  statut: string;
  datePose: string;
  dateControle: string;
  dateRetrait: string;
  notes: string;
}

// ── Helpers ────────────────────────────────────────────────────────────

/** Type guard : vérifie que la valeur est un objet non-null non-tableau */
function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === 'object' && val !== null && !Array.isArray(val);
}

/** String non-null : retourne la valeur ou '' */
function s(val: unknown): string {
  return typeof val === 'string' ? val : '';
}

/**
 * String pour champ enum : retourne la valeur si non-vide, sinon undefined.
 * Les champs enum du JSON schema (civilite, sexe, statut...) n'acceptent pas ''
 * → on omet la clé plutôt qu'envoyer une chaîne vide.
 */
function enumOrUndefined(val: unknown): string | undefined {
  if (typeof val === 'string' && val.trim() !== '') return val;
  return undefined;
}

/** Boolean non-null : retourne la valeur ou false */
function b(val: unknown): boolean {
  return typeof val === 'boolean' ? val : false;
}

/**
 * Supprime tout caractère non-numérique (espaces, points, tirets, parenthèses…).
 * Retourne une chaîne de chiffres purs ou '' si vide/absent.
 * Exporté pour réutilisation dans useEvaluationWizard (sanitization pré-saveDraft).
 */
export function sanitizePhone(val: unknown): string {
  if (typeof val !== 'string') return '';
  return val.replace(/[^0-9]/g, '');
}

function emptyAdresse(): EvalSchemaAdresse {
  return { ligne: '', commentaire: '', codePostal: '', libelleCommune: '' };
}

// ── Type Guards (exportés pour SectionRenderer.vue) ───────────────────

/**
 * Détecte le format EvalSchema pour la section Usager.
 * Clé discriminante : présence de "Informations d'état civil" (clé nested).
 */
export function isEvalSchemaUsager(raw: unknown): raw is EvalSchemaUsager {
  return isRecord(raw) && "Informations d'état civil" in raw;
}

/**
 * Détecte le format EvalSchema pour la section Matériels.
 * Clé discriminante : présence de noMateriel ou items (objet, pas tableau).
 */
export function isEvalSchemaMateriels(raw: unknown): raw is EvalSchemaMateriels {
  return isRecord(raw) && ('noMateriel' in raw || 'items' in raw);
}

// ── Contacts ──────────────────────────────────────────────────────────

/**
 * Contacts : wizard stocke { noContact, contacts: ContactItem[] } (plat)
 *            schema attend Contact[] avec nested personnePhysique + contactInfosPersonnels
 */
export function adaptContacts(raw: unknown): EvalSchemaContact[] {
  if (!raw) return [];

  // Déjà au format EvalSchema (tableau direct) → passer tel quel
  if (Array.isArray(raw)) return raw as EvalSchemaContact[];

  // Format wizard : { noContact, contacts: [...] }
  const wizardData = raw as WizardContactsData;
  const contacts = wizardData.contacts;
  if (!Array.isArray(contacts)) return [];

  return contacts.map((c: WizardContactItem) => {
    const contact: EvalSchemaContact = {
      typeContact: s(c.typeContact),
      personnePhysique: {
        nomUtilise: s(c.nomUtilise),
        prenomUtilise: s(c.prenomUtilise),
        dateNaissance: s(c.dateNaissance),
      },
      adresse: c.adresse && typeof c.adresse === 'object' ? c.adresse : emptyAdresse(),
      contactInfosPersonnels: {
        domicile: sanitizePhone(c.domicile),
        mobile: sanitizePhone(c.mobile),
        mailMSSANTE: s(c.mailMSSANTE),
        mailPro: s(c.mailPro),
      },
      titre: s(c.titre),
      role: s(c.role),
      numRpps: sanitizePhone(c.numRpps),
      structure: s(c.structure),
      typeStructure: s(c.typeStructure),
      finessET: s(c.finessET),
      natureLien: s(c.natureLien),
      personneConfiance: b(c.personneConfiance),
      dateDesignationPersonneConfiance: s(c.dateDesignationPersonneConfiance),
      responsableLegal: b(c.responsableLegal),
      dateDesignationResponsableLegal: s(c.dateDesignationResponsableLegal),
    };

    // Champs enum : omettre si vides (civilite n'accepte que 'M' | 'MME')
    const civ = enumOrUndefined(c.civilite);
    if (civ) contact.personnePhysique.civilite = civ;

    return contact;
  });
}

// ── Usager ─────────────────────────────────────────────────────────────

/**
 * Usager : wizard stocke un format plat (UsagerForm.serializeFormData()),
 *          schema attend le format EvalSchema nested avec "Informations d'état civil", "adresse", etc.
 */
export function adaptUsager(raw: unknown): EvalSchemaUsager {
  if (!raw) return {} as EvalSchemaUsager;

  // Déjà au format EvalSchema → type guard (pas de cast)
  if (isEvalSchemaUsager(raw)) return raw;

  // Format wizard → reconstruction format EvalSchema
  const w = raw as WizardUsagerData;

  const personnePhysique: EvalSchemaUsagerPersonnePhysique = {
    nomFamille: s(w.nomFamille),
    nomUtilise: s(w.nomUtilise),
    prenomUtilise: s(w.prenomUtilise),
    premierPrenomActeNaissance: s(w.prenomUtilise),
    prenomsActeNaissance: s(w.prenomsActeNaissance),
    dateNaissance: s(w.dateNaissance),
    communeNaissance: {
      codePostal: s(w.communeNaissanceCP),
      libelleCommune: s(w.communeNaissanceLibelle || w.communeNaissance),
    },
    paysNaissance: w.paysNaissance ? { libellePays: s(w.paysNaissance) } : { libellePays: '' },
    situationFamiliale: s(w.situationFamiliale),
    nir: s(w.nir),
    ins: s(w.ins),
  };

  // Champs enum : omettre si vides (civilite='M'|'MME', sexe='M'|'F')
  const civ = enumOrUndefined(w.civilite);
  if (civ) personnePhysique.civilite = civ;
  const sex = enumOrUndefined(w.sexe);
  if (sex) personnePhysique.sexe = sex;

  return {
    "Informations d'état civil": {
      clientId: s(w.clientId),
      personnePhysique,
    },
    adresse: {
      ligne: s(w.adresseLigne),
      commentaire: s(w.adresseCommentaire),
      codePostal: s(w.codePostal),
      libelleCommune: s(w.commune),
    },
    contactInfosPersonnels: {
      domicile: sanitizePhone(w.telDomicile),
      mobile: sanitizePhone(w.telMobile),
      mail: s(w.email),
    },
  };
}

// ── Matériels ──────────────────────────────────────────────────────────

/**
 * Matériels : wizard stocke { noMateriel, items: Materiel[] }
 *             schema attend { noMateriel: boolean, items: Materiel[] } (objet)
 */
export function adaptMateriels(raw: unknown): EvalSchemaMateriels {
  if (!raw) return { noMateriel: true, items: [] };

  // Déjà au format EvalSchema → type guard (pas de cast)
  if (isEvalSchemaMateriels(raw)) return raw;

  // Tableau brut (legacy) → envelopper
  if (Array.isArray(raw)) {
    return {
      noMateriel: raw.length === 0,
      items: (raw as WizardMaterielItem[]).map((item) => ({
        materiel: s(item.materiel),
        statut: s(item.statut),
      })),
    };
  }

  // Format wizard : { noMateriel, items: [...] }
  const w = raw as WizardMaterielsData;
  const items = Array.isArray(w.items) ? w.items : [];
  return {
    noMateriel: b(w.noMateriel),
    items: items.map((item) => ({
      materiel: s(item.materiel),
      statut: s(item.statut),
    })),
  };
}

// ── Dispositifs ────────────────────────────────────────────────────────

/**
 * Dispositifs : wizard stocke { noDispositif, items: Dispositif[] }
 *               schema attend Dispositif[] : [{ dispositif, statut, datePose, dateControle, dateRetrait, notes }]
 */
export function adaptDispositifs(raw: unknown): EvalSchemaDispositif[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw as EvalSchemaDispositif[];

  // Format wizard : { noDispositif, items: [...] }
  const w = raw as WizardDispositifsData;
  const items = w.items;
  if (!Array.isArray(items)) return [];

  return items.map((item) => ({
    dispositif: s(item.dispositif),
    statut: s(item.statut),
    datePose: s(item.datePose),
    dateControle: s(item.dateControle),
    dateRetrait: s(item.dateRetrait),
    notes: s(item.notes),
  }));
}

// ══════════════════════════════════════════════════════════════════════
// REVERSE ADAPTERS — EvalSchema nested → wizard flat (prefill)
// ══════════════════════════════════════════════════════════════════════

/**
 * Usager : inverse de adaptUsager().
 * EvalSchema nested ("Informations d'état civil" → personnePhysique…)
 * → format plat attendu par UsagerForm.loadFromBrouillon().
 *
 * Si les données sont déjà au format wizard (pas de clé "Informations d'état civil"),
 * elles passent telles quelles (compatibilité brouillon).
 */
export function reverseAdaptUsager(raw: unknown): Record<string, unknown> {
  if (!raw || !isRecord(raw)) return {};

  // Déjà en format wizard flat → passer tel quel
  if (!isEvalSchemaUsager(raw)) return raw as Record<string, unknown>;

  // EvalSchema nested → wizard flat
  const etatCivil = raw["Informations d'état civil"];
  const pp = etatCivil?.personnePhysique;
  const adresse = raw.adresse;
  const contact = raw.contactInfosPersonnels;

  const result: Record<string, unknown> = {};

  // ── Personne physique ──
  if (pp) {
    if (pp.civilite) result.civilite = pp.civilite;
    if (pp.sexe) result.sexe = pp.sexe;
    result.nomFamille = s(pp.nomFamille);
    result.nomUtilise = s(pp.nomUtilise);
    result.prenomUtilise = s(pp.prenomUtilise);
    result.prenomsActeNaissance = s(pp.prenomsActeNaissance);
    if (pp.dateNaissance) result.dateNaissance = pp.dateNaissance;
    if (pp.situationFamiliale) result.situationFamiliale = pp.situationFamiliale;
    if (pp.communeNaissance) {
      result.communeNaissanceCP = s(pp.communeNaissance.codePostal);
      result.communeNaissanceLibelle = s(pp.communeNaissance.libelleCommune);
    }
    if (pp.paysNaissance) {
      result.paysNaissance = s(pp.paysNaissance.libellePays);
    }
    if (pp.nir) result.nir = pp.nir;
    if (pp.ins) result.ins = pp.ins;
  }

  if (etatCivil?.clientId) result.clientId = etatCivil.clientId;

  // ── Adresse ──
  if (adresse) {
    result.adresseLigne = s(adresse.ligne);
    result.adresseCommentaire = s(adresse.commentaire);
    result.codePostal = s(adresse.codePostal);
    result.commune = s(adresse.libelleCommune);
  }

  // ── Contacts personnels ──
  if (contact) {
    result.telDomicile = s(contact.domicile);
    result.telMobile = s(contact.mobile);
    result.email = s(contact.mail);
  }

  return result;
}

/**
 * Contacts : inverse de adaptContacts().
 * EvalSchema : Contact[] (tableau direct)
 * → format wizard : { noContact: boolean, contacts: Contact[] }
 *
 * Les contacts restent au format nested (personnePhysique, contactInfosPersonnels…)
 * car ContactsForm.contactFromJson() gère déjà le dénesting via fallback
 * (c.nomUtilise || c.personnePhysique?.nomUtilise).
 */
export function reverseAdaptContacts(raw: unknown): Record<string, unknown> {
  if (!raw) return { noContact: true, contacts: [] };

  // Déjà en format wizard → passer tel quel
  if (isRecord(raw) && 'contacts' in raw) return raw as Record<string, unknown>;

  // EvalSchema format : Contact[] → wrapper wizard
  if (Array.isArray(raw)) {
    return {
      noContact: raw.length === 0,
      contacts: raw,
    };
  }

  return { noContact: true, contacts: [] };
}

/**
 * Dispositifs : inverse de adaptDispositifs().
 * EvalSchema : Dispositif[] (tableau direct)
 * → format wizard : { noDispositif: boolean, items: Dispositif[] }
 */
export function reverseAdaptDispositifs(raw: unknown): Record<string, unknown> {
  if (!raw) return { noDispositif: true, items: [] };

  // Déjà en format wizard → passer tel quel
  if (isRecord(raw) && 'items' in raw) return raw as Record<string, unknown>;

  // EvalSchema format : Dispositif[] → wrapper wizard
  if (Array.isArray(raw)) {
    return {
      noDispositif: raw.length === 0,
      items: raw,
    };
  }

  return { noDispositif: true, items: [] };
}

// ── Assemblage complet ────────────────────────────────────────────────

/**
 * Sections nécessitant une transformation wizard → EvalSchema au submit.
 *
 * materiels : le JSON schema attend un objet { noMateriel, items: [...] }
 * dispositifs : le JSON schema attend un tableau direct [{dispositif, statut, ...}]
 * usager/contacts : reconstruction format nested EvalSchema + filtrage enums vides
 */
const SECTION_ADAPTERS: Record<string, (raw: unknown) => unknown> = {
  usager: adaptUsager,
  contacts: adaptContacts,
  materiels: adaptMateriels,
  dispositifs: adaptDispositifs,
};

/**
 * Transforme les données d'une section si un adaptateur existe.
 * Utilisé par buildEvaluationData() en mode submit.
 */
export function adaptSectionData(sectionId: string, data: unknown): unknown {
  const adapter = SECTION_ADAPTERS[sectionId];
  return adapter ? adapter(data) : data;
}

// ── Assemblage inverse (prefill) ──────────────────────────────────────

/**
 * Sections nécessitant une transformation EvalSchema → wizard au prefill.
 *
 * usager : dénesting complet (personnePhysique, adresse, contactInfosPersonnels → clés plates)
 * contacts : rewrap Contact[] → { noContact, contacts[] }
 * dispositifs : rewrap Dispositif[] → { noDispositif, items[] }
 * materiels : pas besoin (déjà objet { noMateriel, items } dans les deux sens)
 * social : pas besoin (pas de forward adapter → même format)
 */
const REVERSE_SECTION_ADAPTERS: Record<string, (raw: unknown) => unknown> = {
  usager: reverseAdaptUsager,
  contacts: reverseAdaptContacts,
  dispositifs: reverseAdaptDispositifs,
};

/**
 * Transforme les données d'une section EvalSchema → wizard flat si un reverse adapter existe.
 * Utilisé par prefillFromPreviousEvaluation() pour injecter des données lisibles par les formulaires.
 */
export function reverseAdaptSectionData(sectionId: string, data: unknown): unknown {
  const adapter = REVERSE_SECTION_ADAPTERS[sectionId];
  return adapter ? adapter(data) : data;
}