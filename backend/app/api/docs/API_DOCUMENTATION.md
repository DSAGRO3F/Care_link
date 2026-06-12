# 📘 Documentation API CareLink v1

> **CareLink** - Plateforme de coordination des soins médico-sociaux pour le maintien à domicile des personnes âgées.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture des modules](#2-architecture-des-modules)
3. [Rôle de chaque module métier](#3-rôle-de-chaque-module-métier)
4. [Structure des fichiers](#4-structure-des-fichiers)
5. [Fichiers de configuration globaux](#5-fichiers-de-configuration-globaux)
6. [Catalogue des endpoints](#6-catalogue-des-endpoints)
7. [Données d'entrée](#7-données-dentrée)
8. [Données de sortie](#8-données-de-sortie)
9. [Workflows métier](#9-workflows-métier)
10. [Annexes](#10-annexes)

---

## 1. Vue d'ensemble

### Qu'est-ce que CareLink ?

CareLink est une **plateforme numérique** qui permet de coordonner les soins à domicile pour les personnes âgées dépendantes. Elle connecte :

- 🏥 **Les structures de soins** (SSIAD, SAAD, GCSMS)
- 👩‍⚕️ **Les professionnels de santé** (infirmiers, aides-soignants, kinés)
- 👴 **Les patients** et leurs familles
- 📋 **Les plans d'aide** personnalisés

### L'API en chiffres

| Métrique | Valeur |
|----------|--------|
| Modules métier | 8 |
| Endpoints REST | ~168 |
| Tests automatisés | 451 |
| Couverture fonctionnelle | 100% |

### Stack technique

```
┌─────────────────────────────────────┐
│         Applications clientes        │
│   (Web, Mobile, Partenaires)         │
└──────────────┬──────────────────────┘
               │ HTTPS / JSON
               ▼
┌─────────────────────────────────────┐
│          API REST CareLink           │
│            FastAPI + Python          │
└──────────────┬──────────────────────┘
               │ SQLAlchemy ORM
               ▼
┌─────────────────────────────────────┐
│         PostgreSQL Database          │
│     (Données chiffrées AES-256)      │
│     + Row-Level Security (RLS)       │
└─────────────────────────────────────┘
```

---

## 2. Architecture des modules

### Schéma global

```
app/api/v1/
│
├── __init__.py          # Point d'entrée du package
├── router.py            # 🎯 Agrégateur de tous les modules
├── dependencies.py      # 🔧 Pagination uniquement
│
├── organization/        # 🏢 Structures et territoires
├── user/                # 👤 Utilisateurs et rôles
│   └── tenant_users_security.py  # 🔐 Auth utilisateurs tenant
├── patient/             # 🏥 Dossiers patients
├── catalog/             # 📚 Catalogue de services
├── careplan/            # 📋 Plans d'aide
├── coordination/        # 📅 Planning opérationnel
├── tenants/             # 🏛️ Gestion des tenants (clients)
└── platform/            # ⚙️ Administration plateforme
    └── super_admin_security.py   # 🔐 Auth SuperAdmin
```

### Analogie : CareLink comme un immeuble de bureaux

Imaginez CareLink comme un **immeuble de bureaux multi-locataires** :

```
┌────────────────────────────────────────────────────────────────────┐
│                    🏢 IMMEUBLE CARELINK                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   ÉTAGE PLATEFORME (SuperAdmin)               │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │  │
│  │  │  TENANTS   │  │ SUPER-ADM  │  │   AUDIT    │              │  │
│  │  │            │  │            │  │            │              │  │
│  │  │ Gestion    │  │ L'équipe   │  │ Traçabilité│              │  │
│  │  │ des clients│  │ CareLink   │  │ des actions│              │  │
│  │  └────────────┘  └────────────┘  └────────────┘              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              ÉTAGES LOCATAIRES (Tenants/Clients)              │  │
│  │                                                                │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │  │
│  │  │ ORGANIZATION │    │     USER     │    │   PATIENT    │    │  │
│  │  │              │    │              │    │              │    │  │
│  │  │  Le bâtiment │    │ Le personnel │    │ Les malades  │    │  │
│  │  │  Les étages  │    │ Qui travaille│    │ Leurs fiches │    │  │
│  │  │  Les services│    │ Leurs rôles  │    │ Leur état    │    │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘    │  │
│  │                                                                │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │  │
│  │  │   CATALOG    │    │   CAREPLAN   │    │ COORDINATION │    │  │
│  │  │              │    │              │    │              │    │  │
│  │  │ Le menu des  │    │ L'ordonnance │    │ L'agenda     │    │  │
│  │  │ soins        │    │ de soins     │    │ quotidien    │    │  │
│  │  │ disponibles  │    │ du patient   │    │ des visites  │    │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘    │  │
│  │                                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Deux niveaux d'accès

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ARCHITECTURE MULTI-TENANT                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  👑 NIVEAU PLATEFORME (équipe CareLink)                              │
│  ───────────────────────────────────────                             │
│  • SuperAdmins : gèrent les tenants, voient l'audit global           │
│  • Authentification : JWT type "super_admin"                         │
│  • Routes : /platform/*, /tenants/*                                  │
│  • Session : sans contexte tenant (get_db_no_rls)                    │
│                                                                      │
│  👤 NIVEAU TENANT (professionnels de santé)                          │
│  ──────────────────────────────────────────                          │
│  • Utilisateurs : travaillent dans leur(s) structure(s)              │
│  • Authentification : JWT type "user" + tenant_id                    │
│  • Routes : tous les autres endpoints métier                         │
│  • Session : avec contexte tenant (RLS activé)                       │
│  • Cross-tenant : via user_tenant_assignment                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Flux de données entre modules

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   TENANTS   │────▶│ ORGANIZATION│────▶│    USER     │
│             │     │             │     │             │
│ Crée les    │     │ Crée les    │     │ Emploie les │
│ clients     │     │ structures  │     │ soignants   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐             │
                    │   PATIENT   │◀────────────┘
                    │             │
                    │ Prend en    │
                    │ charge les  │
                    └──────┬──────┘
                           │
┌─────────────┐            │
│   CATALOG   │            │
│             │            │
│ Définit les │            │
│ services    │            │
└──────┬──────┘            │
       │                   │
       ▼                   ▼
┌─────────────────────────────┐
│         CAREPLAN            │
│                             │
│  Combine services +         │
│  patient = plan d'aide      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       COORDINATION          │
│                             │
│  Transforme le plan en      │
│  RDV concrets + historique  │
└─────────────────────────────┘
```

---

## 3. Rôle de chaque module métier

### 🏛️ Platform - Administration globale

> **Analogie** : C'est le **syndic de copropriété** de l'immeuble. Il gère les locataires et surveille tout.

**Ce module gère :**
- Les **tenants** (clients CareLink : SSIAD, GCSMS...)
- Les **SuperAdmins** (équipe CareLink)
- Les **logs d'audit** plateforme
- Les **affectations cross-tenant** (accès inter-organisations)
- Les **statistiques globales**

**Exemple concret :**
```
Équipe CareLink (SuperAdmins)
├── Marie (PLATFORM_OWNER) : tous les droits
├── Jean (PLATFORM_ADMIN) : gère les tenants
└── Sophie (PLATFORM_SUPPORT) : consultation seule

Tenants gérés :
├── SSIAD Paris 15e (tenant_id: 1) - ACTIVE
├── GCSMS Île-de-France (tenant_id: 2) - ACTIVE
└── SAAD Lyon (tenant_id: 3) - SUSPENDED
```

**Questions auxquelles ce module répond :**
- Combien de clients utilisent CareLink ?
- Qui a créé ce tenant et quand ?
- Quels utilisateurs ont accès à plusieurs organisations ?

---

### 🏛️ Tenants - Gestion des clients

> **Analogie** : C'est le **registre des locataires** de l'immeuble.

**Ce module gère :**
- Les **informations contractuelles** des clients
- Le **cycle de vie** (création → activation → suspension → résiliation)
- Les **statistiques d'utilisation**

**Exemple concret :**
```
Tenant: SSIAD Paris 15e
├── Code : SSIAD-75015
├── SIRET : 12345678901234
├── Statut : ACTIVE
├── Activé le : 15/01/2024
├── Patients : 150
└── Utilisateurs : 25
```

---

### 🏢 Organization - Les structures

> **Analogie** : C'est le **cadastre** de CareLink. Qui existe ? Où sont-ils ?

**Ce module gère :**
- Les **pays** (référentiel géographique)
- Les **entités** (SSIAD, SAAD, EHPAD, cabinets libéraux)
- La **hiérarchie** entre structures (GCSMS → membres)

**Exemple concret :**
```
GCSMS Île-de-France (groupement)
├── SSIAD Paris 15e (service de soins)
├── SAAD Paris 16e (service d'aide)
└── Cabinet Infirmier Auteuil (libéral)
```

**Questions auxquelles ce module répond :**
- Quelles structures existent dans ma zone ?
- Quelle est la hiérarchie entre elles ?
- Quel est leur numéro FINESS ?

---

### 👤 User - Les professionnels

> **Analogie** : C'est le **service RH** de CareLink. Qui travaille ? Avec quels droits ?

**Ce module gère :**
- Les **professions** (infirmier, aide-soignant, médecin...)
- Les **rôles** et **permissions** (admin, coordinateur, intervenant)
- Les **utilisateurs** et leurs rattachements aux structures
- Les **disponibilités** horaires

**Exemple concret :**
```
Sophie Martin
├── Profession : Infirmière (RPPS: 12345678901)
├── Rôle : Coordinatrice
├── Entité : SSIAD Paris 15e
├── Disponibilités : Lun-Ven 8h-18h
└── Permissions : Créer plans, affecter soignants
```

**Questions auxquelles ce module répond :**
- Qui peut intervenir sur ce patient ?
- Quels sont les droits de cet utilisateur ?
- Qui est disponible demain matin ?

---

### 🏥 Patient - Les dossiers patients

> **Analogie** : C'est le **dossier médical** informatisé. Tout sur le patient.

**Ce module gère :**
- Les **données personnelles** (chiffrées AES-256)
- Les **évaluations** AGGIR (niveau de dépendance GIR 1-6)
- Les **constantes vitales** (tension, température, glycémie)
- Les **seuils d'alerte** personnalisés
- Les **devices connectés** (balance, tensiomètre)
- Les **documents** générés (PPA, PPCS)
- La **traçabilité RGPD** des accès

**Exemple concret :**
```
Jean Dupont, 78 ans
├── GIR : 4 (dépendance modérée)
├── Médecin traitant : Dr Martin
├── Seuils : Tension max 145 mmHg
├── Devices : Balance Withings connectée
├── Dernière évaluation : 15/01/2024
└── Accès autorisés : 3 soignants
```

**Questions auxquelles ce module répond :**
- Quel est le niveau de dépendance de ce patient ?
- Sa tension est-elle dans les normes ?
- Qui a accédé à son dossier cette semaine ?

---

### 📚 Catalog - Le catalogue de services

> **Analogie** : C'est le **menu** des prestations possibles. Que peut-on faire ?

**Ce module gère :**
- Les **templates de services** (référentiel national)
- Les **services activés par entité** (personnalisation locale)
- Les **tarifs** et **durées** personnalisés

**Exemple concret :**
```
Catalogue national
├── TOILETTE_COMPLETE (45 min, Aide-soignant)
├── INJECTION_INSULINE (15 min, IDE, sur prescription)
├── AIDE_REPAS (30 min, tout professionnel)
└── PANSEMENT_COMPLEXE (45 min, IDE, sur prescription)

SSIAD Paris 15e active :
├── TOILETTE_COMPLETE → 50 min (durée adaptée)
├── INJECTION_INSULINE → tarif 25€
└── PANSEMENT_COMPLEXE → 50 créneaux/semaine max
```

**Questions auxquelles ce module répond :**
- Quels services cette structure propose-t-elle ?
- Combien de temps dure une toilette ici ?
- Ce service nécessite-t-il une prescription ?

---

### 📋 CarePlan - Les plans d'aide

> **Analogie** : C'est l'**ordonnance de soins** personnalisée. Qui reçoit quoi, quand ?

**Ce module gère :**
- Les **plans d'aide** (issus des évaluations)
- Les **services planifiés** (fréquence, horaires préférés)
- L'**affectation** aux professionnels
- Le **workflow de validation** (brouillon → validé → actif)

**Exemple concret :**
```
Plan d'aide de Jean Dupont
├── Statut : ACTIF (validé le 20/01/2024)
├── Durée : 15h/semaine
├── Services :
│   ├── Toilette complète : 5x/sem, 7h-9h
│   │   └── Affecté à : Marie (aide-soignante) ✓
│   ├── Injection insuline : 7x/sem, 8h
│   │   └── Affecté à : Sophie (IDE) ✓
│   └── Aide repas midi : 5x/sem, 12h-13h
│       └── En attente d'affectation ⏳
└── Taux d'affectation : 66%
```

**Questions auxquelles ce module répond :**
- Quels soins ce patient doit-il recevoir ?
- Tous les services sont-ils affectés ?
- Le plan est-il validé et actif ?

---

### 📅 Coordination - Le planning opérationnel

> **Analogie** : C'est l'**agenda** quotidien + le **carnet de liaison**. Qui fait quoi aujourd'hui ?

**Ce module gère :**
- Les **interventions planifiées** (RDV concrets)
- Le **workflow d'intervention** (prévu → en cours → terminé)
- Le **carnet de coordination** (historique des passages)
- Le **planning journalier** par professionnel

**Exemple concret :**
```
Planning de Marie - Lundi 22/01/2024
├── 08:00-08:45 │ Jean Dupont │ Toilette │ ✅ Terminé
├── 09:00-09:45 │ Mme Martin │ Toilette │ ✅ Terminé  
├── 10:00-10:30 │ M. Bernard │ Toilette │ 🔄 En cours
└── 11:00-11:45 │ Mme Petit  │ Toilette │ ⏳ À venir

Carnet de coordination - Jean Dupont
├── 22/01 08:45 │ Marie │ Toilette réalisée, RAS
├── 21/01 08:30 │ Marie │ Patient fatigué, à surveiller
└── 20/01 08:40 │ Julie │ Toilette OK, bonne humeur
```

**Questions auxquelles ce module répond :**
- Que dois-je faire aujourd'hui ?
- Qu'ont fait mes collègues chez ce patient ?
- Cette intervention a-t-elle été réalisée ?

---

## 4. Structure des fichiers

Chaque module suit la **même structure** pour faciliter la maintenance :

```
module/
├── __init__.py      # 📦 Export du router
├── schemas.py       # 📝 Contrats de données
├── services.py      # ⚙️ Logique métier
└── routes.py        # 🛣️ Points d'entrée HTTP
```

### 📦 `__init__.py` - Le point d'entrée

> **Analogie** : C'est la **réceptionniste** du module. Elle indique ce qui est disponible.

```python
# Exemple simplifié
from app.api.v1.patient.routes import router

__all__ = ["router"]
```

**Rôle** : Expose uniquement ce qui doit être visible de l'extérieur (le router).

---

### 📝 `schemas.py` - Les contrats de données

> **Analogie** : Ce sont les **formulaires** à remplir. Quelles informations sont requises ?

**Ce fichier définit :**
- Les **données d'entrée** (création, mise à jour)
- Les **données de sortie** (réponses API)
- Les **règles de validation** (format email, longueur min/max)
- Les **filtres de recherche**

```python
# Exemple simplifié
class PatientCreate(BaseModel):
    """Formulaire de création d'un patient."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    birth_date: date
    nir: str = Field(..., pattern=r"^\d{13,15}$")  # N° Sécu

class PatientResponse(BaseModel):
    """Fiche patient renvoyée par l'API."""
    id: int
    first_name: str
    last_name: str
    gir_score: Optional[int]
    is_active: bool
```

**Questions auxquelles ce fichier répond :**
- Quelles données dois-je envoyer pour créer un patient ?
- Quelles données vais-je recevoir en retour ?
- Quelles sont les contraintes de validation ?

---

### ⚙️ `services.py` - La logique métier

> **Analogie** : C'est le **cerveau** du module. Il sait comment faire les choses.

**Ce fichier contient :**
- Les **opérations CRUD** (Create, Read, Update, Delete)
- Les **règles métier** (un plan validé ne peut pas être modifié)
- Les **exceptions personnalisées** (PatientNotFoundError)
- Les **requêtes à la base de données**

```python
# Exemple simplifié
class PatientService:
    @staticmethod
    def create(db: Session, data: PatientCreate) -> Patient:
        """Crée un nouveau patient."""
        # 1. Vérifier que l'entité existe
        # 2. Chiffrer les données sensibles
        # 3. Sauvegarder en base
        # 4. Retourner le patient créé
        ...
    
    @staticmethod
    def archive(db: Session, patient_id: int) -> None:
        """Archive un patient (soft delete)."""
        patient = db.get(Patient, patient_id)
        if not patient:
            raise PatientNotFoundError(f"Patient {patient_id} non trouvé")
        patient.status = "ARCHIVED"
        db.commit()
```

**Questions auxquelles ce fichier répond :**
- Comment créer un patient en base ?
- Quelles vérifications sont faites avant la création ?
- Que se passe-t-il si le patient n'existe pas ?

---

### 🛣️ `routes.py` - Les points d'entrée HTTP

> **Analogie** : Ce sont les **portes d'entrée** du module. Quelle URL pour quelle action ?

**Ce fichier définit :**
- Les **endpoints** (URL + méthode HTTP)
- Les **paramètres** attendus (path, query, body)
- Les **codes de réponse** (200, 201, 404, 409...)
- Les **permissions** requises

```python
# Exemple simplifié
@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Authentification requise
):
    """Récupère un patient par son ID."""
    try:
        return PatientService.get_by_id(db, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**Questions auxquelles ce fichier répond :**
- Quelle URL pour récupérer un patient ?
- Quels paramètres sont attendus ?
- Quels codes d'erreur peuvent être retournés ?

---

## 5. Fichiers de configuration globaux

### 🎯 `router.py` - L'agrégateur central

> **Analogie** : C'est le **standard téléphonique**. Il redirige vers le bon service.

```python
# Structure simplifiée
api_router = APIRouter(prefix="/api/v1")

# Modules métier (utilisateurs tenant)
api_router.include_router(organization_router)  # /api/v1/entities, /api/v1/countries
api_router.include_router(user_router)          # /api/v1/users, /api/v1/roles
api_router.include_router(patient_router)       # /api/v1/patients
api_router.include_router(catalog_router)       # /api/v1/service-templates
api_router.include_router(careplan_router)      # /api/v1/care-plans
api_router.include_router(coordination_router)  # /api/v1/coordination-entries

# Modules plateforme (SuperAdmins)
api_router.include_router(tenants_router)       # /api/v1/tenants
api_router.include_router(platform_router)      # /api/v1/platform/*
```

**Rôle** : 
- Unifie tous les modules sous `/api/v1`
- Point d'entrée unique pour l'application FastAPI
- Expose un endpoint `/health` pour le monitoring

---

### 🔧 `dependencies.py` - Pagination uniquement

> **Analogie** : C'est la **boîte à outils** commune à tous les modules.

**Contenu : `PaginationParams`**

```python
class PaginationParams:
    """Gère la pagination des listes."""
    
    def __init__(
        self,
        page: int = 1,        # Page demandée (commence à 1)
        size: int = 20,       # Éléments par page (max 100)
        sort_by: str = None,  # Champ de tri
        sort_order: str = "asc"  # asc ou desc
    ):
        ...
```

**Utilisation :**
```
GET /api/v1/patients?page=2&size=10&sort_by=created_at&sort_order=desc
```

Retourne les patients 11 à 20, triés par date de création décroissante.

---

### 🔐 Architecture de sécurité

L'authentification est séparée en **trois fichiers spécialisés** :

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE DE SÉCURITÉ                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  app/api/v1/                                                         │
│  ├── dependencies.py                                                 │
│  │   └── PaginationParams              # Pagination uniquement       │
│  │                                                                   │
│  ├── user/                                                           │
│  │   └── tenant_users_security.py      # 🔐 Auth utilisateurs       │
│  │       ├── get_current_user          # Récupère l'utilisateur     │
│  │       ├── get_current_tenant_id     # Extrait le tenant_id       │
│  │       ├── TenantContext             # Contexte multi-tenant      │
│  │       └── verify_write_permission   # Vérifie droits écriture    │
│  │                                                                   │
│  └── platform/                                                       │
│      └── super_admin_security.py       # 🔐 Auth SuperAdmin         │
│          ├── get_current_super_admin   # Récupère le SuperAdmin     │
│          ├── require_super_admin_permission  # Vérifie permission   │
│          ├── require_role              # Vérifie rôle minimum       │
│          └── SuperAdminPermissions     # Constantes permissions     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Authentification utilisateurs tenant (`tenant_users_security.py`)

```python
# Récupérer le contexte multi-tenant
@router.get("/patients")
async def list_patients(
    ctx: TenantContext = Depends(),  # Fournit user + tenant_id
    db: Session = Depends(get_db)
):
    query = db.query(Patient).filter(Patient.tenant_id == ctx.tenant_id)
    ...

# Vérifier les droits d'écriture (pour cross-tenant)
@router.post("/patients")
async def create_patient(
    ctx: TenantContext = Depends(),
    _: None = Depends(verify_write_permission()),  # Bloque si lecture seule
    ...
):
    ...
```

#### Authentification SuperAdmin (`super_admin_security.py`)

```python
# Vérifier une permission spécifique
@router.post("/tenants")
def create_tenant(
    admin: SuperAdmin = Depends(
        require_super_admin_permission(SuperAdminPermissions.TENANTS_CREATE)
    )
):
    ...

# Vérifier un rôle minimum
@router.delete("/super-admins/{id}")
def delete_super_admin(
    admin: SuperAdmin = Depends(require_role(SuperAdminRole.PLATFORM_OWNER))
):
    ...
```

#### Mapping rôles → permissions SuperAdmin

| Rôle | Niveau | Permissions |
|------|--------|-------------|
| `PLATFORM_OWNER` | 4 | Toutes (gestion complète) |
| `PLATFORM_ADMIN` | 3 | tenants.*, audit.view, assignments.*, superadmins.view |
| `PLATFORM_SUPPORT` | 2 | tenants.view, audit.view, assignments.view |
| `PLATFORM_SALES` | 1 | Accès démos uniquement |

---

## 6. Catalogue des endpoints

### ⚙️ Platform (22 endpoints)

> Routes réservées aux **SuperAdmins** (équipe CareLink)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **Tenants** ||||
| `GET` | `/platform/tenants` | Liste paginée des tenants | `tenants.view` |
| `POST` | `/platform/tenants` | Créer un tenant | `tenants.create` |
| `GET` | `/platform/tenants/{id}` | Détails d'un tenant | `tenants.view` |
| `PATCH` | `/platform/tenants/{id}` | Modifier un tenant | `tenants.update` |
| `DELETE` | `/platform/tenants/{id}` | Résilier un tenant | `tenants.delete` |
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

---

### 🏛️ Tenants (7 endpoints)

> Routes alternatives pour la gestion des tenants

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `GET` | `/tenants` | Liste paginée | `tenants.view` |
| `POST` | `/tenants` | Créer un tenant | `tenants.create` |
| `GET` | `/tenants/{id}` | Détails avec stats | `tenants.view` |
| `PATCH` | `/tenants/{id}` | Modifier | `tenants.update` |
| `POST` | `/tenants/{id}/suspend` | Suspendre | `tenants.suspend` |
| `POST` | `/tenants/{id}/activate` | Activer | `tenants.update` |
| `DELETE` | `/tenants/{id}` | Résilier | `tenants.delete` |

---

### 🏢 Organization (12 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/countries` | Liste des pays |
| `GET` | `/countries/{id}` | Détail d'un pays |
| `POST` | `/countries` | Créer un pays |
| `PATCH` | `/countries/{id}` | Modifier un pays |
| `DELETE` | `/countries/{id}` | Supprimer un pays |
| `GET` | `/entities` | Liste des entités (structures) |
| `GET` | `/entities/{id}` | Détail d'une entité |
| `GET` | `/entities/{id}/children` | Sous-entités (hiérarchie) |
| `POST` | `/entities` | Créer une entité |
| `PATCH` | `/entities/{id}` | Modifier une entité |
| `DELETE` | `/entities/{id}` | Désactiver une entité |
| `GET` | `/entities/by-finess/{finess}` | Recherche par FINESS |

---

### 👤 User (28 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **Professions** |||
| `GET` | `/professions` | Liste des professions |
| `GET` | `/professions/{id}` | Détail d'une profession |
| `POST` | `/professions` | Créer une profession |
| `PATCH` | `/professions/{id}` | Modifier une profession |
| `DELETE` | `/professions/{id}` | Supprimer une profession |
| **Rôles** |||
| `GET` | `/roles` | Liste des rôles |
| `GET` | `/roles/{id}` | Détail d'un rôle |
| `POST` | `/roles` | Créer un rôle |
| `PATCH` | `/roles/{id}` | Modifier un rôle |
| `DELETE` | `/roles/{id}` | Supprimer un rôle |
| **Utilisateurs** |||
| `GET` | `/users` | Liste des utilisateurs |
| `GET` | `/users/{id}` | Détail d'un utilisateur |
| `POST` | `/users` | Créer un utilisateur |
| `PATCH` | `/users/{id}` | Modifier un utilisateur |
| `DELETE` | `/users/{id}` | Désactiver un utilisateur |
| `GET` | `/users/{id}/entities` | Entités de l'utilisateur |
| `POST` | `/users/{id}/entities` | Rattacher à une entité |
| `DELETE` | `/users/{id}/entities/{eid}` | Détacher d'une entité |
| `GET` | `/users/{id}/roles` | Rôles de l'utilisateur |
| `POST` | `/users/{id}/roles` | Attribuer un rôle |
| `DELETE` | `/users/{id}/roles/{rid}` | Retirer un rôle |
| **Disponibilités** |||
| `GET` | `/users/{id}/availabilities` | Disponibilités |
| `POST` | `/users/{id}/availabilities` | Ajouter une disponibilité |
| `PATCH` | `/users/{id}/availabilities/{aid}` | Modifier |
| `DELETE` | `/users/{id}/availabilities/{aid}` | Supprimer |

---

### 🏥 Patient (30 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **Patients** |||
| `GET` | `/patients` | Liste des patients |
| `GET` | `/patients/{id}` | Détail d'un patient |
| `POST` | `/patients` | Créer un patient |
| `PATCH` | `/patients/{id}` | Modifier un patient |
| `DELETE` | `/patients/{id}` | Archiver un patient |
| **Accès RGPD** |||
| `GET` | `/patients/{id}/access` | Liste des accès autorisés |
| `POST` | `/patients/{id}/access` | Accorder un accès |
| `DELETE` | `/patients/{id}/access/{aid}` | Révoquer un accès |
| **Évaluations** |||
| `GET` | `/patients/{id}/evaluations` | Liste des évaluations |
| `GET` | `/patients/{id}/evaluations/{eid}` | Détail d'une évaluation |
| `POST` | `/patients/{id}/evaluations` | Créer une évaluation |
| `PATCH` | `/patients/{id}/evaluations/{eid}` | Modifier (si non validée) |
| `POST` | `/patients/{id}/evaluations/{eid}/validate` | Valider |
| `DELETE` | `/patients/{id}/evaluations/{eid}` | Supprimer (si non validée) |
| **Seuils vitaux** |||
| `GET` | `/patients/{id}/thresholds` | Seuils du patient |
| `POST` | `/patients/{id}/thresholds` | Créer un seuil |
| `PATCH` | `/patients/{id}/thresholds/{tid}` | Modifier |
| `DELETE` | `/patients/{id}/thresholds/{tid}` | Supprimer |
| **Constantes vitales** |||
| `GET` | `/patients/{id}/vitals` | Historique des constantes |
| `GET` | `/patients/{id}/vitals/latest/{type}` | Dernière valeur |
| `POST` | `/patients/{id}/vitals` | Enregistrer une constante |
| `DELETE` | `/patients/{id}/vitals/{vid}` | Supprimer |
| **Devices connectés** |||
| `GET` | `/patients/{id}/devices` | Appareils du patient |
| `POST` | `/patients/{id}/devices` | Enregistrer un appareil |
| `PATCH` | `/patients/{id}/devices/{did}` | Modifier |
| `DELETE` | `/patients/{id}/devices/{did}` | Désactiver |
| **Documents** |||
| `GET` | `/patients/{id}/documents` | Documents générés |
| `GET` | `/patients/{id}/documents/{did}` | Détail d'un document |
| `DELETE` | `/patients/{id}/documents/{did}` | Supprimer (admin) |

---

### 📚 Catalog (15 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **Templates de services** |||
| `GET` | `/service-templates` | Catalogue national |
| `GET` | `/service-templates/categories` | Liste des catégories |
| `GET` | `/service-templates/by-category/{cat}` | Services par catégorie |
| `GET` | `/service-templates/{id}` | Détail d'un service |
| `GET` | `/service-templates/code/{code}` | Recherche par code |
| `POST` | `/service-templates` | Créer un service (admin) |
| `PATCH` | `/service-templates/{id}` | Modifier (admin) |
| `DELETE` | `/service-templates/{id}` | Désactiver (admin) |
| **Services par entité** |||
| `GET` | `/entities/{id}/services` | Services de l'entité |
| `GET` | `/entities/{id}/services/{sid}` | Détail |
| `POST` | `/entities/{id}/services` | Activer un service |
| `PATCH` | `/entities/{id}/services/{sid}` | Personnaliser |
| `DELETE` | `/entities/{id}/services/{sid}` | Désactiver |

---

### 📋 CarePlan (20 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **Plans d'aide** |||
| `GET` | `/care-plans` | Liste des plans |
| `GET` | `/care-plans/{id}` | Détail avec services |
| `POST` | `/care-plans` | Créer un plan |
| `PATCH` | `/care-plans/{id}` | Modifier |
| `DELETE` | `/care-plans/{id}` | Supprimer (brouillon) |
| **Workflow** |||
| `POST` | `/care-plans/{id}/submit` | Soumettre pour validation |
| `POST` | `/care-plans/{id}/validate` | Valider et activer |
| `POST` | `/care-plans/{id}/suspend` | Suspendre |
| `POST` | `/care-plans/{id}/reactivate` | Réactiver |
| `POST` | `/care-plans/{id}/complete` | Terminer |
| `POST` | `/care-plans/{id}/cancel` | Annuler |
| **Services du plan** |||
| `GET` | `/care-plans/{id}/services` | Services du plan |
| `GET` | `/care-plans/{id}/services/{sid}` | Détail |
| `POST` | `/care-plans/{id}/services` | Ajouter un service |
| `PATCH` | `/care-plans/{id}/services/{sid}` | Modifier |
| `DELETE` | `/care-plans/{id}/services/{sid}` | Supprimer |
| **Affectation** |||
| `POST` | `/care-plans/{id}/services/{sid}/assign` | Affecter |
| `DELETE` | `/care-plans/{id}/services/{sid}/assign` | Désaffecter |
| `POST` | `/care-plans/{id}/services/{sid}/confirm` | Confirmer |
| `POST` | `/care-plans/{id}/services/{sid}/reject` | Refuser |

---

### 📅 Coordination (19 endpoints)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| **Carnet de coordination** |||
| `GET` | `/coordination-entries` | Historique des passages |
| `GET` | `/coordination-entries/{id}` | Détail d'une entrée |
| `POST` | `/coordination-entries` | Enregistrer un passage |
| `PATCH` | `/coordination-entries/{id}` | Modifier |
| `DELETE` | `/coordination-entries/{id}` | Supprimer (soft) |
| `POST` | `/coordination-entries/{id}/restore` | Restaurer |
| **Interventions planifiées** |||
| `GET` | `/scheduled-interventions` | Liste des RDV |
| `GET` | `/scheduled-interventions/{id}` | Détail |
| `POST` | `/scheduled-interventions` | Créer un RDV |
| `PATCH` | `/scheduled-interventions/{id}` | Modifier |
| `DELETE` | `/scheduled-interventions/{id}` | Supprimer |
| **Workflow intervention** |||
| `POST` | `/scheduled-interventions/{id}/confirm` | Confirmer |
| `POST` | `/scheduled-interventions/{id}/start` | Démarrer |
| `POST` | `/scheduled-interventions/{id}/complete` | Terminer |
| `POST` | `/scheduled-interventions/{id}/cancel` | Annuler |
| `POST` | `/scheduled-interventions/{id}/missed` | Marquer manquée |
| `POST` | `/scheduled-interventions/{id}/reschedule` | Reprogrammer |
| **Planning** |||
| `GET` | `/planning/daily/{user_id}` | Planning d'un pro |
| `GET` | `/planning/my-day` | Mon planning |

---

## 7. Données d'entrée

### Sources des données

Les données d'entrée proviennent de l'**interface utilisateur CareLink** (Dash Mantine Components), adaptée à chaque contexte d'utilisation :

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           INTERFACE CARELINK (Dash Mantine)            │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │   ADMIN      │  │ COORDINATEUR │  │ PROFESSIONNEL│ │ │
│  │  │   Bureau     │  │    Bureau    │  │   Tablette   │ │ │
│  │  │              │  │              │  │              │ │ │
│  │  │ Formulaires  │  │ Formulaires  │  │ Grille AGGIR │ │ │
│  │  │ utilisateurs │  │ plans d'aide │  │ évaluations  │ │ │
│  │  │ structures   │  │ affectations │  │ constantes   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  │                                                        │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                      │
│                       ▼ JSON / HTTPS                         │
│                ┌─────────────────┐                           │
│                │   API CareLink  │                           │
│                └─────────────────┘                           │
│                                                              │
│  Sources complémentaires (futures) :                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Devices    │    │    Import    │    │ Partenaires  │   │
│  │  connectés   │    │    fichiers  │    │    API       │   │
│  │  (Withings)  │    │  (CSV, XLS)  │    │  (CPAM...)   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Écrans principaux par profil

| Profil | Écrans UI | Données saisies |
|--------|-----------|-----------------|
| **SuperAdmin** | Console plateforme, Gestion tenants, Audit | Tenants, super-admins, affectations cross-tenant |
| **Administrateur** | Gestion structures, Gestion utilisateurs, Configuration rôles | Entités, professionnels, professions, rôles, permissions |
| **Coordinateur** | Dossiers patients, Plans d'aide, Tableau d'affectation, Planning | Patients, évaluations, services planifiés, affectations horaires |
| **Professionnel** | Grille AGGIR (tablette), Carnet de liaison, Mon planning | Évaluations terrain, constantes vitales, notes de coordination |

### Format des données d'entrée

**Format général : JSON**

```json
{
  "field_name": "value",
  "nested_object": {
    "sub_field": 123
  },
  "array_field": [1, 2, 3]
}
```

**Exemples par type de données :**

| Type | Format | Exemple |
|------|--------|---------|
| Date | ISO 8601 | `"2024-01-22"` |
| DateTime | ISO 8601 + TZ | `"2024-01-22T14:30:00Z"` |
| Time | HH:MM:SS | `"08:30:00"` |
| Decimal | String ou Number | `"25.50"` ou `25.50` |
| Email | RFC 5322 | `"user@example.com"` |
| NIR | 13-15 chiffres | `"1850175123456"` |
| RPPS | 11 chiffres | `"12345678901"` |
| FINESS | 9 chiffres | `"750000001"` |

**Exemple complet - Création d'un patient :**

```json
POST /api/v1/patients
Content-Type: application/json
Authorization: Bearer <token>

{
  "entity_id": 1,
  "first_name": "Jean",
  "last_name": "Dupont",
  "birth_date": "1945-03-15",
  "nir": "1450375123456",
  "address": "10 rue de la Paix, 75001 Paris",
  "phone": "0612345678",
  "email": "jean.dupont@email.fr",
  "medecin_traitant_id": 5,
  "latitude": 48.8566,
  "longitude": 2.3522
}
```

### Validation des données

L'API valide automatiquement :

| Règle | Exemple | Erreur si invalide |
|-------|---------|-------------------|
| Champs requis | `first_name` obligatoire | 422 - Field required |
| Longueur min/max | `name` 1-100 caractères | 422 - String too short/long |
| Format regex | NIR = 13-15 chiffres | 422 - String does not match |
| Valeurs enum | `status` ∈ [DRAFT, ACTIVE] | 422 - Invalid enum value |
| Plage numérique | `gir_score` 1-6 | 422 - Value out of range |
| Unicité | `email` unique | 409 - Already exists |
| Référence existante | `entity_id` existe | 404 - Not found |

---

## 8. Données de sortie

### Consommateurs de l'API

L'API CareLink est consommée par une **interface utilisateur web** développée avec **Dash Mantine Components** (framework Python). Cette interface s'adapte aux différents profils d'utilisateurs métier.

```
┌─────────────────────────────────────────────────────────────┐
│              INTERFACE UTILISATEUR CARELINK                  │
│                (Dash Mantine Components)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ┌─────────────────┐                       │
│                    │   API CareLink  │                       │
│                    │   (JSON/HTTPS)  │                       │
│                    └────────┬────────┘                       │
│                             │                                │
│    ┌────────────────────────┼────────────────────────┐       │
│    │                        │                        │       │
│    ▼                        ▼                        ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ 👑 SUPERADM  │    │ 👑 ADMIN     │    │ 📋 COORDIN.  │   │
│  │              │    │              │    │              │   │
│  │ • Tenants    │    │ • Structures │    │ • Dossiers   │   │
│  │ • Audit      │    │ • Utilisat.  │    │ • Plans aide │   │
│  │ • Stats      │    │ • Rôles      │    │ • Affectation│   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│       Console             Bureau              Bureau         │
│                                                              │
│                        ┌──────────────┐                      │
│                        │ 👩‍⚕️ PRO      │                      │
│                        │              │                      │
│                        │ • Planning   │                      │
│                        │ • Évaluations│                      │
│                        │ • Carnet     │                      │
│                        └──────────────┘                      │
│                            Tablette                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Profils utilisateurs et cas d'usage

| Profil                        | Appareil        | Modules API utilisés                     | Actions principales                                                                  |
|-------------------------------|-----------------|------------------------------------------|--------------------------------------------------------------------------------------|
| **SuperAdmin**                | PC Bureau       | Platform, Tenants                        | Gérer tenants, consulter audit, créer affectations cross-tenant                      |
| **Administrateur**            | PC Bureau       | Organization, User                       | Créer structures, gérer professionnels, définir rôles et permissions                 |
| **Coordinateur**              | PC Bureau       | Patient, CarePlan, Coordination, Catalog | Créer dossiers patients, élaborer plans d'aide, affecter professionnels aux services |
| **Professionnel évaluateur**  | Tablette        | Patient (évaluations)                    | Réaliser évaluations AGGIR sur le terrain, saisir grilles de dépendance              |
| **Professionnel intervenant** | Tablette/Mobile | Coordination                             | Consulter planning, démarrer/terminer interventions, remplir carnet de coordination  |

### Format des réponses

**Structure standard - Élément unique :**

```json
{
  "id": 1,
  "field_name": "value",
  "created_at": "2024-01-22T10:30:00Z",
  "updated_at": "2024-01-22T14:00:00Z"
}
```

**Structure standard - Liste paginée :**

```json
{
  "items": [
    { "id": 1, "name": "..." },
    { "id": 2, "name": "..." }
  ],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**Exemple complet - Réponse patient :**

```json
{
  "id": 123,
  "entity_id": 1,
  "first_name": "Jean",
  "last_name": "Dupont",
  "birth_date": "1945-03-15",
  "status": "ACTIVE",
  "gir_score": 4,
  "medecin_traitant_id": 5,
  "latitude": 48.8566,
  "longitude": 2.3522,
  "created_at": "2024-01-22T10:30:00Z",
  "updated_at": "2024-01-22T14:00:00Z"
}
```

### Codes de réponse HTTP

| Code | Signification | Quand ? |
|------|---------------|---------|
| `200` | OK | GET, PATCH réussis |
| `201` | Created | POST réussi |
| `204` | No Content | DELETE réussi |
| `400` | Bad Request | Requête malformée |
| `401` | Unauthorized | Token manquant/invalide |
| `403` | Forbidden | Permissions insuffisantes |
| `404` | Not Found | Ressource inexistante |
| `409` | Conflict | Conflit (doublon, état invalide) |
| `422` | Unprocessable Entity | Validation échouée |
| `500` | Internal Server Error | Erreur serveur |

### Format des erreurs

```json
{
  "detail": "Patient 999 non trouvé"
}
```

Ou pour les erreurs de validation :

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 9. Workflows métier

### Workflow d'un plan d'aide

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CYCLE DE VIE D'UN PLAN D'AIDE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌──────────┐                                                      │
│    │  DRAFT   │  Brouillon - Modifiable                              │
│    │ (initial)│                                                      │
│    └────┬─────┘                                                      │
│         │ POST /submit                                               │
│         ▼                                                            │
│    ┌──────────────────┐                                              │
│    │ PENDING_VALIDATION│  En attente de validation                   │
│    └────────┬─────────┘                                              │
│             │ POST /validate                                         │
│             ▼                                                        │
│    ┌──────────┐         POST /suspend         ┌───────────┐          │
│    │  ACTIVE  │ ─────────────────────────────▶│ SUSPENDED │          │
│    │          │◀─────────────────────────────│           │          │
│    └────┬─────┘         POST /reactivate      └───────────┘          │
│         │                                                            │
│         │ POST /complete                                             │
│         ▼                                                            │
│    ┌──────────┐                                                      │
│    │ COMPLETED│  Plan terminé                                        │
│    └──────────┘                                                      │
│                                                                      │
│    À tout moment (sauf COMPLETED) :                                  │
│    POST /cancel → CANCELLED                                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Workflow d'un tenant

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CYCLE DE VIE D'UN TENANT                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌──────────┐                                                      │
│    │ PENDING  │  En attente d'activation                             │
│    │ (initial)│                                                      │
│    └────┬─────┘                                                      │
│         │ POST /activate                                             │
│         ▼                                                            │
│    ┌──────────┐         POST /suspend         ┌───────────┐          │
│    │  ACTIVE  │ ─────────────────────────────▶│ SUSPENDED │          │
│    │          │◀─────────────────────────────│           │          │
│    └────┬─────┘         POST /reactivate      └───────────┘          │
│         │                                                            │
│         │ DELETE (avec confirmation)                                 │
│         ▼                                                            │
│    ┌────────────┐                                                    │
│    │ TERMINATED │  Résilié (soft delete)                             │
│    └────────────┘                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Workflow d'une intervention

```
┌─────────────────────────────────────────────────────────────────────┐
│                  CYCLE DE VIE D'UNE INTERVENTION                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌───────────┐                                                     │
│    │ SCHEDULED │  RDV planifié                                       │
│    │ (initial) │                                                     │
│    └─────┬─────┘                                                     │
│          │ POST /confirm (optionnel)                                 │
│          ▼                                                           │
│    ┌───────────┐                                                     │
│    │ CONFIRMED │  RDV confirmé                                       │
│    └─────┬─────┘                                                     │
│          │ POST /start                                               │
│          ▼                                                           │
│    ┌─────────────┐                                                   │
│    │ IN_PROGRESS │  Intervention en cours                            │
│    └──────┬──────┘                                                   │
│           │ POST /complete                                           │
│           ▼                                                          │
│    ┌───────────┐                                                     │
│    │ COMPLETED │  ✅ Terminé avec succès                             │
│    └───────────┘                                                     │
│                                                                      │
│    Chemins alternatifs :                                             │
│    ─────────────────────                                             │
│    POST /cancel    → CANCELLED   (annulé)                            │
│    POST /missed    → MISSED      (manqué - patient absent)           │
│    POST /reschedule→ RESCHEDULED (reprogrammé → nouveau RDV)         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Workflow de l'affectation d'un service

```
┌─────────────────────────────────────────────────────────────────────┐
│                 AFFECTATION D'UN SERVICE À UN PRO                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    ┌────────────┐                                                    │
│    │ UNASSIGNED │  Service non affecté                               │
│    │  (initial) │                                                    │
│    └─────┬──────┘                                                    │
│          │                                                           │
│          ├──── POST /assign (mode: "assign") ────┐                   │
│          │     Affectation directe               │                   │
│          │                                       ▼                   │
│          │                                 ┌──────────┐              │
│          │                                 │ ASSIGNED │              │
│          │                                 └────┬─────┘              │
│          │                                      │                    │
│          │                                      │ POST /confirm      │
│          │                                      ▼                    │
│          │                                 ┌───────────┐             │
│          │                                 │ CONFIRMED │ ✅          │
│          │                                 └───────────┘             │
│          │                                                           │
│          └──── POST /assign (mode: "propose") ───┐                   │
│                Proposition (attente réponse)     │                   │
│                                                  ▼                   │
│                                            ┌─────────┐               │
│                                            │ PENDING │               │
│                                            └────┬────┘               │
│                                   ┌─────────────┼─────────────┐      │
│                                   │             │             │      │
│                      POST /confirm│             │POST /reject │      │
│                                   ▼             │             ▼      │
│                            ┌───────────┐       │      ┌──────────┐   │
│                            │ CONFIRMED │       │      │ REJECTED │   │
│                            └───────────┘       │      └──────────┘   │
│                                                │                     │
│    DELETE /assign : retour à UNASSIGNED ◀──────┘                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Annexes

### Catégories de services

| Code | Libellé | Exemples |
|------|---------|----------|
| `SOINS` | Soins médicaux | Injection, pansement, surveillance |
| `HYGIENE` | Hygiène | Toilette, habillage |
| `REPAS` | Aide aux repas | Préparation, aide à manger |
| `MOBILITE` | Mobilité | Lever, coucher, déplacement |
| `COURSES` | Courses | Accompagnement courses |
| `MENAGE` | Entretien | Ménage, linge |
| `ADMINISTRATIF` | Administratif | Démarches, papiers |
| `SOCIAL` | Social | Accompagnement, visite |

### Types de constantes vitales

| Code | Libellé | Unité |
|------|---------|-------|
| `FC` | Fréquence cardiaque | bpm |
| `TA_SYS` | Tension systolique | mmHg |
| `TA_DIA` | Tension diastolique | mmHg |
| `SPO2` | Saturation O2 | % |
| `TEMP` | Température | °C |
| `GLYC` | Glycémie | g/L |
| `POIDS` | Poids | kg |
| `DOULEUR` | Échelle douleur | 0-10 |

### Niveaux GIR (grille AGGIR)

| GIR | Niveau de dépendance | Description |
|-----|---------------------|-------------|
| 1 | Très forte | Confiné au lit, fonctions mentales altérées |
| 2 | Forte | Confiné ou fonctions mentales altérées |
| 3 | Moyenne | Autonomie mentale, dépendance corporelle |
| 4 | Modérée | Aide pour toilette, habillage, repas |
| 5 | Légère | Aide ponctuelle |
| 6 | Autonome | Autonome pour actes essentiels |

### Statuts des tenants

| Statut | Description |
|--------|-------------|
| `PENDING` | En attente d'activation |
| `ACTIVE` | Actif - accès complet |
| `SUSPENDED` | Suspendu - accès bloqué, données conservées |
| `TERMINATED` | Résilié - soft delete définitif |

### Rôles SuperAdmin

| Rôle | Niveau | Capacités |
|------|--------|-----------|
| `PLATFORM_OWNER` | 4 | Tous les droits, gestion des autres super-admins |
| `PLATFORM_ADMIN` | 3 | Gestion tenants, audit, affectations |
| `PLATFORM_SUPPORT` | 2 | Consultation seule |
| `PLATFORM_SALES` | 1 | Accès démos uniquement |

### Glossaire

| Terme | Définition |
|-------|------------|
| **SSIAD** | Service de Soins Infirmiers À Domicile |
| **SAAD** | Service d'Aide et d'Accompagnement à Domicile |
| **GCSMS** | Groupement de Coopération Sociale et Médico-Sociale |
| **FINESS** | Fichier National des Établissements Sanitaires et Sociaux |
| **RPPS** | Répertoire Partagé des Professionnels de Santé |
| **NIR** | Numéro d'Inscription au Répertoire (n° Sécu) |
| **INS** | Identifiant National de Santé |
| **GIR** | Groupe Iso-Ressources (niveau de dépendance) |
| **AGGIR** | Autonomie Gérontologie Groupes Iso-Ressources |
| **APA** | Allocation Personnalisée d'Autonomie |
| **PPA** | Plan Personnalisé d'Accompagnement |
| **PPCS** | Plan Personnalisé de Coordination en Santé |
| **Tenant** | Client CareLink (organisation utilisant la plateforme) |
| **SuperAdmin** | Membre de l'équipe CareLink (niveau plateforme) |
| **RLS** | Row-Level Security (isolation des données par tenant) |
| **Cross-tenant** | Accès d'un utilisateur à plusieurs organisations |

---

## Historique du document

| Version | Date | Auteur | Modifications |
|---------|------|--------|---------------|
| 1.0 | Janvier 2025 | Équipe CareLink | Création initiale |
| 1.1 | Janvier 2026 | Équipe CareLink | Ajout modules Platform et Tenants, restructuration sécurité (451 tests), architecture multi-tenant |

---

*Documentation générée pour CareLink - Plateforme de coordination médico-sociale*
