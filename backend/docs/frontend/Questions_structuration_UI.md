# 🎯 Cadrage préalable
## Analogie : CareLink comme un hôtel multi-étages
Imagine CareLink comme un grand hôtel avec deux types d'accès bien distincts :
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🏨 HÔTEL CARELINK                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔑 ENTRÉE DIRECTION (back-office)          🚪 ENTRÉE CLIENTS (front-office)│
│  ────────────────────────────────           ─────────────────────────────── │
│  URL: admin.carelink.fr                     URL: app.carelink.fr            │
│                                                                             │
│  Qui ? L'équipe CareLink                    Qui ? Les professionnels de     │
│  (SuperAdmins)                              santé des structures clientes   │
│                                                                             │
│  Fait quoi ?                                Fait quoi ?                     │
│  • Gère les clients (tenants)               • Gère les patients             │
│  • Surveille l'activité                     • Planifie les soins            │
│  • Support technique                        • Coordonne les équipes         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
## Les 3 grandes "familles" d'utilisateurs

| Famille         | Profils                                          | Besoin principal        | Fréquence d'usage          |
|-----------------|--------------------------------------------------|-------------------------|----------------------------|
| 🔧 Plateforme   | PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT | Administrer CareLink    | Quotidien (équipe interne) |
| 👔 Admin Tenant | ADMIN du tenant                                  | Configurer sa structure | Hebdomadaire               |
| 👩‍⚕️ Métier    | Coordinateur, IDE, AS, Médecin...                | Soigner les patients    | Plusieurs fois/jour        |


## 📐 Proposition d'architecture : 2 applications distinctes
Je recommande deux applications Dash séparées plutôt qu'une seule application avec des vues conditionnelles. Pourquoi ?

| Critère     | 1 app monolithique              | 2 apps séparées ✅         |
|-------------|---------------------------------|---------------------------|
| Sécurité    | Risque de fuite entre contextes | Isolation totale          |
| Performance | Charge le code inutile          | Bundle optimisé par usage |
| UX          | Navigation complexe             | Navigation ciblée         |
| Maintenance | Couplage fort                   | Évolutions indépendantes  |
| Déploiement | Tout ou rien                    | Déploiement indépendant   |

## 🏗️ Arborescence proposée
### Application 1 : Console Plateforme (admin.carelink.fr)

Pour l'équipe CareLink uniquement (SuperAdmins)
```
admin.carelink.fr/
│
├── 🔐 /login                          # Connexion SuperAdmin
│
├── 📊 /dashboard                      # Vue d'ensemble plateforme
│   └── Objectif: KPIs globaux, alertes, activité récente
│
├── 🏢 /tenants                        # Gestion des clients
│   ├── /tenants                       # Liste des tenants (tableau filtrable)
│   ├── /tenants/new                   # Création d'un tenant
│   ├── /tenants/{id}                  # Fiche détaillée tenant
│   ├── /tenants/{id}/edit             # Modification
│   ├── /tenants/{id}/subscription     # Gestion abonnement
│   └── /tenants/{id}/stats            # Statistiques d'usage
│
├── 👤 /super-admins                   # Gestion équipe CareLink
│   ├── /super-admins                  # Liste des super-admins
│   ├── /super-admins/new              # Création
│   ├── /super-admins/{id}             # Fiche détaillée
│   └── /super-admins/{id}/edit        # Modification
│
├── 🔗 /assignments                    # Affectations cross-tenant
│   ├── /assignments                   # Liste des affectations
│   ├── /assignments/new               # Nouvelle affectation
│   └── /assignments/{id}              # Détail/modification
│
├── 📜 /audit                          # Logs d'audit
│   └── /audit                         # Journal des actions (filtrable)
│
└── ⚙️ /settings                       # Paramètres plateforme
    ├── /settings/profile              # Mon profil SuperAdmin
    └── /settings/security             # Changement mot de passe
Nombre de pages : ~15
```
### Application 2 : Application Métier (app.carelink.fr)

Pour les professionnels de santé (utilisateurs des tenants)
```
app.carelink.fr/
│
├── 🔐 /login                          # Connexion (PSC ou locale)
├── 🏢 /select-tenant                  # Sélecteur de structure (si multi-tenant)
│
├── 🏠 /                               # Tableau de bord personnalisé
│   └── Objectif: Ma journée, mes alertes, mes tâches
│
│
│ ══════════════════════════════════════════════════════════════════
│  MODULE PATIENTS (cœur de l'application)
│ ══════════════════════════════════════════════════════════════════
│
├── 👴 /patients                       # Gestion des patients
│   ├── /patients                      # Liste patients (cards ou tableau)
│   ├── /patients/new                  # Admission d'un patient
│   ├── /patients/{id}                 # Dossier patient (vue complète)
│   │   ├── ?tab=overview              #   → Synthèse
│   │   ├── ?tab=evaluations           #   → Évaluations AGGIR
│   │   ├── ?tab=vitals                #   → Constantes vitales
│   │   ├── ?tab=careplan              #   → Plan d'aide actif
│   │   ├── ?tab=coordination          #   → Carnet de liaison
│   │   ├── ?tab=documents             #   → Documents (PPA, PPCS)
│   │   └── ?tab=access                #   → Droits d'accès RGPD
│   ├── /patients/{id}/edit            # Modification informations
│   ├── /patients/{id}/evaluation/new  # Nouvelle évaluation AGGIR
│   └── /patients/{id}/vital/new       # Saisie constante vitale
│
│
│ ══════════════════════════════════════════════════════════════════
│  MODULE COORDINATION (planning quotidien)
│ ══════════════════════════════════════════════════════════════════
│
├── 📅 /planning                       # Planning et interventions
│   ├── /planning                      # Mon planning du jour/semaine
│   ├── /planning/team                 # Planning équipe (coordinateur)
│   └── /planning/intervention/{id}    # Détail intervention
│       ├── ?action=start              #   → Démarrer
│       ├── ?action=complete           #   → Terminer + saisie
│       └── ?action=cancel             #   → Annuler
│
├── 📝 /coordination                   # Carnet de liaison
│   ├── /coordination                  # Flux des entrées récentes
│   ├── /coordination/new              # Nouvelle entrée
│   └── /coordination/{id}             # Détail/modification
│
│
│ ══════════════════════════════════════════════════════════════════
│  MODULE PLANS D'AIDE (coordinateurs)
│ ══════════════════════════════════════════════════════════════════
│
├── 📋 /care-plans                     # Gestion des plans d'aide
│   ├── /care-plans                    # Liste des plans
│   ├── /care-plans/new                # Création depuis évaluation
│   ├── /care-plans/{id}               # Détail du plan
│   │   ├── ?tab=services              #   → Services planifiés
│   │   ├── ?tab=assignments           #   → Affectations
│   │   └── ?tab=history               #   → Historique modifications
│   ├── /care-plans/{id}/edit          # Modification
│   └── /care-plans/{id}/assign        # Interface d'affectation
│
│
│ ══════════════════════════════════════════════════════════════════
│  MODULE ADMINISTRATION TENANT (admin uniquement)
│ ══════════════════════════════════════════════════════════════════
│
├── ⚙️ /admin                          # Administration structure
│   ├── /admin/entities                # Gestion des entités
│   │   ├── /admin/entities            # Liste
│   │   ├── /admin/entities/new        # Création
│   │   └── /admin/entities/{id}       # Détail/modification
│   │
│   ├── /admin/users                   # Gestion des utilisateurs
│   │   ├── /admin/users               # Liste
│   │   ├── /admin/users/new           # Création
│   │   ├── /admin/users/{id}          # Fiche utilisateur
│   │   └── /admin/users/{id}/roles    # Gestion des rôles
│   │
│   ├── /admin/roles                   # Gestion des rôles
│   │   ├── /admin/roles               # Liste
│   │   └── /admin/roles/{id}          # Détail/permissions
│   │
│   ├── /admin/services                # Catalogue de services
│   │   ├── /admin/services            # Services activés
│   │   └── /admin/services/configure  # Personnalisation
│   │
│   └── /admin/stats                   # Statistiques structure
│
│
│ ══════════════════════════════════════════════════════════════════
│  PROFIL ET PARAMÈTRES UTILISATEUR
│ ══════════════════════════════════════════════════════════════════
│
└── 👤 /me                             # Mon espace
    ├── /me                            # Mon profil
    ├── /me/availability               # Mes disponibilités
    └── /me/preferences                # Préférences (notifications, thème)
Nombre de pages : ~35-40
```

## 🎨 Logique de regroupement des pages
### Principe 1 : Par "activité mentale"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORGANISATION PAR ACTIVITÉ MENTALE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🏠 DASHBOARD          "Où en suis-je ?"                                    │
│  ───────────────       Vue d'ensemble, alertes, tâches du jour              │
│                                                                             │
│  👴 PATIENTS           "Qui je soigne ?"                                    │
│  ───────────────       Dossiers, évaluations, suivi médical                 │
│                                                                             │
│  📅 PLANNING           "Que dois-je faire ?"                                │
│  ───────────────       Interventions, agenda, déplacements                  │
│                                                                             │
│  📝 COORDINATION       "Qu'ont fait les autres ?"                           │
│  ───────────────       Carnet de liaison, transmissions                     │
│                                                                             │
│  📋 PLANS D'AIDE       "Comment organiser les soins ?"                      │
│  ───────────────       Planification à moyen terme (coordinateurs)          │
│                                                                             │
│  ⚙️ ADMIN              "Comment configurer ?"                               │
│  ───────────────       Paramétrage structure (admin uniquement)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Principe 2 : Par fréquence d'usage

| Fréquence           | Pages                             | Position dans la nav               |
|---------------------|-----------------------------------|------------------------------------|
| Plusieurs fois/jour | Dashboard, Planning, Coordination | Accès direct (sidebar)             |
| Quotidien           | Patients, Interventions           | Accès direct (sidebar)             |
| Hebdomadaire        | Plans d'aide, Évaluations         | Sous-menu ou dans contexte patient |
| Mensuel             | Admin, Services, Stats            | Menu secondaire                    |


### Principe 3 : Navigation contextuelle
Plutôt que de multiplier les pages, on utilise des onglets dans le contexte :
/patients/{id}
│
├── [Onglet] Synthèse        → Vue résumée
├── [Onglet] Évaluations     → Liste + détail inline
├── [Onglet] Constantes      → Graphiques + saisie rapide
├── [Onglet] Plan d'aide     → Plan actif + historique
├── [Onglet] Coordination    → Carnet filtré sur ce patient
└── [Onglet] Documents       → PPA, PPCS, ordonnances
Avantage : L'utilisateur reste dans le contexte du patient, pas de navigation complexe.

## 📱 Adaptation mobile (responsive)

| Écran                 | Adaptation                                              |
|-----------------------|---------------------------------------------------------|
| Desktop (>1200px)     | Sidebar + contenu principal + panneau latéral optionnel |
| Tablette (768-1200px) | Sidebar repliable + contenu adapté                      |
| Mobile (<768px)       | Bottom navigation + pages simplifiées                   |

### Pour les professionnels terrain (tablette), les pages prioritaires :

**Mon planning du jour**
**Saisie rapide constantes**
**Carnet de coordination**
**Grille AGGIR (optimisée tactile)**


## 🎯 Objectifs par page (application métier)

| Page                 | Objectif principal                       | Utilisateurs cibles |
|----------------------|------------------------------------------|---------------------|
| Dashboard            | Voir ma journée en un coup d'œil         | Tous                |
| Liste patients       | Trouver rapidement un patient            | Tous                |
| Dossier patient      | Accéder à toutes les infos d'un patient  | Tous                |
| Évaluation AGGIR     | Réaliser une évaluation sur le terrain   | IDE, Coordinateur   |
| Saisie constantes    | Enregistrer rapidement une mesure        | IDE, AS             |
| Mon planning         | Organiser ma journée                     | Intervenants        |
| Planning équipe      | Visualiser/ajuster les affectations      | Coordinateur        |
| Carnet coordination  | Communiquer avec l'équipe                | Tous                |
| Plans d'aide         | Construire/modifier un plan de soins     | Coordinateur        |
| Affectation services | Assigner les professionnels aux services | Coordinateur        |
| Admin > Utilisateurs | Gérer les comptes                        | Admin tenant        |
| Admin > Services     | Personnaliser le catalogue               | Admin tenant        |


## Précision question: Deux appli au lieu d'une seule, mieux/moins bien ?
1️⃣ "Deux applications distinctes" - Clarification
Analogie : Deux bâtiments avec des entrées séparées
Imagine que CareLink, c'est comme une entreprise avec deux bâtiments distincts :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   🏢 BÂTIMENT A                          🏥 BÂTIMENT B                       │
│   ───────────────                        ───────────────                    │
│   "La Direction"                         "Le Centre de Soins"               │
│                                                                             │
│   URL: admin.carelink.fr                 URL: app.carelink.fr               │
│                                                                             │
│   ┌─────────────────────┐               ┌─────────────────────┐            │
│   │                     │               │                     │            │
│   │  Code source A      │               │  Code source B      │            │
│   │  (dossier admin/)   │               │  (dossier app/)     │            │
│   │                     │               │                     │            │
│   │  • Gestion tenants  │               │  • Dossiers patients│            │
│   │  • Super-admins     │               │  • Évaluations      │            │
│   │  • Audit            │               │  • Planning         │            │
│   │                     │               │  • Coordination     │            │
│   └─────────────────────┘               └─────────────────────┘            │
│                                                                             │
│   Serveur: port 8001                    Serveur: port 8002                  │
│   (ou domaine différent)                (ou domaine différent)              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Concrètement, qu'est-ce que ça signifie ?

| Aspect      | 1 application monolithique               | 2 applications séparées ✅                                        |
|-------------|------------------------------------------|------------------------------------------------------------------|
| Fichiers    | Un seul dossier app/                     | Deux dossiers : admin/ et app/                                   |
| Lancement   | python app.py (un seul)                  | python admin.py + python app.py                                  |
| URL         | carelink.fr/admin/* et carelink.fr/app/* | admin.carelink.fr/* et app.carelink.fr/*                         |
| Session     | Partagée (risque de confusion)           | Isolée (un SuperAdmin ne peut pas "glisser" vers l'app métier)   |
| Déploiement | Tout ensemble                            | Indépendant (tu peux mettre à jour l'admin sans toucher à l'app) |


Structure de fichiers proposée
```
carelink/
├── backend/                    # API FastAPI (déjà existant)
│   └── app/
│
├── frontend/                   # Nouveau - Applications Dash
│   ├── shared/                 # Code partagé entre les deux apps
│   │   ├── components/         # Composants Mantine réutilisables
│   │   ├── api_client.py       # Client HTTP pour appeler le backend
│   │   └── theme.py            # Thème visuel commun
│   │
│   ├── admin/                  # Application Console Plateforme
│   │   ├── app.py              # Point d'entrée Dash
│   │   ├── pages/              # Pages de l'admin
│   │   └── layouts/            # Layouts spécifiques
│   │
│   └── app/                    # Application Métier
│       ├── app.py              # Point d'entrée Dash
│       ├── pages/              # Pages métier
│       └── layouts/            # Layouts spécifiques

```
Question:
Est-ce que cette séparation te convient ?
ou préfères-tu une seule application avec des vues conditionnelles selon le type d'utilisateur ? 
Les deux approches sont valides, c'est une question d'architecture.


## Précision question: qu'est ce qu'il faut comprendre par nav. contextuelle ?
2️⃣ Navigation contextuelle - Explication
Analogie : Le dossier médical papier
Imagine un classeur patient physique que l'infirmière ouvre :
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   📁 CLASSEUR PATIENT : M. DELOIN ALAIN                                     │
│   ══════════════════════════════════════                                    │
│                                                                             │
│   Le classeur reste OUVERT sur le bureau.                                   │
│   On tourne les intercalaires sans jamais fermer le classeur.               │
│                                                                             │
│   ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐            │
│   │ SYNTHÈSE│ AGGIR   │CONSTANTES│COORD.  │ DOCS    │ ACCÈS   │            │
│   └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬────┘            │
│        │         │         │         │         │         │                  │
│        ▼         ▼         ▼         ▼         ▼         ▼                  │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                                                                     │  │
│   │   [Contenu de l'intercalaire sélectionné]                           │  │
│   │                                                                     │  │
│   │   Quand je clique sur "AGGIR", le contenu change                    │  │
│   │   MAIS le patient reste affiché en haut                             │  │
│   │   ET l'URL reste /patients/2910                                     │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
**En termes d'URL**

**Navigation traditionnelle (pages séparées) :**
/patients                    → Liste des patients
/patients/2910               → Fiche patient
/patients/2910/evaluations   → Liste évaluations (nouvelle page)
/patients/2910/vitals        → Constantes (nouvelle page)
/patients/2910/aggir/new     → Nouvelle évaluation (nouvelle page)


**Navigation contextuelle (onglets) :**
/patients                    → Liste des patients
/patients/2910               → Fiche patient (avec onglets intégrés)
/patients/2910?tab=synthese  → Onglet Synthèse
/patients/2910?tab=aggir     → Onglet AGGIR
/patients/2910?tab=vitals    → Onglet Constantes
/patients/2910?tab=coord     → Onglet Coordination
Visuellement avec Dash Mantine
python# Exemple simplifié de navigation contextuelle

```
dmc.Tabs(
    value=current_tab,
    children=[
        dmc.TabsList([
            dmc.TabsTab("Synthèse", value="synthese", leftSection=DashIconify(icon="mdi:account")),
            dmc.TabsTab("AGGIR", value="aggir", leftSection=DashIconify(icon="mdi:clipboard-check")),
            dmc.TabsTab("Constantes", value="vitals", leftSection=DashIconify(icon="mdi:heart-pulse")),
            dmc.TabsTab("Coordination", value="coord", leftSection=DashIconify(icon="mdi:message-text")),
            dmc.TabsTab("Documents", value="docs", leftSection=DashIconify(icon="mdi:file-document")),
        ]),
        
        # Le contenu change selon l'onglet, mais on reste sur la même page
        dmc.TabsPanel(render_synthese(patient), value="synthese"),
        dmc.TabsPanel(render_aggir(patient), value="aggir"),
        dmc.TabsPanel(render_vitals(patient), value="vitals"),
        # ...
    ]
)
```

### Avantages de la navigation contextuelle

| Avantage                       | Explication                                           |
|--------------------------------|-------------------------------------------------------|
| **Moins de clics**             | L'utilisateur reste dans le contexte du patient       |
| **Moins de chargement**        | Seul le contenu de l'onglet change, pas toute la page |
| **Moins de perte de contexte** | Le nom du patient reste visible en permanence         |
| **Plus intuitif**              | Reproduit le modèle mental du "dossier papier"        |

---

## 3️⃣ Structure de l'évaluation : Une page ou plusieurs ?

### Analyse du fichier JSON

J'ai identifié **8 sections principales** dans ton fichier d'évaluation :
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRUCTURE DU FICHIER D'ÉVALUATION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1️⃣ usager              État civil, adresse, contacts personnels           │
│     └── ~35 champs                                                          │
│                                                                             │
│  2️⃣ contacts            Cercle de soins (IDE, médecin...) + entourage      │
│     └── Liste de contacts (6 dans l'exemple)                                │
│                                                                             │
│  3️⃣ aggir               La grille AGGIR officielle                         │
│     ├── GIR calculé (1-6)                                                   │
│     ├── Temps d'aide estimé                                                 │
│     └── 17 variables avec sous-variables et adverbes (S, T, C, H)           │
│                                                                             │
│  4️⃣ social              Contexte social et environnement                   │
│     ├── Contexte (origine demande, événements rupture...)                   │
│     ├── Habitat (type logement, accessibilité...)                           │
│     ├── Vie sociale (situation familiale, animaux...)                       │
│     └── PEC (prise en charge actuelle, APA...)                              │
│                                                                             │
│  5️⃣ materiels           Équipements et aides techniques                    │
│     └── Liste : barres d'appui, lit médicalisé, fauteuil...                 │
│                                                                             │
│  6️⃣ sante               Bilan de santé complet (le plus gros !)            │
│     ├── Anxiété (+ test GAI)                                                │
│     ├── Cardio-respiratoire                                                 │
│     ├── Cognition (+ test Mini-Cog, ICOPE)                                  │
│     ├── Dépression (+ test Mini-GDS)                                        │
│     ├── Élimination                                                         │
│     ├── Général et ressenti                                                 │
│     ├── Médicaments                                                         │
│     ├── Mobilité (+ tests lever chaise, équilibre, marche)                  │
│     ├── Nutrition (+ IMC, MNA)                                              │
│     ├── Douleur                                                             │
│     ├── Polymédications                                                     │
│     ├── Sensoriel (vue, audition)                                           │
│     ├── Peau (risque escarre Norton)                                        │
│     ├── Seuils (constantes à surveiller)                                    │
│     ├── Comorbidités                                                        │
│     └── Mesures des constantes                                              │
│                                                                             │
│  7️⃣ dispositifs         Appareils médicaux (pacemaker, prothèses...)       │
│                                                                             │
│  8️⃣ poaSocial / ppa     Plan d'objectifs et d'actions                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ma recommandation : **Approche hybride "Wizard + Onglets"**

Je recommande une **approche en 2 temps** adaptée au contexte d'utilisation :

#### Temps 1 : La première évaluation (mode "Wizard")

Quand l'infirmière fait une **nouvelle évaluation complète** au domicile du patient, elle a besoin d'être guidée étape par étape :
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODE WIZARD (Nouvelle évaluation)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  URL: /patients/2910/evaluation/new                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ÉTAPE 2 / 6 : Évaluation AGGIR                                      │   │
│  │                                                                       │   │
│  │  ● Identité    ● AGGIR    ○ Social    ○ Santé    ○ Matériel    ○ Plan │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │   │
│  │                                                                       │   │
│  │  [Contenu de l'étape AGGIR]                                           │   │
│  │  • Les 17 variables sont présentées                                   │   │
│  │  • On peut replier/déplier les sections                               │   │
│  │  • Sauvegarde automatique au fur et à mesure                          │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │ [← Précédent]                    [Sauvegarder]    [Suivant →]   │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pourquoi un Wizard ?**
- L'infirmière est **sur le terrain**, souvent avec une tablette
- Elle suit un **protocole** (elle ne peut pas "sauter" l'AGGIR)
- Elle veut savoir **où elle en est** (étape 2/6)
- Elle peut **interrompre et reprendre** (sauvegarde automatique)

#### Temps 2 : Consultation/Modification (mode "Onglets")

Quand on **consulte** une évaluation existante ou qu'on veut **modifier une section** :
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODE ONGLETS (Consultation/Modification)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  URL: /patients/2910?tab=evaluation                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📋 Évaluation du 23/09/2025 - GIR 4                                 │   │
│  │                                                                       │   │
│  │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐      │   │
│  │  │ AGGIR   │ SOCIAL  │ SANTÉ   │MATÉRIEL │  PLAN   │HISTORIQUE│      │   │
│  │  └────┬────┴─────────┴─────────┴─────────┴─────────┴─────────┘      │   │
│  │       │                                                               │   │
│  │       ▼                                                               │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │  GIR : 4  |  Temps d'aide : 1h36/jour  |  Modifié le 19/05/2025 │ │   │
│  │  │                                                                  │ │   │
│  │  │  ▼ Transferts           B  (Spontanément: non, ...)             │ │   │
│  │  │  ▼ Déplacements int.    B                                        │ │   │
│  │  │  ▼ Toilette             B  (Haut: B, Bas: B)                     │ │   │
│  │  │  ▼ Élimination          B  (Urinaire: B, Fécale: B)              │ │   │
│  │  │  ...                                                             │ │   │
│  │  │                                                    [✏️ Modifier] │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Les 6 étapes du Wizard d'évaluation

| Étape | Nom | Contenu | Durée estimée |
|-------|-----|---------|---------------|
| 1 | **Identité** | État civil, adresse, contacts | 5 min |
| 2 | **AGGIR** | 17 variables de la grille officielle | 15-20 min |
| 3 | **Social** | Contexte, habitat, vie sociale, PEC | 10 min |
| 4 | **Santé** | 15 blocs santé + tests (le plus long) | 20-30 min |
| 5 | **Matériel** | Équipements existants / à prévoir | 5 min |
| 6 | **Plan** | Objectifs et actions (POA/PPA) | 10 min |

**Durée totale** : ~1h à 1h30 pour une évaluation complète

---

## 4️⃣ Focus sur la grille AGGIR (ta priorité)

Puisque tu veux commencer par l'évaluation AGGIR, voici une proposition de design plus détaillée :

### Structure de la grille AGGIR
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GRILLE AGGIR - 17 VARIABLES                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  VARIABLES DISCRIMINANTES (déterminent le GIR)                              │
│  ─────────────────────────────────────────────                              │
│  1. Cohérence       (Communication + Comportement)                          │
│  2. Orientation     (Temps + Espace)                                        │
│  3. Toilette        (Haut + Bas)                                            │
│  4. Habillage       (Haut + Moyen + Bas)                                    │
│  5. Alimentation    (Se servir + Manger)                                    │
│  6. Élimination     (Urinaire + Fécale)                                     │
│  7. Transferts                                                              │
│  8. Déplacements intérieurs                                                 │
│                                                                             │
│  VARIABLES ILLUSTRATIVES (contextualisent)                                  │
│  ─────────────────────────────────────────                                  │
│  9. Déplacements extérieurs                                                 │
│  10. Alerter                                                                │
│  11. Cuisine (préparer les repas)                                           │
│  12. Ménage                                                                 │
│  13. Transports                                                             │
│  14. Achats                                                                 │
│  15. Suivi du traitement                                                    │
│  16. Activités temps libre                                                  │
│  17. Gestion                                                                │
│                                                                             │
│  ADVERBES (S, T, C, H)                                                      │
│  ─────────────────────                                                      │
│  S = Spontanément (fait seul sans stimulation)                              │
│  T = Totalement (fait complètement)                                         │
│  C = Correctement (fait de manière adaptée)                                 │
│  H = Habituellement (fait régulièrement)                                    │
│                                                                             │
│  NOTATION                                                                   │
│  ────────                                                                   │
│  A = Fait seul, totalement, correctement, habituellement                    │
│  B = Fait partiellement, ou incorrectement, ou non habituellement           │
│  C = Ne fait pas                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Proposition de design UI pour l'AGGIR
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🧓 M. DELOIN ALAIN - Évaluation AGGIR                                      │
│  ═══════════════════════════════════════                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GIR CALCULÉ : 4     |    Temps d'aide estimé : 1h36/jour            │   │
│  │  (Se recalcule automatiquement à chaque modification)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ▼ COHÉRENCE (Communication + Comportement)                    [B] ────────│
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │  Communication                                         [B]    │ │   │
│  │  │  ┌─────┬─────┬─────┬─────┐                                    │ │   │
│  │  │  │  S  │  T  │  C  │  H  │                                    │ │   │
│  │  │  │ ○   │ ○   │ ●   │ ○   │  ← Boutons radio tactiles          │ │   │
│  │  │  │ Non │ Non │ Oui │ Non │                                    │ │   │
│  │  │  └─────┴─────┴─────┴─────┘                                    │ │   │
│  │  │  💬 Commentaire : _________________________________            │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │  Comportement                                          [B]    │ │   │
│  │  │  ┌─────┬─────┬─────┬─────┐                                    │ │   │
│  │  │  │  S  │  T  │  C  │  H  │                                    │ │   │
│  │  │  │ ○   │ ○   │ ●   │ ○   │                                    │ │   │
│  │  │  │ Non │ Non │ Oui │ Non │                                    │ │   │
│  │  │  └─────┴─────┴─────┴─────┘                                    │ │   │
│  │  │  💬 Commentaire : _________________________________            │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ▶ ORIENTATION (Temps + Espace)                                [A] ────────│
│                                                                             │
│  ▶ TOILETTE (Haut + Bas)                                       [B] ────────│
│                                                                             │
│  ...                                                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [← Retour]              [Sauvegarder]              [Suivant →]      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Caractéristiques clés pour tablette/mobile
| Aspect | Implémentation |
|--------|----------------|
| **Boutons tactiles** | Boutons radio larges (48px minimum) pour les adverbes S/T/C/H |
| **Accordéon** | Les variables se replient pour ne pas surcharger l'écran |
| **Calcul temps réel** | Le GIR se recalcule à chaque modification (algorithme officiel) |
| **Sauvegarde auto** | Chaque modification est sauvegardée (pas de perte si interruption) |
| **Indicateur progrès** | Barre de progression "5/17 variables complétées" |
| **Mode hors-ligne** | Possibilité de travailler sans connexion (sync au retour) |

# Intégration du calculateur AGGIR: Ou l'intégrer dans l'arborescence du projet ? Pourquoi ? Quel flux infirmière-calculateur ?
🔄 Flux d'interaction : Évaluateur ↔ Modèle de calcul
Analogie : La balance de précision
Imagine une balance de pharmacien avec des poids étalons :
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   L'infirmière pose les "poids" (réponses S, T, C, H) sur un plateau        │
│   La balance calcule automatiquement le résultat (GIR)                      │
│                                                                             │
│        👩‍⚕️ Infirmière                              ⚖️ Balance (algorithme)    │
│        ─────────────────                         ────────────────────────   │
│                                                                             │
│   1. Observe le patient faire                                               │
│      "Toilette haut"                                                        │
│                                                                             │
│   2. Répond aux 4 questions :                    3. Convertit en lettre :   │
│      S = Non (stimulation nécessaire)     ───►      → B (partiellement)     │
│      T = Oui (fait tout le haut)                                            │
│      C = Oui (fait correctement)                                            │
│      H = Oui (fait tous les jours)                                          │
│                                                                             │
│   4. Passe à la variable suivante...             5. Accumule les lettres    │
│                                                                             │
│   [...après toutes les variables...]                                        │
│                                                                             │
│                                                  6. Calcule le score :      │
│                                                     Groupe A → score 1240   │
│                                                     → pas de GIR, suivant   │
│                                                     Groupe B → score 856    │
│                                                     → pas de GIR, suivant   │
│                                                     ...                     │
│                                                     Groupe G → score 700    │
│                                                     → GIR 4 ✓               │
│                                                                             │
│   7. Voit le résultat :                                                     │
│      "GIR 4 - Temps d'aide estimé : 1h36/jour"                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Le flux de données détaillé
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUX DE DONNÉES AGGIR                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FRONTEND (Tablette infirmière)                 BACKEND (Serveur CareLink)  │
│  ───────────────────────────────                ─────────────────────────── │
│                                                                             │
│  ┌─────────────────────────┐                                                │
│  │ Interface de saisie     │                                                │
│  │ ┌─────┬─────┬─────┬────┐│                                                │
│  │ │  S  │  T  │  C  │  H ││                                                │
│  │ │ Non │ Oui │ Oui │ Oui││                                                │
│  │ └─────┴─────┴─────┴────┘│                                                │
│  └───────────┬─────────────┘                                                │
│              │                                                              │
│              │ À chaque modification...                                     │
│              ▼                                                              │
│  ┌─────────────────────────┐      POST /api/v1/patients/{id}/evaluations    │
│  │ Sauvegarde locale       │─────────────────────────────────────────────►  │
│  │ (brouillon)             │      { "aggir": { "variables": [...] } }       │
│  └─────────────────────────┘                    │                           │
│                                                 ▼                           │
│                                    ┌─────────────────────────┐              │
│                                    │ aggir_calculator.py     │              │
│                                    │                         │              │
│                                    │ 1. Parse les réponses   │              │
│                                    │ 2. Convertit en lettres │              │
│                                    │ 3. Combine sous-var.    │              │
│                                    │ 4. Calcule scores       │              │
│                                    │ 5. Détermine GIR        │              │
│                                    └───────────┬─────────────┘              │
│                                                │                            │
│              ◄─────────────────────────────────┘                            │
│              │  { "gir": 4, "details": {...} }                              │
│              ▼                                                              │
│  ┌─────────────────────────┐                                                │
│  │ Affichage temps réel    │                                                │
│  │                         │                                                │
│  │   GIR : 4               │                                                │
│  │   Temps : ~1h36/jour    │                                                │
│  └─────────────────────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

📍 Où placer le calculateur AGGIR ?
Recommandation : Backend uniquement
| Option | Avantages | Inconvénients | Recommandation |
|--------|-----------|---------------|----------------|
| **Frontend seul** | Calcul instantané, fonctionne hors-ligne | Risque de divergence si algorithme mis à jour, validation côté client = contournable | ❌ Non |
| **Backend seul** | Source unique de vérité, sécurisé, auditable | Nécessite connexion pour le calcul | ✅ **Oui** |
| **Les deux** | Meilleur des deux mondes | Duplication de code, risque de divergence | ⚠️ Possible mais complexe |

Pourquoi le backend ?

Source unique de vérité : L'algorithme officiel (décret 1997) ne doit exister qu'à un seul endroit
Auditabilité : En cas de contestation du GIR, on peut prouver le calcul
Mise à jour centralisée : Si l'algorithme change (rare mais possible), une seule mise à jour
Sécurité : Le GIR détermine l'APA (argent public), le calcul doit être inviolable

Structure dans le backend
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── patients/
    │           └── evaluations/
    │               ├── routes.py          # Endpoints API
    │               ├── schemas.py         # Pydantic schemas
    │               └── service.py         # Logique métier
    │
    ├── services/
    │   └── aggir/                         # ← Module AGGIR dédié
    │       ├── __init__.py
    │       ├── calculator.py              # ← Ton fichier aggir_calculator.py
    │       ├── parser.py                  # Convertit JSON → objets Adverbes
    │       └── time_estimator.py          # Calcul temps d'aide (optionnel)
    │
    └── models/
        └── patient/
            └── patient_evaluation.py      # Modèle SQLAlchemy
Le rôle du frontend
Le frontend ne calcule pas le GIR, il :

Affiche l'interface de saisie des adverbes
Envoie les données au backend à chaque sauvegarde
Affiche le GIR calculé retourné par le backend
Peut afficher un GIR "provisoire" pendant la saisie (optionnel)


⏱️ Évaluation sur plusieurs jours : Impact sur l'UI
C'est une information cruciale que tu me donnes. Cela change complètement la conception.
Analogie : Le carnet de notes de l'étudiant
Imagine un étudiant qui passe un examen sur plusieurs jours :
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   JOUR 1 (Lundi matin)                                                      │
│   ────────────────────                                                      │
│   L'infirmière commence l'évaluation chez M. Deloin                         │
│   Elle fait :                                                               │
│   ✓ Cohérence (Communication + Comportement)                                │
│   ✓ Orientation (Temps + Espace)                                            │
│   ✓ Toilette (Haut + Bas) ← observation pendant la toilette matinale        │
│   → M. Deloin est fatigué, on s'arrête là                                   │
│                                                                             │
│   L'infirmière clique sur [Sauvegarder et quitter]                          │
│   Statut : BROUILLON (3/17 variables)                                       │
│                                                                             │
│   ─────────────────────────────────────────────────────────────────────     │
│                                                                             │
│   JOUR 2 (Mercredi après-midi)                                              │
│   ────────────────────────────                                              │
│   L'infirmière revient, rouvre l'évaluation en cours                        │
│   Elle reprend là où elle s'était arrêtée :                                 │
│   ✓ Habillage (Haut + Moyen + Bas)                                          │
│   ✓ Alimentation (Se servir + Manger) ← observation pendant le déjeuner     │
│   ✓ Élimination                                                             │
│   → Encore quelques variables à faire                                       │
│                                                                             │
│   Statut : BROUILLON (6/17 variables)                                       │
│                                                                             │
│   ─────────────────────────────────────────────────────────────────────     │
│                                                                             │
│   JOUR 3 (Vendredi matin)                                                   │
│   ──────────────────────                                                    │
│   L'infirmière termine l'évaluation :                                       │
│   ✓ Transferts                                                              │
│   ✓ Déplacements intérieurs                                                 │
│   ✓ Déplacements extérieurs                                                 │
│   ✓ Alerter                                                                 │
│   ✓ Variables illustratives (Cuisine, Ménage, etc.)                         │
│                                                                             │
│   L'infirmière clique sur [Valider l'évaluation]                            │
│   Le GIR est calculé : GIR 4                                                │
│   Statut : VALIDÉE                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Conséquences sur la conception UI
| Aspect | Sans multi-jours | Avec multi-jours ✅ |
|--------|------------------|---------------------|
| **Sauvegarde** | À la fin | Continue (à chaque variable) |
| **Statut** | Draft → Validé | Draft (partiel) → Draft (complet) → Validé |
| **Reprise** | Non nécessaire | **Essentielle** (reprendre là où on s'est arrêté) |
| **Indicateur** | Simple progression | Progression + "dernière modif il y a 2 jours" |
| **Calcul GIR** | À la fin | Provisoire pendant, définitif à la validation |
| **Historique** | Simple | Qui a saisi quoi et quand |

Nouvelle proposition de flux UI
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ÉVALUATION AGGIR - MODE MULTI-SESSIONS                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🧓 M. DELOIN ALAIN - Évaluation en cours                                   │
│  ═══════════════════════════════════════════                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📊 Progression : 6 / 17 variables                                   │   │
│  │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%  │   │
│  │                                                                       │   │
│  │  🕐 Dernière modification : Mercredi 15h42 par Marie Dupont (IDE)     │   │
│  │  📋 Commencée le : Lundi 9h30                                         │   │
│  │                                                                       │   │
│  │  ⚠️ GIR provisoire : ~4 (basé sur les variables saisies)              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  VARIABLES DISCRIMINANTES                                             │   │
│  │  ─────────────────────────                                           │   │
│  │  ✅ Cohérence         B    (saisie Lun. 9h45 par M. Dupont)          │   │
│  │  ✅ Orientation       A    (saisie Lun. 10h02 par M. Dupont)         │   │
│  │  ✅ Toilette          B    (saisie Lun. 10h30 par M. Dupont)         │   │
│  │  ✅ Habillage         B    (saisie Mer. 14h15 par M. Dupont)         │   │
│  │  ✅ Alimentation      B    (saisie Mer. 15h00 par M. Dupont)         │   │
│  │  ✅ Élimination       B    (saisie Mer. 15h42 par M. Dupont)         │   │
│  │  ⏳ Transferts        -    [Saisir]  ← Reprendre ici                  │   │
│  │  ⬜ Dépl. intérieurs  -                                               │   │
│  │                                                                       │   │
│  │  VARIABLES ILLUSTRATIVES                                              │   │
│  │  ───────────────────────                                              │   │
│  │  ⬜ Dépl. extérieurs  -                                               │   │
│  │  ⬜ Alerter           -                                               │   │
│  │  ⬜ Cuisine           -                                               │   │
│  │  ⬜ Ménage            -                                               │   │
│  │  ...                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [Reprendre la saisie]     [Exporter brouillon PDF]     [Annuler]    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘



# Stockage des données d'évaluation multi-sessions
## Analogie : Le carnet de chantier
Imagine un carnet de chantier sur un chantier de construction :
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   📓 CARNET DE CHANTIER - Rénovation Maison Deloin                          │
│   ══════════════════════════════════════════════                            │
│                                                                             │
│   Une FICHE PRINCIPALE (l'évaluation)                                       │
│   qui référence plusieurs VISITES (les sessions de saisie)                  │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ÉVALUATION #eval_2910_20250923                                      │  │
│   │  Patient: M. DELOIN ALAIN                                            │  │
│   │  Statut: EN_COURS                                                    │  │
│   │  Créée le: 23/09/2025 09:30                                          │  │
│   │  Expire le: 30/09/2025 09:30 (J+7)                                   │  │
│   │  Progression: 6/17 variables (35%)                                   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│          │                                                                  │
│          │ contient plusieurs sessions                                      │
│          ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  SESSION #1 - Lundi 23/09 matin                                      │  │
│   │  Par: Marie Dupont (IDE)                                             │  │
│   │  Variables saisies: Cohérence, Orientation, Toilette                 │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  SESSION #2 - Mercredi 25/09 après-midi                              │  │
│   │  Par: Marie Dupont (IDE)                                             │  │
│   │  Variables saisies: Habillage, Alimentation, Élimination             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  SESSION #3 - À venir...                                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Architecture de données proposée
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODÈLE DE DONNÉES - ÉVALUATIONS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │  patient_evaluations    │       │  evaluation_sessions    │             │
│  │  (table principale)     │       │  (sessions de saisie)   │             │
│  ├─────────────────────────┤       ├─────────────────────────┤             │
│  │  id (PK)                │       │  id (PK)                │             │
│  │  patient_id (FK)        │       │  evaluation_id (FK) ────┼──┐          │
│  │  tenant_id (FK)         │       │  user_id (FK)           │  │          │
│  │  type (AGGIR, SOCIAL...)|       │  started_at             │  │          │
│  │  status (enum)          │       │  ended_at               │  │          │
│  │  created_at             │       │  device_info            │  │          │
│  │  created_by_user_id     │       │  sync_status            │  │          │
│  │  expires_at             │◄──────┼─────────────────────────┘  │          │
│  │  validated_at           │       └─────────────────────────┘  │          │
│  │  validated_by_user_id   │                                    │          │
│  │  medical_validator_id   │       ┌─────────────────────────┐  │          │
│  │  completion_percent     │       │  aggir_variables        │  │          │
│  │  aggir_gir (null si     │       │  (détail des variables) │  │          │
│  │       non validé)       │       ├─────────────────────────┤  │          │
│  │  version                │       │  id (PK)                │  │          │
│  └─────────────────────────┘       │  evaluation_id (FK) ────┼──┘          │
│                                    │  session_id (FK)        │             │
│                                    │  variable_code          │             │
│                                    │  sub_variable_code      │             │
│                                    │  adverb_s (bool)        │             │
│                                    │  adverb_t (bool)        │             │
│                                    │  adverb_c (bool)        │             │
│                                    │  adverb_h (bool)        │             │
│                                    │  result_letter (A/B/C)  │             │
│                                    │  comment                │             │
│                                    │  recorded_at            │             │
│                                    │  recorded_by_user_id    │             │
│                                    └─────────────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Enum pour les statuts
pythonclass EvaluationStatus(str, Enum):
    """Statuts d'une évaluation"""
    DRAFT = "draft"                    # En cours de saisie
    PENDING_COMPLETION = "pending"     # Saisie complète, en attente validation
    PENDING_VALIDATION = "validation"  # Soumise au médecin coordonnateur
    PENDING_DEPARTMENT = "department"  # En attente validation Conseil Départemental
    VALIDATED = "validated"            # Validée (GIR officiel)
    EXPIRED = "expired"                # Expirée (délai dépassé)
    CANCELLED = "cancelled"            # Annulée manuellement
Jointure entre les sessions
La jointure se fait naturellement via l'evaluation_id :
sql-- Récupérer toutes les variables saisies pour une évaluation
SELECT 
    e.id as evaluation_id,
    e.status,
    e.completion_percent,
    s.id as session_id,
    s.started_at as session_date,
    u.full_name as recorded_by,
    v.variable_code,
    v.result_letter,
    v.recorded_at
FROM patient_evaluations e
JOIN evaluation_sessions s ON s.evaluation_id = e.id
JOIN aggir_variables v ON v.evaluation_id = e.id AND v.session_id = s.id
JOIN users u ON u.id = v.recorded_by_user_id
WHERE e.id = 'eval_2910_20250923'
ORDER BY v.recorded_at;

2️⃣ Fichier JSON enrichi pour multi-sessions
Voici comment adapter le fichier DELOIN_ALAIN_23_09_2025.json :
json{
  "evaluation": {
    "id": "eval_2910_20250923",
    "patient_id": 2910,
    "tenant_id": "tenant_ssiad_94",
    "type": "FULL_ASSESSMENT",
    "status": "DRAFT",
    "completion_percent": 35,
    
    "created_at": "2025-09-23T09:30:00Z",
    "created_by": {
      "user_id": 42,
      "name": "Marie Dupont",
      "role": "IDE"
    },
    "expires_at": "2025-09-30T09:30:00Z",
    
    "validated_at": null,
    "validated_by": null,
    "medical_validator": null,
    "department_validator": null,
    
    "version": 3
  },
  
  "sessions": [
    {
      "id": "session_001",
      "started_at": "2025-09-23T09:30:00Z",
      "ended_at": "2025-09-23T11:15:00Z",
      "user": {
        "user_id": 42,
        "name": "Marie Dupont",
        "role": "IDE"
      },
      "device_info": "iPad Pro - Safari",
      "sync_status": "SYNCED",
      "variables_recorded": ["COHERENCE", "ORIENTATION", "TOILETTE"]
    },
    {
      "id": "session_002",
      "started_at": "2025-09-25T14:00:00Z",
      "ended_at": "2025-09-25T15:45:00Z",
      "user": {
        "user_id": 42,
        "name": "Marie Dupont",
        "role": "IDE"
      },
      "device_info": "iPad Pro - Safari",
      "sync_status": "SYNCED",
      "variables_recorded": ["HABILLAGE", "ALIMENTATION", "ELIMINATION"]
    }
  ],


# Mode hors-ligne : Stratégie de synchronisation

## Analogie : Le bloc-notes de terrain

┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRATÉGIE HORS-LIGNE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   📱 TABLETTE (Frontend)                    ☁️ SERVEUR (Backend)             │
│   ─────────────────────                     ────────────────────             │
│                                                                             │
│   ┌─────────────────────┐                                                   │
│   │  IndexedDB local    │     Connexion OK                                  │
│   │  (cache navigateur) │ ◄─────────────────► PostgreSQL                    │
│   └─────────────────────┘     Sync bidirec.                                 │
│                                                                             │
│   SCÉNARIO : L'infirmière perd la connexion                                 │
│   ─────────────────────────────────────────                                 │
│                                                                             │
│   1. Avant la visite :                                                      │
│      [Télécharger le dossier patient en local]                              │
│      → Le JSON complet est stocké dans IndexedDB                            │
│                                                                             │
│   2. Pendant la visite (hors-ligne) :                                       │
│      → Saisie normale dans l'interface                                      │
│      → Chaque modification → sauvegarde locale                              │
│      → Indicateur : 🔴 "Mode hors-ligne"                                    │
│                                                                             │
│   3. Retour de la connexion :                                               │
│      → Détection automatique du réseau                                      │
│      → Synchronisation des modifications                                    │
│      → Gestion des conflits (si autre utilisateur a modifié)                │
│      → Indicateur : 🟢 "Synchronisé"                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Structure pour la sync hors-ligne
```
json{
  "local_changes": [
    {
      "change_id": "local_001",
      "timestamp": "2025-09-25T14:32:00Z",
      "entity": "aggir_variable",
      "evaluation_id": "eval_2910_20250923",
      "variable_code": "HABILLAGE_HAUT",
      "action": "UPDATE",
      "data": {
        "adverb_s": false,
        "adverb_t": true,
        "adverb_c": true,
        "adverb_h": true
      },
      "sync_status": "PENDING"
    }
  ],
  "last_sync_at": "2025-09-25T14:00:00Z",
  "server_version": 2
}
```

---

# Structure des pages proposée

Voici une structure qui fonctionne **qu'on choisisse 1 ou 2 applications** :

## Vue d'ensemble de la navigation

┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARBORESCENCE DES PAGES - ÉVALUATIONS                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  /patients                                                                  │
│  └── /patients/{id}                      # Dossier patient                  │
│      │                                                                      │
│      ├── ?tab=overview                   # Synthèse                         │
│      │                                                                      │
│      ├── ?tab=evaluations                # Liste des évaluations            │
│      │   │                                                                  │
│      │   │   ┌─────────────────────────────────────────────────────────┐   │
│      │   │   │  Évaluations de M. DELOIN                               │   │
│      │   │   │                                                          │   │
│      │   │   │  🟡 En cours - 35% - Expire dans 5 jours    [Reprendre] │   │
│      │   │   │     Commencée le 23/09 par M. Dupont                     │   │
│      │   │   │                                                          │   │
│      │   │   │  ✅ Validée - GIR 4 - 15/06/2025            [Voir]      │   │
│      │   │   │     Validée par Dr Martin + CD94                         │   │
│      │   │   │                                                          │   │
│      │   │   │  ✅ Validée - GIR 5 - 12/01/2025            [Voir]      │   │
│      │   │   │                                                          │   │
│      │   │   │                              [+ Nouvelle évaluation]     │   │
│      │   │   └─────────────────────────────────────────────────────────┘   │
│      │   │                                                                  │
│      │   └── /patients/{id}/evaluations/{eval_id}                          │
│      │       │                                                              │
│      │       ├── ?section=aggir          # Section AGGIR                   │
│      │       ├── ?section=social         # Section Social                  │
│      │       ├── ?section=sante          # Section Santé                   │
│      │       ├── ?section=materiel       # Section Matériel                │
│      │       └── ?section=plan           # Section Plan d'aide             │
│      │                                                                      │
│      ├── ?tab=vitals                     # Constantes vitales              │
│      ├── ?tab=coordination               # Carnet de liaison               │
│      └── ?tab=documents                  # Documents                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


### Page principale : Liste des évaluations

┌─────────────────────────────────────────────────────────────────────────────┐
│  🧓 M. DELOIN ALAIN                                           [← Retour]   │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  ┌─────────┬─────────────┬───────────┬─────────────┬──────────┬─────────┐  │
│  │ Synthèse│ ÉVALUATIONS │ Constantes│ Coordination│ Documents│  Accès  │  │
│  └─────────┴──────┬──────┴───────────┴─────────────┴──────────┴─────────┘  │
│                   │                                                         │
│                   ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ⚠️ ÉVALUATION EN COURS                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  📋 Évaluation #2025-09-23                                   │   │   │
│  │  │  Statut: EN COURS (35%)                                      │   │   │
│  │  │  ████████████░░░░░░░░░░░░░░░░░░░░░░░  6/17 variables          │   │   │
│  │  │                                                               │   │   │
│  │  │  🕐 Dernière activité: Mer. 25/09 à 15h42                     │   │   │
│  │  │  👤 Par: Marie Dupont (IDE)                                   │   │   │
│  │  │  ⏰ Expire dans: 5 jours                                      │   │   │
│  │  │                                                               │   │   │
│  │  │  [▶️ Reprendre l'évaluation]           [🗑️ Annuler]           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  HISTORIQUE DES ÉVALUATIONS VALIDÉES                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Date        │ GIR │ Validé par           │ Actions         │   │   │
│  │  │──────────────│─────│──────────────────────│─────────────────│   │   │
│  │  │  15/06/2025  │  4  │ Dr Martin + CD94     │ [Voir] [PDF]    │   │   │
│  │  │  12/01/2025  │  5  │ Dr Martin + CD94     │ [Voir] [PDF]    │   │   │
│  │  │  03/09/2024  │  5  │ Dr Leblanc + CD94    │ [Voir] [PDF]    │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  [+ Nouvelle évaluation]                                           │   │
│  │  (Désactivé si une évaluation est déjà en cours)                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


### Page de saisie : Évaluation en cours

┌─────────────────────────────────────────────────────────────────────────────┐
│  🧓 M. DELOIN ALAIN - Évaluation en cours                                   │
│  ═══════════════════════════════════════                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Progression: 6/17 variables   ⏰ Expire dans 5 jours                │   │
│  │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%   │   │
│  │                                                    🟢 Connecté       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────┬────────┬────────┬──────────┬────────┐                          │
│  │ AGGIR  │ Social │ Santé  │ Matériel │  Plan  │  ← Navigation sections    │
│  │  6/17  │  0/4   │  0/15  │   0/1    │  0/1   │                          │
│  └───┬────┴────────┴────────┴──────────┴────────┘                          │
│      │                                                                      │
│      ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  VARIABLES DISCRIMINANTES                              6/8 ✓        │   │
│  │  ────────────────────────────────────────────────────────────────   │   │
│  │                                                                     │   │
│  │  ✅ Cohérence           B    Lun. 23/09 09:45 - M. Dupont  [✏️]    │   │
│  │  ✅ Orientation         A    Lun. 23/09 10:02 - M. Dupont  [✏️]    │   │
│  │  ✅ Toilette            B    Lun. 23/09 10:30 - M. Dupont  [✏️]    │   │
│  │  ✅ Habillage           B    Mer. 25/09 14:15 - M. Dupont  [✏️]    │   │
│  │  ✅ Alimentation        B    Mer. 25/09 15:00 - M. Dupont  [✏️]    │   │
│  │  ✅ Élimination         B    Mer. 25/09 15:42 - M. Dupont  [✏️]    │   │
│  │  ⏳ Transferts          —    [Saisir maintenant]  ← Point de reprise │   │
│  │  ⬜ Dépl. intérieurs    —                                           │   │
│  │                                                                     │   │
│  │  VARIABLES ILLUSTRATIVES                               0/9          │   │
│  │  ────────────────────────────────────────────────────────────────   │   │
│  │  ⬜ Dépl. extérieurs    —                                           │   │
│  │  ⬜ Alerter             —                                           │   │
│  │  ⬜ Cuisine             —                                           │   │
│  │  ⬜ Ménage              —                                           │   │
│  │  ⬜ Transports          —                                           │   │
│  │  ⬜ Achats              —                                           │   │
│  │  ⬜ Suivi traitement    —                                           │   │
│  │  ⬜ Activités temps libre —                                         │   │
│  │  ⬜ Gestion             —                                           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [Sauvegarder et quitter]           [Continuer la saisie →]         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


### Page de saisie d'une variable (Modal ou page dédiée)

┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Retour                                                    🟢 Connecté   │
│                                                                             │
│  TRANSFERTS                                                                 │
│  ══════════                                                                 │
│                                                                             │
│  📖 Définition officielle:                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  "Transferts : se lever, se coucher, s'asseoir, passer de l'une     │   │
│  │   de ces trois positions à une autre, dans les deux sens."          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  La personne effectue-t-elle les transferts...                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  S - SPONTANÉMENT ?                                                 │   │
│  │  (Sans qu'on ait besoin de la stimuler ou de lui rappeler)          │   │
│  │                                                                     │   │
│  │  ┌─────────────────────┐   ┌─────────────────────┐                 │   │
│  │  │                     │   │ ████████████████████│                 │   │
│  │  │        OUI          │   │        NON         │                 │   │
│  │  │                     │   │    (sélectionné)   │                 │   │
│  │  └─────────────────────┘   └─────────────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  T - TOTALEMENT ?                                                   │   │
│  │  (Entièrement, du début à la fin)                                   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────┐   ┌─────────────────────┐                 │   │
│  │  │ ████████████████████│   │                     │                 │   │
│  │  │        OUI          │   │        NON          │                 │   │
│  │  │    (sélectionné)    │   │                     │                 │   │
│  │  └─────────────────────┘   └─────────────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  C - CORRECTEMENT ?                                                 │   │
│  │  (De façon adaptée, sans danger)                                    │   │
│  │                                                                     │   │
│  │  ┌─────────────────────┐   ┌─────────────────────┐                 │   │
│  │  │ ████████████████████│   │                     │                 │   │
│  │  │        OUI          │   │        NON          │                 │   │
│  │  │    (sélectionné)    │   │                     │                 │   │
│  │  └─────────────────────┘   └─────────────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  H - HABITUELLEMENT ?                                               │   │
│  │  (De façon régulière, pas seulement certains jours)                 │   │
│  │                                                                     │   │
│  │  ┌─────────────────────┐   ┌─────────────────────┐                 │   │
│  │  │ ████████████████████│   │                     │                 │   │
│  │  │        OUI          │   │        NON          │                 │   │
│  │  │    (sélectionné)    │   │                     │                 │   │
│  │  └─────────────────────┘   └─────────────────────┘                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Résultat calculé: B (fait partiellement)                                   │
│                                                                             │
│  💬 Commentaire (optionnel):                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Nécessite une stimulation verbale pour initier le mouvement        │   │
│  │  _                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [← Variable précédente]    [Enregistrer]    [Variable suivante →]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


---

## 5️⃣ Workflow de validation

┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW DE VALIDATION AGGIR                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DRAFT                PENDING              VALIDATION           VALIDATED  │
│   (En cours)           (Complet)            (Méd. coord.)        (Final)    │
│                                                                             │
│   ┌─────────┐         ┌─────────┐          ┌─────────┐         ┌─────────┐ │
│   │         │         │         │          │         │         │         │ │
│   │  IDE    │────────►│  IDE    │─────────►│ Médecin │────────►│   CD    │ │
│   │  saisit │  17/17  │ soumet  │  Valide  │ coord.  │ Valide  │  valide │ │
│   │         │         │         │          │         │         │         │ │
│   └─────────┘         └─────────┘          └─────────┘         └─────────┘ │
│       │                    │                    │                    │      │
│       │                    │                    │                    │      │
│       ▼                    ▼                    ▼                    ▼      │
│   Peut modifier       Peut corriger        Peut renvoyer       GIR OFFICIEL│
│   Peut annuler        avant soumission     pour correction     Immuable    │
│   Expire J+7                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

# Précision JSON Schema, contenieur json
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   📋 JSON SCHEMA                          📝 DOCUMENT JSON                      │
│   ════════════════                        ════════════════                      │
│                                                                                 │
│   C'est le FORMULAIRE VIDE               C'est le FORMULAIRE REMPLI            │
│   avec les cases définies                 avec les données saisies              │
│                                                                                 │
│   ┌─────────────────────────┐            ┌─────────────────────────┐           │
│   │ Nom: [______] (requis)  │            │ Nom: [Dupont]           │           │
│   │ Prénom: [______]        │            │ Prénom: [Marie]         │           │
│   │ Date: [JJ/MM/AAAA]      │     →      │ Date: [15/03/1942]      │           │
│   │ GIR: [1-6] (requis)     │   remplit  │ GIR: [4]                │           │
│   │ Variables: [liste]      │            │ Variables: [...]        │           │
│   └─────────────────────────┘            └─────────────────────────┘           │
│                                                                                 │
│   NE CHANGE JAMAIS                       SE REMPLIT PROGRESSIVEMENT            │
│   (c'est la spécification)               (c'est l'instance)                    │
│                                                                                 │
│   Fichier: evaluation_v1.json            Stocké dans: evaluation_data (JSONB)  │
│   Rôle: VALIDER                          Rôle: STOCKER les données             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

## Workflow envisagé
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📱 UI (Tablette) - DÈS LE DÉBUT                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. Au démarrage de l'app, on charge le JSON SCHEMA (la spécification)         │
│     ┌──────────────────────────────────────────────────────────────────────┐   │
│     │ // Chargement du schema (une seule fois)                             │   │
│     │ const evaluationSchema = await fetch('/schemas/evaluation_v1.json'); │   │
│     └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  2. On crée un OBJET VIDE qui va recevoir les données (le conteneur)           │
│     ┌──────────────────────────────────────────────────────────────────────┐   │
│     │ // C'est ÇA le conteneur, pas le schema !                            │   │
│     │ const evaluationData = {                                             │   │
│     │   usager: {},                                                        │   │
│     │   contacts: [],                                                      │   │
│     │   aggir: { GIR: null, AggirVariable: [] },                           │   │
│     │   social: {},                                                        │   │
│     │   sante: {}                                                          │   │
│     │ };                                                                   │   │
│     └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  3. L'infirmière saisit → les données remplissent l'objet                      │
│     ┌──────────────────────────────────────────────────────────────────────┐   │
│     │ // Saisie de l'identité                                              │   │
│     │ evaluationData.usager = {                                            │   │
│     │   "Informations d'état civil": {                                     │   │
│     │     clientId: "PAT-2026-001",                                        │   │
│     │     personnePhysique: {                                              │   │
│     │       nomFamille: "Dupont",                                          │   │
│     │       premierPrenomActeNaissance: "Marie",                           │   │
│     │       sexe: "F",                                                     │   │
│     │       dateNaissance: "1942-03-15"                                    │   │
│     │     }                                                                │   │
│     │   },                                                                 │   │
│     │   adresse: { ligne: "12 rue des Lilas", codePostal: "75020", ... }   │   │
│     │ };                                                                   │   │
│     └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  4. À chaque saisie, on VALIDE l'objet CONTRE le schema                        │
│     ┌──────────────────────────────────────────────────────────────────────┐   │
│     │ // Validation en temps réel                                          │   │
│     │ import Ajv from 'ajv';                                               │   │
│     │ const ajv = new Ajv({ allErrors: true });                            │   │
│     │ const validate = ajv.compile(evaluationSchema);                      │   │
│     │                                                                      │   │
│     │ // À chaque modification :                                           │   │
│     │ const isValid = validate(evaluationData);                            │   │
│     │ if (!isValid) {                                                      │   │
│     │   console.log(validate.errors); // Afficher les erreurs              │   │
│     │ }                                                                    │   │
│     └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  5. On envoie l'OBJET (pas le schema) au serveur                               │
│     ┌──────────────────────────────────────────────────────────────────────┐   │
│     │ // POST pour créer ou PATCH pour mettre à jour                       │   │
│     │ await fetch('/api/v1/patients/123/evaluations', {                    │   │
│     │   method: 'POST',                                                    │   │
│     │   body: JSON.stringify({                                             │   │
│     │     schema_type: "evaluation_complete",                              │   │
│     │     schema_version: "v1",                                            │   │
│     │     evaluation_date: "2026-01-23",                                   │   │
│     │     evaluation_data: evaluationData  // ← L'OBJET REMPLI             │   │
│     │   })                                                                 │   │
│     │ });                                                                  │   │
│     └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

## Schéma visuel complet
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  📋 evaluation_v1.json                                                          │
│  (JSON SCHEMA - la spécification)                                               │
│  ┌─────────────────────────────────┐                                           │
│  │ {                               │                                           │
│  │   "$schema": "...",             │      NE BOUGE PAS                         │
│  │   "required": ["usager","aggir"]│      Sert de RÉFÉRENCE                    │
│  │   "properties": {               │      pour valider                         │
│  │     "usager": {...},            │                                           │
│  │     "aggir": {...}              │                                           │
│  │   }                             │                                           │
│  │ }                               │                                           │
│  └───────────────┬─────────────────┘                                           │
│                  │                                                              │
│                  │ valide ↓                                                     │
│                  ▼                                                              │
│  📝 evaluationData                                                              │
│  (DOCUMENT JSON - les données)                                                  │
│  ┌─────────────────────────────────┐                                           │
│  │ {                               │      SE REMPLIT                           │
│  │   "usager": {                   │      progressivement                      │
│  │     "Informations d'état civil":│      par l'infirmière                     │
│  │       { "nomFamille": "Dupont"} │                                           │
│  │   },                            │                                           │
│  │   "aggir": {                    │                                           │
│  │     "GIR": 4,                   │                                           │
│  │     "AggirVariable": [...]      │                                           │
│  │   }                             │                                           │
│  │ }                               │                                           │
│  └───────────────┬─────────────────┘                                           │
│                  │                                                              │
│                  │ HTTP POST/PATCH                                              │
│                  ▼                                                              │
│  🖥️ Serveur FastAPI                                                            │
│  ┌─────────────────────────────────┐                                           │
│  │ PatientEvaluationCreate         │                                           │
│  │ {                               │                                           │
│  │   schema_type: "evaluation_     │                                           │
│  │                 complete",      │                                           │
│  │   schema_version: "v1",         │  ← Indique QUEL schema utiliser           │
│  │   evaluation_data: {...}        │  ← Le DOCUMENT JSON                       │
│  │ }                               │                                           │
│  └───────────────┬─────────────────┘                                           │
│                  │                                                              │
│                  │ Validation + Persistance                                     │
│                  ▼                                                              │
│  🗄️ PostgreSQL                                                                 │
│  ┌─────────────────────────────────┐                                           │
│  │ patient_evaluations             │                                           │
│  │ ┌─────────────────────────────┐ │                                           │
│  │ │ id: 42                      │ │                                           │
│  │ │ schema_type: "evaluation_   │ │                                           │
│  │ │              complete"      │ │                                           │
│  │ │ schema_version: "v1"        │ │                                           │
│  │ │ evaluation_data: {          │ │  ← Colonne JSONB                          │
│  │ │   "usager": {...},          │ │    contient le DOCUMENT                   │
│  │ │   "aggir": {...}            │ │                                           │
│  │ │ }                           │ │                                           │
│  │ └─────────────────────────────┘ │                                           │
│  └─────────────────────────────────┘                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

## Le rôle du schema_validator.py
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  JSON SCHEMA vérifie 2 choses :                                                 │
│                                                                                 │
│  1️⃣  PRÉSENCE des données obligatoires                                         │
│      → "required": ["usager", "aggir"]                                         │
│      → Si "usager" manque → ERREUR                                             │
│                                                                                 │
│  2️⃣  FORMAT des données                                                        │
│      → "dateNaissance": { "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}" }           │
│      → Si "15/03/1942" au lieu de "1942-03-15" → ERREUR                        │
│                                                                                 │
│      → "sexe": { "enum": ["M", "F"] }                                          │
│      → Si "Masculin" au lieu de "M" → ERREUR                                   │
│                                                                                 │
│      → "GIR": { "minimum": 1, "maximum": 6 }                                   │
│      → Si GIR = 7 → ERREUR                                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

### QUAND l'erreur bloque-t-elle ?
L'implémentation prévoit deux modes de validation selon le moment :
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  MODE 1 : VALIDATION PARTIELLE (pendant la saisie)                             │
│  ══════════════════════════════════════════════════                            │
│                                                                                 │
│  Quand ? → POST /evaluations (création)                                        │
│          → PATCH /evaluations (mise à jour)                                    │
│          → POST /sync (synchronisation hors-ligne)                             │
│                                                                                 │
│  Comportement :                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  Données incomplètes ?     → ✅ ACCEPTÉ (c'est un brouillon)            │   │
│  │  Champ "usager" manquant ? → ✅ ACCEPTÉ (elle n'a pas encore saisi)     │   │
│  │  GIR non renseigné ?       → ✅ ACCEPTÉ (sera calculé plus tard)        │   │
│  │                                                                          │   │
│  │  MAIS :                                                                  │   │
│  │  Format date invalide ?    → ❌ ERREUR (le format doit être bon)        │   │
│  │  GIR = 7 ?                 → ❌ ERREUR (valeur impossible)              │   │
│  │  Sexe = "Masculin" ?       → ❌ ERREUR (doit être "M" ou "F")           │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  → On tolère l'ABSENCE mais pas le MAUVAIS FORMAT                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  MODE 2 : VALIDATION COMPLÈTE (à la soumission)                                │
│  ══════════════════════════════════════════════                                │
│                                                                                 │
│  Quand ? → POST /evaluations/{id}/submit (soumission pour validation)          │
│                                                                                 │
│  Comportement :                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  TOUT doit être conforme, sinon → ❌ ERREUR BLOQUANTE                   │   │
│  │                                                                          │   │
│  │  Champ "usager" manquant ?       → ❌ ERREUR                            │   │
│  │  GIR non renseigné ?             → ❌ ERREUR                            │   │
│  │  17 variables AGGIR incomplètes? → ❌ ERREUR                            │   │
│  │  Format date invalide ?          → ❌ ERREUR                            │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  → Ici on exige la CONFORMITÉ TOTALE au JSON Schema                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

# Exemple concret du workflow
┌─────────────────────────────────────────────────────────────────────────────────┐
│  JOUR 1 - L'infirmière commence la saisie                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Elle saisit :                                                                  │
│  {                                                                              │
│    "usager": {                                                                  │
│      "Informations d'état civil": {                                            │
│        "personnePhysique": {                                                   │
│          "nomFamille": "Dupont",                                               │
│          "dateNaissance": "1942-03-15",  ← Format OK ✅                        │
│          "sexe": "F"                      ← Enum OK ✅                          │
│        }                                                                        │
│      }                                                                          │
│    }                                                                            │
│    // Pas encore de "aggir" !                                                   │
│  }                                                                              │
│                                                                                 │
│  → PATCH /evaluations/42                                                        │
│  → Validation PARTIELLE                                                         │
│  → Résultat : ✅ ACCEPTÉ (aggir manquant mais c'est un brouillon)              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  JOUR 1 - Elle fait une erreur de format                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Elle saisit :                                                                  │
│  {                                                                              │
│    "usager": {                                                                  │
│      "Informations d'état civil": {                                            │
│        "personnePhysique": {                                                   │
│          "dateNaissance": "15/03/1942",  ← Format INVALIDE ❌                  │
│        }                                                                        │
│      }                                                                          │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  → PATCH /evaluations/42                                                        │
│  → Validation PARTIELLE                                                         │
│  → Résultat : ❌ ERREUR 400                                                     │
│    {                                                                            │
│      "detail": "Format invalide",                                              │
│      "errors": [{                                                              │
│        "path": "usager.Informations d'état civil.personnePhysique.dateNaissance",
│        "message": "'15/03/1942' does not match pattern '^[0-9]{4}-[0-9]{2}-[0-9]{2}'"
│      }]                                                                         │
│    }                                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  JOUR 2 - Elle termine et veut soumettre                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Données actuelles :                                                            │
│  {                                                                              │
│    "usager": { ... complet ... },                                              │
│    "aggir": {                                                                   │
│      "GIR": null,                         ← Pas encore calculé                 │
│      "AggirVariable": [ ... 15 sur 17 ... ] ← Incomplet !                      │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  → POST /evaluations/42/submit                                                  │
│  → Validation COMPLÈTE                                                          │
│  → Résultat : ❌ ERREUR 400                                                     │
│    {                                                                            │
│      "detail": "L'évaluation est incomplète",                                  │
│      "errors": [                                                               │
│        {"path": "aggir.GIR", "message": "'GIR' is a required property"},       │
│        {"path": "aggir.AggirVariable", "message": "Array has 15 items, minimum is 17"}
│      ]                                                                          │
│    }                                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  JOUR 2 - Elle complète tout et re-soumet                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Données complètes :                                                            │
│  {                                                                              │
│    "usager": { ... complet ... },                                              │
│    "aggir": {                                                                   │
│      "GIR": 4,                            ← Calculé ✅                          │
│      "AggirVariable": [ ... 17 sur 17 ... ] ← Complet ✅                       │
│    }                                                                            │
│  }                                                                              │
│                                                                                 │
│  → POST /evaluations/42/submit                                                  │
│  → Validation COMPLÈTE                                                          │
│  → Résultat : ✅ SUCCÈS                                                         │
│  → Statut passe à "PENDING_MEDICAL"                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

## 📊 Résumé en une phrase

| Moment            | Ce qu'on vérifie                                                | Si erreur  |
|-------------------|-----------------------------------------------------------------|------------|
| Pendant la saisie | Que les données FOURNIES sont au bon FORMAT                     | Erreur 400 |
| À la soumission   | Que TOUTES les données requises sont présentes ET au bon format | Erreur 400 |

