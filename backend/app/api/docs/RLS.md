
Cas à traiter:
Si un professionnel de santé doit intervenir sur deux tenants différents de façon temporaire, alors il sera créé dans deux tables différentes avec bien entendu des données identiques à part le tenant_id.
Mais, quand même, est ce que cette situation ne comprend un risque de confusion que RLS pourrait neutraliser ?


- Le problème sans RLS
Prenons ton exemple concret :
Sophie Martin, IDE, travaille temporairement pour 2 structures :

┌─────────────────────────────┐     ┌─────────────────────────────┐
│      TENANT A (id=1)        │     │      TENANT B (id=2)        │
│   GCSMS Île-de-France       │     │      SSIAD Lyon             │
├─────────────────────────────┤     ├─────────────────────────────┤
│ users:                      │     │ users:                      │
│   id=10, Sophie Martin      │     │   id=45, Sophie Martin      │
│   tenant_id=1               │     │   tenant_id=2               │
│   rpps=12345678901          │     │   rpps=12345678901          │
│                             │     │                             │
│ patients: 2800              │     │ patients: 120               │
└─────────────────────────────┘     └─────────────────────────────┘

- Risques SANS RLS (isolation applicative uniquement)

| Risque                 | Scénario                                                      | Gravité  |
|------------------------|---------------------------------------------------------------|----------|
| Bug de code            | Un développeur oublie .filter(tenant_id=X) dans une requête   | Critique |
| Injection de paramètre | Requête malveillante : GET /patients?tenant_id=2              | Critique |
| Erreur de session      | Mauvaise gestion du contexte JWT après switch de tenant       | Élevée   |
| Jointure non filtrée   | SELECT * FROM patients JOIN entities ON... sans clause tenant | Critique |


- Exemple de bug typique :
# ❌ DANGEREUX - Oubli du filtre tenant
def get_all_patients_by_city(db: Session, city: str):
    return db.query(Patient).filter(Patient.city == city).all()
    # Retourne TOUS les patients de Lyon, tous tenants confondus !
```

## RLS : le filet de sécurité au niveau PostgreSQL
```
┌─────────────────────────────────────────────────────────────────────┐
│                        AVEC RLS ACTIVÉ                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Application FastAPI                                               │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Sophie se connecte → JWT contient tenant_id=1              │   │
│   │  SET app.current_tenant_id = '1'                            │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Code bugué : SELECT * FROM patients WHERE city='Lyon'      │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  PostgreSQL RLS POLICY automatiquement appliquée :          │   │
│   │  SELECT * FROM patients                                     │   │
│   │  WHERE city='Lyon'                                          │   │
│   │  AND tenant_id = current_setting('app.current_tenant_id')   │   │
│   │  ───────────────────────────────────────────────────────    │   │
│   │  → Résultat : 0 patients (aucun patient Lyon dans tenant 1) │   │
│   │  → Les 120 patients du SSIAD Lyon (tenant 2) sont PROTÉGÉS  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘


- Row Level Security (RLS)
Le problème à résoudre
Dans une architecture multi-tenant comme celle de CareLink, il y a plusieurs organisations (tenants) qui partagent les mêmes tables de base de données. 
Le défi est de garantir qu'un utilisateur d'une organisation A ne puisse jamais voir ou modifier les données d'une organisation B, même en cas de bug applicatif ou de requête mal construite.
Traditionnellement, cette sécurité est gérée au niveau applicatif : chaque requête SQL inclut un filtre WHERE tenant_id = :current_tenant. 
Mais c'est fragile — il suffit d'oublier ce filtre une seule fois pour créer une fuite de données.

- Le principe du RLS
Row Level Security est une fonctionnalité native de PostgreSQL (et d'autres SGBD) qui déplace cette sécurité au niveau de la base de données elle-même. 
On définit des policies qui filtrent automatiquement les lignes auxquelles un utilisateur peut accéder, indépendamment de la requête envoyée.
Concrètement, même si l' application envoie un SELECT * FROM patients sans filtre, PostgreSQL n'affichera que les lignes autorisées par la policy.


- Comment ça fonctionne
L'implémentation se fait en trois étapes :
1. Activer le RLS sur une table
sqlALTER TABLE patients ENABLE ROW LEVEL SECURITY;
2. Définir une policy
sqlCREATE POLICY tenant_isolation ON patients
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
3. Définir le contexte à chaque connexion
sqlSET app.current_tenant = 'uuid-du-tenant';
À partir de là, toutes les opérations (SELECT, INSERT, UPDATE, DELETE) sont automatiquement filtrées. Un SELECT * ne retournera que les lignes du tenant courant, et un INSERT avec un mauvais tenant_id sera refusé.

