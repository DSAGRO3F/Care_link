# CareLink - Cahier des Charges Backend

**Version :** 4.4 (Validation JSON Schema des Évaluations)  
**Date :** Janvier 2026  
**Auteur :** Olivier de Gouveia  
**Statut :** En développement actif

---

## 📋 Sommaire

1. [Introduction et Contexte](#1-introduction-et-contexte)
   - [1.1 Vision du projet](#11-vision-du-projet)
   - [1.2 Problématique adressée](#12-problématique-adressée)
   - [1.3 Cibles utilisateurs](#13-cibles-utilisateurs)
   - [1.4 Fonctionnalités principales](#14-fonctionnalités-principales)
2. [Stack Technique](#2-stack-technique)
   - [2.1 Technologies backend](#21-technologies-backend)
   - [2.2 Base de données](#22-base-de-données)
   - [2.3 Sécurité et chiffrement](#23-sécurité-et-chiffrement)
   - [2.4 Validation JSON Schema des évaluations](#24-validation-json-schema-des-évaluations)
3. [Architecture Multi-Tenant](#3-architecture-multi-tenant)
   - [3.1 Décisions architecturales](#31-décisions-architecturales)
   - [3.2 Stratégie d'isolation des données](#32-stratégie-disolation-des-données)
   - [3.3 Row-Level Security (RLS)](#33-row-level-security-rls)
   - [3.4 Accès cross-tenant](#34-accès-cross-tenant)
4. [Modèles de Données](#4-modèles-de-données)
   - [4.1 Vue d'ensemble](#41-vue-densemble)
   - [4.2 Tables de référence](#42-tables-de-référence)
   - [4.3 Module Organisation](#43-module-organisation)
   - [4.4 Module Utilisateurs](#44-module-utilisateurs)
   - [4.5 Module Patients](#45-module-patients)
   - [4.6 Module Coordination](#46-module-coordination)
   - [4.7 Module Plans d'Aide](#47-module-plans-daide)
   - [4.8 Module Catalogue](#48-module-catalogue)
   - [4.9 Module Platform (Super-Admin)](#49-module-platform-super-admin)
   - [4.10 Module Tenants](#410-module-tenants)
   - [4.11 Diagramme ERD complet](#411-diagramme-erd-complet)
5. [Sécurité et Conformité](#5-sécurité-et-conformité)
   - [5.1 Conformité RGPD](#51-conformité-rgpd)
   - [5.2 Hébergement HDS](#52-hébergement-hds)
   - [5.3 Chiffrement des données](#53-chiffrement-des-données)
   - [5.4 Traçabilité des accès](#54-traçabilité-des-accès)
   - [5.5 Architecture de sécurité API](#55-architecture-de-sécurité-api)
6. [Authentification Pro Santé Connect](#6-authentification-pro-santé-connect)
   - [6.1 Vue d'ensemble OAuth2/OIDC](#61-vue-densemble-oauth2oidc)
   - [6.2 Flux d'authentification](#62-flux-dauthentification)
   - [6.3 Gestion des tokens](#63-gestion-des-tokens)
7. [API REST](#7-api-rest)
   - [7.1 Conventions et standards](#71-conventions-et-standards)
   - [7.2 Module Auth](#72-module-auth)
   - [7.3 Module Users](#73-module-users)
   - [7.4 Module Patients](#74-module-patients)
   - [7.5 Module Organization](#75-module-organization)
   - [7.6 Module Coordination](#76-module-coordination)
   - [7.7 Module CarePlan](#77-module-careplan)
   - [7.8 Module Catalog](#78-module-catalog)
   - [7.9 Module Platform (Super-Admin)](#79-module-platform-super-admin)
   - [7.10 Module Tenants](#710-module-tenants)
8. [Rôles et Permissions](#8-rôles-et-permissions)
   - [8.1 Hiérarchie des rôles](#81-hiérarchie-des-rôles)
   - [8.2 Matrice des permissions tenant](#82-matrice-des-permissions-tenant)
   - [8.3 Permissions SuperAdmin](#83-permissions-superadmin)
   - [8.4 Architecture des permissions (v4.3)](#84-architecture-des-permissions-v43)
9. [Schémas Pydantic](#9-schémas-pydantic)
   - [9.1 Module Platform](#91-module-platform)
   - [9.2 Module Tenants](#92-module-tenants)
   - [9.3 Module Évaluations](#93-module-évaluations)
10. [Configuration Technique](#10-configuration-technique)
    - [10.1 PostgreSQL](#101-postgresql)
    - [10.2 Redis](#102-redis)
    - [10.3 Variables d'environnement](#103-variables-denvironnement)
11. [Diagrammes d'Architecture](#11-diagrammes-darchitecture)
    - [11.1 Architecture globale](#111-architecture-globale)
    - [11.2 Flux d'une requête](#112-flux-dune-requête)
    - [11.3 Architecture RLS](#113-architecture-rls)
12. [Roadmap et Évolutions](#12-roadmap-et-évolutions)
13. [Annexes](#13-annexes)

---

## 1. Introduction et Contexte

### 1.1 Vision du projet

**CareLink** est une plateforme SaaS de coordination médico-sociale destinée aux structures de soins à domicile pour personnes âgées en France. L'objectif est de faciliter la coordination entre professionnels de santé, d'optimiser les parcours de soins et de réduire la charge administrative tout en garantissant la conformité réglementaire.

### 1.2 Problématique adressée

Le secteur médico-social français fait face à plusieurs défis majeurs :

| Problème | Impact | Solution CareLink |
|----------|--------|-------------------|
| **Crise hospitalière** | Engorgement des urgences, manque de lits | Coordination des soins à domicile pour éviter les hospitalisations évitables |
| **Fragmentation des outils** | Perte d'information, doublons d'interventions | Plateforme unifiée de coordination |
| **Faible maturité numérique** | Résistance au changement, interfaces complexes | UX simplifiée, mobile-first |
| **Conformité réglementaire** | Sanctions RGPD, non-conformité HDS | Architecture secure-by-design |
| **Coordination multi-acteurs** | Manque de visibilité sur les interventions | Carnet de liaison digital partagé |

### 1.3 Cibles utilisateurs

| Structure  | Description                                                  | Exemples de besoins                       |
|------------|--------------------------------------------------------------|-------------------------------------------|
| **SSIAD**  | Service de Soins Infirmiers À Domicile                       | Planning infirmier, suivi constantes      |
| **SAAD**   | Service d'Aide et d'Accompagnement à Domicile                | Coordination aides à domicile             |
| **SAD**    | Service d'Aide à Domicile                                    | Gestion des interventions                 |
| **SPASAD** | Service Polyvalent d'Aide et de Soins À Domicile             | Coordination soins + aide                 |
| **EHPAD**  | Établissement d'Hébergement pour Personnes Âgées Dépendantes | Suivi résidents, coordination externe     |
| **GCSMS**  | Groupement de Coopération Sociale et Médico-Sociale          | Mutualisation ressources multi-structures |
| **DAC**    | Dispositif d'Appui à la Coordination                         | Parcours complexes                        |
| **CPTS**   | Communauté Professionnelle Territoriale de Santé             | Coordination territoriale                 |

### 1.4 Fonctionnalités principales

| Fonctionnalité             | Description                                                                    | Statut        |
|----------------------------|--------------------------------------------------------------------------------|---------------|
| **Évaluation AGGIR**       | Grille de mesure de l'autonomie (GIR 1-6) avec algorithme officiel décret 1997 | 🟢 Implémenté |
| **Coordination des soins** | Planning des interventions multi-professionnels, carnet de liaison digital     | 🟢 Implémenté |
| **Plans d'aide**           | Production automatisée de PPA, PPCS ou recommandations par patient             | 🟡 En cours   |
| **Constantes vitales**     | Suivi avec alertes sur seuils personnalisés, intégration devices connectés     | 🟢 Implémenté |
| **Authentification PSC**   | Pro Santé Connect (e-CPS), identification par RPPS                             | 🟢 Implémenté |
| **Multi-tenant SaaS**      | Isolation des données par tenant avec RLS PostgreSQL                           | 🟢 Implémenté |
| **Gestion Platform**       | Administration des tenants, super-admins, audit                                | 🟢 Implémenté |
| **Statistiques**           | Tableaux de bord, indicateurs qualité, aide à la formation                     | 🔴 Planifié   |
| **Génération IA**          | Documents PPA/PPCS générés par LLM à partir des évaluations                    | 🔴 Planifié   |

---

## 2. Stack Technique

### 2.1 Technologies backend

```
┌─────────────────────────────────────────────────────────────────┐
│                     STACK TECHNIQUE                              │
├─────────────────────────────────────────────────────────────────┤
│  Langage         │  Python 3.13                                 │
│  Framework API   │  FastAPI 0.100+                              │
│  ORM             │  SQLAlchemy 2.0 (async-ready)                │
│  Validation      │  Pydantic v2 + jsonschema>=4.20.0            │
│  Migrations      │  Alembic                                     │
│  Tests           │  pytest + pytest-asyncio (451 tests)         │
│  Serveur ASGI    │  Uvicorn                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Base de données

| Composant           | Technologie    | Usage                                 |
|---------------------|----------------|---------------------------------------|
| **Base principale** | PostgreSQL 14+ | Données métier, RLS activé            |
| **Cache/Sessions**  | Redis 7+       | Sessions utilisateur, locks d'édition |
| **Migrations**      | Alembic        | Versioning schéma                     |

### 2.3 Sécurité et chiffrement

| Élément               | Algorithme          | Usage                                   |
|-----------------------|---------------------|-----------------------------------------|
| **Données sensibles** | AES-256-GCM         | NIR, INS, nom, prénom, adresse patients |
| **JWT internes**      | ES256 (ECDSA P-256) | Tokens d'authentification CareLink      |
| **Mots de passe**     | bcrypt (cost=12)    | Hash des passwords locaux               |
| **Tokens API**        | SHA-256             | Clés API super-admin                    |

### 2.4 Validation JSON Schema des évaluations

#### Principe : le formulaire vs les données

Imaginez le JSON Schema comme un **formulaire officiel imprimé** (la spécification) et le document JSON comme le **formulaire rempli** (les données). Le formulaire ne change jamais, il définit les champs et leurs règles ; ce sont les données qui sont saisies dans les cases.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  UI         │     │  Schemas    │     │  Services   │     │  Base de    │
│  (Tablette) │ ──▶ │  Pydantic   │ ──▶ │  (logique   │ ──▶ │  données    │
│             │     │  (validation│     │   métier)   │     │  PostgreSQL │
│             │     │   structure)│     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       │                                       │
       ▼                                       ▼
┌─────────────┐                         ┌─────────────┐
│ JSON Schema │                         │ JSON Schema │
│ (validation │                         │ (validation │
│  côté client│                         │  côté       │
│  optionnelle│                         │  serveur)   │
└─────────────┘                         └─────────────┘
```

| Concept | Description | Fichier/Stockage |
|---------|-------------|------------------|
| **JSON Schema** | Spécification (le "formulaire vide") | `app/schemas/json_schemas/evaluation_v1.json` |
| **Document JSON** | Données (le "formulaire rempli") | Colonne `evaluation_data` (JSONB) |

#### Ce que valide le JSON Schema

| Validation | Exemple |
|------------|---------|
| Présence des champs obligatoires | `required: ["patient_identity", "aggir_variables"]` |
| Format des données | `pattern`, `enum`, `min/max`, `type` |
| Structure attendue | Objets imbriqués, tableaux typés |

#### Séparation des données cliniques et métadonnées

| Données cliniques (JSON Schema) | Métadonnées workflow (Tables SQL) |
|---------------------------------|-----------------------------------|
| Identité du patient | Statut de l'évaluation (DRAFT...) |
| Score GIR et variables AGGIR | Pourcentage de complétion |
| État de santé, contexte social | Date d'expiration (J+7) |
| Contacts, équipements | Sessions de saisie |
| Plans d'actions (POA) | Infos de synchronisation |

**Justification** : Les ARS/Conseils Départementaux s'intéressent aux données cliniques exportables. Les métadonnées de session servent à l'audit interne, la facturation, la qualité. Le JSON Schema reste interopérable et focalisé sur le métier.

#### Structure des services de validation

```
app/
├── services/
│   ├── aggir/
│   │   ├── __init__.py
│   │   ├── calculator.py          # Calcul du score GIR
│   │   └── parser.py              # Parsing des variables AGGIR
│   │
│   └── validation/                # Service de validation JSON Schema
│       ├── __init__.py
│       └── schema_validator.py    # Validation partielle/complète
│
├── schemas/
│   └── json_schemas/              # Schémas JSON (spécifications)
│       └── evaluation_v1.json
│
├── models/patient/
│   ├── patient.py
│   ├── patient_evaluation.py
│   └── evaluation_session.py      # Sessions de saisie
│
└── api/v1/patient/
    ├── routes.py                  # Gère InvalidEvaluationDataError
    ├── schemas.py                 # ValidationErrorResponse
    └── services.py                # Appelle le validateur
```

---

## 3. Architecture Multi-Tenant

### 3.1 Décisions architecturales

| Décision                  | Choix retenu                    | Alternatives écartées             | Justification                                        |
|---------------------------|---------------------------------|-----------------------------------|------------------------------------------------------|
| **Isolation des données** | Colonne `tenant_id` (Option C)  | BDD par tenant, Schema par tenant | Maintenabilité, coût, simplicité cross-tenant        |
| **Sécurité BDD**          | Row-Level Security PostgreSQL   | Filtrage applicatif seul          | Protection contre bugs applicatifs, defense-in-depth |
| **Déploiement**           | Une instance par pays           | Instance unique mondiale          | Conformité réglementaire locale (RGPD, HDS)          |
| **Périmètre tenant**      | GCSMS ou structure indépendante | Par établissement                 | Aligné sur la facturation SaaS                       |
| **Super-admins**          | Table séparée `super_admins`    | Flag `is_admin` sur `users`       | Séparation claire, audit distinct                    |
| **Gestion des clés**      | HashiCorp Vault (prévu)         | AWS KMS                           | Portabilité multi-cloud                              |

### 3.2 Stratégie d'isolation des données

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE MULTI-TENANT                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    TABLES PARTAGÉES (sans tenant_id)                │   │
│  │                                                                     │   │
│  │   countries    professions    service_templates    roles            │   │
│  │                                                                     │   │
│  │   → Référentiels nationaux communs à tous les tenants               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    TABLES ISOLÉES (avec tenant_id)                  │   │
│  │                                                                     │   │
│  │   tenants           entities          users            patients     │   │
│  │   user_roles        user_entities     patient_access   evaluations  │   │
│  │   care_plans        interventions     coordination_entries  ...     │   │
│  │                                                                     │   │
│  │   → Données métier isolées par Row-Level Security                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    TABLES PLATFORM (super-admin only)               │   │
│  │                                                                     │   │
│  │   super_admins      platform_audit_logs      user_tenant_assignments│   │
│  │                                                                     │   │
│  │   → Administration CareLink, accès cross-tenant                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Row-Level Security (RLS)

#### Principe de fonctionnement

```sql
-- Variables de session PostgreSQL
SET app.current_tenant_id = '1';    -- Tenant actif
SET app.is_super_admin = 'false';   -- Mode normal

-- Fonctions helper RLS
CREATE FUNCTION get_current_tenant_id() RETURNS INTEGER AS $$
BEGIN
  RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::INTEGER;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE FUNCTION is_super_admin() RETURNS BOOLEAN AS $$
BEGIN
  RETURN COALESCE(current_setting('app.is_super_admin', true), 'false')::BOOLEAN;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE FUNCTION check_tenant_access(row_tenant_id INTEGER) RETURNS BOOLEAN AS $$
BEGIN
  -- Super-admin bypass
  IF is_super_admin() THEN
    RETURN TRUE;
  END IF;
  
  -- Vérification tenant
  RETURN row_tenant_id = get_current_tenant_id();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### Policies RLS appliquées

```sql
-- Exemple pour la table patients
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients FORCE ROW LEVEL SECURITY;

CREATE POLICY patients_tenant_isolation ON patients
  FOR ALL
  USING (check_tenant_access(tenant_id))
  WITH CHECK (tenant_id = get_current_tenant_id());
```

#### Tables avec RLS activé (17 tables)

| Table                     | Policy             | Description               |
|---------------------------|--------------------|---------------------------|
| `entities`                | `tenant_isolation` | Structures de soins       |
| `users`                   | `tenant_isolation` | Professionnels            |
| `patients`                | `tenant_isolation` | Dossiers patients         |
| `patient_access`          | `tenant_isolation` | Droits d'accès RGPD       |
| `patient_evaluations`     | `tenant_isolation` | Évaluations AGGIR         |
| `patient_vitals`          | `tenant_isolation` | Constantes vitales        |
| `patient_thresholds`      | `tenant_isolation` | Seuils personnalisés      |
| `patient_devices`         | `tenant_isolation` | Devices connectés         |
| `patient_documents`       | `tenant_isolation` | Documents générés         |
| `coordination_entries`    | `tenant_isolation` | Carnet de liaison         |
| `user_roles`              | `tenant_isolation` | Attribution des rôles     |
| `user_entities`           | `tenant_isolation` | Rattachements aux entités |
| `care_plans`              | `tenant_isolation` | Plans d'aide              |
| `care_plan_services`      | `tenant_isolation` | Services du plan          |
| `scheduled_interventions` | `tenant_isolation` | Planning interventions    |
| `entity_services`         | `tenant_isolation` | Services par entité       |

### 3.4 Accès cross-tenant

#### Cas d'usage

Un professionnel de santé peut être amené à intervenir temporairement sur un autre tenant (remplacement congé maternité, renfort ponctuel entre structures voisines, etc.).

#### Table `user_tenant_assignments`

```sql
CREATE TABLE user_tenant_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    assignment_type VARCHAR(20) NOT NULL,  -- PERMANENT, TEMPORARY, EMERGENCY
    start_date DATE NOT NULL,
    end_date DATE,
    reason TEXT NOT NULL,
    permissions JSONB,  -- Permissions spécifiques ou NULL (hérite du user)
    granted_by_user_id INTEGER REFERENCES users(id),
    granted_by_super_admin_id INTEGER REFERENCES super_admins(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Flux d'authentification multi-tenant

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    CONNEXION MULTI-TENANT                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Sophie se connecte via PSC (RPPS 12345678901)                        │
│                                                                          │
│  2. Backend vérifie : user.all_tenant_ids = [1, 2]                       │
│     (tenant principal + assignments actifs)                              │
│                                                                          │
│  3. Interface affiche le sélecteur de tenant :                           │
│     ┌───────────────────────────────────────────┐                        │
│     │  Vous avez accès à plusieurs structures   │                        │
│     │                                           │                        │
│     │  ○ GCSMS Île-de-France (principal)        │                        │
│     │  ○ SSIAD Lyon (temporaire jusqu'au        │                        │
│     │    15/04/2025)                            │                        │
│     │                                           │                        │
│     │  [Continuer]                              │                        │
│     └───────────────────────────────────────────┘                        │
│                                                                          │
│  4. Sophie choisit "SSIAD Lyon"                                          │
│     → JWT contient tenant_id=2                                           │
│     → Toutes les requêtes filtrées via RLS                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Modèles de Données

### 4.1 Vue d'ensemble

Le schéma de données est organisé en modules thématiques :

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORGANISATION DES MODÈLES                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  app/models/                                                            │
│  ├── reference/          # Données de référence (countries)             │
│  ├── organization/       # Structures (entities)                        │
│  ├── user/               # Utilisateurs (users, roles, professions)     │
│  ├── patient/            # Dossier patient (patients, evaluations...)   │
│  ├── coordination/       # Coordination (entries, interventions)        │
│  ├── careplan/           # Plans d'aide (care_plans, services)          │
│  ├── catalog/            # Catalogue (service_templates, entity_services)│
│  ├── tenants/            # Multi-tenant (tenants, subscriptions)        │
│  └── platform/           # Administration (super_admins, audit_logs)    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Tables de référence

#### `countries`

| Colonne        | Type                | Description             |
|----------------|---------------------|-------------------------|
| `id`           | `SERIAL PK`         | Identifiant unique      |
| `name`         | `VARCHAR(100)`      | Nom du pays             |
| `country_code` | `VARCHAR(3) UNIQUE` | Code ISO 3166-1 alpha-3 |
| `phone_code`   | `VARCHAR(10)`       | Indicatif téléphonique  |
| `status`       | `VARCHAR(20)`       | active, inactive        |

#### `professions`

| Colonne         | Type                  | Description                         |
|-----------------|-----------------------|-------------------------------------|
| `id`            | `SERIAL PK`           | Identifiant unique                  |
| `code`          | `VARCHAR(20) UNIQUE`  | Code profession (IDE, AS, MED...)   |
| `name`          | `VARCHAR(100) UNIQUE` | Nom complet                         |
| `category`      | `VARCHAR(50)`         | MEDICAL, PARAMEDICAL, SOCIAL, ADMIN |
| `requires_rpps` | `BOOLEAN`             | Nécessite un numéro RPPS            |
| `display_order` | `INTEGER`             | Ordre d'affichage                   |
| `status`        | `VARCHAR(20)`         | active, inactive                    |

### 4.3 Module Organisation

#### `entities`

| Colonne         | Type                | Description                                          |
|-----------------|---------------------|------------------------------------------------------|
| `id`            | `SERIAL PK`         | Identifiant unique                                   |
| `tenant_id`     | `FK → tenants`      | Tenant propriétaire                                  |
| `parent_id`     | `FK → entities`     | Entité parente (hiérarchie)                          |
| `name`          | `VARCHAR(255)`      | Nom de l'entité                                      |
| `entity_type`   | `ENUM`              | GCSMS, SSIAD, SAAD, EHPAD, CABINET, DAC, CPTS, OTHER |
| `finess_number` | `VARCHAR(9) UNIQUE` | Numéro FINESS (nullable)                             |
| `siret`         | `VARCHAR(14)`       | Numéro SIRET                                         |
| `address_line1` | `VARCHAR(255)`      | Adresse ligne 1                                      |
| `postal_code`   | `VARCHAR(10)`       | Code postal                                          |
| `city`          | `VARCHAR(100)`      | Ville                                                |
| `country_id`    | `FK → countries`    | Pays                                                 |
| `phone`         | `VARCHAR(20)`       | Téléphone                                            |
| `email`         | `VARCHAR(255)`      | Email de contact                                     |
| `latitude`      | `DECIMAL(10,8)`     | Coordonnées GPS                                      |
| `longitude`     | `DECIMAL(11,8)`     | Coordonnées GPS                                      |
| `status`        | `VARCHAR(20)`       | active, inactive                                     |
| `created_at`    | `TIMESTAMP`         | Date création                                        |
| `updated_at`    | `TIMESTAMP`         | Date modification                                    |

### 4.4 Module Utilisateurs

#### `users`

| Colonne         | Type                  | Description                            |
|-----------------|-----------------------|----------------------------------------|
| `id`            | `SERIAL PK`           | Identifiant unique                     |
| `tenant_id`     | `FK → tenants`        | Tenant principal                       |
| `rpps_number`   | `VARCHAR(11) UNIQUE`  | Numéro RPPS (professions réglementées) |
| `email`         | `VARCHAR(255) UNIQUE` | Email de connexion                     |
| `first_name`    | `VARCHAR(100)`        | Prénom (chiffré)                       |
| `last_name`     | `VARCHAR(100)`        | Nom (chiffré)                          |
| `profession_id` | `FK → professions`    | Profession                             |
| `phone`         | `VARCHAR(20)`         | Téléphone                              |
| `password_hash` | `VARCHAR(255)`        | Hash bcrypt (connexion locale)         |
| `psc_sub`       | `VARCHAR(255)`        | Subject PSC (connexion PSC)            |
| `is_active`     | `BOOLEAN`             | Compte actif                           |
| `last_login`    | `TIMESTAMP`           | Dernière connexion                     |
| `created_at`    | `TIMESTAMP`           | Date création                          |
| `updated_at`    | `TIMESTAMP`           | Date modification                      |
| `version`       | `INTEGER`             | Optimistic locking                     |

#### `roles`

| Colonne          | Type           | Description                   |
|------------------|----------------|-------------------------------|
| `id`             | `SERIAL PK`    | Identifiant unique            |
| `tenant_id`      | `FK → tenants` | NULL pour rôles système       |
| `name`           | `VARCHAR(50)`  | Code du rôle                  |
| `description`    | `TEXT`         | Description                   |
| `is_system_role` | `BOOLEAN`      | Rôle système (non modifiable) |
| `created_at`     | `TIMESTAMP`    | Date création                 |
| `updated_at`     | `TIMESTAMP`    | Date modification             |

#### `permissions`

| Colonne         | Type                 | Description                         |
|-----------------|----------------------|-------------------------------------|
| `id`            | `SERIAL PK`          | Identifiant unique                  |
| `tenant_id`     | `FK → tenants`       | NULL pour permissions système       |
| `code`          | `VARCHAR(50) UNIQUE` | Code permission (PATIENT_VIEW...)   |
| `name`          | `VARCHAR(100)`       | Nom lisible                         |
| `description`   | `TEXT`               | Description                         |
| `category`      | `VARCHAR(50)`        | Catégorie (PATIENT, USER, ADMIN...) |
| `is_system`     | `BOOLEAN`            | Permission système                  |
| `display_order` | `INTEGER`            | Ordre affichage                     |

#### `role_permissions`

| Colonne         | Type               | Description               |
|-----------------|--------------------|---------------------------|
| `id`            | `SERIAL PK`        | Identifiant unique        |
| `role_id`       | `FK → roles`       | Rôle                      |
| `permission_id` | `FK → permissions` | Permission                |
| `tenant_id`     | `FK → tenants`     | Contexte tenant           |
| `granted_at`    | `TIMESTAMP`        | Date attribution          |
| `granted_by_id` | `FK → users`       | Utilisateur ayant accordé |

### 4.5 Module Patients

#### `patients`

| Colonne                | Type            | Description                |
|------------------------|-----------------|----------------------------|
| `id`                   | `SERIAL PK`     | Identifiant unique         |
| `tenant_id`            | `FK → tenants`  | Tenant propriétaire        |
| `entity_id`            | `FK → entities` | Entité de rattachement     |
| `first_name_encrypted` | `BYTEA`         | Prénom (AES-256-GCM)       |
| `last_name_encrypted`  | `BYTEA`         | Nom (AES-256-GCM)          |
| `birth_date`           | `DATE`          | Date de naissance          |
| `nir_encrypted`        | `BYTEA`         | N° Sécu (AES-256-GCM)      |
| `ins_encrypted`        | `BYTEA`         | INS (AES-256-GCM)          |
| `address_encrypted`    | `BYTEA`         | Adresse (AES-256-GCM)      |
| `phone`                | `VARCHAR(20)`   | Téléphone                  |
| `email`                | `VARCHAR(255)`  | Email                      |
| `medecin_traitant_id`  | `FK → users`    | Médecin traitant           |
| `gir_score`            | `INTEGER`       | Score GIR actuel (1-6)     |
| `latitude`             | `DECIMAL(10,8)` | Coordonnées GPS            |
| `longitude`            | `DECIMAL(11,8)` | Coordonnées GPS            |
| `status`               | `VARCHAR(20)`   | active, archived, deceased |
| `created_at`           | `TIMESTAMP`     | Date création              |
| `updated_at`           | `TIMESTAMP`     | Date modification          |
| `created_by`           | `FK → users`    | Créateur                   |
| `version`              | `INTEGER`       | Optimistic locking         |

#### `patient_evaluations`

Cette table stocke les évaluations cliniques complètes (ex: AGGIR). La colonne `evaluation_data` (JSONB) contient le document JSON avec toutes les données cliniques, validé par un JSON Schema.

| Colonne             | Type            | Description                                  |
|---------------------|-----------------|----------------------------------------------|
| `id`                | `SERIAL PK`     | Identifiant unique                           |
| `patient_id`        | `FK → patients` | Patient évalué                               |
| `tenant_id`         | `FK → tenants`  | Contexte tenant                              |
| `evaluation_type`   | `ENUM`          | AGGIR, CUSTOM                                |
| `evaluation_date`   | `DATE`          | Date de l'évaluation                         |
| `evaluator_id`      | `FK → users`    | Évaluateur principal                         |
| `evaluation_data`   | `JSONB`         | Données cliniques (validées par JSON Schema) |
| `schema_type`       | `VARCHAR(50)`   | Type de schema (ex: "aggir")                 |
| `schema_version`    | `VARCHAR(10)`   | Version du schéma JSON (ex: "1.0")           |
| `gir_score`         | `INTEGER`       | Score GIR calculé (1-6)                      |
| `notes`             | `TEXT`          | Observations                                 |
| `status`            | `VARCHAR(20)`   | DRAFT, SUBMITTED, VALIDATED, ARCHIVED        |
| `completion_percent`| `INTEGER`       | Pourcentage de complétion (0-100)            |
| `expires_at`        | `TIMESTAMP`     | Date d'expiration (J+7 après création)       |
| `validated_by`      | `FK → users`    | Validateur                                   |
| `validated_at`      | `TIMESTAMP`     | Date validation                              |
| `created_at`        | `TIMESTAMP`     | Date création                                |
| `updated_at`        | `TIMESTAMP`     | Date dernière modification                   |

**Distinction clé** : `evaluation_data` (JSONB) contient les données cliniques exportables (identité patient, variables AGGIR, contexte social...), tandis que les colonnes SQL gèrent le workflow interne (statut, complétion, expiration).

#### `evaluation_sessions`

Trace chaque session de saisie d'une évaluation. Une évaluation peut s'étendre sur plusieurs jours (fatigue du patient), d'où la nécessité de tracer les sessions individuellement.

| Colonne           | Type                     | Description                              |
|-------------------|--------------------------|------------------------------------------|
| `id`              | `SERIAL PK`              | Identifiant unique                       |
| `evaluation_id`   | `FK → patient_evaluations` | Évaluation parente                     |
| `tenant_id`       | `FK → tenants`           | Contexte tenant                          |
| `user_id`         | `FK → users`             | Utilisateur ayant saisi                  |
| `started_at`      | `TIMESTAMP`              | Début de la session                      |
| `ended_at`        | `TIMESTAMP`              | Fin de la session (NULL si en cours)     |
| `duration_seconds`| `INTEGER`                | Durée calculée de la session             |
| `variables_saved` | `JSONB`                  | Liste des variables saisies/modifiées    |
| `device_info`     | `JSONB`                  | Infos appareil (tablette, navigateur...) |
| `sync_status`     | `VARCHAR(20)`            | SYNCED, PENDING, CONFLICT                |
| `offline_id`      | `UUID`                   | ID unique pour synchronisation offline   |
| `created_at`      | `TIMESTAMP`              | Date création                            |

**Usage** : Ces métadonnées servent à l'audit interne, la facturation (temps passé), et la qualité (identification des sessions problématiques). Elles ne font pas partie du JSON Schema exportable.

### 4.6 Module Coordination

#### `coordination_entries`

| Colonne      | Type            | Description                     |
|--------------|-----------------|---------------------------------|
| `id`         | `SERIAL PK`     | Identifiant unique              |
| `patient_id` | `FK → patients` | Patient concerné                |
| `tenant_id`  | `FK → tenants`  | Contexte tenant                 |
| `author_id`  | `FK → users`    | Auteur de l'entrée              |
| `entry_date` | `DATE`          | Date de l'intervention          |
| `entry_time` | `TIME`          | Heure de l'intervention         |
| `entry_type` | `ENUM`          | VISIT, OBSERVATION, ALERT, NOTE |
| `content`    | `TEXT`          | Contenu de l'entrée             |
| `is_alert`   | `BOOLEAN`       | Entrée prioritaire              |
| `is_private` | `BOOLEAN`       | Visible uniquement par l'auteur |
| `is_deleted` | `BOOLEAN`       | Soft delete                     |
| `created_at` | `TIMESTAMP`     | Date création                   |
| `updated_at` | `TIMESTAMP`     | Date modification               |

#### `scheduled_interventions`

| Colonne                 | Type                        | Description                                                     |
|-------------------------|-----------------------------|-----------------------------------------------------------------|
| `id`                    | `SERIAL PK`                 | Identifiant unique                                              |
| `care_plan_service_id`  | `FK → care_plan_services`   | Service du plan                                                 |
| `patient_id`            | `FK → patients`             | Patient                                                         |
| `tenant_id`             | `FK → tenants`              | Contexte tenant                                                 |
| `assigned_user_id`      | `FK → users`                | Professionnel affecté                                           |
| `scheduled_date`        | `DATE`                      | Date planifiée                                                  |
| `scheduled_start_time`  | `TIME`                      | Heure début                                                     |
| `scheduled_end_time`    | `TIME`                      | Heure fin                                                       |
| `status`                | `ENUM`                      | SCHEDULED, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, MISSED |
| `actual_start_time`     | `TIME`                      | Heure réelle début                                              |
| `actual_end_time`       | `TIME`                      | Heure réelle fin                                                |
| `completion_notes`      | `TEXT`                      | Notes fin intervention                                          |
| `cancellation_reason`   | `TEXT`                      | Raison annulation                                               |
| `coordination_entry_id` | `FK → coordination_entries` | Lien historique                                                 |

### 4.7 Module Plans d'Aide

#### `care_plans`

| Colonne                | Type                       | Description                                             |
|------------------------|----------------------------|---------------------------------------------------------|
| `id`                   | `SERIAL PK`                | Identifiant unique                                      |
| `patient_id`           | `FK → patients`            | Patient                                                 |
| `tenant_id`            | `FK → tenants`             | Contexte tenant                                         |
| `entity_id`            | `FK → entities`            | Entité coordinatrice                                    |
| `source_evaluation_id` | `FK → patient_evaluations` | Évaluation source                                       |
| `title`                | `VARCHAR(200)`             | Titre du plan                                           |
| `reference_number`     | `VARCHAR(50) UNIQUE`       | Numéro de référence                                     |
| `status`               | `ENUM`                     | DRAFT, PENDING_VALIDATION, ACTIVE, SUSPENDED, COMPLETED |
| `start_date`           | `DATE`                     | Date début                                              |
| `end_date`             | `DATE`                     | Date fin (NULL = indéterminée)                          |
| `total_hours_week`     | `NUMERIC(5,2)`             | Total heures/semaine                                    |
| `gir_at_creation`      | `INTEGER`                  | GIR à la création                                       |
| `validated_by_id`      | `FK → users`               | Validateur                                              |
| `validated_at`         | `TIMESTAMP`                | Date validation                                         |
| `notes`                | `TEXT`                     | Observations                                            |
| `created_by`           | `FK → users`               | Créateur                                                |
| `updated_by`           | `FK → users`               | Modificateur                                            |

#### `care_plan_services`

| Colonne                | Type                     | Description                                        |
|------------------------|--------------------------|----------------------------------------------------|
| `id`                   | `SERIAL PK`              | Identifiant unique                                 |
| `care_plan_id`         | `FK → care_plans`        | Plan parent                                        |
| `service_template_id`  | `FK → service_templates` | Type de service                                    |
| `quantity_per_week`    | `INTEGER`                | Fois par semaine                                   |
| `frequency_type`       | `ENUM`                   | DAILY, WEEKLY, SPECIFIC_DAYS, MONTHLY, ON_DEMAND   |
| `frequency_days`       | `JSONB`                  | Jours [1=Lun...7=Dim]                              |
| `preferred_time_start` | `TIME`                   | Heure début souhaitée                              |
| `preferred_time_end`   | `TIME`                   | Heure fin souhaitée                                |
| `duration_minutes`     | `INTEGER`                | Durée prévue                                       |
| `priority`             | `ENUM`                   | LOW, MEDIUM, HIGH, CRITICAL                        |
| `assigned_user_id`     | `FK → users`             | Professionnel affecté                              |
| `assignment_status`    | `ENUM`                   | UNASSIGNED, PENDING, ASSIGNED, CONFIRMED, REJECTED |
| `assigned_at`          | `TIMESTAMP`              | Date affectation                                   |
| `special_instructions` | `TEXT`                   | Instructions spécifiques                           |
| `status`               | `VARCHAR(20)`            | active, paused, completed                          |

### 4.8 Module Catalogue

#### `service_templates`

| Colonne                    | Type                 | Description                                                             |
|----------------------------|----------------------|-------------------------------------------------------------------------|
| `id`                       | `SERIAL PK`          | Identifiant unique                                                      |
| `code`                     | `VARCHAR(50) UNIQUE` | Code unique (TOILETTE_COMPLETE, INJECTION_SC...)                        |
| `name`                     | `VARCHAR(100)`       | Nom lisible                                                             |
| `category`                 | `ENUM`               | SOINS, HYGIENE, REPAS, MOBILITE, COURSES, MENAGE, ADMINISTRATIF, SOCIAL |
| `description`              | `TEXT`               | Description détaillée                                                   |
| `required_profession_id`   | `FK → professions`   | Profession requise (NULL = polyvalent)                                  |
| `default_duration_minutes` | `INTEGER`            | Durée standard                                                          |
| `requires_prescription`    | `BOOLEAN`            | Nécessite ordonnance                                                    |
| `is_medical_act`           | `BOOLEAN`            | Acte médical/paramédical                                                |
| `apa_eligible`             | `BOOLEAN`            | Facturable APA                                                          |
| `display_order`            | `INTEGER`            | Ordre affichage                                                         |
| `status`                   | `VARCHAR(20)`        | active, inactive                                                        |

#### `entity_services`

| Colonne                   | Type                     | Description              |
|---------------------------|--------------------------|--------------------------|
| `id`                      | `SERIAL PK`              | Identifiant unique       |
| `entity_id`               | `FK → entities`          | Entité                   |
| `service_template_id`     | `FK → service_templates` | Service du catalogue     |
| `tenant_id`               | `FK → tenants`           | Contexte tenant          |
| `is_active`               | `BOOLEAN`                | Service proposé          |
| `price_euros`             | `NUMERIC(10,2)`          | Tarif personnalisé       |
| `max_capacity_week`       | `INTEGER`                | Capacité hebdo max       |
| `custom_duration_minutes` | `INTEGER`                | Durée personnalisée      |
| `notes`                   | `TEXT`                   | Conditions particulières |

### 4.9 Module Platform (Super-Admin)

#### `super_admins`

| Colonne         | Type                  | Description                                                      |
|-----------------|-----------------------|------------------------------------------------------------------|
| `id`            | `SERIAL PK`           | Identifiant unique                                               |
| `email`         | `VARCHAR(255) UNIQUE` | Email de connexion                                               |
| `first_name`    | `VARCHAR(100)`        | Prénom                                                           |
| `last_name`     | `VARCHAR(100)`        | Nom                                                              |
| `password_hash` | `VARCHAR(255)`        | Hash bcrypt                                                      |
| `role`          | `ENUM`                | PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT, PLATFORM_SALES |
| `api_key_hash`  | `VARCHAR(255)`        | Hash clé API                                                     |
| `is_active`     | `BOOLEAN`             | Compte actif                                                     |
| `is_locked`     | `BOOLEAN`             | Compte verrouillé                                                |
| `mfa_enabled`   | `BOOLEAN`             | MFA activé                                                       |
| `last_login`    | `TIMESTAMP`           | Dernière connexion                                               |
| `created_at`    | `TIMESTAMP`           | Date création                                                    |
| `updated_at`    | `TIMESTAMP`           | Date modification                                                |

**Rôles super-admin (v4.3.1) :**

| Rôle               | Niveau | Description             | Capacités                             |
|--------------------|--------|-------------------------|---------------------------------------|
| `PLATFORM_OWNER`   | 4      | Propriétaire plateforme | Tous les droits, gestion super-admins |
| `PLATFORM_ADMIN`   | 3      | Administrateur          | Gestion tenants, audit, assignments   |
| `PLATFORM_SUPPORT` | 2      | Support client          | Consultation, aide utilisateurs       |
| `PLATFORM_SALES`   | 1      | Commercial              | Accès démos uniquement                |

#### `platform_audit_logs`

| Colonne            | Type                | Description                                              |
|--------------------|---------------------|----------------------------------------------------------|
| `id`               | `SERIAL PK`         | Identifiant unique                                       |
| `super_admin_id`   | `FK → super_admins` | Acteur                                                   |
| `action`           | `VARCHAR(50)`       | TENANT_CREATED, TENANT_SUSPENDED, SUPER_ADMIN_CREATED... |
| `resource_type`    | `VARCHAR(100)`      | Type de ressource (tenant, super_admin...)               |
| `resource_id`      | `VARCHAR(50)`       | ID de la ressource                                       |
| `target_tenant_id` | `FK → tenants`      | Tenant concerné                                          |
| `details`          | `JSONB`             | Détails de l'action                                      |
| `ip_address`       | `VARCHAR(45)`       | IP source                                                |
| `user_agent`       | `TEXT`              | User-Agent                                               |
| `created_at`       | `TIMESTAMP`         | Horodatage                                               |

### 4.10 Module Tenants

#### `tenants`

| Colonne             | Type                 | Description                                         |
|---------------------|----------------------|-----------------------------------------------------|
| `id`                | `SERIAL PK`          | Identifiant unique                                  |
| `code`              | `VARCHAR(50) UNIQUE` | Code unique (GCSMS-BV-IDF)                          |
| `name`              | `VARCHAR(255)`       | Nom commercial                                      |
| `legal_name`        | `VARCHAR(255)`       | Raison sociale                                      |
| `siret`             | `VARCHAR(14) UNIQUE` | Numéro SIRET                                        |
| `tenant_type`       | `ENUM`               | GCSMS, SSIAD, SAAD, SPASAD, EHPAD, DAC, CPTS, OTHER |
| `status`            | `ENUM`               | PENDING, ACTIVE, SUSPENDED, TERMINATED              |
| `contact_email`     | `VARCHAR(255)`       | Email contact principal                             |
| `contact_phone`     | `VARCHAR(20)`        | Téléphone                                           |
| `billing_email`     | `VARCHAR(255)`       | Email facturation                                   |
| `address_line1`     | `VARCHAR(255)`       | Adresse                                             |
| `postal_code`       | `VARCHAR(20)`        | Code postal                                         |
| `city`              | `VARCHAR(100)`       | Ville                                               |
| `country_id`        | `FK → countries`     | Pays                                                |
| `timezone`          | `VARCHAR(50)`        | Fuseau horaire (Europe/Paris)                       |
| `locale`            | `VARCHAR(10)`        | Locale (fr_FR)                                      |
| `max_patients`      | `INTEGER`            | Limite patients (NULL=illimité)                     |
| `max_users`         | `INTEGER`            | Limite utilisateurs                                 |
| `max_storage_gb`    | `INTEGER`            | Quota stockage                                      |
| `encryption_key_id` | `VARCHAR(100)`       | Référence clé Vault                                 |
| `settings`          | `JSONB`              | Paramètres personnalisés                            |
| `activated_at`      | `TIMESTAMP`          | Date activation                                     |
| `terminated_at`     | `TIMESTAMP`          | Date résiliation                                    |
| `created_at`        | `TIMESTAMP`          | Date création                                       |
| `updated_at`        | `TIMESTAMP`          | Date modification                                   |

#### `subscriptions`

| Colonne               | Type           | Description                                  |
|-----------------------|----------------|----------------------------------------------|
| `id`                  | `SERIAL PK`    | Identifiant unique                           |
| `tenant_id`           | `FK → tenants` | Tenant                                       |
| `plan_code`           | `ENUM`         | TRIAL, STARTER, PROFESSIONAL, ENTERPRISE     |
| `plan_name`           | `VARCHAR(100)` | Nom du plan                                  |
| `status`              | `ENUM`         | TRIAL, ACTIVE, SUSPENDED, CANCELLED, EXPIRED |
| `started_at`          | `DATE`         | Date début                                   |
| `expires_at`          | `DATE`         | Date expiration                              |
| `trial_ends_at`       | `DATE`         | Fin période essai                            |
| `base_price_cents`    | `INTEGER`      | Prix de base (centimes)                      |
| `currency`            | `VARCHAR(3)`   | Devise (EUR)                                 |
| `billing_cycle`       | `ENUM`         | MONTHLY, QUARTERLY, YEARLY                   |
| `included_patients`   | `INTEGER`      | Patients inclus                              |
| `included_users`      | `INTEGER`      | Utilisateurs inclus                          |
| `included_storage_gb` | `INTEGER`      | Stockage inclus                              |

---

## 5. Sécurité et Conformité

### 5.1 Conformité RGPD

| Exigence                       | Implémentation CareLink                        |
|--------------------------------|------------------------------------------------|
| **Minimisation des données**   | Seules les données nécessaires sont collectées |
| **Limitation de conservation** | Archivage automatique après période légale     |
| **Droit d'accès**              | Export des données patient via API             |
| **Droit à l'effacement**       | Anonymisation sur demande (conservation audit) |
| **Portabilité**                | Export JSON/CSV des données                    |
| **Traçabilité**                | Table `patient_access` avec justification      |

### 5.2 Hébergement HDS

CareLink est conçu pour être déployé chez un hébergeur certifié HDS (Hébergeur de Données de Santé) :

| Critère HDS                | Réponse CareLink                   |
|----------------------------|------------------------------------|
| **Chiffrement au repos**   | AES-256-GCM pour données sensibles |
| **Chiffrement en transit** | TLS 1.3 obligatoire                |
| **Gestion des accès**      | RBAC + RLS PostgreSQL              |
| **Traçabilité**            | Audit logs complets                |
| **Sauvegarde**             | Backup quotidien chiffré           |

### 5.3 Chiffrement des données

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRATÉGIE DE CHIFFREMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DONNÉES CHIFFRÉES (AES-256-GCM)                DONNÉES EN CLAIR           │
│  ┌─────────────────────────────────┐            ┌────────────────────────┐ │
│  │  • first_name (patients)        │            │  • email               │ │
│  │  • last_name (patients)         │            │  • phone               │ │
│  │  • nir (N° Sécu)                │            │  • birth_date          │ │
│  │  • ins (INS)                    │            │  • gir_score           │ │
│  │  • address                      │            │  • dates diverses      │ │
│  │  • notes médicales sensibles    │            │  • statuts             │ │
│  └─────────────────────────────────┘            └────────────────────────┘ │
│                                                                             │
│  GESTION DES CLÉS                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Phase actuelle : Clé unique dans variable d'environnement          │   │
│  │  Phase future   : HashiCorp Vault avec clé par tenant               │   │
│  │                                                                     │   │
│  │  encryption_key_id dans table tenants → référence Vault             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Traçabilité des accès

| Niveau                    | Table                    | Usage                                               |
|---------------------------|--------------------------|-----------------------------------------------------|
| **Accès patient**         | `patient_access`         | Qui a accès à quel dossier, avec justification RGPD |
| **Actions utilisateur**   | `coordination_entries`   | Interventions réalisées                             |
| **Audit super-admin**     | `platform_audit_logs`    | Actions administratives plateforme                  |
| **Modifications données** | `version` + `updated_by` | Optimistic locking, traçabilité modifs              |

### 5.5 Architecture de sécurité API

L'authentification et l'autorisation sont gérées par **trois fichiers spécialisés** :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE DE SÉCURITÉ API (v4.3.1)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  app/api/v1/                                                                │
│  │                                                                          │
│  ├── dependencies.py                                                        │
│  │   └── PaginationParams              # Pagination uniquement              │
│  │                                                                          │
│  ├── user/                                                                  │
│  │   └── tenant_users_security.py      # 🔐 Auth utilisateurs tenant        │
│  │       ├── get_current_user()        # Récupère l'utilisateur courant     │
│  │       ├── get_current_tenant_id()   # Extrait le tenant_id               │
│  │       ├── TenantContext             # Contexte multi-tenant complet      │
│  │       └── verify_write_permission() # Vérifie droits écriture            │
│  │                                                                          │
│  └── platform/                                                              │
│      └── super_admin_security.py       # 🔐 Auth SuperAdmin                 │
│          ├── get_current_super_admin() # Récupère le SuperAdmin             │
│          ├── require_super_admin_permission()  # Vérifie permission         │
│          ├── require_role()            # Vérifie rôle minimum               │
│          └── SuperAdminPermissions     # Constantes permissions             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Utilisation dans les routes

```python
# Route utilisateur tenant (avec contexte multi-tenant)
@router.get("/patients")
async def list_patients(
    ctx: TenantContext = Depends(),  # Fournit user + tenant_id
    db: Session = Depends(get_db)
):
    # ctx.tenant_id est automatiquement injecté
    # ctx.user est l'utilisateur courant
    ...

# Route SuperAdmin (avec vérification de permission)
@router.post("/platform/tenants")
def create_tenant(
    admin: SuperAdmin = Depends(
        require_super_admin_permission(SuperAdminPermissions.TENANTS_CREATE)
    )
):
    # Seuls les SuperAdmins avec la permission peuvent accéder
    ...
```

---

## 6. Authentification Pro Santé Connect

### 6.1 Vue d'ensemble OAuth2/OIDC

Pro Santé Connect (PSC) est le service d'authentification de l'ANS (Agence du Numérique en Santé) pour les professionnels de santé français. Il utilise le protocole OAuth2/OpenID Connect.

| Composant | Description |
|-----------|-------------|
| **Provider** | ANS (État français) |
| **Protocole** | OAuth2 + OpenID Connect |
| **Authentification** | e-CPS (app mobile) ou carte CPS physique |
| **Données retournées** | RPPS, nom, prénom, profession |
| **Environnements** | BAS (test), PROD |

### 6.2 Flux d'authentification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUX AUTHENTIFICATION PSC                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  👨‍⚕️ Professionnel        🌐 Navigateur       🏥 CareLink       🏛️ PSC (ANS)  │
│        │                      │                   │                │        │
│        │─── Clic "PSC" ──────>│                   │                │        │
│        │                      │── GET /login ────>│                │        │
│        │                      │<── Redirect PSC ──│                │        │
│        │                      │                   │                │        │
│        │<─────────────────────│── Redirect ──────────────────────>│        │
│        │                      │                   │                │        │
│        │   [Page PSC : scan QR code e-CPS, PIN]                   │        │
│        │                      │                   │                │        │
│        │<── Redirect + code=abc123 ─────────────────────────────────│        │
│        │                      │                   │                │        │
│        │                      │── GET /callback?code=abc123 ─────>│        │
│        │                      │                   │                │        │
│        │                      │                   │── POST /token ────────>│
│        │                      │                   │   (code=abc123)        │
│        │                      │                   │<── access_token ───────│
│        │                      │                   │                        │
│        │                      │                   │── GET /userinfo ──────>│
│        │                      │                   │<── {RPPS, nom...} ─────│
│        │                      │                   │                │        │
│        │                      │                   │ ┌────────────────────┐ │
│        │                      │                   │ │ SELECT user        │ │
│        │                      │                   │ │ WHERE rpps=123...  │ │
│        │                      │                   │ │                    │ │
│        │                      │                   │ │ Si pas trouvé:     │ │
│        │                      │                   │ │   INSERT user      │ │
│        │                      │                   │ │                    │ │
│        │                      │                   │ │ Générer JWT        │ │
│        │                      │                   │ │ CareLink           │ │
│        │                      │                   │ └────────────────────┘ │
│        │                      │                   │                │        │
│        │                      │<── JWT CareLink ──│                │        │
│        │<─────────────────────│   (stocké local)  │                │        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Gestion des tokens

| Token | Émetteur | Durée | Usage |
|-------|----------|-------|-------|
| **Authorization code** | PSC | 30 secondes | Échange unique contre access_token |
| **Access token PSC** | PSC | Quelques minutes | Récupérer userinfo |
| **JWT CareLink** | CareLink | 30 minutes (configurable) | Authentifier requêtes API |
| **Refresh token** | CareLink | 7 jours | Renouveler JWT sans re-auth |

**Structure du JWT CareLink :**

```json
{
  "sub": "user_123",
  "type": "user",
  "email": "marie.dupont@ssiad.fr",
  "rpps": "12345678901",
  "tenant_id": 1,
  "entity_ids": [1, 2],
  "roles": ["INFIRMIERE", "COORDINATEUR"],
  "permissions": ["PATIENT_VIEW", "PATIENT_EDIT", "..."],
  "iat": 1704067200,
  "exp": 1704069000
}
```

**Structure du JWT SuperAdmin :**

```json
{
  "sub": "admin_5",
  "type": "super_admin",
  "email": "admin@carelink.fr",
  "role": "PLATFORM_ADMIN",
  "iat": 1704067200,
  "exp": 1704069000
}
```

---

## 7. API REST

### 7.1 Conventions et standards

| Convention | Valeur |
|------------|--------|
| **Base URL** | `/api/v1` |
| **Format** | JSON (application/json) |
| **Authentification** | Bearer token (JWT) |
| **Tenant** | Extrait du JWT ou header `X-Tenant-ID` |
| **Pagination** | `?page=1&size=20` |
| **Tri** | `?sort_by=created_at&sort_order=desc` |
| **Erreurs** | Format RFC 7807 (Problem Details) |

**Headers requis :**

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json
```

**Format d'erreur :**

```json
{
  "detail": "Patient not found",
  "status": 404,
  "title": "Not Found",
  "type": "about:blank"
}
```

### 7.2 Module Auth

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/auth/psc/login` | Initie la connexion PSC (redirect) |
| `GET` | `/auth/psc/callback` | Callback PSC, échange code → JWT |
| `POST` | `/auth/login` | Connexion locale (email/password) |
| `POST` | `/auth/refresh` | Renouvelle le JWT avec refresh token |
| `POST` | `/auth/logout` | Déconnexion (invalide le token) |
| `GET` | `/auth/me` | Informations utilisateur connecté |

### 7.3 Module Users

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/users` | Liste des utilisateurs du tenant |
| `POST` | `/users` | Créer un utilisateur |
| `GET` | `/users/{id}` | Détail d'un utilisateur |
| `PATCH` | `/users/{id}` | Modifier un utilisateur |
| `DELETE` | `/users/{id}` | Désactiver un utilisateur |
| `GET` | `/users/{id}/roles` | Rôles de l'utilisateur |
| `POST` | `/users/{id}/roles` | Attribuer un rôle |
| `DELETE` | `/users/{id}/roles/{role_id}` | Retirer un rôle |
| `GET` | `/users/{id}/entities` | Entités de l'utilisateur |
| `POST` | `/users/{id}/entities` | Rattacher à une entité |
| `DELETE` | `/users/{id}/entities/{eid}` | Détacher d'une entité |
| `GET` | `/users/{id}/availabilities` | Disponibilités |
| `POST` | `/users/{id}/availabilities` | Ajouter une disponibilité |
| `PATCH` | `/users/{id}/availabilities/{aid}` | Modifier |
| `DELETE` | `/users/{id}/availabilities/{aid}` | Supprimer |

### 7.4 Module Patients

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/patients` | Liste des patients |
| `POST` | `/patients` | Créer un patient |
| `GET` | `/patients/{id}` | Détail d'un patient |
| `PATCH` | `/patients/{id}` | Modifier un patient |
| `DELETE` | `/patients/{id}` | Archiver un patient |
| `GET` | `/patients/{id}/evaluations` | Évaluations du patient |
| `POST` | `/patients/{id}/evaluations` | Créer une évaluation (validation JSON Schema partielle) |
| `PATCH` | `/patients/{id}/evaluations/{eid}` | Modifier (si DRAFT, validation partielle) |
| `POST` | `/patients/{id}/evaluations/{eid}/submit` | Soumettre (validation JSON Schema complète) |
| `POST` | `/patients/{id}/evaluations/{eid}/validate` | Valider définitivement |
| `DELETE` | `/patients/{id}/evaluations/{eid}` | Supprimer (si DRAFT) |
| `GET` | `/patients/{id}/evaluations/{eid}/sessions` | Liste des sessions de saisie |
| `POST` | `/patients/{id}/evaluations/{eid}/sessions` | Démarrer une nouvelle session |
| `PATCH` | `/patients/{id}/evaluations/{eid}/sessions/{sid}` | Mettre à jour/terminer une session |
| `POST` | `/patients/{id}/evaluations/{eid}/sync` | Synchroniser données offline |
| `GET` | `/patients/{id}/vitals` | Constantes vitales |
| `GET` | `/patients/{id}/vitals/latest/{type}` | Dernière valeur |
| `POST` | `/patients/{id}/vitals` | Enregistrer une mesure |
| `DELETE` | `/patients/{id}/vitals/{vid}` | Supprimer |
| `GET` | `/patients/{id}/thresholds` | Seuils personnalisés |
| `POST` | `/patients/{id}/thresholds` | Créer un seuil |
| `PATCH` | `/patients/{id}/thresholds/{tid}` | Modifier |
| `DELETE` | `/patients/{id}/thresholds/{tid}` | Supprimer |
| `GET` | `/patients/{id}/documents` | Documents générés |
| `GET` | `/patients/{id}/documents/{did}` | Détail document |
| `DELETE` | `/patients/{id}/documents/{did}` | Supprimer |
| `GET` | `/patients/{id}/access` | Droits d'accès |
| `POST` | `/patients/{id}/access` | Accorder un accès |
| `DELETE` | `/patients/{id}/access/{aid}` | Révoquer un accès |
| `GET` | `/patients/{id}/devices` | Appareils connectés |
| `POST` | `/patients/{id}/devices` | Enregistrer un appareil |
| `PATCH` | `/patients/{id}/devices/{did}` | Modifier |
| `DELETE` | `/patients/{id}/devices/{did}` | Désactiver |

#### Modes de validation des évaluations

| Mode | Déclencheur | Comportement |
|------|-------------|--------------|
| **Partielle** | `PATCH`, `POST /sync` | Tolère l'absence de champs requis, rejette les mauvais formats |
| **Complète** | `POST /submit` | Exige tous les champs requis + bons formats |

### 7.5 Module Organization

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/countries` | Liste des pays |
| `GET` | `/countries/{id}` | Détail d'un pays |
| `POST` | `/countries` | Créer un pays |
| `PATCH` | `/countries/{id}` | Modifier |
| `DELETE` | `/countries/{id}` | Supprimer |
| `GET` | `/entities` | Liste des entités |
| `POST` | `/entities` | Créer une entité |
| `GET` | `/entities/{id}` | Détail d'une entité |
| `PATCH` | `/entities/{id}` | Modifier |
| `DELETE` | `/entities/{id}` | Désactiver |
| `GET` | `/entities/{id}/children` | Sous-entités |
| `GET` | `/entities/by-finess/{finess}` | Recherche par FINESS |

### 7.6 Module Coordination

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/coordination-entries` | Historique des passages |
| `POST` | `/coordination-entries` | Créer une entrée |
| `GET` | `/coordination-entries/{id}` | Détail d'une entrée |
| `PATCH` | `/coordination-entries/{id}` | Modifier |
| `DELETE` | `/coordination-entries/{id}` | Supprimer (soft) |
| `POST` | `/coordination-entries/{id}/restore` | Restaurer |
| `GET` | `/scheduled-interventions` | Liste des RDV |
| `POST` | `/scheduled-interventions` | Créer un RDV |
| `GET` | `/scheduled-interventions/{id}` | Détail |
| `PATCH` | `/scheduled-interventions/{id}` | Modifier |
| `DELETE` | `/scheduled-interventions/{id}` | Supprimer |
| `POST` | `/scheduled-interventions/{id}/confirm` | Confirmer |
| `POST` | `/scheduled-interventions/{id}/start` | Démarrer |
| `POST` | `/scheduled-interventions/{id}/complete` | Terminer |
| `POST` | `/scheduled-interventions/{id}/cancel` | Annuler |
| `POST` | `/scheduled-interventions/{id}/missed` | Marquer manquée |
| `POST` | `/scheduled-interventions/{id}/reschedule` | Reprogrammer |
| `GET` | `/planning/daily/{user_id}` | Planning d'un pro |
| `GET` | `/planning/my-day` | Mon planning |

### 7.7 Module CarePlan

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/care-plans` | Liste des plans |
| `POST` | `/care-plans` | Créer un plan |
| `GET` | `/care-plans/{id}` | Détail avec services |
| `PATCH` | `/care-plans/{id}` | Modifier |
| `DELETE` | `/care-plans/{id}` | Supprimer (si draft) |
| `POST` | `/care-plans/{id}/submit` | Soumettre pour validation |
| `POST` | `/care-plans/{id}/validate` | Valider et activer |
| `POST` | `/care-plans/{id}/suspend` | Suspendre |
| `POST` | `/care-plans/{id}/reactivate` | Réactiver |
| `POST` | `/care-plans/{id}/complete` | Terminer |
| `POST` | `/care-plans/{id}/cancel` | Annuler |
| `GET` | `/care-plans/{id}/services` | Services du plan |
| `POST` | `/care-plans/{id}/services` | Ajouter un service |
| `GET` | `/care-plans/{id}/services/{sid}` | Détail service |
| `PATCH` | `/care-plans/{id}/services/{sid}` | Modifier |
| `DELETE` | `/care-plans/{id}/services/{sid}` | Supprimer |
| `POST` | `/care-plans/{id}/services/{sid}/assign` | Affecter |
| `DELETE` | `/care-plans/{id}/services/{sid}/assign` | Désaffecter |
| `POST` | `/care-plans/{id}/services/{sid}/confirm` | Confirmer |
| `POST` | `/care-plans/{id}/services/{sid}/reject` | Refuser |

### 7.8 Module Catalog

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/service-templates` | Catalogue national |
| `GET` | `/service-templates/categories` | Liste des catégories |
| `GET` | `/service-templates/by-category/{cat}` | Services par catégorie |
| `GET` | `/service-templates/{id}` | Détail d'un service |
| `GET` | `/service-templates/code/{code}` | Recherche par code |
| `POST` | `/service-templates` | Créer (admin) |
| `PATCH` | `/service-templates/{id}` | Modifier (admin) |
| `DELETE` | `/service-templates/{id}` | Désactiver (admin) |
| `GET` | `/entities/{id}/services` | Services de l'entité |
| `GET` | `/entities/{id}/services/{sid}` | Détail |
| `POST` | `/entities/{id}/services` | Activer un service |
| `PATCH` | `/entities/{id}/services/{sid}` | Personnaliser |
| `DELETE` | `/entities/{id}/services/{sid}` | Désactiver |

### 7.9 Module Platform (Super-Admin)

> ⚠️ **Toutes ces routes nécessitent une authentification SuperAdmin**

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **Tenants** ||||
| `GET` | `/platform/tenants` | Liste paginée des tenants | `tenants.view` |
| `POST` | `/platform/tenants` | Créer un tenant | `tenants.create` |
| `GET` | `/platform/tenants/{id}` | Détails d'un tenant | `tenants.view` |
| `PATCH` | `/platform/tenants/{id}` | Modifier un tenant | `tenants.update` |
| `DELETE` | `/platform/tenants/{id}` | Résilier un tenant (soft delete) | `tenants.delete` |
| `POST` | `/platform/tenants/{id}/suspend` | Suspendre | `tenants.update` |
| `POST` | `/platform/tenants/{id}/reactivate` | Réactiver | `tenants.update` |
| `GET` | `/platform/tenants/{id}/stats` | Statistiques du tenant | `tenants.view` |
| **SuperAdmins** ||||
| `GET` | `/platform/super-admins` | Liste des super admins | `superadmins.view` |
| `POST` | `/platform/super-admins` | Créer un super admin | `superadmins.create` |
| `GET` | `/platform/super-admins/{id}` | Détails | `superadmins.view` |
| `PATCH` | `/platform/super-admins/{id}` | Modifier | `superadmins.update` |
| `DELETE` | `/platform/super-admins/{id}` | Désactiver | `superadmins.delete` |
| `POST` | `/platform/super-admins/{id}/change-password` | Changer mot de passe | (soi-même) |
| **Audit** ||||
| `GET` | `/platform/audit-logs` | Liste des logs d'audit | `audit.view` |
| `GET` | `/platform/audit-logs/{id}` | Détails d'un log | `audit.view` |
| **Assignments cross-tenant** ||||
| `GET` | `/platform/assignments` | Liste des affectations | `assignments.view` |
| `POST` | `/platform/assignments` | Créer une affectation | `assignments.create` |
| `GET` | `/platform/assignments/{id}` | Détails | `assignments.view` |
| `PATCH` | `/platform/assignments/{id}` | Modifier | `assignments.update` |
| `DELETE` | `/platform/assignments/{id}` | Supprimer | `assignments.delete` |
| **Stats** ||||
| `GET` | `/platform/stats` | Statistiques globales | (tout SuperAdmin) |

### 7.10 Module Tenants

> ⚠️ **Routes alternatives pour la gestion des tenants (SuperAdmin)**

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `GET` | `/tenants` | Liste paginée | `tenants.view` |
| `POST` | `/tenants` | Créer un tenant | `tenants.create` |
| `GET` | `/tenants/{id}` | Détails avec stats | `tenants.view` |
| `PATCH` | `/tenants/{id}` | Modifier | `tenants.update` |
| `POST` | `/tenants/{id}/suspend` | Suspendre | `tenants.suspend` |
| `POST` | `/tenants/{id}/activate` | Activer | `tenants.update` |
| `DELETE` | `/tenants/{id}` | Résilier (avec ?confirm=true) | `tenants.delete` |

---

## 8. Rôles et Permissions

### 8.1 Hiérarchie des rôles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HIÉRARCHIE DES RÔLES (v4.3.1)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NIVEAU PLATEFORME (super_admins - équipe CareLink)                         │
│  ├── PLATFORM_OWNER    → Accès complet, gestion super-admins                │
│  ├── PLATFORM_ADMIN    → Gestion tenants, audit, assignments                │
│  ├── PLATFORM_SUPPORT  → Consultation, aide utilisateurs                    │
│  └── PLATFORM_SALES    → Accès démos uniquement                             │
│                                                                             │
│  NIVEAU TENANT (users.roles - professionnels de santé)                      │
│  ├── ADMIN             → Administration du tenant                           │
│  ├── COORDINATEUR      → Coordination des soins, gestion planning           │
│  ├── MEDECIN_TRAITANT  → Suivi patients, validations médicales              │
│  ├── MEDECIN_SPECIALISTE → Consultation, avis spécialisé                    │
│  ├── INFIRMIERE        → Soins, évaluations, constantes                     │
│  ├── AIDE_SOIGNANTE    → Aide aux soins, observations                       │
│  ├── KINESITHERAPEUTE  → Rééducation, mobilité                              │
│  ├── AUXILIAIRE_VIE    → Aide à domicile                                    │
│  ├── ASSISTANT_SOCIAL  → Accompagnement social                              │
│  └── INTERVENANT       → Accès ponctuel, lecture                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Matrice des permissions tenant

| Permission            | ADMIN | COORDINATEUR | MEDECIN | IDE | AS | INTERV |
|-----------------------|-------|--------------|---------|-----|----|--------|
| `PATIENT_VIEW`        | ✅     | ✅            | ✅       | ✅   | ✅  | ✅      |
| `PATIENT_CREATE`      | ✅     | ✅            | ❌       | ❌   | ❌  | ❌      |
| `PATIENT_EDIT`        | ✅     | ✅            | ✅       | ✅   | ❌  | ❌      |
| `EVALUATION_VIEW`     | ✅     | ✅            | ✅       | ✅   | ✅  | ❌      |
| `EVALUATION_CREATE`   | ✅     | ✅            | ✅       | ✅   | ❌  | ❌      |
| `EVALUATION_VALIDATE` | ✅     | ❌            | ✅       | ❌   | ❌  | ❌      |
| `VITALS_VIEW`         | ✅     | ✅            | ✅       | ✅   | ✅  | ✅      |
| `VITALS_CREATE`       | ✅     | ✅            | ✅       | ✅   | ✅  | ❌      |
| `CAREPLAN_VIEW`       | ✅     | ✅            | ✅       | ✅   | ✅  | ❌      |
| `CAREPLAN_CREATE`     | ✅     | ✅            | ❌       | ❌   | ❌  | ❌      |
| `CAREPLAN_VALIDATE`   | ✅     | ✅            | ✅       | ❌   | ❌  | ❌      |
| `ACCESS_GRANT`        | ✅     | ✅            | ❌       | ❌   | ❌  | ❌      |
| `ACCESS_REVOKE`       | ✅     | ✅            | ❌       | ❌   | ❌  | ❌      |
| `USER_VIEW`           | ✅     | ✅            | ❌       | ❌   | ❌  | ❌      |
| `USER_CREATE`         | ✅     | ❌            | ❌       | ❌   | ❌  | ❌      |
| `USER_EDIT`           | ✅     | ❌            | ❌       | ❌   | ❌  | ❌      |
| `ENTITY_MANAGE`       | ✅     | ❌            | ❌       | ❌   | ❌  | ❌      |
| `ADMIN_FULL`          | ✅     | ❌            | ❌       | ❌   | ❌  | ❌      |

### 8.3 Permissions SuperAdmin

| Permission | Description | OWNER | ADMIN | SUPPORT | SALES |
|------------|-------------|-------|-------|---------|-------|
| `tenants.view` | Voir les tenants | ✅ | ✅ | ✅ | ❌ |
| `tenants.create` | Créer un tenant | ✅ | ✅ | ❌ | ❌ |
| `tenants.update` | Modifier un tenant | ✅ | ✅ | ❌ | ❌ |
| `tenants.delete` | Résilier un tenant | ✅ | ✅ | ❌ | ❌ |
| `tenants.suspend` | Suspendre un tenant | ✅ | ✅ | ❌ | ❌ |
| `superadmins.view` | Voir les super-admins | ✅ | ✅ | ❌ | ❌ |
| `superadmins.create` | Créer un super-admin | ✅ | ❌ | ❌ | ❌ |
| `superadmins.update` | Modifier un super-admin | ✅ | ❌ | ❌ | ❌ |
| `superadmins.delete` | Supprimer un super-admin | ✅ | ❌ | ❌ | ❌ |
| `audit.view` | Consulter les logs d'audit | ✅ | ✅ | ✅ | ❌ |
| `assignments.view` | Voir les affectations | ✅ | ✅ | ✅ | ❌ |
| `assignments.create` | Créer une affectation | ✅ | ✅ | ❌ | ❌ |
| `assignments.update` | Modifier une affectation | ✅ | ✅ | ❌ | ❌ |
| `assignments.delete` | Supprimer une affectation | ✅ | ✅ | ❌ | ❌ |

### 8.4 Architecture des permissions (v4.3)

L'architecture des permissions utilise une approche **normalisée** avec trois tables relationnelles.
Les rôles système (`is_system_role = true`) sont créés automatiquement et ne peuvent pas être modifiés :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE PERMISSIONS v4.3                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  permissions (29)          role_permissions (61)           roles (10)       │
│  ┌─────────────────┐      ┌──────────────────┐      ┌───────────────────┐  │
│  │ PATIENT_VIEW    │──┐   │ role_id ─────────────────│ COORDINATEUR     │  │
│  │ PATIENT_CREATE  │──┼──>│ permission_id    │      │ is_system: true  │  │
│  │ EVALUATION_VIEW │──┤   │ granted_at       │      │ tenant_id: NULL  │  │
│  │ ...             │──┘   │ granted_by_id    │      └───────────────────┘  │
│  └─────────────────┘      └──────────────────┘                              │
│                                                                             │
│  AVANTAGES:                                                                 │
│  ✅ Intégrité référentielle (FK)    ✅ Requêtes optimisées                 │
│  ✅ Traçabilité (granted_at/by)     ✅ Permissions custom par tenant       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Schémas Pydantic

### 9.1 Module Platform

#### Enums

```python
class TenantStatusAPI(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"

class TenantTypeAPI(str, Enum):
    GCSMS = "GCSMS"
    SSIAD = "SSIAD"
    SAAD = "SAAD"
    SPASAD = "SPASAD"
    EHPAD = "EHPAD"
    DAC = "DAC"
    CPTS = "CPTS"
    OTHER = "OTHER"

class SuperAdminRoleAPI(str, Enum):
    PLATFORM_OWNER = "PLATFORM_OWNER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    PLATFORM_SUPPORT = "PLATFORM_SUPPORT"
    PLATFORM_SALES = "PLATFORM_SALES"

class AssignmentTypeAPI(str, Enum):
    PERMANENT = "PERMANENT"
    TEMPORARY = "TEMPORARY"
    EMERGENCY = "EMERGENCY"
```

#### TenantCreate / TenantUpdate / TenantResponse

```python
class TenantCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=255)
    tenant_type: TenantTypeAPI
    contact_email: EmailStr
    # ... autres champs optionnels

class TenantResponse(BaseModel):
    id: int
    code: str
    name: str
    tenant_type: TenantTypeAPI
    status: TenantStatusAPI
    contact_email: str
    max_patients: Optional[int]
    max_users: Optional[int]
    activated_at: Optional[datetime]
    created_at: datetime
    # ...
```

#### SuperAdminCreate / SuperAdminResponse

```python
class SuperAdminCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12)  # Validation complexité
    role: SuperAdminRoleAPI = SuperAdminRoleAPI.PLATFORM_SUPPORT

class SuperAdminResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: SuperAdminRoleAPI
    is_active: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
```

#### UserTenantAssignmentCreate / Response

```python
class UserTenantAssignmentCreate(BaseModel):
    user_id: int
    tenant_id: int
    assignment_type: AssignmentTypeAPI = AssignmentTypeAPI.TEMPORARY
    start_date: date
    end_date: Optional[date]
    reason: Optional[str] = Field(None, max_length=1000)
    permissions: Optional[List[str]]

class UserTenantAssignmentResponse(BaseModel):
    id: int
    user_id: int
    user_email: Optional[str]
    tenant_id: int
    tenant_code: Optional[str]
    assignment_type: AssignmentTypeAPI
    start_date: date
    end_date: Optional[date]
    is_active: bool
    is_valid: bool  # Calculé : actif + dans les dates
    days_remaining: Optional[int]
```

#### PlatformStats

```python
class PlatformStats(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_users: int
    total_patients: int
    active_assignments: int
    tenants_created_last_30_days: int
```

### 9.2 Module Tenants

#### Subscription Schemas

```python
class SubscriptionPlan(str, Enum):
    TRIAL = "TRIAL"
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"

class SubscriptionCreate(BaseModel):
    plan_code: SubscriptionPlan
    started_at: date
    expires_at: Optional[date]
    base_price_cents: int = Field(..., ge=0)
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    included_patients: int = Field(..., ge=0)

class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: int
    plan_code: SubscriptionPlan
    status: SubscriptionStatus
    started_at: date
    base_price_cents: int
    included_patients: int
    
    @property
    def base_price_euros(self) -> float:
        return self.base_price_cents / 100
```

#### TenantWithStats

```python
class TenantWithStats(TenantResponse):
    current_patients_count: int = 0
    current_users_count: int = 0
    current_storage_used_mb: int = 0
    active_subscription: Optional[SubscriptionSummary]
```

### 9.3 Module Évaluations

#### Enums

```python
class EvaluationStatus(str, Enum):
    DRAFT = "DRAFT"           # En cours de saisie
    SUBMITTED = "SUBMITTED"   # Soumis pour validation
    VALIDATED = "VALIDATED"   # Validé définitivement
    ARCHIVED = "ARCHIVED"     # Archivé

class SyncStatus(str, Enum):
    SYNCED = "SYNCED"         # Synchronisé avec le serveur
    PENDING = "PENDING"       # En attente de synchronisation
    CONFLICT = "CONFLICT"     # Conflit détecté
```

#### EvaluationCreate / EvaluationUpdate / EvaluationResponse

```python
class EvaluationCreate(BaseModel):
    patient_id: int
    evaluation_type: str = "AGGIR"
    evaluation_date: date
    evaluation_data: dict = Field(default_factory=dict)  # Validé par JSON Schema
    notes: Optional[str] = None

class EvaluationUpdate(BaseModel):
    evaluation_data: Optional[dict] = None  # Validation partielle
    notes: Optional[str] = None

class EvaluationResponse(BaseModel):
    id: int
    patient_id: int
    evaluation_type: str
    evaluation_date: date
    evaluator_id: int
    evaluation_data: dict
    schema_type: str
    schema_version: str
    gir_score: Optional[int]
    status: EvaluationStatus
    completion_percent: int
    expires_at: Optional[datetime]
    validated_by: Optional[int]
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

#### EvaluationSessionCreate / Response

```python
class EvaluationSessionCreate(BaseModel):
    device_info: Optional[dict] = None
    offline_id: Optional[UUID] = None  # Pour mode hors-ligne

class EvaluationSessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    variables_saved: Optional[List[str]] = None

class EvaluationSessionResponse(BaseModel):
    id: int
    evaluation_id: int
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    variables_saved: List[str]
    device_info: Optional[dict]
    sync_status: SyncStatus
    offline_id: Optional[UUID]
```

#### ValidationErrorResponse

```python
class ValidationError(BaseModel):
    path: str               # Chemin JSON du champ en erreur (ex: "$.patient_identity.name")
    message: str            # Message d'erreur
    constraint: str         # Type de contrainte violée (required, pattern, enum...)

class ValidationErrorResponse(BaseModel):
    detail: str = "Validation failed"
    errors: List[ValidationError]
    is_partial: bool        # True si validation partielle
```

#### SyncRequest / SyncResponse

```python
class SyncRequest(BaseModel):
    offline_id: UUID
    evaluation_data: dict
    variables_saved: List[str]
    client_timestamp: datetime

class SyncResponse(BaseModel):
    status: SyncStatus
    server_version: dict            # Données serveur si conflit
    merged_data: Optional[dict]     # Données fusionnées si résolution auto
    conflict_fields: List[str]      # Champs en conflit
```

---

## 10. Configuration Technique

### 10.1 PostgreSQL

#### Prérequis

- PostgreSQL 14+ avec extension `pgcrypto`
- Utilisateur applicatif dédié (non-superuser)
- RLS activé sur les tables multi-tenant

#### Rôles PostgreSQL

| Rôle | Type | Usage |
|------|------|-------|
| `postgres` | Superuser | Maintenance, création de schéma |
| `carelink` | Applicatif | Connexion application, RLS actif |

```sql
-- Création du rôle applicatif
CREATE ROLE carelink WITH LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE carelink_db TO carelink;
GRANT USAGE ON SCHEMA public TO carelink;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO carelink;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO carelink;

-- IMPORTANT : RLS s'applique à ce rôle
ALTER TABLE patients FORCE ROW LEVEL SECURITY;
```

### 10.2 Redis

#### Configuration

```ini
# Redis pour sessions et locks
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false
REDIS_MAX_CONNECTIONS=50
```

#### Usage

| Clé | TTL | Usage |
|-----|-----|-------|
| `session:{user_id}` | 30 min | Token de session |
| `lock:patient:{id}` | 5 min | Lock édition concurrent |
| `cache:entity:{id}` | 1 heure | Cache entité |

### 10.3 Variables d'environnement

```ini
# Application
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-min-32-chars

# Database
DATABASE_URL=postgresql://carelink:password@localhost:5432/carelink_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Pro Santé Connect
PSC_CLIENT_ID=your-client-id
PSC_CLIENT_SECRET=your-client-secret
PSC_REDIRECT_URI=https://app.carelink.fr/auth/psc/callback
PSC_ENVIRONMENT=BAS  # ou PROD

# Chiffrement
ENCRYPTION_KEY=base64-encoded-32-bytes-key

# JWT
JWT_PRIVATE_KEY_PATH=keys/jwt_private_key.pem
JWT_PUBLIC_KEY_PATH=keys/jwt_public_key.pem
JWT_ALGORITHM=ES256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 11. Diagrammes d'Architecture

### 11.1 Architecture globale

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE GLOBALE CARELINK                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CLIENTS                                          │   │
│  │                                                                     │   │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐        │   │
│  │   │   Web   │    │ Mobile  │    │ Tablet  │    │   API   │        │   │
│  │   │  (Dash) │    │  (PWA)  │    │  (PWA)  │    │ Partners│        │   │
│  │   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘        │   │
│  │        │              │              │              │              │   │
│  └────────┼──────────────┼──────────────┼──────────────┼──────────────┘   │
│           │              │              │              │                   │
│           └──────────────┴──────────────┴──────────────┘                   │
│                                   │                                         │
│                                   ▼ HTTPS / JSON                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    API GATEWAY                                      │   │
│  │                                                                     │   │
│  │   • Rate limiting      • CORS           • Load balancing           │   │
│  │   • SSL termination    • Request logging                           │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FASTAPI APPLICATION                              │   │
│  │                                                                     │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │   │    Auth     │  │   Tenant    │  │  Platform   │               │   │
│  │   │   Module    │  │   Context   │  │   Module    │               │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  │                                                                     │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │   │   Patient   │  │    User     │  │ Coordination│               │   │
│  │   │   Module    │  │   Module    │  │   Module    │               │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  │                                                                     │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│           ┌───────────────────────┼───────────────────────┐                │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │   PostgreSQL    │    │      Redis      │    │  HashiCorp      │        │
│  │                 │    │                 │    │    Vault        │        │
│  │  • Data + RLS   │    │  • Sessions     │    │  (future)       │        │
│  │  • Encryption   │    │  • Cache        │    │  • Keys mgmt    │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Flux d'une requête

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUX D'UNE REQUÊTE AUTHENTIFIÉE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CLIENT                                                                  │
│     │                                                                       │
│     │  GET /api/v1/patients                                                 │
│     │  Authorization: Bearer eyJ...                                         │
│     │                                                                       │
│     ▼                                                                       │
│  2. JWT VERIFICATION                                                        │
│     │                                                                       │
│     │  get_current_user() → Valide signature ES256                          │
│     │                     → Extrait user_id, tenant_id, permissions         │
│     │                                                                       │
│     ▼                                                                       │
│  3. TENANT CONTEXT                                                          │
│     │                                                                       │
│     │  TenantContext.tenant_id = 1                                          │
│     │  TenantContext.user = User(id=42)                                     │
│     │                                                                       │
│     ▼                                                                       │
│  4. DATABASE SESSION + RLS                                                  │
│     │                                                                       │
│     │  SET app.current_tenant_id = '1';                                     │
│     │  SET app.current_user_id = '42';                                      │
│     │                                                                       │
│     ▼                                                                       │
│  5. QUERY EXECUTION                                                         │
│     │                                                                       │
│     │  SELECT * FROM patients;                                              │
│     │  → RLS filtre automatiquement sur tenant_id = 1                       │
│     │  → Retourne uniquement les patients du tenant 1                       │
│     │                                                                       │
│     ▼                                                                       │
│  6. RESPONSE                                                                │
│     │                                                                       │
│     │  { "items": [...], "total": 42, "page": 1 }                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Roadmap et Évolutions

### Phase actuelle (Q1 2026)

| Composant | Statut | Remarque |
|-----------|--------|----------|
| Architecture multi-tenant | ✅ Terminé | RLS PostgreSQL actif |
| Modèles de données | ✅ Terminé | 30+ tables, relations |
| Authentification PSC | ✅ Terminé | OAuth2/OIDC intégré |
| API REST v1 | 🟡 En cours | ~175 endpoints (~92% implémentés) |
| Chiffrement AES-256 | ✅ Terminé | Données patients |
| Module Platform | ✅ Terminé | 22 endpoints super-admin |
| Module Tenants | ✅ Terminé | 7 endpoints gestion clients |
| **Architecture sécurité** | ✅ Terminé | v4.3.1 - Fichiers spécialisés |
| **Permissions normalisées** | ✅ Terminé | v4.3 - Tables relationnelles |
| **Validation JSON Schema** | 🟡 En cours | v4.4 - Évaluations multi-sessions |
| **Sessions d'évaluation** | 🟡 En cours | Table evaluation_sessions, sync offline |
| **Tests automatisés** | ✅ Terminé | 451 tests passés |

### Prochaines étapes (Q2 2026)

| Composant | Priorité | Description |
|-----------|----------|-------------|
| Documentation API | 🔴 Haute | OpenAPI/Swagger complet |
| Frontend Dash | 🔴 Haute | Interface utilisateur |
| Génération PPA/PPCS | 🟡 Moyenne | Intégration LLM |
| Devices connectés | 🟡 Moyenne | API Withings, Apple HealthKit |
| Module Facturation | 🟡 Moyenne | Gestion abonnements |

### Évolutions futures

| Fonctionnalité | Horizon | Description |
|----------------|---------|-------------|
| HashiCorp Vault | 2026 | Gestion clés par tenant |
| IA prédictive | 2026 | Alertes dégradation GIR |
| Télésurveillance | 2027 | Monitoring temps réel |
| Facturation APA | 2027 | Module financier |
| Interop DMP | 2027 | Connexion Dossier Médical Partagé |

---

## 13. Annexes

### A. Glossaire

| Terme | Définition |
|-------|------------|
| **AGGIR** | Autonomie Gérontologie Groupes Iso-Ressources - grille d'évaluation de l'autonomie |
| **APA** | Allocation Personnalisée d'Autonomie |
| **DAC** | Dispositif d'Appui à la Coordination |
| **EHPAD** | Établissement d'Hébergement pour Personnes Âgées Dépendantes |
| **FINESS** | Fichier National des Établissements Sanitaires et Sociaux |
| **GCSMS** | Groupement de Coopération Sociale et Médico-Sociale |
| **GIR** | Groupe Iso-Ressources (1 = dépendance totale, 6 = autonome) |
| **HDS** | Hébergeur de Données de Santé (certification) |
| **INS** | Identifiant National de Santé |
| **JSON Schema** | Spécification de structure pour valider des documents JSON (utilisé pour les évaluations) |
| **JSONB** | Type PostgreSQL pour stocker du JSON en format binaire indexable |
| **NIR** | Numéro d'Inscription au Répertoire (N° Sécu) |
| **PPA** | Plan Personnalisé d'Accompagnement |
| **PPCS** | Plan Personnalisé de Coordination en Santé |
| **PSC** | Pro Santé Connect (authentification ANS) |
| **RLS** | Row-Level Security (PostgreSQL) |
| **RPPS** | Répertoire Partagé des Professionnels de Santé |
| **SAAD** | Service d'Aide et d'Accompagnement à Domicile |
| **SSIAD** | Service de Soins Infirmiers À Domicile |
| **Tenant** | Client CareLink (organisation utilisant la plateforme) |
| **SuperAdmin** | Membre de l'équipe CareLink (niveau plateforme) |
| **Cross-tenant** | Accès d'un utilisateur à plusieurs organisations |

### B. Références

- [Pro Santé Connect - Documentation ANS](https://esante.gouv.fr/securite/pro-sante-connect)
- [RGPD - CNIL](https://www.cnil.fr/fr/rgpd-de-quoi-parle-t-on)
- [Certification HDS](https://esante.gouv.fr/labels-certifications/hds)
- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [JSON Schema Specification](https://json-schema.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)

### C. Contacts

| Rôle | Contact |
|------|---------|
| Product Owner | Olivier de Gouveia |
| Développement | - |
| Infrastructure | - |

---

*Document généré le 23 janvier 2026*  
*Version du schéma de données : v4.4 (Validation JSON Schema des évaluations)*  
*Tests automatisés : 451 passés*  
*Migration Alembic HEAD : normalize_permissions*
