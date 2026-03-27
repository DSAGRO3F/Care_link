<!--
  CareLink - SocialForm
  Chemin : frontend/src/components/evaluation/forms/SocialForm.vue

  Rôle : Section 4/10 du wizard saisie évaluation — Contexte social du patient.
         4 blocs fixes : Contexte, Habitat, Vie Sociale, PEC.
         Sérialise vers { blocs: [{ nom, questionReponse: [{question, reponse}] }] }
         Compatible avec SocialBlocSection.vue (formatter visualisation).

  Habitat — Composant cascade pièces :
    Étape 1 : composition (chips + stepper) → array composition[{piece, nombre}]
    Étape 2 : flags + détails (accordion) → array difficultes[{piece, numero, detail}]
    Sérialisation JSON structurée (plus d'encodage ;&;).
    🆕 18/03/2026 : remplacement encodage ;&; par JSON structuré

  Conventions :
  - form-fieldset / form-legend / form-legend-icon--amber (section colorClass)
  - form-grid-2 / form-group / form-label (main.css)
  - habitat-* classes dans main.css (accordion, toggle, stepper, chips)
  - Palette slate-* + amber-500/600
  - Icônes Lucide uniquement
  - Emit : @update:data + @update:status (pattern ContactsForm / UsagerForm)
  - null pour "pas de valeur", jamais undefined
-->
<template>
  <div class="space-y-7">
    <!-- ── Bloc 1 : Contexte ─────────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--amber">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--amber">
          <FileText :size="15" />
        </span>
        Contexte de la demande
      </legend>

      <div class="form-grid-2">
        <!-- Nature de la demande -->
        <div class="form-group">
          <label class="form-label form-label--required">Nature de la demande</label>
          <Select
            v-model="natureDemandeSelection"
            :options="OPTIONS_NATURE_DEMANDE"
            placeholder="Sélectionner..."
            class="w-full"
          />
          <InputText
            v-if="natureDemandeSelection === 'Autre'"
            v-model="autreNatureDemande"
            placeholder="Précisez la nature de la demande..."
            class="w-full mt-2"
          />
        </div>

        <!-- Origine de la demande -->
        <div class="form-group">
          <label class="form-label form-label--required">Origine de la demande</label>
          <Select
            v-model="blocs.contexte['ORIGINE DE LA DEMANDE']"
            :options="OPTIONS_ORIGINE_DEMANDE"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Date de la demande -->
        <div class="form-group">
          <label class="form-label">Date de la demande</label>
          <div class="split-date-input">
            <InputText
              v-model="dateParts.dateDemandeJour"
              placeholder="JJ"
              class="split-date-input__jour"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.dateDemandeMois"
              placeholder="MM"
              class="split-date-input__mois"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.dateDemandeAnnee"
              placeholder="AAAA"
              class="split-date-input__annee"
              maxlength="4"
            />
          </div>
        </div>

        <!-- Date du rendez-vous -->
        <div class="form-group">
          <label class="form-label">Date du rendez-vous</label>
          <div class="split-date-input">
            <InputText
              v-model="dateParts.dateRdvJour"
              placeholder="JJ"
              class="split-date-input__jour"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.dateRdvMois"
              placeholder="MM"
              class="split-date-input__mois"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.dateRdvAnnee"
              placeholder="AAAA"
              class="split-date-input__annee"
              maxlength="4"
            />
          </div>
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Heure du rendez-vous -->
        <div class="form-group">
          <label class="form-label">Heure du rendez-vous</label>
          <InputText v-model="blocs.contexte['Heure du rendez-vous']" type="time" class="w-full" />
        </div>

        <!-- Tiers présent -->
        <div class="form-group">
          <label class="form-label">Tiers présent ou contact pour cette évaluation</label>
          <Select
            v-model="blocs.contexte['TIERS PRÉSENT OU CONTACT POUR CETTE ÉVALUATION']"
            :options="OPTIONS_OUI_NON"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <!-- Événements et situation de rupture -->
      <div class="form-group mt-5">
        <label class="form-label">Événements et situation de rupture</label>
        <Textarea
          v-model="blocs.contexte['ÉVÈNEMENTS ET SITUATION DE RUPTURE']"
          rows="2"
          placeholder="Hospitalisation récente, chute, dégradation…"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Autres demandes en cours -->
      <div class="form-group mt-5">
        <label class="form-label">Autres demandes en cours</label>
        <InputText
          v-model="blocs.contexte['Autres demandes en cours']"
          placeholder="SSIAD, APA, PCH…"
          class="w-full"
        />
      </div>

      <!-- Commentaires tiers -->
      <div class="form-group mt-5">
        <label class="form-label">Commentaires du tiers présent ou du contact principal</label>
        <Textarea
          v-model="blocs.contexte['Commentaires du tiers présent ou du contact principal']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Expression de la personne -->
      <div class="form-group mt-5">
        <label class="form-label">Expression de la personne (souhaits, projets, attentes…)</label>
        <Textarea
          v-model="blocs.contexte['Expression de la personne (souhaits, projets, attentes,…)']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Précisions origine orientation -->
      <div class="form-group mt-5">
        <label class="form-label"
          >Précisions sur l'origine de l'orientation vers nos services</label
        >
        <Textarea
          v-model="blocs.contexte['Précisions sur l\'origine de l\'orientation vers nos services']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Commentaires évaluateur contexte -->
      <div class="form-group mt-5">
        <label class="form-label">Commentaires de l'évaluateur sur le contexte de la demande</label>
        <Textarea
          v-model="blocs.contexte['Commentaires de l\'évaluateur sur le contexte de la demande']"
          rows="3"
          class="w-full"
          auto-resize
        />
      </div>
    </fieldset>

    <!-- Séparateur Contexte → Habitat -->
    <div class="bloc-separator">
      <div class="bloc-separator__dot"></div>
    </div>

    <!-- ── Bloc 2 : Habitat ──────────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--emerald">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--emerald">
          <Home :size="15" />
        </span>
        Habitat et environnement
      </legend>

      <div class="form-grid-2">
        <!-- Localisation -->
        <div class="form-group">
          <label class="form-label form-label--required">Localisation</label>
          <Select
            v-model="blocs.habitat['LOCALISATION']"
            :options="OPTIONS_LOCALISATION"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Type logement -->
        <div class="form-group">
          <label class="form-label form-label--required">Type de logement</label>
          <Select
            v-model="blocs.habitat['TYPE DE LOGEMENT']"
            :options="OPTIONS_TYPE_LOGEMENT"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Statut -->
        <div class="form-group">
          <label class="form-label">Statut d'occupation</label>
          <Select
            v-model="blocs.habitat['STATUT']"
            :options="OPTIONS_STATUT_LOGEMENT"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Surface -->
        <div class="form-group">
          <label class="form-label">Surface approximative</label>
          <Select
            v-model="blocs.habitat['SURFACE APPROXIMATIVE DU LOGEMENT']"
            :options="OPTIONS_SURFACE"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <!-- Accessibilité -->
      <div class="form-group mt-5">
        <label class="form-label">Éléments d'accessibilité au logement</label>
        <InputText
          v-model="blocs.habitat['ÉLÉMENTS D\'ACCESSIBILITÉ AU LOGEMENT']"
          placeholder="Marches, ascenseur, rampe…"
          class="w-full"
        />
      </div>

      <!-- Commerces proximité -->
      <div class="form-group mt-5">
        <label class="form-label">Commerces et services de proximité (&lt; 10 mn à pied)</label>
        <InputText
          v-model="
            blocs.habitat['COMMERCES ET SERVICES DE PROXIMITÉ ( À MOINS DE 10 MN DE MARCHE)']
          "
          placeholder="Pharmacie, superette, médecin…"
          class="w-full"
        />
      </div>

      <!-- Transports -->
      <div class="form-group mt-5">
        <label class="form-label">Moyens de transport à proximité (&lt; 10 mn à pied)</label>
        <InputText
          v-model="
            blocs.habitat[
              'MOYENS DE TRANSPORT À PROXIMITÉ (A MOINS DE 10 MN À PIED - INDIQUEZ SI POSSIBLE LES LIGNES ET ARRÊTS)'
            ]
          "
          placeholder="Bus ligne X, arrêt Y…"
          class="w-full"
        />
      </div>

      <!-- ── Composition et difficultés du logement (cascade structurée) ── -->
      <div class="habitat-rooms-section mt-5">
        <!-- Étape 1 : Composition -->
        <label class="form-label" style="margin-bottom: 8px">Composition du logement</label>

        <!-- Chips pièces avec steppers -->
        <div class="habitat-room-chips">
          <div v-for="rt in roomTypes" :key="rt.type" class="habitat-room-chip">
            <span class="habitat-room-chip__label">{{ rt.type }}</span>
            <div class="habitat-stepper">
              <button
                :disabled="rt.count <= 1"
                type="button"
                class="habitat-stepper__btn"
                @click="updateRoomCount(rt.type, -1)"
              >
                −
              </button>
              <span class="habitat-stepper__val">{{ rt.count }}</span>
              <button
                type="button"
                class="habitat-stepper__btn"
                @click="updateRoomCount(rt.type, 1)"
              >
                +
              </button>
            </div>
            <button
              type="button"
              class="habitat-room-chip__remove"
              title="Retirer cette pièce"
              @click="removeRoomType(rt.type)"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Ajout pièce -->
        <div class="habitat-add-bar">
          <Select
            v-model="roomTypeToAdd"
            :options="availableRoomOptions"
            placeholder="Ajouter une pièce…"
            class="habitat-add-bar__select"
          />
          <button
            :disabled="!roomTypeToAdd"
            type="button"
            class="habitat-add-bar__btn"
            @click="addRoomType()"
          >
            <Plus :size="14" />
            Ajouter
          </button>
        </div>

        <!-- Étape 2 : Difficultés par pièce (accordion) -->
        <template v-if="roomInstances.length > 0">
          <div class="habitat-separator"></div>
          <label class="form-label" style="margin-bottom: 8px">Difficultés par pièce</label>
          <p class="habitat-help-text">
            Activez le toggle pour signaler des difficultés, puis décrivez-les.
          </p>

          <div class="habitat-accordion">
            <div
              v-for="inst in roomInstances"
              :key="inst.key"
              :class="{
                'habitat-accordion__item--flagged': inst.flagged,
                'habitat-accordion__item--open': openRooms.has(inst.key),
              }"
              class="habitat-accordion__item"
            >
              <!-- Header -->
              <div class="habitat-accordion__header" @click="toggleAccordion(inst.key)">
                <ChevronRight :size="16" class="habitat-accordion__chevron" />
                <span class="habitat-accordion__name">{{ inst.type }} {{ inst.num }}</span>
                <span
                  :class="
                    inst.flagged
                      ? 'habitat-accordion__badge--amber'
                      : 'habitat-accordion__badge--slate'
                  "
                  class="habitat-accordion__badge"
                >
                  {{ inst.flagged ? 'Difficultés' : 'OK' }}
                </span>
                <div
                  :class="{ 'habitat-toggle--on': inst.flagged }"
                  class="habitat-toggle"
                  @click.stop="toggleFlag(inst.key)"
                />
              </div>

              <!-- Body -->
              <div v-if="openRooms.has(inst.key)" class="habitat-accordion__body">
                <template v-if="inst.flagged">
                  <label class="form-label">Précisez les difficultés</label>
                  <Textarea
                    :model-value="inst.detail"
                    rows="2"
                    placeholder="Décrivez les difficultés constatées dans cette pièce…"
                    class="w-full"
                    auto-resize
                    @update:model-value="updateDetail(inst.key, $event)"
                  />
                </template>
                <p v-else class="habitat-accordion__empty">
                  Aucune difficulté signalée pour cette pièce.
                </p>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Commentaires évaluateur habitat -->
      <div class="form-group mt-5">
        <label class="form-label">Commentaires de l'évaluateur sur l'habitat</label>
        <Textarea
          v-model="
            blocs.habitat[
              'Commentaires de l\'évaluateur sur l\'habitat et l\'environnement de proximité'
            ]
          "
          rows="3"
          class="w-full"
          auto-resize
        />
      </div>
    </fieldset>

    <!-- Séparateur Habitat → Vie Sociale -->
    <div class="bloc-separator">
      <div class="bloc-separator__dot"></div>
    </div>

    <!-- ── Bloc 3 : Vie Sociale ──────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--violet">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--violet">
          <Users :size="15" />
        </span>
        Vie sociale et participation
      </legend>

      <div class="form-grid-2">
        <!-- Situation familiale -->
        <div class="form-group">
          <label class="form-label form-label--required">Situation familiale</label>
          <Select
            v-model="blocs.vieSociale['SITUATION FAMILIALE']"
            :options="OPTIONS_SITUATION_FAMILIALE"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Mode de vie -->
        <div class="form-group">
          <label class="form-label form-label--required">Mode de vie</label>
          <Select
            v-model="blocs.vieSociale['MODE DE VIE']"
            :options="OPTIONS_MODE_VIE"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Mesure de protection -->
        <div class="form-group">
          <label class="form-label">Mesure de protection</label>
          <Select
            v-model="blocs.vieSociale['MESURE DE PROTECTION']"
            :options="OPTIONS_MESURE_PROTECTION"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Animal de compagnie -->
        <div class="form-group">
          <label class="form-label">Présence d'un animal de compagnie</label>
          <Select
            v-model="blocs.vieSociale['PRÉSENCE D\'UN ANIMAL DE COMPAGNIE']"
            :options="OPTIONS_OUI_NON"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Précautions animal — affiché juste à côté de la question de présence -->
        <div class="form-group">
          <label class="form-label">Précautions vis-à-vis de l'animal de compagnie</label>
          <InputText
            v-model="blocs.vieSociale['PRÉCAUTIONS A PRENDRE VIS-À-VIS DE L\'ANIMAL DE COMPAGNIE']"
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Reçoit des visites -->
        <div class="form-group">
          <label class="form-label">Reçoit des visites de proches</label>
          <Select
            v-model="blocs.vieSociale['LA PERSONNE REÇOIT-ELLE DES VISITES DE PROCHES ?']"
            :options="OPTIONS_OUI_NON"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Sentiment isolement -->
        <div class="form-group">
          <label class="form-label">Sentiment d'isolement ou de solitude</label>
          <Select
            v-model="
              blocs.vieSociale[
                'LA PERSONNE ÉPROUVE-T-ELLE UN SENTIMENT D\'ISOLEMENT OU DE SOLITUDE ?'
              ]
            "
            :options="OPTIONS_OUI_NON"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Participation activités extérieures -->
        <div class="form-group">
          <label class="form-label">Participation à des activités à l'extérieur</label>
          <Select
            v-model="blocs.vieSociale['Participation à des activités à l\'extérieur']"
            :options="OPTIONS_OUI_NON"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Description activités extérieur — couplée à la question de participation -->
        <div class="form-group">
          <label class="form-label">Description des activités à l'extérieur</label>
          <Textarea
            v-model="blocs.vieSociale['DESCRIPTION DES ACTIVITES A L\'EXTÉRIEUR']"
            rows="2"
            class="w-full"
            auto-resize
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Souhait autres activités -->
        <div class="form-group">
          <label class="form-label">Souhait d'autres activités</label>
          <Select
            v-model="blocs.vieSociale['SOUHAIT D\'AUTRES ACTIVITÉS']"
            :options="OPTIONS_OUI_NON_NSP"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Si oui lesquelles — couplé au souhait -->
        <div class="form-group">
          <label class="form-label">Si oui, lesquelles ?</label>
          <InputText v-model="blocs.vieSociale['Si oui lesquelles?']" class="w-full" />
        </div>
      </div>

      <!-- Activités au domicile — champ seul pleine largeur -->
      <div class="form-group mt-5">
        <label class="form-label">Description des activités au domicile</label>
        <Textarea
          v-model="blocs.vieSociale['DESCRIPTION DES ACTIVITES AU DOMICILE']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Commentaires participation sociale -->
      <div class="form-group mt-5">
        <label class="form-label">Commentaire de l'évaluateur sur la participation sociale</label>
        <Textarea
          v-model="blocs.vieSociale['Commentaire de l\'évaluateur sur la participation social']"
          rows="3"
          class="w-full"
          auto-resize
        />
      </div>
    </fieldset>

    <!-- Séparateur Vie Sociale → PEC -->
    <div class="bloc-separator">
      <div class="bloc-separator__dot"></div>
    </div>

    <!-- ── Bloc 4 : PEC ──────────────────────────────────────────────── -->
    <fieldset class="form-fieldset form-fieldset--slate">
      <legend class="form-legend">
        <span class="form-legend-icon form-legend-icon--slate">
          <ClipboardList :size="15" />
        </span>
        Prise en charge actuelle (PEC)
      </legend>

      <div class="form-grid-2">
        <!-- Plan d'aide en cours -->
        <div class="form-group">
          <label class="form-label form-label--required">Plan d'aide en cours</label>
          <Select
            v-model="blocs.pec['PLAN D\'AIDE EN COURS']"
            :options="OPTIONS_PLAN_AIDE"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>

        <!-- Aide extra-légale -->
        <div class="form-group">
          <label class="form-label">Aide extra-légale en cours</label>
          <Select
            v-model="blocs.pec['AIDE EXTRA LÉGALE EN COURS']"
            :options="OPTIONS_AIDE_EXTRA"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Numéro de dossier -->
        <div class="form-group">
          <label class="form-label">Numéro de dossier</label>
          <InputText v-model="blocs.pec['NUMÉRO DE DOSSIER']" class="w-full" />
        </div>

        <!-- Classement GIR retenu -->
        <div class="form-group">
          <label class="form-label">Classement GIR retenu</label>
          <Select
            v-model="blocs.pec['CLASSEMENT GIR RETENU']"
            :options="OPTIONS_GIR"
            placeholder="Sélectionner..."
            class="w-full"
          />
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Droits ouverts du -->
        <div class="form-group">
          <label class="form-label">Droits ouverts du</label>
          <div class="split-date-input">
            <InputText
              v-model="dateParts.droitsOuvertsDuJour"
              placeholder="JJ"
              class="split-date-input__jour"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.droitsOuvertsDuMois"
              placeholder="MM"
              class="split-date-input__mois"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.droitsOuvertsDuAnnee"
              placeholder="AAAA"
              class="split-date-input__annee"
              maxlength="4"
            />
          </div>
        </div>

        <!-- Au -->
        <div class="form-group">
          <label class="form-label">Au</label>
          <div class="split-date-input">
            <InputText
              v-model="dateParts.droitsOuvertsAuJour"
              placeholder="JJ"
              class="split-date-input__jour"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.droitsOuvertsAuMois"
              placeholder="MM"
              class="split-date-input__mois"
              maxlength="2"
            />
            <span class="split-date-input__sep">/</span>
            <InputText
              v-model="dateParts.droitsOuvertsAuAnnee"
              placeholder="AAAA"
              class="split-date-input__annee"
              maxlength="4"
            />
          </div>
        </div>
      </div>

      <div class="form-grid-2">
        <!-- Taux participation usager -->
        <div class="form-group">
          <label class="form-label">Taux de participation usager</label>
          <InputText
            v-model="blocs.pec['TAUX DE PARTICIP. USAGER']"
            placeholder="ex : 10%"
            class="w-full"
          />
        </div>

        <!-- Mode intervention aide humaine -->
        <div class="form-group">
          <label class="form-label">Mode d'intervention de l'aide humaine</label>
          <InputText
            v-model="blocs.pec['MODE D\'INTERVENTION DE L\'AIDE HUMAINE']"
            class="w-full"
          />
        </div>
      </div>

      <!-- Coordonnées organisme financement -->
      <div class="form-group mt-5">
        <label class="form-label">Coordonnées de l'organisme de financement</label>
        <InputText
          v-model="blocs.pec['COORDONNÉES DE L\'ORGANISME INTERVENANT DANS LE FINANCEMENT']"
          class="w-full"
        />
      </div>

      <!-- Autres éléments plan d'aide -->
      <div class="form-group mt-5">
        <label class="form-label">Autres éléments inscrits au plan d'aide</label>
        <Textarea
          v-model="blocs.pec['Autres éléments inscrits au plan d\'aide']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Infos sup aides extra-légales -->
      <div class="form-group mt-5">
        <label class="form-label">Informations supplémentaires sur les aides extra-légales</label>
        <Textarea
          v-model="blocs.pec['INFORMATIONS SUPPLEMENTAIRES SUR LES AIDES EXTRA LEGALES']"
          rows="2"
          class="w-full"
          auto-resize
        />
      </div>

      <!-- Commentaires évaluateur PEC -->
      <div class="form-group mt-5">
        <label class="form-label">Commentaires de l'évaluateur sur la prise en charge</label>
        <Textarea
          v-model="
            blocs.pec[
              'Commentaires de l\'évaluateur sur la prise en charge (préciser si le médecin traitant est informé de la démarche)'
            ]
          "
          rows="3"
          placeholder="Préciser si le médecin traitant est informé de la démarche…"
          class="w-full"
          auto-resize
        />
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
  /**
   * CareLink - SocialForm
   * Chemin : frontend/src/components/evaluation/forms/SocialForm.vue
   */
  import { reactive, ref, computed, watch, onMounted } from 'vue';
  import InputText from 'primevue/inputtext';
  import Textarea from 'primevue/textarea';
  import Select from 'primevue/select';
  import { FileText, Home, Users, ClipboardList, ChevronRight, Plus } from 'lucide-vue-next';
  import type { PatientResponse } from '@/types';
  import type { SectionStatus, WizardSectionData } from '@/composables/useEvaluationWizard';
  import { parseDateParts, joinDateParts, prefillDateParts } from './dateHelpers';

  // ── Props & Emits ──────────────────────────────────────────────────────

  interface Props {
    patient: PatientResponse | null;
    initialData?: WizardSectionData;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<{
    (e: 'update:data', data: WizardSectionData): void;
    (e: 'update:status', status: SectionStatus): void;
  }>();

  // ── Référentiels options ───────────────────────────────────────────────

  const OPTIONS_NATURE_DEMANDE = [
    'Première demande',
    'Admission en urgence',
    'Admission programmée',
    'Renouvellement',
    'Réévaluation',
    'Autre',
  ];

  const OPTIONS_ORIGINE_DEMANDE = [
    'Hôpital',
    'Médecin traitant',
    'Famille',
    'Auto-saisine',
    'CCAS',
    'Assistante sociale',
    'Autre',
  ];

  const OPTIONS_OUI_NON = ['Oui', 'Non'];
  const OPTIONS_OUI_NON_NSP = ['Oui', 'Non', 'NSP'];

  const OPTIONS_LOCALISATION = ['Urbain', 'Péri-urbain', 'Rural'];

  const OPTIONS_TYPE_LOGEMENT = [
    'Maison',
    'Appartement',
    'Résidence autonomie',
    'Foyer-logement',
    'Autre',
  ];

  const OPTIONS_STATUT_LOGEMENT = ['Propriétaire', 'Locataire', 'Hébergé chez un proche', 'Autre'];

  const OPTIONS_SURFACE = ['< 30 M2', '30-50 M2', '50-80 M2', '80-100 M2', '> 100 M2'];

  const OPTIONS_SITUATION_FAMILIALE = [
    'Célibataire',
    'Marié(e)',
    'Pacsé(e)',
    'Divorcé(e)',
    'Séparé(e)',
    'Veuf(ve)',
    'Autre',
  ];

  const OPTIONS_MODE_VIE = [
    'Vit seul(e)',
    'Vit avec conjoint',
    'Vit avec personne autonome',
    'Vit avec aidant',
    'En institution',
    'Autre',
  ];

  const OPTIONS_MESURE_PROTECTION = [
    'Aucune',
    'Sauvegarde de justice',
    'Curatelle simple',
    'Curatelle renforcée',
    'Tutelle',
    'Mesure accompagnement social ou judiciaire',
    'Autre',
  ];

  const OPTIONS_PLAN_AIDE = [
    'Aucun',
    'APA domicile',
    'APA établissement',
    'PCH',
    'Aide ménagère CAF/CARSAT',
    'Autre',
  ];

  const OPTIONS_AIDE_EXTRA = ['Aucune', 'Aide mutuelle', 'Aide employeur', 'Autre'];

  const OPTIONS_GIR = ['Non renseigné', 'GIR 1', 'GIR 2', 'GIR 3', 'GIR 4', 'GIR 5', 'GIR 6'];

  // ── Habitat : types de pièces disponibles ────────────────────────────────

  const ROOM_TYPE_OPTIONS = [
    'Séjour',
    'Chambre',
    'SDB',
    'WC',
    'Cuisine',
    'Couloirs',
    'Entrée',
    'Bureau',
    'Autre',
  ];

  // ── Habitat : état structuré pièces ──────────────────────────────────────
  //
  // Le composant cascade gère un état structuré (roomTypes + roomInstances)
  // sérialisé en JSON propre dans buildData() :
  //   - composition: [{ piece, nombre }]
  //   - difficultes: [{ piece, numero, detail }]

  interface RoomType {
    type: string;
    count: number;
  }

  interface RoomInstance {
    key: string; // ex: 'Chambre1'
    type: string; // ex: 'Chambre'
    num: number; // ex: 1
    flagged: boolean;
    detail: string;
  }

  const roomTypes = ref<RoomType[]>([]);
  const roomInstancesRaw = ref<RoomInstance[]>([]);
  const openRooms = ref<Set<string>>(new Set());
  const roomTypeToAdd = ref<string | null>(null);

  /** Instances dérivées des types — préserve les données existantes */
  function rebuildInstances() {
    const oldMap: Record<string, RoomInstance> = {};
    roomInstancesRaw.value.forEach((i) => {
      oldMap[i.key] = i;
    });

    const result: RoomInstance[] = [];
    roomTypes.value.forEach((t) => {
      for (let n = 1; n <= t.count; n++) {
        const key = `${t.type}${n}`;
        result.push(oldMap[key] ?? { key, type: t.type, num: n, flagged: false, detail: '' });
      }
    });
    roomInstancesRaw.value = result;
  }

  /** Proxy lecture seule pour le template */
  const roomInstances = computed(() => roomInstancesRaw.value);

  /** Options de pièces non encore ajoutées */
  const availableRoomOptions = computed(() =>
    ROOM_TYPE_OPTIONS.filter((t) => !roomTypes.value.some((rt) => rt.type === t)),
  );

  // ── Habitat rooms : actions template ─────────────────────────────────────

  function addRoomType() {
    const type = roomTypeToAdd.value;
    if (!type) return;
    const existing = roomTypes.value.find((rt) => rt.type === type);
    if (existing) {
      existing.count++;
    } else {
      roomTypes.value.push({ type, count: 1 });
    }
    roomTypeToAdd.value = null;
    rebuildInstances();
  }

  function removeRoomType(type: string) {
    roomTypes.value = roomTypes.value.filter((rt) => rt.type !== type);
    rebuildInstances();
  }

  function updateRoomCount(type: string, delta: number) {
    const rt = roomTypes.value.find((x) => x.type === type);
    if (!rt) return;
    rt.count = Math.max(1, rt.count + delta);
    rebuildInstances();
  }

  function toggleFlag(key: string) {
    const inst = roomInstancesRaw.value.find((i) => i.key === key);
    if (!inst) return;
    inst.flagged = !inst.flagged;
    if (!inst.flagged) inst.detail = '';
    // Auto-open si flaggé
    if (inst.flagged) openRooms.value.add(key);
  }

  function updateDetail(key: string, val: string) {
    const inst = roomInstancesRaw.value.find((i) => i.key === key);
    if (inst) inst.detail = val;
  }

  function toggleAccordion(key: string) {
    if (openRooms.value.has(key)) openRooms.value.delete(key);
    else openRooms.value.add(key);
  }

  // ── Chargement : données structurées → état pièces ─────────────────────

  function loadRoomsFromStructured(
    composition: Array<{ piece: string; nombre: number }>,
    difficultes: Array<{ piece: string; numero: number; detail?: string }>,
  ) {
    if (!composition || composition.length === 0) return;

    // Reconstruire roomTypes depuis composition
    roomTypes.value = composition.map((c) => ({ type: c.piece, count: c.nombre }));
    rebuildInstances();

    // Appliquer les difficultés
    const detailMap: Record<string, string> = {};
    for (const d of difficultes ?? []) {
      const key = `${d.piece}${d.numero}`;
      detailMap[key] = d.detail ?? '';
    }

    roomInstancesRaw.value.forEach((inst) => {
      if (detailMap[inst.key] !== undefined) {
        inst.flagged = true;
        inst.detail = detailMap[inst.key];
        openRooms.value.add(inst.key);
      }
    });
  }

  // ── État local réactif ─────────────────────────────────────────────────
  //
  // Un objet par bloc. La clé = libellé exact de la question dans le JSON
  // (doit correspondre exactement pour la compatibilité avec le formatter).

  const blocs = reactive({
    contexte: {
      'NATURE DE LA DEMANDE': null as string | null,
      'ORIGINE DE LA DEMANDE': null as string | null,
      'ÉVÈNEMENTS ET SITUATION DE RUPTURE': '',
      'Autres demandes en cours': '',
      'TIERS PRÉSENT OU CONTACT POUR CETTE ÉVALUATION': null as string | null,
      'Commentaires du tiers présent ou du contact principal': '',
      'Expression de la personne (souhaits, projets, attentes,…)': '',
      "Précisions sur l'origine de l'orientation vers nos services": '',
      'Date de la demande': '',
      'Date du rendez-vous': '',
      'Heure du rendez-vous': '',
      "Commentaires de l'évaluateur sur le contexte de la demande": '',
    },
    habitat: {
      LOCALISATION: null as string | null,
      'TYPE DE LOGEMENT': null as string | null,
      STATUT: null as string | null,
      "ÉLÉMENTS D'ACCESSIBILITÉ AU LOGEMENT": '',
      'SURFACE APPROXIMATIVE DU LOGEMENT': null as string | null,
      'COMMERCES ET SERVICES DE PROXIMITÉ ( À MOINS DE 10 MN DE MARCHE)': '',
      'MOYENS DE TRANSPORT À PROXIMITÉ (A MOINS DE 10 MN À PIED - INDIQUEZ SI POSSIBLE LES LIGNES ET ARRÊTS)':
        '',
      'Lesquels ?': '',
      "Commentaires de l'évaluateur sur l'habitat et l'environnement de proximité": '',
    },
    vieSociale: {
      'SITUATION FAMILIALE': null as string | null,
      'MODE DE VIE': null as string | null,
      'MESURE DE PROTECTION': null as string | null,
      "PRÉSENCE D'UN ANIMAL DE COMPAGNIE": null as string | null,
      "PRÉCAUTIONS A PRENDRE VIS-À-VIS DE L'ANIMAL DE COMPAGNIE": '',
      'LA PERSONNE REÇOIT-ELLE DES VISITES DE PROCHES ?': null as string | null,
      "Participation à des activités à l'extérieur": null as string | null,
      "SOUHAIT D'AUTRES ACTIVITÉS": null as string | null,
      'Si oui lesquelles?': '',
      "LA PERSONNE ÉPROUVE-T-ELLE UN SENTIMENT D'ISOLEMENT OU DE SOLITUDE ?": null as string | null,
      'DESCRIPTION DES ACTIVITES AU DOMICILE': '',
      "DESCRIPTION DES ACTIVITES A L'EXTÉRIEUR": '',
      "Commentaire de l'évaluateur sur la participation social": '',
    },
    pec: {
      "PLAN D'AIDE EN COURS": null as string | null,
      'AIDE EXTRA LÉGALE EN COURS': null as string | null,
      "COORDONNÉES DE L'ORGANISME INTERVENANT DANS LE FINANCEMENT": '',
      'NUMÉRO DE DOSSIER': '',
      'DROITS OUVERTS DU': '',
      AU: '',
      'CLASSEMENT GIR RETENU': null as string | null,
      'TAUX DE PARTICIP. USAGER': '',
      "MODE D'INTERVENTION DE L'AIDE HUMAINE": '',
      "Autres éléments inscrits au plan d'aide": '',
      'INFORMATIONS SUPPLEMENTAIRES SUR LES AIDES EXTRA LEGALES': '',
      "Commentaires de l'évaluateur sur la prise en charge (préciser si le médecin traitant est informé de la démarche)":
        '',
    },
  });

  // ── Gestion "Autre" Nature de la demande ───────────────────────────────
  const natureDemandeSelection = ref<string | null>(null);
  const autreNatureDemande = ref('');

  // Sync Select → valeur Bachelard
  watch(natureDemandeSelection, (val) => {
    if (val && val !== 'Autre') {
      blocs.contexte['NATURE DE LA DEMANDE'] = val;
      autreNatureDemande.value = '';
    } else if (val === 'Autre') {
      blocs.contexte['NATURE DE LA DEMANDE'] = autreNatureDemande.value || null;
    } else {
      blocs.contexte['NATURE DE LA DEMANDE'] = null;
    }
  });

  // Sync InputText libre → valeur Bachelard
  watch(autreNatureDemande, (val) => {
    if (natureDemandeSelection.value === 'Autre') {
      blocs.contexte['NATURE DE LA DEMANDE'] = val || null;
    }
  });

  // ── Dates 3 champs (JJ / MM / AAAA) ─────────────────────────────────────
  //
  // Les blocs conservent la valeur ISO (pour buildData), le template binde
  // sur dateParts, et un watcher synchronise parts → ISO dans blocs.

  const _dp = prefillDateParts();
  const dateParts = reactive({
    dateDemandeJour: '',
    dateDemandeMois: _dp.mois,
    dateDemandeAnnee: _dp.annee,
    dateRdvJour: '',
    dateRdvMois: _dp.mois,
    dateRdvAnnee: _dp.annee,
    droitsOuvertsDuJour: '',
    droitsOuvertsDuMois: _dp.mois,
    droitsOuvertsDuAnnee: _dp.annee,
    droitsOuvertsAuJour: '',
    droitsOuvertsAuMois: _dp.mois,
    droitsOuvertsAuAnnee: _dp.annee,
  });

  watch(dateParts, () => {
    blocs.contexte['Date de la demande'] = joinDateParts(
      dateParts.dateDemandeJour,
      dateParts.dateDemandeMois,
      dateParts.dateDemandeAnnee,
    );
    blocs.contexte['Date du rendez-vous'] = joinDateParts(
      dateParts.dateRdvJour,
      dateParts.dateRdvMois,
      dateParts.dateRdvAnnee,
    );
    blocs.pec['DROITS OUVERTS DU'] = joinDateParts(
      dateParts.droitsOuvertsDuJour,
      dateParts.droitsOuvertsDuMois,
      dateParts.droitsOuvertsDuAnnee,
    );
    blocs.pec['AU'] = joinDateParts(
      dateParts.droitsOuvertsAuJour,
      dateParts.droitsOuvertsAuMois,
      dateParts.droitsOuvertsAuAnnee,
    );
  });

  // ── Sérialisation vers le format { blocs: [...] } ──────────────────────
  //
  // Compatibilité exacte avec SocialBlocSection.vue :
  // chaque bloc → { nom, questionReponse: [{ question, reponse }] }

  function buildData(): WizardSectionData {
    const blocsTuples: Array<[string, Record<string, string | null>]> = [
      ['Contexte', blocs.contexte],
      ['Habitat', blocs.habitat],
      ['Vie Sociale', blocs.vieSociale],
      ['PEC', blocs.pec],
    ];

    return {
      blocs: blocsTuples.map(([nom, questions]) => {
        const bloc: Record<string, unknown> = {
          nom,
          questionReponse: Object.entries(questions).map(([question, reponse]) => ({
            question,
            reponse: reponse ?? '',
          })),
        };

        // Habitat : données structurées des pièces (composition + difficultés)
        if (nom === 'Habitat') {
          bloc.composition = roomTypes.value.map((t) => ({
            piece: t.type,
            nombre: t.count,
          }));
          bloc.difficultes = roomInstancesRaw.value
            .filter((i) => i.flagged && i.detail.trim())
            .map((i) => ({
              piece: i.type,
              numero: i.num,
              detail: i.detail,
            }));
        }

        return bloc;
      }),
    };
  }

  // ── Calcul du statut ───────────────────────────────────────────────────
  //
  // Champs pilotes (un par bloc) : si tous renseignés → complete
  // Si au moins un champ quelconque renseigné → partial
  // Sinon → empty

  function computeStatus(): SectionStatus {
    const pilots = [
      blocs.contexte['NATURE DE LA DEMANDE'],
      blocs.habitat['TYPE DE LOGEMENT'],
      blocs.vieSociale['SITUATION FAMILIALE'],
      blocs.pec["PLAN D'AIDE EN COURS"],
    ];

    const allPilotsFilled = pilots.every((v) => v !== null && v !== '');
    if (allPilotsFilled) return 'complete';

    // Au moins un champ renseigné dans n'importe quel bloc
    const allValues = [
      ...Object.values(blocs.contexte),
      ...Object.values(blocs.habitat),
      ...Object.values(blocs.vieSociale),
      ...Object.values(blocs.pec),
    ];
    const hasAny = allValues.some((v) => v !== null && v !== '');
    return hasAny ? 'partial' : 'empty';
  }

  // ── Chargement depuis initialData ─────────────────────────────────────

  function loadFromInitialData(data: WizardSectionData) {
    const blocsData: Array<{
      nom: string;
      questionReponse: Array<{ question: string; reponse: string }>;
      composition?: Array<{ piece: string; nombre: number }>;
      difficultes?: Array<{ piece: string; numero: number; detail: string }>;
    }> = data?.blocs ?? [];

    const blocMap: Record<string, Record<string, string>> = {};
    for (const b of blocsData) {
      blocMap[b.nom] = {};
      for (const qr of b.questionReponse ?? []) {
        blocMap[b.nom][qr.question] = qr.reponse ?? '';
      }
    }

    const fill = (target: Record<string, string | null>, nomBloc: string) => {
      const src = blocMap[nomBloc] ?? {};
      for (const key of Object.keys(target)) {
        if (key in src) {
          target[key] = src[key] || null;
        }
      }
    };

    fill(blocs.contexte, 'Contexte');
    fill(blocs.habitat, 'Habitat');
    fill(blocs.vieSociale, 'Vie Sociale');
    fill(blocs.pec, 'PEC');

    // ── Restore "Autre" Nature de la demande après chargement brouillon ──
    const loadedNature = blocs.contexte['NATURE DE LA DEMANDE'];
    if (loadedNature && OPTIONS_NATURE_DEMANDE.includes(loadedNature)) {
      natureDemandeSelection.value = loadedNature;
    } else if (loadedNature) {
      natureDemandeSelection.value = 'Autre';
      autreNatureDemande.value = loadedNature;
    }

    // Hydrater les dateParts depuis les valeurs ISO chargées
    const dd = parseDateParts(blocs.contexte['Date de la demande'] ?? '');
    dateParts.dateDemandeJour = dd.jour;
    dateParts.dateDemandeMois = dd.mois || dateParts.dateDemandeMois;
    dateParts.dateDemandeAnnee = dd.annee || dateParts.dateDemandeAnnee;

    const dr = parseDateParts(blocs.contexte['Date du rendez-vous'] ?? '');
    dateParts.dateRdvJour = dr.jour;
    dateParts.dateRdvMois = dr.mois || dateParts.dateRdvMois;
    dateParts.dateRdvAnnee = dr.annee || dateParts.dateRdvAnnee;

    const dou = parseDateParts(blocs.pec['DROITS OUVERTS DU'] ?? '');
    dateParts.droitsOuvertsDuJour = dou.jour;
    dateParts.droitsOuvertsDuMois = dou.mois || dateParts.droitsOuvertsDuMois;
    dateParts.droitsOuvertsDuAnnee = dou.annee || dateParts.droitsOuvertsDuAnnee;

    const dau = parseDateParts(blocs.pec['AU'] ?? '');
    dateParts.droitsOuvertsAuJour = dau.jour;
    dateParts.droitsOuvertsAuMois = dau.mois || dateParts.droitsOuvertsAuMois;
    dateParts.droitsOuvertsAuAnnee = dau.annee || dateParts.droitsOuvertsAuAnnee;

    // Reconstruire l'état structuré des pièces depuis les données Habitat
    const habitatBloc = blocsData.find((b) => b.nom === 'Habitat');
    if (habitatBloc) {
      loadRoomsFromStructured(habitatBloc.composition ?? [], habitatBloc.difficultes ?? []);
    }
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────

  onMounted(() => {
    if (props.initialData && Object.keys(props.initialData).length > 0) {
      loadFromInitialData(props.initialData);
    }
    // Émettre l'état initial (notamment si données pré-remplies depuis réévaluation)
    emit('update:data', buildData());
    emit('update:status', computeStatus());
  });

  // ── Réactivité : émet à chaque modification ──────────────────────────

  watch(
    [blocs, roomTypes, roomInstancesRaw],
    () => {
      emit('update:data', buildData());
      emit('update:status', computeStatus());
    },
    { deep: true },
  );
</script>
