# Objectifs de la section app/database/

## 1. base.py - Classe de base et imports centralisés

### Objectifs :

- ✅ Créer la classe Base SQLAlchemy (point central pour tous les modèles)
- ✅ Importer tous les modèles au même endroit (essentiel pour Alembic/migrations)
- ✅ Garantir que SQLAlchemy connaît toutes les relations entre tables

### Pourquoi c'est important ?

```python
# Sans base.py centralisé
from app.models.user import User  # ❌ Relation avec Role inconnue
from app.models.role import Role  # ❌ Relation avec User inconnue

# Avec base.py
from app.database.base import Base  # ✅ Tous les modèles chargés
# → SQLAlchemy connaît TOUTES les relations
```

---

## 2. session.py - Connexion PostgreSQL et gestion de sessions

### Objectifs :

- ✅ Configurer la connexion à PostgreSQL
- ✅ Créer le SessionLocal (factory pour créer des sessions DB)
- ✅ Fournir get_db() (dependency FastAPI pour injection de session)
- ✅ Gérer proprement l'ouverture/fermeture des connexions
- ✅ **Supporter le multi-tenant via tenant_session()** (v4.1)

### Ce que ça fait concrètement :

```python
# Connexion PostgreSQL
DATABASE_URL = "postgresql://carelink:password@localhost:5432/carelink_db"
engine = create_engine(DATABASE_URL)

# Factory de sessions
SessionLocal = sessionmaker(bind=engine)

# Dependency FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db  # Fournit la session à la route
    finally:
        db.close()  # Ferme proprement la connexion

# Utilisation dans une route
@app.get("/patients/{id}")
def get_patient(id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == id).first()
    return patient
```

### Multi-tenant (v4.1) :

```python
# Context manager pour sessions avec isolation tenant
@contextmanager
def tenant_session(db: Session, tenant_id: int):
    """Configure le tenant pour la session (Row-Level Security)."""
    try:
        db.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
        yield db
    finally:
        db.execute(text("RESET app.current_tenant_id"))

# Dependency FastAPI avec tenant
def get_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Session:
    """Injecte une session avec le bon tenant."""
    db.execute(text(f"SET app.current_tenant_id = '{current_user.tenant_id}'"))
    return db
```

---

## 3. init_db.py - Initialisation de la base de données

### Objectifs :

- ✅ Créer toutes les tables
- ✅ Insérer les données de référence (pays, professions)
- ✅ Créer les rôles système (ADMIN, COORDINATEUR, etc.)
- ✅ **Créer un tenant par défaut** (v4.1)
- ✅ Créer un compte admin par défaut
- ✅ Script exécutable en ligne de commande

### Ordre d'exécution :

```
1. create_all_tables()
   └─> tenants, subscriptions, subscription_usage (v4.1)
   └─> countries, professions
   └─> entities, users, roles
   └─> patients, care_plans, etc.

2. init_reference_data()
   └─> Pays (France, Belgique, Suisse...)
   └─> Professions (Infirmier, Aide-soignant...)
   └─> Service templates (catalogue national)

3. init_default_tenant() (v4.1)
   └─> Tenant par défaut pour développement
   └─> Subscription d'essai

4. init_roles()
   └─> ADMIN, COORDINATEUR, INTERVENANT, ...

5. init_default_admin()
   └─> admin@carelink.fr
   └─> Rôle ADMIN
   └─> Rattaché au tenant par défaut
```

---

## 📊 Schéma d'ensemble (v4.1)

```
┌─────────────────────────────────────────────────────────────┐
│                     app/database/                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  base.py                                                    │
│  ├─> Importe tous les modèles                              │
│  ├─> Crée Base SQLAlchemy                                  │
│  └─> Expose metadata pour migrations                       │
│                                                             │
│  session.py                                                 │
│  ├─> Configure engine PostgreSQL                           │
│  ├─> Crée SessionLocal (factory)                           │
│  ├─> Fournit get_db() pour FastAPI                         │
│  └─> Fournit get_tenant_db() pour multi-tenant (v4.1)      │
│                                                             │
│  init_db.py                                                 │
│  ├─> create_all_tables()                                   │
│  ├─> init_reference_data() ──> pays, professions           │
│  ├─> init_default_tenant() ──> tenant dev (v4.1)           │
│  ├─> init_roles() ──> rôles système                        │
│  └─> init_default_admin() ──> admin@carelink.fr            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      PostgreSQL                             │
│  carelink_db                                                │
│                                                             │
│  MODULE TENANT (v4.1)                                       │
│  ├─> tenants                                                │
│  ├─> subscriptions                                          │
│  └─> subscription_usage                                     │
│                                                             │
│  MODULE REFERENCE                                           │
│  └─> countries                                              │
│                                                             │
│  MODULE ORGANIZATION                                        │
│  └─> entities (+ tenant_id)                                 │
│                                                             │
│  MODULE USER                                                │
│  ├─> professions                                            │
│  ├─> roles                                                  │
│  ├─> users (+ tenant_id)                                    │
│  ├─> user_roles                                             │
│  ├─> user_entities                                          │
│  └─> user_availabilities                                    │
│                                                             │
│  MODULE PATIENT                                             │
│  ├─> patients (+ tenant_id)                                 │
│  ├─> patient_access                                         │
│  ├─> patient_evaluations                                    │
│  ├─> patient_thresholds                                     │
│  ├─> patient_devices                                        │
│  ├─> patient_vitals                                         │
│  └─> patient_documents                                      │
│                                                             │
│  MODULE CATALOG                                             │
│  ├─> service_templates                                      │
│  └─> entity_services                                        │
│                                                             │
│  MODULE CAREPLAN                                            │
│  ├─> care_plans                                             │
│  └─> care_plan_services                                     │
│                                                             │
│  MODULE COORDINATION                                        │
│  ├─> scheduled_interventions                                │
│  └─> coordination_entries                                   │
│                                                             │
│  TOTAL: 24 tables (v4.1)                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Statistiques du schéma v4.1

| Métrique | v4.0 | v4.1 | Différence |
|----------|------|------|------------|
| Tables | 21 | 24 | +3 |
| Enums | 21 | 26 | +5 |
| Modules | 6 | 7 | +1 |

### Nouvelles tables (v4.1)

| Table | Description |
|-------|-------------|
| `tenants` | Clients/locataires de CareLink |
| `subscriptions` | Abonnements et plans tarifaires |
| `subscription_usage` | Suivi consommation mensuelle |

### Nouveaux enums (v4.1)

| Enum | Valeurs |
|------|---------|
| `tenant_type_enum` | GCSMS, SSIAD, SAAD, SPASAD, EHPAD, DAC, CPTS, OTHER |
| `tenant_status_enum` | ACTIVE, SUSPENDED, TERMINATED |
| `subscription_plan_enum` | S, M, L, XL, ENTERPRISE |
| `subscription_status_enum` | TRIAL, ACTIVE, PAST_DUE, CANCELLED |
| `billing_cycle_enum` | MONTHLY, QUARTERLY, YEARLY |

### Tables modifiées (v4.1)

| Table | Modification |
|-------|--------------|
| `entities` | Ajout `tenant_id` (FK → tenants) |
| `users` | Ajout `tenant_id` (FK → tenants) |
| `patients` | Ajout `tenant_id` (FK → tenants) |

---

## 🔐 Architecture Multi-Tenant (v4.1)

### Principe d'isolation

```
┌─────────────────────────────────────────────────────────────┐
│                    INSTANCE FRANCE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DONNÉES PARTAGÉES (niveau instance)                        │
│  ├─> countries (référentiel pays)                           │
│  ├─> professions (référentiel RPPS)                         │
│  └─> service_templates (catalogue national)                 │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   TENANT A      │  │   TENANT B      │                  │
│  │   GCSMS IDF     │  │   SSIAD Lyon    │                  │
│  │   ───────────   │  │   ───────────   │                  │
│  │   🔐 Clé AES A  │  │   🔐 Clé AES B  │                  │
│  │                 │  │                 │                  │
│  │   entities      │  │   entities      │                  │
│  │   users         │  │   users         │                  │
│  │   patients      │  │   patients      │                  │
│  │   care_plans    │  │   care_plans    │                  │
│  │   ...           │  │   ...           │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  Isolation garantie par :                                   │
│  1. Colonne tenant_id sur tables principales               │
│  2. Row-Level Security PostgreSQL                          │
│  3. Clé de chiffrement AES par tenant                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Row-Level Security (RLS)

```sql
-- Activer RLS sur les tables principales
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;

-- Politique d'isolation
CREATE POLICY tenant_isolation ON entities
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
```

---

## 🚀 Flux d'utilisation typique

### 1. Créer la base PostgreSQL
```bash
createdb carelink_db
```

### 2. Initialiser les tables et données
```bash
python -m app.database.init_db
```

### 3. Appliquer les migrations
```bash
alembic upgrade head
```

### 4. Démarrer l'application
```bash
uvicorn app.main:app --reload
```

---

## 📁 Structure des modèles

```
app/models/
├── __init__.py              # Exports centralisés
├── mixins.py                # TimestampMixin, AuditMixin, TenantMixin
├── enums.py                 # Tous les enums
├── types.py                 # Types personnalisés (JSONBCompatible)
│
├── tenants/                 # MODULE TENANT (v4.1)
│   ├── __init__.py
│   ├── tenant.py            # Tenant, TenantStatus, TenantType
│   ├── subscription.py      # Subscription, plans, cycles
│   └── subscription_usage.py # SubscriptionUsage
│
├── reference/               # MODULE REFERENCE
│   └── country.py
│
├── organization/            # MODULE ORGANIZATION
│   └── entity.py
│
├── user/                    # MODULE USER
│   ├── profession.py
│   ├── role.py
│   ├── user.py
│   ├── user_associations.py # UserRole, UserEntity
│   └── user_availability.py
│
├── patient/                 # MODULE PATIENT
│   ├── patient.py
│   ├── patient_access.py
│   ├── patient_evaluation.py
│   ├── patient_vitals.py
│   └── patient_document.py
│
├── catalog/                 # MODULE CATALOG
│   ├── service_template.py
│   └── entity_service.py
│
├── careplan/                # MODULE CAREPLAN
│   ├── care_plan.py
│   └── care_plan_service.py
│
└── coordination/            # MODULE COORDINATION
    ├── scheduled_intervention.py
    └── coordination_entry.py
```

---

## ⚠️ Notes importantes

### Imports et # noqa: F401

Les imports dans base.py incluent `# noqa: F401` :
```python
from app.models.user import User  # noqa: F401
```

**Pourquoi ?**
- Les linters détectent des imports "inutilisés"
- Ces imports SONT utilisés par SQLAlchemy en arrière-plan
- `# noqa: F401` dit au linter : "Ignore cet avertissement"

### Sécurité Multi-Tenant

- **Ne jamais exposer tenant_id** dans les réponses API publiques
- **Toujours valider** que l'utilisateur appartient au tenant
- **Utiliser get_tenant_db()** pour toutes les requêtes avec données tenant
- **Clés de chiffrement** : Une clé AES différente par tenant (stockée dans vault)

### Compatibilité

- **SQLite** : Pour les tests, utiliser JSONBCompatible au lieu de JSONB natif
- **PostgreSQL** : Row-Level Security disponible uniquement en PostgreSQL

# Notes
Je comprends que `superuser` et `carelink_app`sont des types de connexion (avec droits plus ou moins étendus) à la base.
Mais du mal à comprendre car je ne connais pas particulièrement le fonctionnement Des bases de données et les modes de connexion à mettre en place pour qu'une application puisse accéder à une base PostgreSQL.

Peux tu m'expliquer ça de façon synthétique et de façon imagée ?

Comment une application se connecte à PostgreSQL
Analogie : L'immeuble de bureaux
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  🏢 IMMEUBLE = Base de données PostgreSQL                          │
│  📁 BUREAUX = Tables (patients, users, entities...)                │
│  📄 DOSSIERS = Données dans les tables                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
Pour entrer dans l'immeuble, il faut un BADGE
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  Ton application CareLink veut lire/écrire dans PostgreSQL         │
│                                                                     │
│  Elle doit montrer patte blanche :                                  │
│                                                                     │
│     DATABASE_URL = postgresql://QUI:MOT_DE_PASSE@OU/QUELLE_BASE    │
│                                 ───  ────────────                   │
│                                  │        │                         │
│                                  │        └─ Mot de passe du badge  │
│                                  │                                  │
│                                  └─ Nom sur le badge                │
│                                     (= rôle PostgreSQL)             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
Il existe 2 types de badges
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  🔴 BADGE ROUGE : "postgres" (superuser)                           │
│  ───────────────────────────────────────                            │
│                                                                     │
│     • Ouvre TOUTES les portes                                       │
│     • Peut casser les murs (modifier la structure)                  │
│     • Peut créer d'autres badges                                    │
│     • Les alarmes sont DÉSACTIVÉES pour lui                         │
│       (RLS ignoré = voit toutes les données)                        │
│                                                                     │
│     → C'est le badge du propriétaire de l'immeuble                 │
│     → Créé automatiquement quand tu installes PostgreSQL           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🟢 BADGE VERT : "carelink_app" (rôle applicatif)                  │
│  ────────────────────────────────────────────────                   │
│                                                                     │
│     • Ouvre uniquement les portes autorisées                        │
│     • Ne peut PAS casser les murs                                   │
│     • Ne peut PAS créer d'autres badges                             │
│     • Les alarmes FONCTIONNENT pour lui                             │
│       (RLS actif = voit seulement son étage/tenant)                │
│                                                                     │
│     → C'est le badge qu'on crée pour l'application                 │
│     → Doit être créé manuellement (c'est ce qui a planté)          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
Ce qui se passe aujourd'hui chez toi
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  SITUATION ACTUELLE (développement)                                 │
│  ──────────────────────────────────                                 │
│                                                                     │
│  Ton .env contient probablement :                                   │
│                                                                     │
│     DATABASE_URL=postgresql://postgres:xxx@localhost/carelink_db   │
│                               ────────                              │
│                               Badge rouge (superuser)               │
│                                                                     │
│  → Ça marche pour développer                                       │
│  → Mais le RLS est ignoré (pas de vraie isolation)                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SITUATION IDÉALE (production)                                      │
│  ─────────────────────────────                                      │
│                                                                     │
│  Le .env devrait contenir :                                         │
│                                                                     │
│     DATABASE_URL=postgresql://carelink_app:xxx@localhost/carelink  │
│                               ────────────                          │
│                               Badge vert (rôle limité)              │
│                                                                     │
│  → L'application a les droits minimum                              │
│  → Le RLS est appliqué (vraie isolation)                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
Pourquoi la migration a planté ?
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  La migration essayait de faire :                                   │
│                                                                     │
│     "Créer un nouveau badge vert (carelink_app)"                   │
│                                                                     │
│  Mais ton badge actuel (probablement pas superuser complet)        │
│  n'a pas le droit de créer d'autres badges !                       │
│                                                                     │
│  C'est comme si un employé essayait de fabriquer                   │
│  un badge pour un collègue → Refusé par la sécurité               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
Résumé en une image
                     🏢 PostgreSQL (l'immeuble)
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
     🔴 postgres        🟢 carelink_app    🟢 autres apps
     (superuser)        (ton appli)        (si besoin)
            │                 │
            │                 │
    Utilisé pour:      Utilisé pour:
    • Migrations       • L'application
    • Maintenance        au quotidien
    • Urgences         • RLS actif
Ce qu'il faut faire
Option A : Simple (pour continuer en dev)

Commenter le code qui crée le badge vert
Continuer avec le badge rouge (superuser)
Le RLS existe mais est ignoré

Option B : Propre (recommandé)

Créer manuellement le badge vert une seule fois
Configurer l'application pour l'utiliser
Le RLS fonctionne vraiment

# Commandes utliles.
Résumé des connexions
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  🔴 SUPERUSER (odb_admin_1) - Pour développer                      │
│  ─────────────────────────────────────────────                      │
│                                                                     │
│  Utilisation :                                                      │
│  • Migrations Alembic                                               │
│  • Modifier la structure (CREATE TABLE, ALTER...)                  │
│  • Maintenance, debug                                               │
│  • Insérer des données de test (bypass RLS)                        │
│                                                                     │
│  Commande :                                                         │
│  psql -d carelink_db                                               │
│  (utilise ton user macOS par défaut = odb_admin_1)                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🟢 APPLICATIF (carelink) - Pour tester comme l'app               │
│  ──────────────────────────────────────────────────                 │
│                                                                     │
│  Utilisation :                                                      │
│  • Tester le RLS                                                    │
│  • Simuler ce que voit l'application                               │
│  • Vérifier l'isolation des données                                │
│                                                                     │
│  Commande :                                                         │
│  psql -U carelink -d carelink_db                                   │
│       ───────────                                                   │
│       Spécifie le rôle                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
En pratique
TâcheCommandeMigration Alembicalembic upgrade head (utilise superuser via ton .env actuel)Créer des tablespsql -d carelink_dbInsérer données testpsql -d carelink_dbTester le RLSpsql -U carelink -d carelink_dbLancer l'applicationuvicorn app.main:app (utilise carelink via DATABASE_URL)
Astuce : Créer des alias
Ajoute dans ton ~/.zshrc ou ~/.bashrc :
bash# Alias pour connexion PostgreSQL CareLink
alias psql-admin='psql -d carelink_db'                    # Superuser
alias psql-app='psql -U carelink -d carelink_db'          # Comme l'application
Puis recharge :
bashsource ~/.zshrc
Après ça :
bashpsql-admin    # → Connexion superuser (développement)
psql-app      # → Connexion applicative (test RLS)
```

## Important à retenir
```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  Ton application FastAPI utilise TOUJOURS "carelink"               │
│  (défini dans DATABASE_URL de ton .env)                            │
│                                                                     │
│  → Le RLS est TOUJOURS appliqué en production                      │
│  → Même si toi tu développes en superuser                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘


L'URL n'est pas un "propriétaire", c'est une carte d'accès
postgresql://carelink:Fer458it@localhost:5432/carelink_db
             └──────────────┘
             Badge d'entrée : "Je suis carelink, mon code est Fer458it"

PostgreSQL = L'immeuble
├── postgres (super-admin) = Le syndic, peut tout faire
├── carelink (utilisateur) = Un locataire avec les clés de son appart
└── carelink_db (base) = L'appartement

L'appartement a été créé PAR le syndic (postgres)
→ Le syndic reste propriétaire
→ carelink a juste le droit d'y habiter

## Comment voir qui est propriétaire ?
PGPASSWORD=Fer458it psql -U carelink -d carelink_db -c "\l"

### Résultat de cette instruction:
(env) odb_admin_1@admin-odbs-MacBook-Air CareLink % PGPASSWORD=Fer458it psql -U carelink -d carelink_db -c "\l"
                                       List of databases
    Name     |    Owner    | Encoding |   Collate   |    Ctype    |      Access privileges      
-------------+-------------+----------+-------------+-------------+-----------------------------
 carelink_db | odb_admin_1 | UTF8     | en_US.UTF-8 | en_US.UTF-8 | 
 postgres    | odb_admin_1 | UTF8     | en_US.UTF-8 | en_US.UTF-8 | 
 template0   | odb_admin_1 | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/odb_admin_1             +
             |             |          |             |             | odb_admin_1=CTc/odb_admin_1
 template1   | odb_admin_1 | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/odb_admin_1             +
             |             |          |             |             | odb_admin_1=CTc/odb_admin_1
(4 rows)

### Ce que montre \l : les BASES DE DONNÉES
    Name     |    Owner    
-------------+-------------
 carelink_db | odb_admin_1   ← Base "carelink_db", appartient à odb_admin_1
 postgres    | odb_admin_1   ← Base "postgres", appartient à odb_admin_1
 template0   | odb_admin_1   ← Base "template0", appartient à odb_admin_1
 template1   | odb_admin_1   ← Base "template1", appartient à odb_admin_1
C'est comme lister des appartements et leur propriétaire.


### Pour voir les utilisateurs PostgreSQL, il faut une autre commande :
psql -d carelink_db -c "\du"


(env) odb_admin_1@admin-odbs-MacBook-Air CareLink % psql -d carelink_db -c "\du"
                                    List of roles
  Role name  |                         Attributes                         | Member of 
-------------+------------------------------------------------------------+-----------
 carelink    |                                                            | {}
 odb_admin_1 | Superuser, Create role, Create DB, Replication, Bypass RLS | {}


### Schéma
```
PostgreSQL sur ton Mac
│
├── UTILISATEURS (qui peut se connecter)
│   ├── odb_admin_1  → Super-admin (peut tout faire)
│   └── carelink     → Utilisateur limité (pour l'application)
│
└── BASES DE DONNÉES (conteneurs de données)
    ├── carelink_db  → Propriétaire: odb_admin_1
    ├── postgres     → Propriétaire: odb_admin_1
    └── templates... → Propriétaire: odb_admin_1
```

### Analogie 
```
PostgreSQL = Un immeuble de bureaux

UTILISATEURS = Les personnes avec un badge
├── odb_admin_1 = Le directeur (accès partout, peut démolir)
└── carelink = Un employé (accès limité à son bureau)

BASES DE DONNÉES = Les bureaux
├── carelink_db = Bureau principal (propriété du directeur)
└── postgres = Bureau admin (propriété du directeur)
L'employé carelink a les clés du bureau carelink_db pour y travailler, mais c'est le directeur odb_admin_1 qui peut supprimer le bureau.















